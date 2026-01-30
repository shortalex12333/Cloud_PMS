#!/usr/bin/env bash
#
# Run V2 Embeddings Docker Test Suite
# ====================================
#
# Builds and runs complete V2 embeddings infrastructure tests in Docker:
# - Database schema (pgvector, columns, indexes, triggers)
# - Shadow logging (privacy, alpha=0.0, statistics)
# - SIGNED action variant (allowed_roles)
# - Attachments table name (pms_attachments)
# - Worker health
#
# Usage:
#   ./scripts/run_docker_v2_tests.sh
#
# Prerequisites:
#   - Docker and docker-compose installed
#   - .env.test or environment variables configured
#
# Exit Codes:
#   0 - All tests passed
#   1 - One or more tests failed
#   2 - Docker build/run failed

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
echo -e "${BLUE}V2 Embeddings Docker Test Suite${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# Check prerequisites
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: docker not found${NC}"
    echo "Install Docker: https://docs.docker.com/get-docker/"
    exit 2
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: docker-compose not found${NC}"
    echo "Install docker-compose: https://docs.docker.com/compose/install/"
    exit 2
fi

# Check for docker-compose.test.yml
if [[ ! -f "$PROJECT_ROOT/docker-compose.test.yml" ]]; then
    echo -e "${RED}Error: docker-compose.test.yml not found${NC}"
    exit 2
fi

# Load environment if .env.test exists
if [[ -f "$PROJECT_ROOT/.env.test" ]]; then
    echo -e "${YELLOW}Loading environment from .env.test${NC}"
    set -a
    source "$PROJECT_ROOT/.env.test"
    set +a
fi

cd "$PROJECT_ROOT"

echo -e "${BLUE}Building Docker images...${NC}"
echo ""

# Build images
if ! docker-compose -f docker-compose.test.yml build; then
    echo -e "${RED}Error: Docker build failed${NC}"
    exit 2
fi

echo ""
echo -e "${BLUE}Running V2 embeddings tests...${NC}"
echo ""

# Run tests
# Override CMD to run V2 embeddings tests instead of default RLS tests
if docker-compose -f docker-compose.test.yml run --rm test-runner python run_v2_embeddings_tests.py; then
    echo ""
    echo -e "${GREEN}✓ V2 Embeddings Docker tests completed successfully${NC}"
    EXIT_CODE=0
else
    EXIT_CODE=$?
    echo ""
    echo -e "${RED}✗ V2 Embeddings Docker tests failed (exit code: ${EXIT_CODE})${NC}"
fi

# Cleanup
echo ""
echo -e "${YELLOW}Cleaning up containers...${NC}"
docker-compose -f docker-compose.test.yml down

echo ""
echo -e "${BLUE}============================================================${NC}"

if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}All V2 embedding checks passed!${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Run local pytest: pytest apps/api/tests/test_*.py -v"
    echo "  2. Run staging tests: python tests/ci/staging_embeds_shadow_check.py"
    echo "  3. Deploy to staging Render services"
    echo "  4. Verify on tenant database: ./scripts/verify_tenant_v2_embeddings.sh"
else
    echo -e "${RED}Tests failed. Review output above for details.${NC}"
fi

echo -e "${BLUE}============================================================${NC}"

exit $EXIT_CODE
