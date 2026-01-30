#!/bin/bash
# =============================================================================
# Part Lens v2 - Deployment Verification Script
# =============================================================================
# Verifies Part Lens v2 deployment on staging with comprehensive smoke tests
# Exit code 0 = all tests pass, 1 = any test fails
#
# Usage:
#   ./scripts/ops/verify_part_lens_v2_deployment.sh [expected_commit]
#
# Environment:
#   HOD_JWT - Required JWT token for authentication
#   API_BASE - API base URL (default: https://pipeline-core.int.celeste7.ai)
# =============================================================================

set -euo pipefail

# Configuration
API_BASE="${API_BASE:-https://pipeline-core.int.celeste7.ai}"
EXPECTED_COMMIT="${1:-f72d159}"
YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"
PART_ID="8ad67e2f-2579-4d6c-afd2-0dee85f4d8b3"

# HOD JWT with long expiry
HOD_JWT="${HOD_JWT:-eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL3F2em1rYWFtemFxeHB6YmV3anhlLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI4OWIxMjYyYy1mZjU5LTQ1OTEtYjk1NC03NTdjZGYzZDYwOWQiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxODAxMTQzMTk0LCJpYXQiOjE3Njk1OTk5OTQsImVtYWlsIjoiaG9kLnRlbmFudEBhbGV4LXNob3J0LmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnt9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzY5NTk5OTk0fV0sInNlc3Npb25faWQiOiJjaS10ZXN0LTg5YjEyNjJjIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.eHSqBRQrBpARVVyAc_IuQWJ-9JGIs08yEFLH1kkhUyg}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Results array
declare -a RESULTS

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

test_pass() {
    local test_name="$1"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    RESULTS+=("✅ PASS: $test_name")
    echo -e "${GREEN}✓${NC} $test_name"
}

test_fail() {
    local test_name="$1"
    local reason="$2"
    FAILED_TESTS=$((FAILED_TESTS + 1))
    RESULTS+=("❌ FAIL: $test_name - $reason")
    echo -e "${RED}✗${NC} $test_name - $reason"
}

run_test() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
}

# =============================================================================
# Test 1: Version Endpoint
# =============================================================================
test_version() {
    run_test
    log_info "Test 1: Checking deployed commit version..."

    RESPONSE=$(curl -sf "$API_BASE/version" || echo '{"error": "failed"}')
    DEPLOYED_COMMIT=$(echo "$RESPONSE" | jq -r '.git_commit' 2>/dev/null || echo "")

    if [ -z "$DEPLOYED_COMMIT" ]; then
        test_fail "Version Endpoint" "No commit hash returned"
        return 1
    fi

    # Check if deployed commit starts with expected (7-char match)
    if [[ "$DEPLOYED_COMMIT" == "$EXPECTED_COMMIT"* ]]; then
        test_pass "Version Endpoint - Commit: ${DEPLOYED_COMMIT:0:7}"
    else
        test_fail "Version Endpoint" "Expected $EXPECTED_COMMIT, got ${DEPLOYED_COMMIT:0:7}"
        return 1
    fi
}

# =============================================================================
# Test 2: Health Endpoint
# =============================================================================
test_health() {
    run_test
    log_info "Test 2: Health check..."

    RESPONSE=$(curl -sf "$API_BASE/health" || echo '{"error": "failed"}')
    STATUS=$(echo "$RESPONSE" | jq -r '.status' 2>/dev/null || echo "")

    if [[ "$STATUS" == "healthy" || "$STATUS" == "ok" ]]; then
        test_pass "Health Endpoint"
    else
        test_fail "Health Endpoint" "Status: $STATUS"
        return 1
    fi
}

# =============================================================================
# Test 3: view_part_details (Direct SQL)
# =============================================================================
test_view_part_details() {
    run_test
    log_info "Test 3: view_part_details (Direct SQL)..."

    PAYLOAD=$(cat <<EOF
{
  "action": "view_part_details",
  "context": {"yacht_id": "$YACHT_ID"},
  "payload": {"part_id": "$PART_ID"}
}
EOF
)

    RESPONSE=$(curl -sf -X POST \
        -H "Authorization: Bearer $HOD_JWT" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" \
        "$API_BASE/v1/actions/execute" || echo '{"error": "request_failed"}')

    STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        -H "Authorization: Bearer $HOD_JWT" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" \
        "$API_BASE/v1/actions/execute")

    if [ "$STATUS_CODE" -eq 200 ]; then
        ON_HAND=$(echo "$RESPONSE" | jq -r '.data.stock.on_hand' 2>/dev/null || echo "null")
        if [ "$ON_HAND" != "null" ]; then
            test_pass "view_part_details - Stock: $ON_HAND"
        else
            test_fail "view_part_details" "200 but missing stock data"
        fi
    elif [ "$STATUS_CODE" -eq 400 ]; then
        ERROR_MSG=$(echo "$RESPONSE" | jq -r '.detail.message' 2>/dev/null || echo "Unknown")
        if [[ "$ERROR_MSG" == *"204"* || "$ERROR_MSG" == *"Missing response"* ]]; then
            test_fail "view_part_details" "PostgREST 204 error - Direct SQL not deployed"
        else
            test_fail "view_part_details" "400: $ERROR_MSG"
        fi
    else
        test_fail "view_part_details" "HTTP $STATUS_CODE"
    fi
}

# =============================================================================
# Test 4: consume_part (Sufficient Stock)
# =============================================================================
test_consume_part_sufficient() {
    run_test
    log_info "Test 4: consume_part (sufficient stock)..."

    PAYLOAD=$(cat <<EOF
{
  "action": "consume_part",
  "context": {"yacht_id": "$YACHT_ID"},
  "payload": {
    "part_id": "$PART_ID",
    "quantity": 1
  }
}
EOF
)

    RESPONSE=$(curl -sf -X POST \
        -H "Authorization: Bearer $HOD_JWT" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" \
        "$API_BASE/v1/actions/execute" || echo '{"error": "request_failed"}')

    STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        -H "Authorization: Bearer $HOD_JWT" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" \
        "$API_BASE/v1/actions/execute")

    if [ "$STATUS_CODE" -eq 200 ]; then
        QTY_BEFORE=$(echo "$RESPONSE" | jq -r '.data.quantity_before' 2>/dev/null || echo "null")
        QTY_AFTER=$(echo "$RESPONSE" | jq -r '.data.quantity_after' 2>/dev/null || echo "null")

        if [ "$QTY_BEFORE" != "null" ] && [ "$QTY_AFTER" != "null" ]; then
            test_pass "consume_part (sufficient) - $QTY_BEFORE → $QTY_AFTER"
        else
            test_fail "consume_part (sufficient)" "200 but missing quantity data"
        fi
    else
        test_fail "consume_part (sufficient)" "HTTP $STATUS_CODE"
    fi
}

# =============================================================================
# Test 5: consume_part (Insufficient Stock)
# =============================================================================
test_consume_part_insufficient() {
    run_test
    log_info "Test 5: consume_part (insufficient stock)..."

    PAYLOAD=$(cat <<EOF
{
  "action": "consume_part",
  "context": {"yacht_id": "$YACHT_ID"},
  "payload": {
    "part_id": "$PART_ID",
    "quantity": 99999
  }
}
EOF
)

    STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        -H "Authorization: Bearer $HOD_JWT" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" \
        "$API_BASE/v1/actions/execute")

    if [ "$STATUS_CODE" -eq 409 ] || [ "$STATUS_CODE" -eq 400 ]; then
        test_pass "consume_part (insufficient) - HTTP $STATUS_CODE"
    else
        test_fail "consume_part (insufficient)" "Expected 409/400, got $STATUS_CODE"
    fi
}

# =============================================================================
# Test 6: Low Stock Suggestions
# =============================================================================
test_low_stock() {
    run_test
    log_info "Test 6: Low stock suggestions..."

    RESPONSE=$(curl -sf -H "Authorization: Bearer $HOD_JWT" \
        "$API_BASE/v1/parts/low-stock" || echo '{"error": "failed"}')

    STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $HOD_JWT" \
        "$API_BASE/v1/parts/low-stock")

    if [ "$STATUS_CODE" -eq 200 ]; then
        COUNT=$(echo "$RESPONSE" | jq '.data | length' 2>/dev/null || echo "0")
        test_pass "Low Stock Suggestions - $COUNT parts"
    else
        test_fail "Low Stock Suggestions" "HTTP $STATUS_CODE"
    fi
}

# =============================================================================
# Test 7: Part Suggestions (Focus)
# =============================================================================
test_part_suggestions() {
    run_test
    log_info "Test 7: Part suggestions (focus context)..."

    STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer $HOD_JWT" \
        "$API_BASE/v1/parts/suggestions?part_id=$PART_ID")

    if [ "$STATUS_CODE" -eq 200 ]; then
        test_pass "Part Suggestions"
    else
        test_fail "Part Suggestions" "HTTP $STATUS_CODE"
    fi
}

# =============================================================================
# Test 8: No 5xx Errors
# =============================================================================
test_no_5xx() {
    run_test
    log_info "Test 8: Verifying zero 5xx errors across all tests..."

    # Check if any test returned 5xx
    HAS_5XX=false
    for result in "${RESULTS[@]}"; do
        if [[ "$result" == *"HTTP 5"* ]]; then
            HAS_5XX=true
            break
        fi
    done

    if [ "$HAS_5XX" = false ]; then
        test_pass "Zero 5xx Errors"
    else
        test_fail "Zero 5xx Errors" "5xx detected in previous tests"
    fi
}

# =============================================================================
# Main Execution
# =============================================================================
main() {
    echo "============================================================================="
    echo "Part Lens v2 - Deployment Verification"
    echo "============================================================================="
    echo "API Base: $API_BASE"
    echo "Expected Commit: $EXPECTED_COMMIT"
    echo "============================================================================="
    echo ""

    # Run all tests
    test_version
    test_health
    test_view_part_details
    test_consume_part_sufficient
    test_consume_part_insufficient
    test_low_stock
    test_part_suggestions
    test_no_5xx

    # Summary
    echo ""
    echo "============================================================================="
    echo "VERIFICATION RESULTS"
    echo "============================================================================="
    echo "Total Tests: $TOTAL_TESTS"
    echo "Passed: $PASSED_TESTS"
    echo "Failed: $FAILED_TESTS"
    echo "Success Rate: $(awk "BEGIN {printf \"%.1f\", ($PASSED_TESTS/$TOTAL_TESTS)*100}")%"
    echo "============================================================================="
    echo ""

    # Print detailed results
    for result in "${RESULTS[@]}"; do
        echo "$result"
    done

    echo ""
    echo "============================================================================="

    # Exit code
    if [ "$FAILED_TESTS" -eq 0 ]; then
        echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
        echo "============================================================================="
        exit 0
    else
        echo -e "${RED}✗ SOME TESTS FAILED${NC}"
        echo "============================================================================="
        exit 1
    fi
}

main "$@"
