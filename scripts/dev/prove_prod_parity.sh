#!/bin/bash
# =============================================================================
# PROD-PARITY PROOF HARNESS
# =============================================================================
# Runs tests against real Render backend and generates proof bundle.
#
# Usage:
#   ./scripts/dev/prove_prod_parity.sh          # Full run
#   ./scripts/dev/prove_prod_parity.sh --local  # Local mode only
#   ./scripts/dev/prove_prod_parity.sh --record # Record new cassettes
#
# Output:
#   proof/<timestamp>/
#     cassettes/          - Request/response recordings
#     screenshots/        - UI state captures
#     schema_validation/  - Schema check results
#     summary.json        - Overall results
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PROOF_DIR="$PROJECT_ROOT/proof/$TIMESTAMP"

# Parse arguments
MODE="remote"
RECORD="1"
while [[ $# -gt 0 ]]; do
    case $1 in
        --local)
            MODE="local"
            shift
            ;;
        --replay)
            MODE="replay"
            RECORD="0"
            shift
            ;;
        --record)
            RECORD="1"
            shift
            ;;
        *)
            shift
            ;;
    esac
done

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE} PROD-PARITY PROOF HARNESS${NC}"
echo -e "${BLUE}============================================${NC}"
echo -e "Mode: ${YELLOW}$MODE${NC}"
echo -e "Record: ${YELLOW}$RECORD${NC}"
echo -e "Proof Dir: ${YELLOW}$PROOF_DIR${NC}"
echo ""

# Create proof directory structure
mkdir -p "$PROOF_DIR/cassettes"
mkdir -p "$PROOF_DIR/screenshots"
mkdir -p "$PROOF_DIR/schema_validation"

# Export environment for API
export PIPELINE_MODE="$MODE"
export PIPELINE_RECORD="$RECORD"
export PIPELINE_REPLAY_DIR="$PROOF_DIR/cassettes"
export PIPELINE_REMOTE_URL="${PIPELINE_REMOTE_URL:-https://cloud-pms.onrender.com/search}"

# =============================================================================
# Step 1: Check Render backend health (if remote mode)
# =============================================================================
if [ "$MODE" = "remote" ]; then
    echo -e "${BLUE}[1/5] Checking Render backend health...${NC}"

    RENDER_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "$PIPELINE_REMOTE_URL" -X POST \
        -H "Content-Type: application/json" \
        -d '{"query": "health check", "context": {}}' 2>/dev/null || echo "000")

    if [ "$RENDER_HEALTH" = "000" ]; then
        echo -e "${RED}✗ Render backend unreachable${NC}"
        echo -e "${YELLOW}  URL: $PIPELINE_REMOTE_URL${NC}"
        echo -e "${YELLOW}  Check deployment status at: https://dashboard.render.com${NC}"
        exit 1
    elif [ "$RENDER_HEALTH" = "500" ] || [ "$RENDER_HEALTH" = "502" ]; then
        echo -e "${RED}✗ Render backend error (HTTP $RENDER_HEALTH)${NC}"
        echo -e "${YELLOW}  This may indicate deployment failure${NC}"
        exit 1
    else
        echo -e "${GREEN}✓ Render backend responding (HTTP $RENDER_HEALTH)${NC}"
    fi
else
    echo -e "${BLUE}[1/5] Skipping Render check (mode=$MODE)${NC}"
fi

# =============================================================================
# Step 2: Start local services
# =============================================================================
echo -e "${BLUE}[2/5] Starting local services...${NC}"

# Check if Supabase is running
if ! curl -s http://127.0.0.1:54321/rest/v1/ > /dev/null 2>&1; then
    echo -e "${YELLOW}  Starting Supabase...${NC}"
    cd "$PROJECT_ROOT" && supabase start > /dev/null 2>&1 &
    sleep 10
fi

# Check if API is running on port 8000
if ! curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo -e "${YELLOW}  Starting API server...${NC}"
    cd "$PROJECT_ROOT/apps/api" && uvicorn microaction_service:app --host 0.0.0.0 --port 8000 > "$PROOF_DIR/api.log" 2>&1 &
    API_PID=$!
    echo $API_PID > "$PROOF_DIR/api.pid"
    sleep 5
fi

# Check API health
if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API server running${NC}"
else
    echo -e "${RED}✗ API server failed to start${NC}"
    exit 1
fi

# =============================================================================
# Step 3: Run query contract tests
# =============================================================================
echo -e "${BLUE}[3/5] Running query contract tests...${NC}"

# Canonical queries to test
QUERIES=(
    "show inventory box 2d"
    "overdue work orders"
    "generator manual"
    "low stock parts"
    "recent faults"
)

PASSED=0
FAILED=0
RESULTS=()

for QUERY in "${QUERIES[@]}"; do
    echo -n "  Testing: '$QUERY'... "

    # Call pipeline gateway
    RESPONSE=$(curl -s -X POST "http://127.0.0.1:8000/api/pipeline/execute" \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$QUERY\", \"context\": {\"yacht_id\": \"aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa\"}}")

    # Check for success
    SUCCESS=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('success', False))" 2>/dev/null || echo "False")

    # Check for schema errors
    SCHEMA_ERRORS=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('_schema_errors', [])))" 2>/dev/null || echo "0")

    # Save response
    QUERY_SLUG=$(echo "$QUERY" | tr ' ' '_' | tr -cd '[:alnum:]_')
    echo "$RESPONSE" | python3 -m json.tool > "$PROOF_DIR/cassettes/${QUERY_SLUG}_response.json" 2>/dev/null || echo "$RESPONSE" > "$PROOF_DIR/cassettes/${QUERY_SLUG}_response.json"

    if [ "$SUCCESS" = "True" ] && [ "$SCHEMA_ERRORS" = "0" ]; then
        echo -e "${GREEN}PASS${NC}"
        ((PASSED++))
        RESULTS+=("{\"query\": \"$QUERY\", \"status\": \"pass\"}")
    else
        echo -e "${RED}FAIL${NC}"
        ((FAILED++))
        RESULTS+=("{\"query\": \"$QUERY\", \"status\": \"fail\", \"schema_errors\": $SCHEMA_ERRORS}")
    fi
done

echo ""
echo -e "Results: ${GREEN}$PASSED passed${NC}, ${RED}$FAILED failed${NC}"

# =============================================================================
# Step 4: Schema validation summary
# =============================================================================
echo -e "${BLUE}[4/5] Generating schema validation report...${NC}"

cat > "$PROOF_DIR/schema_validation/report.json" << EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "mode": "$MODE",
    "queries_tested": ${#QUERIES[@]},
    "passed": $PASSED,
    "failed": $FAILED,
    "results": [$(IFS=,; echo "${RESULTS[*]}")]
}
EOF

echo -e "${GREEN}✓ Schema validation report saved${NC}"

# =============================================================================
# Step 5: Generate summary
# =============================================================================
echo -e "${BLUE}[5/5] Generating proof summary...${NC}"

cat > "$PROOF_DIR/summary.json" << EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "proof_id": "$TIMESTAMP",
    "mode": "$MODE",
    "pipeline_remote_url": "$PIPELINE_REMOTE_URL",
    "tests": {
        "total": ${#QUERIES[@]},
        "passed": $PASSED,
        "failed": $FAILED
    },
    "services": {
        "supabase": "local",
        "api": "local:8000",
        "pipeline": "$MODE"
    },
    "artifacts": {
        "cassettes": "$PROOF_DIR/cassettes",
        "screenshots": "$PROOF_DIR/screenshots",
        "schema_validation": "$PROOF_DIR/schema_validation"
    }
}
EOF

# =============================================================================
# Summary
# =============================================================================
echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE} PROOF BUNDLE GENERATED${NC}"
echo -e "${BLUE}============================================${NC}"
echo -e "Location: ${GREEN}$PROOF_DIR${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
    exit 0
else
    echo -e "${RED}✗ $FAILED TESTS FAILED${NC}"
    echo -e "${YELLOW}Review: $PROOF_DIR/schema_validation/report.json${NC}"
    exit 1
fi
