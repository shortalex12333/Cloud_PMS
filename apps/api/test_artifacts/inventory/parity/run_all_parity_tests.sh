#!/bin/bash
# Master script to run all parity tests with correct production URL

export API_URL="https://pipeline-core.int.celeste7.ai"

echo "Using production API: $API_URL"
echo

# Refresh JWTs if needed
echo "Checking JWT tokens..."
CREW_JWT=$(jq -r '.crew.access_token' /private/tmp/claude/-Volumes-Backup-CELESTE/c98cc619-82ab-402f-91a6-c868af22a09a/scratchpad/test_user_tokens.json 2>/dev/null)
if [ -z "$CREW_JWT" ] || [ "$CREW_JWT" == "null" ]; then
  echo "⚠️  JWT tokens not found or expired. Please run obtain_jwt_tokens.py first"
  exit 1
fi
echo "✓ JWT tokens found"
echo

# Test 1: Suggestions contract
echo "=========================================================================="
echo "TEST 1: ACTION SUGGESTIONS CONTRACT"
echo "=========================================================================="
bash /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api/test_artifacts/inventory/parity/test_suggestions_contract.sh
echo
echo

# Test 2: Action execution
echo "=========================================================================="
echo "TEST 2: ACTION EXECUTION"
echo "=========================================================================="
bash /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api/test_artifacts/inventory/parity/test_action_execution.sh
echo
echo

# Test 3: Endpoint parity
echo "=========================================================================="
echo "TEST 3: ENDPOINT PARITY"
echo "=========================================================================="
bash /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api/test_artifacts/inventory/parity/test_parity_all_endpoints.sh
echo
echo

echo "=========================================================================="
echo "ALL PARITY TESTS COMPLETE"
echo "=========================================================================="
