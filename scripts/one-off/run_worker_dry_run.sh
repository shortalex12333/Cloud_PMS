#!/usr/bin/env bash
#
# Embedding Refresh Worker - Dry-Run Mode
# ========================================
#
# Runs embedding refresh worker in dry-run mode to preview what would be refreshed
# without actually calling OpenAI API or writing to database.
#
# Usage:
#   ./scripts/run_worker_dry_run.sh
#
# Environment Variables:
#   TENANT_SUPABASE_URL          - Tenant database URL
#   TENANT_SUPABASE_SERVICE_KEY  - Tenant service role key
#   EMBEDDING_MAX_PER_RUN        - Max embeddings per run (default: 500)
#
# Output:
#   - Stale row counts per table
#   - Estimated API cost
#   - No actual API calls or DB writes

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}Embedding Refresh Worker - Dry-Run Mode${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# Check required environment variables
if [[ -z "${TENANT_SUPABASE_URL:-}" ]]; then
    echo -e "${RED}Error: TENANT_SUPABASE_URL not set${NC}"
    echo "Export from .env.tenant1 or set manually"
    exit 1
fi

if [[ -z "${TENANT_SUPABASE_SERVICE_KEY:-}" ]]; then
    echo -e "${RED}Error: TENANT_SUPABASE_SERVICE_KEY not set${NC}"
    echo "Export from .env.tenant1 or set manually"
    exit 1
fi

# Set defaults
export EMBEDDING_MAX_PER_RUN="${EMBEDDING_MAX_PER_RUN:-500}"
export CIRCUIT_BREAKER_THRESHOLD="${CIRCUIT_BREAKER_THRESHOLD:-10}"
export RETRY_ATTEMPTS="${RETRY_ATTEMPTS:-3}"

echo -e "${YELLOW}Configuration:${NC}"
echo "  Database: ${TENANT_SUPABASE_URL%%/*}..."
echo "  Max per run: $EMBEDDING_MAX_PER_RUN"
echo "  Circuit breaker threshold: $CIRCUIT_BREAKER_THRESHOLD"
echo "  Retry attempts: $RETRY_ATTEMPTS"
echo ""

# Navigate to API directory
cd "$PROJECT_ROOT/apps/api"

# Run worker in dry-run mode
echo -e "${BLUE}Running dry-run...${NC}"
echo ""

python3 -m workers.embedding_refresh_worker --dry-run 2>&1 | tee /tmp/embedding_worker_dry_run.log

# Check exit code
EXIT_CODE="${PIPESTATUS[0]}"

echo ""
echo -e "${BLUE}============================================================${NC}"

if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}✓ Dry-run completed successfully${NC}"
    echo ""
    echo "Log saved to: /tmp/embedding_worker_dry_run.log"
    echo ""

    # Extract key stats from log
    if grep -q "Found.*stale" /tmp/embedding_worker_dry_run.log; then
        echo -e "${YELLOW}Summary:${NC}"
        grep "Found.*stale" /tmp/embedding_worker_dry_run.log || true
        grep "cost_estimate" /tmp/embedding_worker_dry_run.log || true
        echo ""
    fi

    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Review stale counts above"
    echo "  2. If reasonable, run actual refresh: python3 -m workers.embedding_refresh_worker"
    echo "  3. Monitor shadow logs: SHOW_RELATED_SHADOW=true in env"
else
    echo -e "${RED}✗ Dry-run failed (exit code: $EXIT_CODE)${NC}"
    echo ""
    echo "Check log for errors: /tmp/embedding_worker_dry_run.log"
    exit $EXIT_CODE
fi

echo -e "${BLUE}============================================================${NC}"
