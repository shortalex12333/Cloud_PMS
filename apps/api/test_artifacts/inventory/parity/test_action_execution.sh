#!/bin/bash
# Test action execution with error mapping and role gating
# Client errors must be 4xx, never 500

OUTPUT_DIR="/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api/test_artifacts/inventory/parity"
API_URL="${API_URL:-https://pipeline-core.int.celeste7.ai}"
CREW_JWT=$(jq -r '.crew.access_token' /private/tmp/claude/-Volumes-Backup-CELESTE/c98cc619-82ab-402f-91a6-c868af22a09a/scratchpad/test_user_tokens.json)
HOD_JWT=$(jq -r '.hod.access_token' /private/tmp/claude/-Volumes-Backup-CELESTE/c98cc619-82ab-402f-91a6-c868af22a09a/scratchpad/test_user_tokens.json)
YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"

echo "=========================================================================="
echo "ACTION EXECUTION TESTS"
echo "Testing error mapping and role gating"
echo "=========================================================================="
echo

# Test 1: Invalid part_id should return 4xx, NOT 500
echo "Test 1: Invalid part_id handling (should be 4xx, not 500)"
echo "----------------------------------------------------------------------"
HTTP_CODE=$(curl -sS -o "$OUTPUT_DIR/invalid_part_response.json" -w "%{http_code}" \
  -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  "$API_URL/v1/actions/execute" \
  -d "{
    \"action_id\": \"check_stock_level\",
    \"yacht_id\": \"$YACHT_ID\",
    \"part_id\": \"00000000-0000-0000-0000-000000000000\"
  }")

echo "HTTP Status Code: $HTTP_CODE"
if [ "$HTTP_CODE" -ge 400 ] && [ "$HTTP_CODE" -lt 500 ]; then
  echo "✅ PASS: Invalid part_id returns 4xx ($HTTP_CODE)"
elif [ "$HTTP_CODE" == "500" ]; then
  echo "❌ FAIL: Invalid part_id returns 500 (should be 4xx)"
else
  echo "⚠️  UNKNOWN: Unexpected status code $HTTP_CODE"
fi
echo

# Test 2: Crew attempting MUTATE action should return 403
echo "Test 2: Crew attempting MUTATE action (should be 403 forbidden)"
echo "----------------------------------------------------------------------"
HTTP_CODE=$(curl -sS -o "$OUTPUT_DIR/crew_mutate_response.json" -w "%{http_code}" \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  "$API_URL/v1/actions/execute" \
  -d "{
    \"action_id\": \"log_part_usage\",
    \"yacht_id\": \"$YACHT_ID\",
    \"part_id\": \"12345678-1234-1234-1234-123456789012\",
    \"quantity_used\": 1,
    \"work_order_id\": \"12345678-1234-1234-1234-123456789012\",
    \"notes\": \"test usage log\"
  }")

echo "HTTP Status Code: $HTTP_CODE"
if [ "$HTTP_CODE" == "403" ]; then
  echo "✅ PASS: Crew forbidden from MUTATE action (403)"
elif [ "$HTTP_CODE" == "200" ]; then
  echo "❌ FAIL: Crew allowed to execute MUTATE action (should be 403)"
else
  echo "⚠️  Status: $HTTP_CODE (expected 403)"
fi
echo

# Test 3: HOD executing MUTATE action should NOT be 403
echo "Test 3: HOD executing MUTATE action (should be 200/404, not 403)"
echo "----------------------------------------------------------------------"
HTTP_CODE=$(curl -sS -o "$OUTPUT_DIR/hod_mutate_response.json" -w "%{http_code}" \
  -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  "$API_URL/v1/actions/execute" \
  -d "{
    \"action_id\": \"log_part_usage\",
    \"yacht_id\": \"$YACHT_ID\",
    \"part_id\": \"12345678-1234-1234-1234-123456789012\",
    \"quantity_used\": 1,
    \"work_order_id\": \"12345678-1234-1234-1234-123456789012\",
    \"notes\": \"test usage log\"
  }")

echo "HTTP Status Code: $HTTP_CODE"
if [ "$HTTP_CODE" == "200" ]; then
  echo "✅ PASS: HOD successfully executed MUTATE action (200)"
elif [ "$HTTP_CODE" == "404" ]; then
  echo "✅ PASS: HOD authorized (404 = part not found, not auth failure)"
elif [ "$HTTP_CODE" == "403" ]; then
  echo "❌ FAIL: HOD forbidden from MUTATE action (should be allowed)"
else
  echo "⚠️  Status: $HTTP_CODE"
fi
echo

# Test 4: Missing required field should return 400
echo "Test 4: Missing required field (should be 400 bad request)"
echo "----------------------------------------------------------------------"
HTTP_CODE=$(curl -sS -o "$OUTPUT_DIR/missing_field_response.json" -w "%{http_code}" \
  -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  "$API_URL/v1/actions/execute" \
  -d "{
    \"action_id\": \"check_stock_level\",
    \"yacht_id\": \"$YACHT_ID\"
  }")

echo "HTTP Status Code: $HTTP_CODE"
if [ "$HTTP_CODE" == "400" ]; then
  echo "✅ PASS: Missing required field returns 400"
elif [ "$HTTP_CODE" == "500" ]; then
  echo "❌ FAIL: Missing field returns 500 (should be 400)"
else
  echo "⚠️  Status: $HTTP_CODE (expected 400)"
fi
echo

# Test 5: Invalid action_id should return 4xx
echo "Test 5: Invalid action_id (should be 400/404, not 500)"
echo "----------------------------------------------------------------------"
HTTP_CODE=$(curl -sS -o "$OUTPUT_DIR/invalid_action_response.json" -w "%{http_code}" \
  -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  "$API_URL/v1/actions/execute" \
  -d "{
    \"action_id\": \"nonexistent_action\",
    \"yacht_id\": \"$YACHT_ID\"
  }")

echo "HTTP Status Code: $HTTP_CODE"
if [ "$HTTP_CODE" -ge 400 ] && [ "$HTTP_CODE" -lt 500 ]; then
  echo "✅ PASS: Invalid action_id returns 4xx ($HTTP_CODE)"
elif [ "$HTTP_CODE" == "500" ]; then
  echo "❌ FAIL: Invalid action_id returns 500 (should be 4xx)"
else
  echo "⚠️  Status: $HTTP_CODE"
fi
echo

echo "=========================================================================="
echo "ACTION EXECUTION TEST COMPLETE"
echo "Response files saved to:"
echo "  $OUTPUT_DIR/invalid_part_response.json"
echo "  $OUTPUT_DIR/crew_mutate_response.json"
echo "  $OUTPUT_DIR/hod_mutate_response.json"
echo "  $OUTPUT_DIR/missing_field_response.json"
echo "  $OUTPUT_DIR/invalid_action_response.json"
echo "=========================================================================="
