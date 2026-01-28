#!/bin/bash
# =============================================================================
# Part Lens v2: Deploy API + Run Staging Validation
# =============================================================================
# This script verifies API deployment and runs all staging tests.
#
# Prerequisites:
# 1. API must be deployed to staging
# 2. Environment variables must be set (see .env.staging.example)
#
# Usage:
#   export $(grep -v '^#' .env.staging | xargs)
#   ./deploy_and_test.sh
# =============================================================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_BASE="${API_BASE:-https://app.celeste7.ai}"
EVIDENCE_DIR="test-evidence"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$EVIDENCE_DIR/deploy_test_${TIMESTAMP}.log"

# Create evidence directory
mkdir -p "$EVIDENCE_DIR"

echo "============================================================================="
echo "PART LENS V2: STAGING VALIDATION"
echo "============================================================================="
echo "API Base: $API_BASE"
echo "Timestamp: $(date)"
echo "Log: $LOG_FILE"
echo ""

# Redirect all output to log file AND console
exec > >(tee -a "$LOG_FILE") 2>&1

# =============================================================================
# STEP 1: VERIFY API DEPLOYMENT
# =============================================================================

echo ""
echo "=== STEP 1: Verify API Deployment ==="
echo ""

echo "Checking health endpoint..."
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE/health" || echo "000")

if [ "$HEALTH_STATUS" = "200" ]; then
    echo -e "${GREEN}✓ Health endpoint: 200 OK${NC}"
else
    echo -e "${RED}✗ Health endpoint: $HEALTH_STATUS (expected 200)${NC}"
    echo ""
    echo "ERROR: API not deployed or health endpoint not working"
    echo "Please deploy the API first:"
    echo "  cd apps/api"
    echo "  docker build -t celeste-api:staging -f Dockerfile.microaction ."
    echo "  # Then deploy to your cloud provider"
    exit 1
fi

echo ""
echo "Checking Part Lens routes..."

# Check low-stock endpoint (should return 200/204/401/403, NOT 404)
LOW_STOCK_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  "$API_BASE/v1/parts/low-stock?yacht_id=$TEST_YACHT_ID" \
  -H "Authorization: Bearer $HOD_JWT" || echo "000")

if [ "$LOW_STOCK_STATUS" = "404" ]; then
    echo -e "${RED}✗ /v1/parts/low-stock: 404 (route not registered)${NC}"
    echo ""
    echo "ERROR: Part Lens routes not registered"
    echo "This means microaction_service.py is not deployed or routes aren't included"
    echo ""
    echo "Verify:"
    echo "  1. Dockerfile.microaction is used (not Dockerfile)"
    echo "  2. Entry point is: uvicorn microaction_service:app"
    echo "  3. microaction_service.py includes: app.include_router(part_routes_router)"
    exit 1
elif [ "$LOW_STOCK_STATUS" = "200" ] || [ "$LOW_STOCK_STATUS" = "204" ] || [ "$LOW_STOCK_STATUS" = "401" ] || [ "$LOW_STOCK_STATUS" = "403" ]; then
    echo -e "${GREEN}✓ /v1/parts/low-stock: $LOW_STOCK_STATUS (route registered)${NC}"
else
    echo -e "${YELLOW}⚠ /v1/parts/low-stock: $LOW_STOCK_STATUS (unexpected)${NC}"
fi

echo ""
echo -e "${GREEN}✓ API is deployed and routes are registered${NC}"

# =============================================================================
# STEP 2: GENERATE JWTS
# =============================================================================

echo ""
echo "=== STEP 2: Generate JWTs ==="
echo ""

if [ -z "$TENANT_1_SUPABASE_JWT_SECRET" ]; then
    echo -e "${RED}✗ TENANT_1_SUPABASE_JWT_SECRET not set${NC}"
    exit 1
fi

python3 tests/ci/generate_all_test_jwts.py > /tmp/jwts_${TIMESTAMP}.sh

if [ $? -eq 0 ]; then
    source /tmp/jwts_${TIMESTAMP}.sh
    echo -e "${GREEN}✓ JWTs generated (HOD, CAPTAIN, CREW)${NC}"
else
    echo -e "${RED}✗ Failed to generate JWTs${NC}"
    exit 1
fi

# =============================================================================
# STEP 3: RUN COMPREHENSIVE STAGING ACCEPTANCE
# =============================================================================

echo ""
echo "=== STEP 3: Run Comprehensive Staging Acceptance ==="
echo ""

python3 tests/ci/comprehensive_staging_acceptance.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Staging acceptance passed${NC}"

    # Check for zero 5xx
    FIVE_XX_COUNT=$(cat test-evidence/comprehensive_acceptance_summary.json | jq -r '.five_xx_count // 0')
    if [ "$FIVE_XX_COUNT" -eq 0 ]; then
        echo -e "${GREEN}✓ Zero 5xx errors confirmed${NC}"
    else
        echo -e "${RED}✗ Found $FIVE_XX_COUNT 5xx errors${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Staging acceptance failed${NC}"
    exit 1
fi

# =============================================================================
# STEP 4: COLLECT SQL EVIDENCE
# =============================================================================

echo ""
echo "=== STEP 4: Collect SQL Evidence ==="
echo ""

python3 tests/ci/collect_sql_evidence.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ SQL evidence collected${NC}"
else
    echo -e "${RED}✗ Failed to collect SQL evidence${NC}"
    exit 1
fi

# =============================================================================
# STEP 5: RUN STRESS TEST (IF AVAILABLE)
# =============================================================================

echo ""
echo "=== STEP 5: Run Stress Test (optional) ==="
echo ""

if [ -f "tests/stress/stress_action_list.py" ]; then
    export CONCURRENCY=10
    export REQUESTS=50
    export OUTPUT_JSON="test-evidence/stress-results.json"
    export TEST_JWT=$HOD_JWT

    python3 tests/stress/stress_action_list.py

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Stress test passed${NC}"

        # Check results
        SUCCESS_RATE=$(cat test-evidence/stress-results.json | jq -r '.success_rate // 0')
        P95=$(cat test-evidence/stress-results.json | jq -r '.p95_latency_ms // 9999')

        if (( $(echo "$SUCCESS_RATE > 0.99" | bc -l) )); then
            echo -e "${GREEN}✓ Success rate: $SUCCESS_RATE (>99%)${NC}"
        else
            echo -e "${RED}✗ Success rate: $SUCCESS_RATE (<99%)${NC}"
        fi

        if (( $(echo "$P95 < 500" | bc -l) )); then
            echo -e "${GREEN}✓ P95 latency: ${P95}ms (<500ms)${NC}"
        else
            echo -e "${YELLOW}⚠ P95 latency: ${P95}ms (>500ms)${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Stress test failed (optional)${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Stress test script not found (skipping)${NC}"
fi

# =============================================================================
# STEP 6: GENERATE ARTIFACTS SUMMARY
# =============================================================================

echo ""
echo "=== STEP 6: Generate Artifacts Summary ==="
echo ""

cat > "$EVIDENCE_DIR/STAGING_VALIDATION_COMPLETE.md" << EOF
# Part Lens v2: Staging Validation Complete

**Date**: $(date)
**API Base**: $API_BASE
**Status**: ✅ **VALIDATION COMPLETE**

## Test Results

### Comprehensive Acceptance
$(cat test-evidence/comprehensive_acceptance_summary.json | jq -r '"- Total tests: \(.total_tests)\n- Passed: \(.passed)\n- Failed: \(.failed)\n- Success rate: \(.success_rate * 100)%\n- 5xx errors: \(.five_xx_count)"')

### SQL Evidence
- View definitions: $(ls test-evidence/viewdef_*.sql 2>/dev/null | wc -l | tr -d ' ') files
- RLS policies: Collected
- Single-tenant assertion: Verified
- Transaction parity samples: Collected

### Artifacts Created
\`\`\`
$(ls -1 test-evidence/ | grep -E '\.(json|sql|txt|md)$' | head -20)
\`\`\`

## Canary Approval

$(cat test-evidence/comprehensive_acceptance_summary.json | jq -r 'if .success_rate == 1.0 and .five_xx_count == 0 then "✅ **APPROVED FOR CANARY**\n\nAll tests passed with zero 5xx errors. Ready to enable 5% canary." else "❌ **NOT APPROVED**\n\nTests failed or 5xx errors detected. Review artifacts before canary." end')

## Next Steps

1. Review all artifacts in test-evidence/
2. Enable 5% canary:
   \`\`\`sql
   UPDATE feature_flags
   SET enabled = true, canary_percentage = 5
   WHERE flag_name = 'part_lens_v2';
   \`\`\`
3. Monitor for 1 hour
4. Ramp: 5% → 20% → 50% → 100%

---
Generated: $(date)
EOF

echo -e "${GREEN}✓ Artifacts summary generated${NC}"

# =============================================================================
# FINAL SUMMARY
# =============================================================================

echo ""
echo "============================================================================="
echo "STAGING VALIDATION COMPLETE"
echo "============================================================================="
echo ""
echo "Artifacts location: $EVIDENCE_DIR/"
echo "Log file: $LOG_FILE"
echo ""
echo "Key artifacts:"
echo "  - comprehensive_acceptance_summary.json (main results)"
echo "  - zero_5xx_comprehensive.json (5xx proof)"
echo "  - role_based_suggestions.json (role visibility)"
echo "  - viewdef_*.sql (view definitions)"
echo "  - rls_policies.json (RLS policies)"
echo "  - STAGING_VALIDATION_COMPLETE.md (summary)"
echo ""

# Check if ready for canary
SUCCESS_RATE=$(cat test-evidence/comprehensive_acceptance_summary.json | jq -r '.success_rate // 0')
FIVE_XX_COUNT=$(cat test-evidence/comprehensive_acceptance_summary.json | jq -r '.five_xx_count // 99')

if [ "$SUCCESS_RATE" = "1" ] && [ "$FIVE_XX_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✅ READY FOR CANARY${NC}"
    echo ""
    echo "Next step: Enable 5% canary with monitoring"
else
    echo -e "${RED}❌ NOT READY FOR CANARY${NC}"
    echo ""
    echo "Issues found - review artifacts before proceeding"
fi

echo ""
echo "============================================================================="
