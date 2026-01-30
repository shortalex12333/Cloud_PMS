#!/usr/bin/env bash
#
# Tenant V2 Embeddings Verification
# ==================================
#
# Runs verification SQL against tenant database to confirm V2 migration:
#   - pgvector extension enabled
#   - embedding_updated_at columns (6 tables)
#   - pms_attachments embedding columns (3 columns)
#   - Vector dimensions (1536)
#   - Partial indexes for stale queries
#
# Usage:
#   ./scripts/verify_tenant_v2_embeddings.sh
#
# Environment Variables:
#   TENANT_SUPABASE_URL          - Tenant database URL
#   TENANT_SUPABASE_SERVICE_KEY  - Tenant service role key
#
# Output:
#   PASS/FAIL per check
#   Summary report

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}V2 Embeddings Migration Verification${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# Check environment
if [[ -z "${TENANT_SUPABASE_URL:-}" ]]; then
    echo -e "${RED}Error: TENANT_SUPABASE_URL not set${NC}"
    exit 1
fi

if [[ -z "${TENANT_SUPABASE_SERVICE_KEY:-}" ]]; then
    echo -e "${RED}Error: TENANT_SUPABASE_SERVICE_KEY not set${NC}"
    exit 1
fi

# Extract database connection details from Supabase URL
# Format: https://xyz.supabase.co
# Connection: postgres://postgres:[password]@db.xyz.supabase.co:5432/postgres

# Extract project ID from URL
PROJECT_ID=$(echo "$TENANT_SUPABASE_URL" | sed -E 's|https://([^.]+)\.supabase\.co.*|\1|')
DB_HOST="db.${PROJECT_ID}.supabase.co"
DB_PORT="5432"
DB_NAME="postgres"
DB_USER="postgres"
DB_PASS="$TENANT_SUPABASE_SERVICE_KEY"

echo -e "${YELLOW}Database Connection:${NC}"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  Database: $DB_NAME"
echo ""

# Verification SQL file
VERIFY_SQL="$PROJECT_ROOT/supabase/migrations/verify_v2_embedding_migration.sql"

if [[ ! -f "$VERIFY_SQL" ]]; then
    echo -e "${RED}Error: Verification SQL not found: $VERIFY_SQL${NC}"
    exit 1
fi

echo -e "${BLUE}Running verification SQL...${NC}"
echo ""

# Run verification using psql
# Suppress connection messages with -q
# Use -t for tuples-only output (no headers/footers)
# Use -A for unaligned output

PGPASSWORD="$DB_PASS" psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -f "$VERIFY_SQL" \
    2>&1 | tee /tmp/v2_embeddings_verification.log

EXIT_CODE="${PIPESTATUS[0]}"

echo ""
echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}Verification Results${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# Parse results
PASS_COUNT=$(grep -c "✓" /tmp/v2_embeddings_verification.log || echo "0")
FAIL_COUNT=$(grep -c "✗" /tmp/v2_embeddings_verification.log || echo "0")

if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}✓ Verification SQL executed successfully${NC}"
    echo ""
    echo "Checks passed: $PASS_COUNT"
    echo "Checks failed: $FAIL_COUNT"
    echo ""

    if [[ $FAIL_COUNT -gt 0 ]]; then
        echo -e "${YELLOW}Failed checks:${NC}"
        grep "✗" /tmp/v2_embeddings_verification.log || true
        echo ""
        echo -e "${YELLOW}Action required:${NC}"
        echo "  1. Review failed checks above"
        echo "  2. Run missing migrations if needed"
        echo "  3. Re-run this script to verify fixes"
        exit 1
    else
        echo -e "${GREEN}All checks passed! V2 embeddings migration verified.${NC}"
        echo ""
        echo -e "${YELLOW}Next steps:${NC}"
        echo "  1. Run dry-run worker: ./scripts/run_worker_dry_run.sh"
        echo "  2. Run actual worker with small batch for testing"
        echo "  3. Enable shadow logging: SHOW_RELATED_SHADOW=true"
    fi
else
    echo -e "${RED}✗ Verification failed (exit code: $EXIT_CODE)${NC}"
    echo ""
    echo "Check log: /tmp/v2_embeddings_verification.log"
    exit $EXIT_CODE
fi

echo -e "${BLUE}============================================================${NC}"
echo ""
echo "Full log saved to: /tmp/v2_embeddings_verification.log"
