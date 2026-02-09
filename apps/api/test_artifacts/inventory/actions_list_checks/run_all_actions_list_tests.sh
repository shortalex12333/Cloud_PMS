#!/bin/bash
# Run all /v1/actions/list tests and save transcripts

OUTPUT_DIR="/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api/test_artifacts/inventory/actions_list_checks"
API_URL="${API_URL:-https://celeste-9dce.onrender.com}"
CREW_JWT=$(jq -r '.crew.access_token' /private/tmp/claude/-Volumes-Backup-CELESTE/c98cc619-82ab-402f-91a6-c868af22a09a/scratchpad/test_user_tokens.json)
HOD_JWT=$(jq -r '.hod.access_token' /private/tmp/claude/-Volumes-Backup-CELESTE/c98cc619-82ab-402f-91a6-c868af22a09a/scratchpad/test_user_tokens.json)

echo "=========================================================================="
echo "ACTION SUGGESTIONS CONTRACT VERIFICATION"
echo "Testing GET /v1/actions/list with different roles"
echo "=========================================================================="
echo

# Test 1: Crew role
echo "Test 1: Crew role (parts domain)"
echo "--------------------------------------------------------------------------"
curl -sS -H "Authorization: Bearer $CREW_JWT" \
  "$API_URL/v1/actions/list?domain=parts" \
  > "$OUTPUT_DIR/crew_parts_response.json"

cat "$OUTPUT_DIR/crew_parts_response.json" | jq '{
  role,
  total_count,
  action_ids: .actions | map(.action_id)
}'
echo

# Test 2: HOD role
echo "Test 2: HOD (chief_engineer) role (parts domain)"
echo "--------------------------------------------------------------------------"
curl -sS -H "Authorization: Bearer $HOD_JWT" \
  "$API_URL/v1/actions/list?domain=parts" \
  > "$OUTPUT_DIR/hod_parts_response.json"

cat "$OUTPUT_DIR/hod_parts_response.json" | jq '{
  role,
  total_count,
  action_ids: .actions | map(.action_id)
}'
echo

# Test 3: Compare results
echo "Test 3: Comparison"
echo "--------------------------------------------------------------------------"
CREW_COUNT=$(cat "$OUTPUT_DIR/crew_parts_response.json" | jq '.total_count')
HOD_COUNT=$(cat "$OUTPUT_DIR/hod_parts_response.json" | jq '.total_count')

echo "Crew total_count: $CREW_COUNT"
echo "HOD total_count: $HOD_COUNT"
echo

if [ "$HOD_COUNT" -gt "$CREW_COUNT" ]; then
  echo "✅ PASS: HOD has more actions than crew ($HOD_COUNT > $CREW_COUNT)"
else
  echo "❌ FAIL: HOD should have more actions than crew (HOD=$HOD_COUNT, crew=$CREW_COUNT)"
fi
echo

# Test 4: Verify crew only has READ actions
echo "Test 4: Verify crew only has READ actions"
echo "--------------------------------------------------------------------------"
CREW_VARIANTS=$(cat "$OUTPUT_DIR/crew_parts_response.json" | jq -r '.actions[].variant' | sort -u | tr '\n' ',')
echo "Crew variants: $CREW_VARIANTS"
if [ "$CREW_VARIANTS" == "READ," ]; then
  echo "✅ PASS: Crew only has READ actions"
else
  echo "❌ FAIL: Crew should only have READ actions, got: $CREW_VARIANTS"
fi
echo

# Test 5: Verify HOD has both READ and MUTATE
echo "Test 5: Verify HOD has READ and MUTATE actions"
echo "--------------------------------------------------------------------------"
HOD_VARIANTS=$(cat "$OUTPUT_DIR/hod_parts_response.json" | jq -r '.actions[].variant' | sort -u | tr '\n' ' ')
echo "HOD variants: $HOD_VARIANTS"
if echo "$HOD_VARIANTS" | grep -q "READ" && echo "$HOD_VARIANTS" | grep -q "MUTATE"; then
  echo "✅ PASS: HOD has both READ and MUTATE actions"
else
  echo "❌ FAIL: HOD should have READ and MUTATE actions, got: $HOD_VARIANTS"
fi
echo

echo "=========================================================================="
echo "ALL TESTS COMPLETE"
echo "Response files saved to:"
echo "  - $OUTPUT_DIR/crew_parts_response.json"
echo "  - $OUTPUT_DIR/hod_parts_response.json"
echo "=========================================================================="
