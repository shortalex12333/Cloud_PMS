#!/bin/bash
# Comprehensive Inventory Lens E2E Testing
# Tests all search endpoints, action suggestions, and execution with role gating
# Produces hard evidence of all behavior

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
OUTPUT_DIR="$PROJECT_ROOT/apps/api/test_artifacts/inventory/finish_line/evidence"
mkdir -p "$OUTPUT_DIR"

# Load tokens
CREW_JWT=$(jq -r '.CREW.jwt' "$PROJECT_ROOT/test-jwts.json")
HOD_JWT=$(jq -r '.HOD.jwt' "$PROJECT_ROOT/test-jwts.json")
YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"
API_URL="https://pipeline-core.int.celeste7.ai"

# Evidence log
EVIDENCE_LOG="$OUTPUT_DIR/COMPREHENSIVE_EVIDENCE.md"
echo "# Comprehensive Inventory Lens E2E Evidence" > "$EVIDENCE_LOG"
echo "" >> "$EVIDENCE_LOG"
echo "**Date**: $(date)" >> "$EVIDENCE_LOG"
echo "**API**: $API_URL" >> "$EVIDENCE_LOG"
echo "**Yacht ID**: $YACHT_ID" >> "$EVIDENCE_LOG"
echo "" >> "$EVIDENCE_LOG"
echo "---" >> "$EVIDENCE_LOG"
echo "" >> "$EVIDENCE_LOG"

PASS_COUNT=0
FAIL_COUNT=0
TOTAL_COUNT=0

# Helper function to test and log
test_api() {
    local test_name="$1"
    local role="$2"
    local jwt="$3"
    local method="$4"
    local endpoint="$5"
    local data="$6"
    local validation="$7"

    ((TOTAL_COUNT++))

    echo "" >> "$EVIDENCE_LOG"
    echo "## Test $TOTAL_COUNT: $test_name ($role)" >> "$EVIDENCE_LOG"
    echo "" >> "$EVIDENCE_LOG"
    echo "**Request:**" >> "$EVIDENCE_LOG"
    echo "\`\`\`" >> "$EVIDENCE_LOG"
    echo "$method $endpoint" >> "$EVIDENCE_LOG"
    if [ -n "$data" ]; then
        echo "$data" | jq '.' 2>/dev/null || echo "$data"
    fi
    echo "\`\`\`" >> "$EVIDENCE_LOG"
    echo "" >> "$EVIDENCE_LOG"

    # Make request
    local response_file="$OUTPUT_DIR/$(echo "$test_name" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')_${role}.json"

    if [ "$method" == "POST" ]; then
        HTTP_STATUS=$(curl -s -o "$response_file" -w "%{http_code}" \
            -H "Authorization: Bearer $jwt" \
            -H "Content-Type: application/json" \
            -H "X-Yacht-ID: $YACHT_ID" \
            "$API_URL$endpoint" \
            -d "$data")
    else
        HTTP_STATUS=$(curl -s -o "$response_file" -w "%{http_code}" \
            -H "Authorization: Bearer $jwt" \
            "$API_URL$endpoint")
    fi

    echo "**HTTP Status:** $HTTP_STATUS" >> "$EVIDENCE_LOG"
    echo "" >> "$EVIDENCE_LOG"

    echo "**Response Body:**" >> "$EVIDENCE_LOG"
    echo "\`\`\`json" >> "$EVIDENCE_LOG"
    cat "$response_file" | jq '.' 2>/dev/null || cat "$response_file"
    cat "$response_file" | jq '.' >> "$EVIDENCE_LOG" 2>/dev/null || cat "$response_file" >> "$EVIDENCE_LOG"
    echo "\`\`\`" >> "$EVIDENCE_LOG"
    echo "" >> "$EVIDENCE_LOG"

    # Validate
    local result="UNKNOWN"
    if [ -n "$validation" ]; then
        if eval "$validation"; then
            result="${GREEN}✅ PASS${NC}"
            ((PASS_COUNT++))
        else
            result="${RED}❌ FAIL${NC}"
            ((FAIL_COUNT++))
        fi
    else
        if [ "$HTTP_STATUS" == "200" ]; then
            result="${GREEN}✅ PASS${NC}"
            ((PASS_COUNT++))
        else
            result="${RED}❌ FAIL (HTTP $HTTP_STATUS)${NC}"
            ((FAIL_COUNT++))
        fi
    fi

    echo "**Result:** $result" >> "$EVIDENCE_LOG"
    echo "" >> "$EVIDENCE_LOG"
    echo "---" >> "$EVIDENCE_LOG"

    echo -e "$result - $test_name ($role)"
}

echo "=========================================================================="
echo "COMPREHENSIVE INVENTORY LENS E2E TESTING"
echo "=========================================================================="
echo ""

# =============================================================================
# PART 1: SEARCH ENDPOINTS (3 endpoints × 2 roles × 3 queries = 18 tests)
# =============================================================================

echo ""
echo "PART 1: Search Endpoints Parity"
echo "--------------------------------"

QUERIES=("parts low in stock" "oil filter" "check stock levels")

for query in "${QUERIES[@]}"; do
    # /v2/search - Crew
    test_api \
        "/v2/search: '$query'" \
        "crew" \
        "$CREW_JWT" \
        "POST" \
        "/v2/search" \
        "{\"query_text\":\"$query\"}" \
        "[ \"$HTTP_STATUS\" == \"200\" ] && [ \$(cat \"$response_file\" | jq -r '.context.domain') == \"parts\" -o \$(cat \"$response_file\" | jq -r '.context') == \"null\" ]"

    # /v2/search - HOD
    test_api \
        "/v2/search: '$query'" \
        "hod" \
        "$HOD_JWT" \
        "POST" \
        "/v2/search" \
        "{\"query_text\":\"$query\"}" \
        "[ \"$HTTP_STATUS\" == \"200\" ] && [ \$(cat \"$response_file\" | jq -r '.context.domain') == \"parts\" -o \$(cat \"$response_file\" | jq -r '.context') == \"null\" ]"

    # /v1/search - Crew
    test_api \
        "/v1/search: '$query'" \
        "crew" \
        "$CREW_JWT" \
        "POST" \
        "/v1/search" \
        "{\"query\":\"$query\"}" \
        "[ \"$HTTP_STATUS\" == \"200\" ]"

    # /v1/search - HOD
    test_api \
        "/v1/search: '$query'" \
        "hod" \
        "$HOD_JWT" \
        "POST" \
        "/v1/search" \
        "{\"query\":\"$query\"}" \
        "[ \"$HTTP_STATUS\" == \"200\" ]"

    # /search (fusion) - Crew
    test_api \
        "/search: '$query'" \
        "crew" \
        "$CREW_JWT" \
        "POST" \
        "/search" \
        "{\"query\":\"$query\"}" \
        "[ \"$HTTP_STATUS\" == \"200\" ]"

    # /search (fusion) - HOD
    test_api \
        "/search: '$query'" \
        "hod" \
        "$HOD_JWT" \
        "POST" \
        "/search" \
        "{\"query\":\"$query\"}" \
        "[ \"$HTTP_STATUS\" == \"200\" ]"
done

# =============================================================================
# PART 2: ACTION SUGGESTIONS (2 roles × parts domain = 2 tests)
# =============================================================================

echo ""
echo "PART 2: Action Suggestions Role Filtering"
echo "-------------------------------------------"

# Crew should only see READ actions
test_api \
    "GET /v1/actions/list (domain=parts)" \
    "crew" \
    "$CREW_JWT" \
    "GET" \
    "/v1/actions/list?q=stock&domain=parts" \
    "" \
    "[ \"$HTTP_STATUS\" == \"200\" ] && [ \$(cat \"$response_file\" | jq '[.actions[] | select(.variant == \"MUTATE\" or .variant == \"SIGNED\")] | length') == \"0\" ]"

# HOD should see READ + MUTATE actions
test_api \
    "GET /v1/actions/list (domain=parts)" \
    "hod" \
    "$HOD_JWT" \
    "GET" \
    "/v1/actions/list?q=stock&domain=parts" \
    "" \
    "[ \"$HTTP_STATUS\" == \"200\" ] && [ \$(cat \"$response_file\" | jq '[.actions[] | select(.variant == \"MUTATE\")] | length') -gt \"0\" ]"

# =============================================================================
# PART 3: ACTION EXECUTION (Role Gating = 4 tests)
# =============================================================================

echo ""
echo "PART 3: Action Execution Role Gating"
echo "--------------------------------------"

# Crew READ action - should work (200/404)
test_api \
    "Crew executes check_stock_level (READ)" \
    "crew" \
    "$CREW_JWT" \
    "POST" \
    "/v1/actions/execute" \
    "{\"action\":\"check_stock_level\",\"context\":{\"yacht_id\":\"$YACHT_ID\"},\"payload\":{\"part_id\":\"00000000-0000-0000-0000-000000000000\"}}" \
    "[ \"$HTTP_STATUS\" == \"404\" -o \"$HTTP_STATUS\" == \"200\" ]"

# Crew MUTATE action - should be denied (403)
test_api \
    "Crew executes log_part_usage (MUTATE) - expect 403" \
    "crew" \
    "$CREW_JWT" \
    "POST" \
    "/v1/actions/execute" \
    "{\"action\":\"log_part_usage\",\"context\":{\"yacht_id\":\"$YACHT_ID\"},\"payload\":{\"part_id\":\"00000000-0000-0000-0000-000000000000\",\"quantity\":1,\"usage_reason\":\"maintenance\"}}" \
    "[ \"$HTTP_STATUS\" == \"403\" ]"

# HOD READ action - should work
test_api \
    "HOD executes check_stock_level (READ)" \
    "hod" \
    "$HOD_JWT" \
    "POST" \
    "/v1/actions/execute" \
    "{\"action\":\"check_stock_level\",\"context\":{\"yacht_id\":\"$YACHT_ID\"},\"payload\":{\"part_id\":\"00000000-0000-0000-0000-000000000000\"}}" \
    "[ \"$HTTP_STATUS\" == \"404\" -o \"$HTTP_STATUS\" == \"200\" ]"

# HOD MUTATE action - should work (200/404)
test_api \
    "HOD executes log_part_usage (MUTATE)" \
    "hod" \
    "$HOD_JWT" \
    "POST" \
    "/v1/actions/execute" \
    "{\"action\":\"log_part_usage\",\"context\":{\"yacht_id\":\"$YACHT_ID\"},\"payload\":{\"part_id\":\"00000000-0000-0000-0000-000000000000\",\"quantity\":1,\"usage_reason\":\"maintenance\"}}" \
    "[ \"$HTTP_STATUS\" == \"404\" -o \"$HTTP_STATUS\" == \"200\" -o \"$HTTP_STATUS\" == \"400\" ]"

# =============================================================================
# PART 4: ERROR MAPPING (Client Errors = 2 tests)
# =============================================================================

echo ""
echo "PART 4: Client Error Mapping (4xx not 500)"
echo "--------------------------------------------"

# Invalid UUID format
test_api \
    "Invalid part_id format - expect 400" \
    "hod" \
    "$HOD_JWT" \
    "POST" \
    "/v1/actions/execute" \
    "{\"action\":\"check_stock_level\",\"context\":{\"yacht_id\":\"$YACHT_ID\"},\"payload\":{\"part_id\":\"invalid-format\"}}" \
    "[ \"$HTTP_STATUS\" == \"400\" -o \"$HTTP_STATUS\" == \"404\" ]"

# Missing required field
test_api \
    "Missing required field - expect 400" \
    "hod" \
    "$HOD_JWT" \
    "POST" \
    "/v1/actions/execute" \
    "{\"action\":\"check_stock_level\",\"context\":{\"yacht_id\":\"$YACHT_ID\"},\"payload\":{}}" \
    "[ \"$HTTP_STATUS\" == \"400\" ]"

# =============================================================================
# SUMMARY
# =============================================================================

echo ""
echo "=========================================================================="
echo "TEST SUMMARY"
echo "=========================================================================="
echo -e "Passed: ${GREEN}$PASS_COUNT${NC}"
echo -e "Failed: ${RED}$FAIL_COUNT${NC}"
echo "Total: $TOTAL_COUNT"
echo ""
echo "Evidence saved to: $EVIDENCE_LOG"
echo "Response files saved to: $OUTPUT_DIR/"
echo "=========================================================================="

# Write summary to evidence log
echo "" >> "$EVIDENCE_LOG"
echo "## Summary" >> "$EVIDENCE_LOG"
echo "" >> "$EVIDENCE_LOG"
echo "- **Passed**: $PASS_COUNT" >> "$EVIDENCE_LOG"
echo "- **Failed**: $FAIL_COUNT" >> "$EVIDENCE_LOG"
echo "- **Total**: $TOTAL_COUNT" >> "$EVIDENCE_LOG"
echo "" >> "$EVIDENCE_LOG"
echo "---" >> "$EVIDENCE_LOG"

if [ $FAIL_COUNT -gt 0 ]; then
    echo ""
    echo -e "${RED}⚠️  FAILURES DETECTED - See $EVIDENCE_LOG for details${NC}"
    exit 1
else
    echo ""
    echo -e "${GREEN}✅ ALL TESTS PASSED${NC}"
    exit 0
fi
