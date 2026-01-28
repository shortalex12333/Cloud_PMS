#!/bin/bash
# ============================================================================
# Receiving Lens v1 - Evidence Bundle Test Runner
# ============================================================================
# Purpose: Orchestrate all tests and generate evidence bundle for PR
# Requirements: All 15 JWTs must be exported before running
# ============================================================================

set -e

echo "============================================================================"
echo "Receiving Lens v1 - Evidence Bundle Generation"
echo "============================================================================"
echo ""

# ============================================================================
# STEP 1: Environment Validation
# ============================================================================

echo "Step 1: Validating environment variables..."
echo ""

REQUIRED_VARS=(
    "TENANT_1_SUPABASE_URL"
    "TENANT_1_SUPABASE_SERVICE_KEY"
    "TEST_YACHT_ID"
    "API_BASE_URL"
    "CREW_JWT"
    "DECKHAND_JWT"
    "STEWARD_JWT"
    "ENGINEER_JWT"
    "ETO_JWT"
    "CHIEF_ENGINEER_JWT"
    "CHIEF_OFFICER_JWT"
    "CHIEF_STEWARD_JWT"
    "PURSER_JWT"
    "CAPTAIN_JWT"
    "MANAGER_JWT"
    "INACTIVE_JWT"
    "EXPIRED_JWT"
    "WRONG_YACHT_JWT"
    "MIXED_ROLE_JWT"
)

MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
        echo "  ✗ $var: NOT SET"
    else
        # Truncate sensitive values for display
        value="${!var}"
        if [[ "$var" == *"JWT"* ]] || [[ "$var" == *"KEY"* ]]; then
            display_value="${value:0:20}...${value: -10}"
        else
            display_value="$value"
        fi
        echo "  ✓ $var: $display_value"
    fi
done

echo ""

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo "❌ ERROR: Missing required environment variables:"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Please export all required variables and try again."
    echo "See docs/architecture/entity_lenses/receiving_lens/v1/TESTING_EVIDENCE.md for details."
    exit 1
fi

echo "✅ All environment variables set"
echo ""

# ============================================================================
# STEP 2: Run Acceptance Tests
# ============================================================================

echo "============================================================================"
echo "Step 2: Running Acceptance Tests"
echo "============================================================================"
echo ""

cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS

echo "Running pytest with verbose output..."
echo ""

if pytest apps/api/tests/test_receiving_lens_v1_acceptance.py -v --tb=short --color=yes; then
    echo ""
    echo "✅ Acceptance tests PASSED"
    ACCEPTANCE_RESULT="PASS"
else
    echo ""
    echo "❌ Acceptance tests FAILED"
    ACCEPTANCE_RESULT="FAIL"
fi

echo ""

# ============================================================================
# STEP 3: Run Stress Test
# ============================================================================

echo "============================================================================"
echo "Step 3: Running Stress Test"
echo "============================================================================"
echo ""

STRESS_OUTPUT="receiving-stress-$(date +%Y%m%d-%H%M%S).json"

echo "Output file: $STRESS_OUTPUT"
echo ""

if OUTPUT_JSON="$STRESS_OUTPUT" TEST_JWT="$CHIEF_ENGINEER_JWT" python tests/stress/stress_receiving_actions.py; then
    echo ""
    echo "✅ Stress test PASSED"
    STRESS_RESULT="PASS"
else
    echo ""
    echo "❌ Stress test FAILED"
    STRESS_RESULT="FAIL"
fi

echo ""

# ============================================================================
# STEP 4: Generate Evidence Summary
# ============================================================================

echo "============================================================================"
echo "Step 4: Evidence Summary"
echo "============================================================================"
echo ""

if [ -f "$STRESS_OUTPUT" ]; then
    echo "Stress Test Metrics:"
    echo "-------------------"

    TOTAL=$(jq '.summary.total_requests' "$STRESS_OUTPUT")
    SUCCESS=$(jq '.summary.success_count' "$STRESS_OUTPUT")
    SUCCESS_RATE=$(jq '.summary.success_rate' "$STRESS_OUTPUT")
    P50=$(jq '.summary.latency_p50' "$STRESS_OUTPUT")
    P95=$(jq '.summary.latency_p95' "$STRESS_OUTPUT")
    P99=$(jq '.summary.latency_p99' "$STRESS_OUTPUT")
    SERVER_ERRORS=$(jq '.summary.server_errors' "$STRESS_OUTPUT")

    echo "Total Requests: $TOTAL"
    echo "Success Rate: ${SUCCESS_RATE}%"
    echo "P50 Latency: ${P50}ms"
    echo "P95 Latency: ${P95}ms"
    echo "P99 Latency: ${P99}ms"
    echo "Server Errors (500+): $SERVER_ERRORS"
    echo ""

    if [ "$SERVER_ERRORS" -eq 0 ]; then
        echo "✅ Zero 500s confirmed"
    else
        echo "⚠️  WARNING: $SERVER_ERRORS server errors detected"
    fi
else
    echo "⚠️  Stress test output file not found: $STRESS_OUTPUT"
fi

echo ""
echo "============================================================================"
echo "Overall Results"
echo "============================================================================"
echo ""
echo "Acceptance Tests: $ACCEPTANCE_RESULT"
echo "Stress Test: $STRESS_RESULT"
echo ""

# ============================================================================
# STEP 5: Generate PR Evidence Document
# ============================================================================

if [ "$ACCEPTANCE_RESULT" = "PASS" ] && [ "$STRESS_RESULT" = "PASS" ]; then
    echo "✅ ALL TESTS PASSED"
    echo ""
    echo "Next steps:"
    echo "1. Review stress test results: $STRESS_OUTPUT"
    echo "2. Capture sample signed acceptance (see TESTING_EVIDENCE.md)"
    echo "3. Create PR with evidence bundle"
    echo "4. Deploy to production"
    echo "5. Canary monitor for 30-60 minutes"
    echo ""
    echo "Evidence files ready for PR:"
    echo "  - DB Gates: docs/architecture/entity_lenses/receiving_lens/v1/TESTING_EVIDENCE.md"
    echo "  - Stress Results: $STRESS_OUTPUT"
    echo "  - Acceptance Tests: pytest output above"
    echo ""
    exit 0
else
    echo "❌ TESTS FAILED - Fix issues before creating PR"
    echo ""
    echo "Failed components:"
    [ "$ACCEPTANCE_RESULT" = "FAIL" ] && echo "  - Acceptance Tests"
    [ "$STRESS_RESULT" = "FAIL" ] && echo "  - Stress Test"
    echo ""
    exit 1
fi
