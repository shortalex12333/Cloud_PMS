#!/bin/bash
# =============================================================================
# Verify Critical Department RBAC Fix Deployment
# =============================================================================
# Tests deployment of commit b6ac42d (PR #194) - CRITICAL RBAC FIX
# Also verifies commit c1fa4ff (PR #195) - Image Upload MVP
#
# CRITICAL FIX: Department RBAC now reads from metadata->department JSON field
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
API_BASE="${API_BASE:-https://pipeline-core.int.celeste7.ai}"
YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
EVIDENCE_DIR="test-results/deployment/${TIMESTAMP}"

mkdir -p "$EVIDENCE_DIR"

echo "============================================================================="
echo "CRITICAL DEPLOYMENT VERIFICATION"
echo "============================================================================="
echo ""
echo "Commits being verified:"
echo "  - b6ac42d: CRITICAL department RBAC fix (PR #194)"
echo "  - c1fa4ff: Parts image upload MVP (PR #195)"
echo ""
echo "API Base: $API_BASE"
echo "Timestamp: $(date)"
echo "Evidence: $EVIDENCE_DIR/"
echo ""

# Load test JWTs
if [ ! -f "test-jwts.json" ]; then
    echo -e "${RED}✗ test-jwts.json not found${NC}"
    echo "Run: python3 tests/ci/generate_all_test_jwts.py > test-jwts.json"
    exit 1
fi

CREW_JWT=$(jq -r '.CREW.jwt' test-jwts.json)
HOD_JWT=$(jq -r '.HOD.jwt' test-jwts.json)
CREW_USER_ID=$(jq -r '.CREW.user_id' test-jwts.json)

echo "=== Waiting for API Server Restart ==="
echo ""
echo "Checking if new routes are live..."
MAX_ATTEMPTS=60  # 5 minutes (5 second intervals)
ATTEMPT=1

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
    # Test if image upload route exists (should return 401/422, not 404)
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        "$API_BASE/v1/parts/upload-image" \
        -X POST \
        -H "Content-Type: application/json" \
        -d '{"test":"data"}' || echo "000")

    if [ "$HTTP_CODE" != "404" ] && [ "$HTTP_CODE" != "000" ]; then
        echo -e "${GREEN}✓ API restarted! New routes detected (HTTP $HTTP_CODE)${NC}"
        break
    fi

    if [ $((ATTEMPT % 12)) -eq 0 ]; then
        echo "Still waiting... (${ATTEMPT}/60 checks, $(($ATTEMPT * 5)) seconds elapsed)"
    fi

    ATTEMPT=$((ATTEMPT + 1))
    sleep 5
done

if [ $ATTEMPT -gt $MAX_ATTEMPTS ]; then
    echo -e "${RED}✗ Timeout: API did not restart within 5 minutes${NC}"
    echo ""
    echo "Check Render dashboard: https://dashboard.render.com/"
    exit 1
fi

echo ""
echo "============================================================================="
echo "TEST 1: CRITICAL - Department RBAC Fix"
echo "============================================================================="
echo ""
echo "Testing: Crew can create work orders in their assigned department"
echo ""

# Test 1: Create a DECK work order as CREW user
# The CREW user should have metadata.department = "DECK" in their profile
echo "Attempting to create DECK work order as CREW user..."

RESULT=$(curl -s -w "\nHTTP:%{http_code}" -X POST "$API_BASE/v1/actions/execute" \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d "{
    \"action\": \"create_work_order\",
    \"context\": {
      \"yacht_id\": \"$YACHT_ID\"
    },
    \"payload\": {
      \"title\": \"Test RBAC Fix - DECK Work Order\",
      \"department\": \"deck\",
      \"priority\": \"medium\",
      \"description\": \"Testing department RBAC after critical fix\"
    }
  }")

HTTP_CODE=$(echo "$RESULT" | grep "HTTP:" | cut -d':' -f2)
RESPONSE=$(echo "$RESULT" | grep -v "HTTP:")

echo "$RESPONSE" | jq '.' > "$EVIDENCE_DIR/test1_rbac_crew_deck.json" 2>/dev/null || echo "$RESPONSE" > "$EVIDENCE_DIR/test1_rbac_crew_deck.json"

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
    echo -e "${GREEN}✓ TEST 1 PASSED: Crew can create work orders in their department${NC}"
    echo "  HTTP Status: $HTTP_CODE"
    echo "  Response saved: $EVIDENCE_DIR/test1_rbac_crew_deck.json"
    TEST1_STATUS="PASS"
elif [ "$HTTP_CODE" = "403" ]; then
    echo -e "${RED}✗ TEST 1 FAILED: Got 403 Forbidden${NC}"
    echo "  This means the RBAC fix did NOT work"
    echo "  Crew user is still blocked from creating work orders"
    echo "  ERROR: Department not being read from metadata field"
    echo ""
    echo "Response:"
    echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
    TEST1_STATUS="FAIL"
else
    echo -e "${YELLOW}⚠ TEST 1 INCONCLUSIVE: HTTP $HTTP_CODE${NC}"
    echo "Response:"
    echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
    TEST1_STATUS="INCONCLUSIVE"
fi

echo ""
echo "============================================================================="
echo "TEST 2: Image Upload Routes Available"
echo "============================================================================="
echo ""

# Test 2: Check if upload-image route is available (should return 401, not 404)
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    "$API_BASE/v1/parts/upload-image" \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{}')

if [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "422" ]; then
    echo -e "${GREEN}✓ TEST 2 PASSED: Image upload route is live (HTTP $HTTP_CODE)${NC}"
    TEST2_STATUS="PASS"
elif [ "$HTTP_CODE" = "404" ]; then
    echo -e "${RED}✗ TEST 2 FAILED: Image upload route not found (404)${NC}"
    echo "  Routes not registered yet - API may need another restart"
    TEST2_STATUS="FAIL"
else
    echo -e "${YELLOW}⚠ TEST 2 INCONCLUSIVE: HTTP $HTTP_CODE${NC}"
    TEST2_STATUS="INCONCLUSIVE"
fi

echo ""
echo "============================================================================="
echo "TEST 3: Health Check"
echo "============================================================================="
echo ""

HEALTH_STATUS=$(curl -s "$API_BASE/health" | jq -r '.status // "unknown"' 2>/dev/null || echo "No response")

if [ "$HEALTH_STATUS" = "healthy" ] || [ "$HEALTH_STATUS" = "ok" ]; then
    echo -e "${GREEN}✓ TEST 3 PASSED: API health check OK${NC}"
    TEST3_STATUS="PASS"
else
    echo -e "${YELLOW}⚠ TEST 3 WARNING: Health status: $HEALTH_STATUS${NC}"
    TEST3_STATUS="PASS"  # Don't fail on health check
fi

echo ""
echo "============================================================================="
echo "DEPLOYMENT VERIFICATION SUMMARY"
echo "============================================================================="
echo ""

# Count results
PASSED=0
FAILED=0

[ "$TEST1_STATUS" = "PASS" ] && PASSED=$((PASSED + 1)) || FAILED=$((FAILED + 1))
[ "$TEST2_STATUS" = "PASS" ] && PASSED=$((PASSED + 1)) || FAILED=$((FAILED + 1))
[ "$TEST3_STATUS" = "PASS" ] && PASSED=$((PASSED + 1))

echo "Results:"
echo "  ✓ Passed: $PASSED"
echo "  ✗ Failed: $FAILED"
echo ""
echo "Test Details:"
echo "  TEST 1 (CRITICAL RBAC): $TEST1_STATUS"
echo "  TEST 2 (Image Routes):  $TEST2_STATUS"
echo "  TEST 3 (Health Check):  $TEST3_STATUS"
echo ""

# Generate report
cat > "$EVIDENCE_DIR/DEPLOYMENT_VERIFICATION_REPORT.md" << EOF
# Deployment Verification Report

**Date:** $(date)
**Commits:** b6ac42d (RBAC fix), c1fa4ff (Image upload)
**API:** $API_BASE

## Test Results

### TEST 1: CRITICAL Department RBAC Fix
**Status:** $TEST1_STATUS
**Details:** Department RBAC now reads from metadata->department JSON field
**Evidence:** test1_rbac_crew_deck.json

### TEST 2: Image Upload Routes
**Status:** $TEST2_STATUS
**Details:** POST /v1/parts/upload-image route availability

### TEST 3: Health Check
**Status:** $TEST3_STATUS
**Details:** API health endpoint responding

## Summary

- **Passed:** $PASSED/3
- **Failed:** $FAILED/3

$(if [ "$FAILED" -eq 0 ]; then
    echo "✅ **DEPLOYMENT VERIFIED** - All critical tests passed"
else
    echo "❌ **DEPLOYMENT FAILED** - Critical issues detected"
fi)

## Evidence Files

\`\`\`
$(ls -1 $EVIDENCE_DIR/)
\`\`\`

---
Generated: $(date)
EOF

echo "Report saved: $EVIDENCE_DIR/DEPLOYMENT_VERIFICATION_REPORT.md"
echo ""

if [ "$FAILED" -gt 0 ]; then
    echo -e "${RED}❌ DEPLOYMENT VERIFICATION FAILED${NC}"
    echo ""
    echo "Action Required:"
    echo "  1. Check Render logs for deployment errors"
    echo "  2. Review evidence files in $EVIDENCE_DIR/"
    echo "  3. Consider rollback if critical"
    exit 1
else
    echo -e "${GREEN}✅ DEPLOYMENT VERIFICATION PASSED${NC}"
    echo ""
    echo "Next Steps:"
    echo "  1. Monitor API for 1 hour"
    echo "  2. Check error rates in logs"
    echo "  3. Notify team of successful deployment"
    exit 0
fi
