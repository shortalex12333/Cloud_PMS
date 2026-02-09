#!/bin/bash
# Test HOD executing MUTATE action - should return 200 (success)

API_URL="${API_URL:-https://celeste-9dce.onrender.com}"
HOD_JWT=$(jq -r '.hod.access_token' /private/tmp/claude/-Volumes-Backup-CELESTE/c98cc619-82ab-402f-91a6-c868af22a09a/scratchpad/test_user_tokens.json)

echo "Test: HOD executes MUTATE action (log_part_usage)"
echo "=========================================================================="
echo "Action: log_part_usage (MUTATE - requires engineer+)"
echo "Role: chief_engineer (HOD)"
echo "Expected: 200 (success) or 404 (part not found - still acceptable)"
echo

curl -i -sS -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: 85fe1119-b04c-41ac-80f1-829d23322598" \
  "$API_URL/v1/actions/execute" \
  -d '{
    "action_id": "log_part_usage",
    "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
    "part_id": "12345678-1234-1234-1234-123456789012",
    "quantity_used": 1,
    "work_order_id": "12345678-1234-1234-1234-123456789012",
    "notes": "test usage log"
  }' 2>&1 | tee /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api/test_artifacts/inventory/execution_sanity/hod_mutate_response.txt

echo
echo "Checking status code..."
STATUS=$(grep "HTTP/" /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api/test_artifacts/inventory/execution_sanity/hod_mutate_response.txt | awk '{print $2}')
echo "Status code: $STATUS"

if [ "$STATUS" == "200" ]; then
  echo "✅ PASS: HOD allowed to execute MUTATE action"
elif [ "$STATUS" == "404" ]; then
  echo "✅ PASS: HOD authorized (404 means part/wo not found, not auth failure)"
elif [ "$STATUS" == "403" ]; then
  echo "❌ FAIL: HOD forbidden from MUTATE action (should be allowed)"
else
  echo "⚠️  Status: $STATUS"
fi
