#!/bin/bash
# Verify Inventory Lens E2E Test Environment
#
# Checks:
# - JWT tokens are valid
# - API endpoints are accessible
# - Test yacht has parts data
# - Action router is available

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Inventory Lens E2E Environment Verification${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Configuration
BASE_URL="https://pipeline-core.int.celeste7.ai"
YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"

# Check if test-jwts.json exists
if [ ! -f "test-jwts.json" ]; then
  echo -e "${RED}❌ test-jwts.json not found${NC}"
  echo "   Expected location: test-jwts.json"
  exit 1
else
  echo -e "${GREEN}✅ test-jwts.json found${NC}"
fi

# Load JWT tokens
CREW_JWT=$(jq -r '.CREW.jwt' test-jwts.json)
HOD_JWT=$(jq -r '.HOD.jwt' test-jwts.json)

if [ "$CREW_JWT" == "null" ] || [ -z "$CREW_JWT" ]; then
  echo -e "${RED}❌ CREW JWT not found in test-jwts.json${NC}"
  exit 1
else
  echo -e "${GREEN}✅ CREW JWT loaded${NC}"
fi

if [ "$HOD_JWT" == "null" ] || [ -z "$HOD_JWT" ]; then
  echo -e "${RED}❌ HOD JWT not found in test-jwts.json${NC}"
  exit 1
else
  echo -e "${GREEN}✅ HOD JWT loaded${NC}"
fi

echo ""
echo -e "${YELLOW}Checking API Endpoints...${NC}"
echo ""

# Check health endpoint
echo "1. Checking API health..."
HEALTH=$(curl -s -w "\n%{http_code}" "$BASE_URL/health" 2>/dev/null || echo "000")
HTTP_CODE=$(echo "$HEALTH" | tail -n1)

if [ "$HTTP_CODE" == "200" ]; then
  echo -e "   ${GREEN}✅ API health check passed (200)${NC}"
else
  echo -e "   ${RED}❌ API health check failed ($HTTP_CODE)${NC}"
  exit 1
fi

# Check search endpoint with CREW
echo "2. Checking search endpoint (CREW)..."
SEARCH_CREW=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/search" \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: $YACHT_ID" \
  -d '{"query":"bearing"}' 2>/dev/null || echo '{}
000')

HTTP_CODE=$(echo "$SEARCH_CREW" | tail -n1)
BODY=$(echo "$SEARCH_CREW" | head -n-1)

if [ "$HTTP_CODE" == "200" ]; then
  RESULTS=$(echo "$BODY" | jq '.results | length' 2>/dev/null || echo "0")
  echo -e "   ${GREEN}✅ Search endpoint works (200, $RESULTS results)${NC}"
else
  echo -e "   ${RED}❌ Search endpoint failed ($HTTP_CODE)${NC}"
  exit 1
fi

# Check search endpoint with HOD
echo "3. Checking search endpoint (HOD)..."
SEARCH_HOD=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/search" \
  -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: $YACHT_ID" \
  -d '{"query":"fuel filter"}' 2>/dev/null || echo '{}
000')

HTTP_CODE=$(echo "$SEARCH_HOD" | tail -n1)
BODY=$(echo "$SEARCH_HOD" | head -n-1)

if [ "$HTTP_CODE" == "200" ]; then
  RESULTS=$(echo "$BODY" | jq '.results | length' 2>/dev/null || echo "0")
  DOMAIN=$(echo "$BODY" | jq -r '.context.domain' 2>/dev/null || echo "unknown")
  echo -e "   ${GREEN}✅ Search endpoint works (200, domain=$DOMAIN, $RESULTS results)${NC}"

  if [ "$RESULTS" == "0" ]; then
    echo -e "   ${YELLOW}⚠️  Warning: No results returned for 'fuel filter' query${NC}"
    echo -e "   ${YELLOW}   Tests may fail if yacht has no parts data${NC}"
  fi
else
  echo -e "   ${RED}❌ Search endpoint failed ($HTTP_CODE)${NC}"
  exit 1
fi

# Check actions list endpoint
echo "4. Checking actions list endpoint (HOD)..."
ACTIONS=$(curl -s -w "\n%{http_code}" "$BASE_URL/v1/actions/list?domain=parts" \
  -H "Authorization: Bearer $HOD_JWT" 2>/dev/null || echo '{}
000')

HTTP_CODE=$(echo "$ACTIONS" | tail -n1)
BODY=$(echo "$ACTIONS" | head -n-1)

if [ "$HTTP_CODE" == "200" ]; then
  ACTION_COUNT=$(echo "$BODY" | jq '.actions | length' 2>/dev/null || echo "0")
  echo -e "   ${GREEN}✅ Actions list endpoint works (200, $ACTION_COUNT actions)${NC}"
else
  echo -e "   ${RED}❌ Actions list endpoint failed ($HTTP_CODE)${NC}"
  exit 1
fi

# Check actions list endpoint for CREW
echo "5. Checking actions list endpoint (CREW)..."
ACTIONS_CREW=$(curl -s -w "\n%{http_code}" "$BASE_URL/v1/actions/list?domain=parts" \
  -H "Authorization: Bearer $CREW_JWT" 2>/dev/null || echo '{}
000')

HTTP_CODE=$(echo "$ACTIONS_CREW" | tail -n1)
BODY=$(echo "$ACTIONS_CREW" | head -n-1)

if [ "$HTTP_CODE" == "200" ]; then
  ACTION_COUNT=$(echo "$BODY" | jq '.actions | length' 2>/dev/null || echo "0")
  echo -e "   ${GREEN}✅ Actions list endpoint works (200, $ACTION_COUNT actions for CREW)${NC}"

  if [ "$ACTION_COUNT" != "2" ]; then
    echo -e "   ${YELLOW}⚠️  Warning: CREW should have exactly 2 READ actions, got $ACTION_COUNT${NC}"
  fi
else
  echo -e "   ${RED}❌ Actions list endpoint failed ($HTTP_CODE)${NC}"
  exit 1
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ Environment verification complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "You can now run the E2E tests:"
echo "  ./scripts/run-inventory-lens-e2e.sh"
echo ""
echo "Or run with Playwright directly:"
echo "  npx playwright test tests/e2e/inventory-lens-integration.spec.ts --project=e2e-chromium"
echo ""
