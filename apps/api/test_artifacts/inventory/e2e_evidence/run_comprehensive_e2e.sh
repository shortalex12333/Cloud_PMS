#!/bin/bash
# Comprehensive E2E Testing with Hard Evidence
# Tests all actions with different roles and validates proper behavior

set -e

OUTPUT_DIR="$(pwd)/test_artifacts/inventory/e2e_evidence"
mkdir -p "$OUTPUT_DIR"

# Load tokens (from project root: ../../.. from apps/api)
CREW_JWT=$(jq -r '.CREW.jwt' ../../test-jwts.json)
HOD_JWT=$(jq -r '.HOD.jwt' ../../test-jwts.json)
YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"
API_URL="https://pipeline-core.int.celeste7.ai"

# Evidence log
EVIDENCE_LOG="$OUTPUT_DIR/EVIDENCE_LOG.md"

echo "# E2E Testing Evidence - $(date)" > "$EVIDENCE_LOG"
echo "" >> "$EVIDENCE_LOG"
echo "## Test Environment" >> "$EVIDENCE_LOG"
echo "- API URL: $API_URL" >> "$EVIDENCE_LOG"
echo "- Yacht ID: $YACHT_ID" >> "$EVIDENCE_LOG"
echo "- Date: $(date)" >> "$EVIDENCE_LOG"
echo "" >> "$EVIDENCE_LOG"
echo "---" >> "$EVIDENCE_LOG"
echo "" >> "$EVIDENCE_LOG"

PASS_COUNT=0
FAIL_COUNT=0

# Helper function to test and log
test_endpoint() {
    local test_name="$1"
    local jwt="$2"
    local method="$3"
    local endpoint="$4"
    local data="$5"
    local expected_status="$6"
    local validation_jq="$7"

    echo "" >> "$EVIDENCE_LOG"
    echo "## Test: $test_name" >> "$EVIDENCE_LOG"
    echo "" >> "$EVIDENCE_LOG"
    echo "**Request:**" >> "$EVIDENCE_LOG"
    echo "\`\`\`" >> "$EVIDENCE_LOG"
    echo "$method $endpoint" >> "$EVIDENCE_LOG"
    if [ -n "$data" ]; then
        echo "$data" >> "$EVIDENCE_LOG"
    fi
    echo "\`\`\`" >> "$EVIDENCE_LOG"
    echo "" >> "$EVIDENCE_LOG"

    # Make request and capture response
    local response_file="$OUTPUT_DIR/$(echo "$test_name" | tr ' ' '_' | tr '[:upper:]' '[:lower:]').json"

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
    cat "$response_file" | jq '.' >> "$EVIDENCE_LOG" 2>/dev/null || cat "$response_file" >> "$EVIDENCE_LOG"
    echo "\`\`\`" >> "$EVIDENCE_LOG"
    echo "" >> "$EVIDENCE_LOG"

    # Validate
    local validation_result="UNKNOWN"
    if [ "$HTTP_STATUS" == "$expected_status" ]; then
        if [ -n "$validation_jq" ]; then
            local jq_result=$(cat "$response_file" | jq -r "$validation_jq" 2>/dev/null)
            if [ "$jq_result" == "true" ] || [ "$jq_result" == "pass" ]; then
                validation_result="✅ PASS"
                ((PASS_COUNT++))
            else
                validation_result="❌ FAIL (validation failed: $jq_result)"
                ((FAIL_COUNT++))
            fi
        else
            validation_result="✅ PASS"
            ((PASS_COUNT++))
        fi
    else
        validation_result="❌ FAIL (expected $expected_status, got $HTTP_STATUS)"
        ((FAIL_COUNT++))
    fi

    echo "**Result:** $validation_result" >> "$EVIDENCE_LOG"
    echo "" >> "$EVIDENCE_LOG"
    echo "---" >> "$EVIDENCE_LOG"

    echo "$validation_result - $test_name"
}

echo "=========================================================================="
echo "COMPREHENSIVE E2E TESTING - INVENTORY LENS"
echo "=========================================================================="
echo ""

# TEST 1: /v2/search with crew - expect context + actions
echo "TEST 1: /v2/search with crew role"
test_endpoint \
    "v2_search_crew_parts_query" \
    "$CREW_JWT" \
    "POST" \
    "/v2/search" \
    '{"query_text":"parts low in stock"}' \
    "200" \
    '(.context != null and .actions != null and (.actions | length) == 2)'

# TEST 2: /v2/search with HOD - expect context + actions
echo "TEST 2: /v2/search with HOD role"
test_endpoint \
    "v2_search_hod_parts_query" \
    "$HOD_JWT" \
    "POST" \
    "/v2/search" \
    '{"query_text":"parts low in stock"}' \
    "200" \
    '(.context != null and .actions != null and (.actions | length) >= 8)'

# TEST 3: Crew READ action - check_stock_level (should work or 404)
echo "TEST 3: Crew executing READ action (check_stock_level)"
test_endpoint \
    "crew_read_action_check_stock" \
    "$CREW_JWT" \
    "POST" \
    "/v1/actions/execute" \
    '{"action":"check_stock_level","context":{"yacht_id":"'$YACHT_ID'"},"payload":{"part_id":"00000000-0000-0000-0000-000000000000"}}' \
    "404" \
    ''

# TEST 4: Crew MUTATE action - log_part_usage (should 403)
echo "TEST 4: Crew attempting MUTATE action (log_part_usage) - expect 403"
test_endpoint \
    "crew_mutate_action_denied" \
    "$CREW_JWT" \
    "POST" \
    "/v1/actions/execute" \
    '{"action":"log_part_usage","context":{"yacht_id":"'$YACHT_ID'"},"payload":{"part_id":"00000000-0000-0000-0000-000000000000","quantity":1,"usage_reason":"maintenance","notes":"test"}}' \
    "403" \
    ''

# TEST 5: HOD MUTATE action - log_part_usage (should work or 404)
echo "TEST 5: HOD executing MUTATE action (log_part_usage)"
test_endpoint \
    "hod_mutate_action_allowed" \
    "$HOD_JWT" \
    "POST" \
    "/v1/actions/execute" \
    '{"action":"log_part_usage","context":{"yacht_id":"'$YACHT_ID'"},"payload":{"part_id":"00000000-0000-0000-0000-000000000000","quantity":1,"usage_reason":"maintenance","notes":"test"}}' \
    "404" \
    ''

# TEST 6: Invalid part_id - should return 404 not 500
echo "TEST 6: Invalid part_id error mapping"
test_endpoint \
    "invalid_part_id_error_mapping" \
    "$HOD_JWT" \
    "POST" \
    "/v1/actions/execute" \
    '{"action":"check_stock_level","context":{"yacht_id":"'$YACHT_ID'"},"payload":{"part_id":"invalid-uuid-format"}}' \
    "400" \
    ''

# TEST 7: Missing required field - should return 400
echo "TEST 7: Missing required field error mapping"
test_endpoint \
    "missing_field_error_mapping" \
    "$HOD_JWT" \
    "POST" \
    "/v1/actions/execute" \
    '{"action":"check_stock_level","context":{"yacht_id":"'$YACHT_ID'"},"payload":{}}' \
    "400" \
    ''

# TEST 8: Verify parts routing (not work orders)
echo "TEST 8: Parts routing verification"
test_endpoint \
    "parts_routing_verification" \
    "$CREW_JWT" \
    "POST" \
    "/v2/search" \
    '{"query_text":"oil filter"}' \
    "200" \
    '((.results | length) == 0 or .results[0].domain == "parts")'

echo ""
echo "=========================================================================="
echo "TEST SUMMARY"
echo "=========================================================================="
echo "Passed: $PASS_COUNT"
echo "Failed: $FAIL_COUNT"
echo "Total: $((PASS_COUNT + FAIL_COUNT))"
echo ""
echo "Evidence saved to: $EVIDENCE_LOG"
echo "Response files saved to: $OUTPUT_DIR/"
echo "=========================================================================="

if [ $FAIL_COUNT -gt 0 ]; then
    echo ""
    echo "⚠️  FAILURES DETECTED - See $EVIDENCE_LOG for details"
    exit 1
else
    echo ""
    echo "✅ ALL TESTS PASSED"
    exit 0
fi
