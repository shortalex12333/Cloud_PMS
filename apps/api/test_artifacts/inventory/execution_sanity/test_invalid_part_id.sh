#!/bin/bash
# Test action execution with invalid part_id - should return 400/404, NOT 500

API_URL="${API_URL:-https://celeste-9dce.onrender.com}"
CREW_JWT=$(jq -r '.crew.access_token' /private/tmp/claude/-Volumes-Backup-CELESTE/c98cc619-82ab-402f-91a6-c868af22a09a/scratchpad/test_user_tokens.json)

echo "Test: Execute action with invalid part_id"
echo "=========================================================================="
echo "Action: check_stock_level"
echo "part_id: 00000000-0000-0000-0000-000000000000 (invalid)"
echo "Expected: 400 or 404 (client error), NOT 500"
echo

curl -i -sS -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: 85fe1119-b04c-41ac-80f1-829d23322598" \
  "$API_URL/v1/actions/execute" \
  -d '{
    "action_id": "check_stock_level",
    "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
    "part_id": "00000000-0000-0000-0000-000000000000"
  }' 2>&1 | tee /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api/test_artifacts/inventory/execution_sanity/invalid_part_id_response.txt

echo
echo "Checking status code..."
STATUS=$(grep "HTTP/" /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api/test_artifacts/inventory/execution_sanity/invalid_part_id_response.txt | awk '{print $2}')
echo "Status code: $STATUS"

if [ "$STATUS" == "400" ] || [ "$STATUS" == "404" ]; then
  echo "✅ PASS: Received client error ($STATUS), not 500"
elif [ "$STATUS" == "500" ]; then
  echo "❌ FAIL: Received 500 (server error) - should be 400/404"
else
  echo "⚠️  UNKNOWN: Received status $STATUS"
fi
