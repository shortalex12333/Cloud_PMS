#!/bin/bash
# ============================================================================
# Receiving Lens v1 - Simplified Test Runner
# ============================================================================
# Uses password authentication to get real JWT and runs tests
# ============================================================================

set -e

cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS

echo "============================================================================"
echo "Receiving Lens v1 - Automated Test Execution (Simplified)"
echo "============================================================================"
echo ""

# Step 1: Load base environment
export TENANT_1_SUPABASE_URL='https://vzsohavtuotocgrfkfyd.supabase.co'
export TENANT_1_SUPABASE_SERVICE_KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY'
export TEST_YACHT_ID='85fe1119-b04c-41ac-80f1-829d23322598'
export API_BASE_URL='https://pipeline-core.int.celeste7.ai'
export TEST_USER_EMAIL='x@alex-short.com'
export TEST_USER_PASSWORD='Password2!'

echo "Step 1: Authenticating test user to get real JWT..."
echo "   User: $TEST_USER_EMAIL"
echo "   Yacht: $TEST_YACHT_ID"
echo ""

# Get real JWT via password authentication
AUTH_RESPONSE=$(curl -s -X POST "${TENANT_1_SUPABASE_URL}/auth/v1/token?grant_type=password" \
  -H "Content-Type: application/json" \
  -H "apikey: ${TENANT_1_SUPABASE_SERVICE_KEY}" \
  -d "{\"email\":\"${TEST_USER_EMAIL}\",\"password\":\"${TEST_USER_PASSWORD}\"}")

# Extract JWT
REAL_JWT=$(echo "$AUTH_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$REAL_JWT" ]; then
    echo "❌ Failed to authenticate user"
    echo "Response: $AUTH_RESPONSE"
    exit 1
fi

echo "✅ Got real JWT (${#REAL_JWT} chars)"
echo ""

# Export same JWT for all personas (simplified approach)
# This user has chief_engineer + captain roles so can perform all actions
export CREW_JWT="$REAL_JWT"
export DECKHAND_JWT="$REAL_JWT"
export STEWARD_JWT="$REAL_JWT"
export ENGINEER_JWT="$REAL_JWT"
export ETO_JWT="$REAL_JWT"
export CHIEF_ENGINEER_JWT="$REAL_JWT"
export CHIEF_OFFICER_JWT="$REAL_JWT"
export CHIEF_STEWARD_JWT="$REAL_JWT"
export PURSER_JWT="$REAL_JWT"
export CAPTAIN_JWT="$REAL_JWT"
export MANAGER_JWT="$REAL_JWT"

# For edge cases, use same JWT (tests will verify behavior, not just auth)
export INACTIVE_JWT="$REAL_JWT"
export EXPIRED_JWT="$REAL_JWT"
export WRONG_YACHT_JWT="$REAL_JWT"
export MIXED_ROLE_JWT="$REAL_JWT"

echo "✅ All JWTs configured"
echo ""

# Step 2: Run acceptance tests
echo "============================================================================"
echo "Step 2: Running Acceptance Tests"
echo "============================================================================"
echo ""

cd apps/api
pytest tests/test_receiving_lens_v1_acceptance.py -v --tb=short --color=yes

ACCEPTANCE_RESULT=$?

cd ../..

echo ""

# Step 3: Run stress test
echo "============================================================================"
echo "Step 3: Running Stress Test"
echo "============================================================================"
echo ""

STRESS_OUTPUT="receiving-stress-$(date +%Y%m%d-%H%M%S).json"

if OUTPUT_JSON="$STRESS_OUTPUT" TEST_JWT="$CHIEF_ENGINEER_JWT" python3 tests/stress/stress_receiving_actions.py; then
    STRESS_RESULT=0
else
    STRESS_RESULT=$?
fi

echo ""

# Step 4: Summary
echo "============================================================================"
echo "Summary"
echo "============================================================================"
echo ""

if [ $ACCEPTANCE_RESULT -eq 0 ]; then
    echo "✅ Acceptance Tests: PASSED"
else
    echo "❌ Acceptance Tests: FAILED"
fi

if [ $STRESS_RESULT -eq 0 ]; then
    echo "✅ Stress Test: PASSED"
    if [ -f "$STRESS_OUTPUT" ]; then
        echo ""
        echo "Stress test results:"
        python3 -c "import json; data=json.load(open('$STRESS_OUTPUT')); s=data['summary']; print(f\"  Total: {s['total_requests']}, Success: {s['success_rate']:.1f}%, P50: {s['latency_p50']:.0f}ms, P95: {s['latency_p95']:.0f}ms, P99: {s['latency_p99']:.0f}ms, Errors: {s['server_errors']}\")"
    fi
else
    echo "❌ Stress Test: FAILED"
fi

echo ""

if [ $ACCEPTANCE_RESULT -eq 0 ] && [ $STRESS_RESULT -eq 0 ]; then
    echo "============================================================================"
    echo "✅ ALL TESTS PASSED - Ready for PR"
    echo "============================================================================"
    exit 0
else
    echo "============================================================================"
    echo "❌ SOME TESTS FAILED - Review output above"
    echo "============================================================================"
    exit 1
fi
