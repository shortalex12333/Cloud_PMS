#!/bin/bash
# Test GET /v1/actions/list as single authority for action suggestions
# Verify role-based filtering works correctly

OUTPUT_DIR="/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api/test_artifacts/inventory/parity"
API_URL="${API_URL:-https://pipeline-core.int.celeste7.ai}"
CREW_JWT=$(jq -r '.crew.access_token' /private/tmp/claude/-Volumes-Backup-CELESTE/c98cc619-82ab-402f-91a6-c868af22a09a/scratchpad/test_user_tokens.json)
HOD_JWT=$(jq -r '.hod.access_token' /private/tmp/claude/-Volumes-Backup-CELESTE/c98cc619-82ab-402f-91a6-c868af22a09a/scratchpad/test_user_tokens.json)

echo "=========================================================================="
echo "ACTION SUGGESTIONS CONTRACT VERIFICATION"
echo "Testing GET /v1/actions/list as single authority"
echo "=========================================================================="
echo

# Test 1: HOD should see check_stock_level action
echo "Test 1: HOD can see check_stock_level (READ action)"
echo "----------------------------------------------------------------------"
curl -sS -H "Authorization: Bearer $HOD_JWT" \
  "$API_URL/v1/actions/list?q=check+stock&domain=parts" \
  > "$OUTPUT_DIR/hod_check_stock.json"

HOD_CHECK=$(jq -r '.actions[] | select(.action_id=="check_stock_level") | .action_id' "$OUTPUT_DIR/hod_check_stock.json" 2>/dev/null)
if [ "$HOD_CHECK" == "check_stock_level" ]; then
  echo "✅ PASS: HOD can see check_stock_level"
else
  echo "❌ FAIL: HOD cannot see check_stock_level"
fi
echo

# Test 2: Crew should NOT see log_part_usage (MUTATE action)
echo "Test 2: Crew cannot see log_part_usage (MUTATE action)"
echo "----------------------------------------------------------------------"
curl -sS -H "Authorization: Bearer $CREW_JWT" \
  "$API_URL/v1/actions/list?q=log+part&domain=parts" \
  > "$OUTPUT_DIR/crew_log_part.json"

CREW_LOG=$(jq -r '.actions[] | select(.action_id=="log_part_usage") | .action_id' "$OUTPUT_DIR/crew_log_part.json" 2>/dev/null)
if [ -z "$CREW_LOG" ]; then
  echo "✅ PASS: Crew cannot see log_part_usage (forbidden)"
else
  echo "❌ FAIL: Crew can see log_part_usage (should be forbidden)"
fi
echo

# Test 3: HOD should see log_part_usage (MUTATE action)
echo "Test 3: HOD can see log_part_usage (MUTATE action)"
echo "----------------------------------------------------------------------"
curl -sS -H "Authorization: Bearer $HOD_JWT" \
  "$API_URL/v1/actions/list?q=log+part&domain=parts" \
  > "$OUTPUT_DIR/hod_log_part.json"

HOD_LOG=$(jq -r '.actions[] | select(.action_id=="log_part_usage") | .action_id' "$OUTPUT_DIR/hod_log_part.json" 2>/dev/null)
if [ "$HOD_LOG" == "log_part_usage" ]; then
  echo "✅ PASS: HOD can see log_part_usage"
else
  echo "❌ FAIL: HOD cannot see log_part_usage"
fi
echo

# Test 4: List all parts actions for crew
echo "Test 4: All parts actions for crew (READ only)"
echo "----------------------------------------------------------------------"
curl -sS -H "Authorization: Bearer $CREW_JWT" \
  "$API_URL/v1/actions/list?domain=parts" \
  > "$OUTPUT_DIR/crew_all_parts.json"

CREW_COUNT=$(jq -r '.actions | length' "$OUTPUT_DIR/crew_all_parts.json" 2>/dev/null)
CREW_VARIANTS=$(jq -r '.actions[].variant' "$OUTPUT_DIR/crew_all_parts.json" 2>/dev/null | sort -u | tr '\n' ',')
echo "Crew parts actions count: $CREW_COUNT"
echo "Crew variants: $CREW_VARIANTS"
if echo "$CREW_VARIANTS" | grep -q "READ," && ! echo "$CREW_VARIANTS" | grep -q "MUTATE"; then
  echo "✅ PASS: Crew only has READ actions"
else
  echo "❌ FAIL: Crew has non-READ actions: $CREW_VARIANTS"
fi
echo

# Test 5: List all parts actions for HOD
echo "Test 5: All parts actions for HOD (READ + MUTATE)"
echo "----------------------------------------------------------------------"
curl -sS -H "Authorization: Bearer $HOD_JWT" \
  "$API_URL/v1/actions/list?domain=parts" \
  > "$OUTPUT_DIR/hod_all_parts.json"

HOD_COUNT=$(jq -r '.actions | length' "$OUTPUT_DIR/hod_all_parts.json" 2>/dev/null)
HOD_VARIANTS=$(jq -r '.actions[].variant' "$OUTPUT_DIR/hod_all_parts.json" 2>/dev/null | sort -u | tr '\n' ' ')
echo "HOD parts actions count: $HOD_COUNT"
echo "HOD variants: $HOD_VARIANTS"
if echo "$HOD_VARIANTS" | grep -q "READ" && echo "$HOD_VARIANTS" | grep -q "MUTATE"; then
  echo "✅ PASS: HOD has both READ and MUTATE actions"
else
  echo "❌ FAIL: HOD missing READ or MUTATE: $HOD_VARIANTS"
fi
echo

# Test 6: Compare crew vs HOD counts
echo "Test 6: HOD should have more actions than crew"
echo "----------------------------------------------------------------------"
echo "Crew count: $CREW_COUNT"
echo "HOD count: $HOD_COUNT"
if [ "$HOD_COUNT" -gt "$CREW_COUNT" ]; then
  echo "✅ PASS: HOD has more actions than crew ($HOD_COUNT > $CREW_COUNT)"
else
  echo "❌ FAIL: HOD should have more actions (crew=$CREW_COUNT, HOD=$HOD_COUNT)"
fi
echo

echo "=========================================================================="
echo "SUGGESTIONS CONTRACT TEST COMPLETE"
echo "Response files saved to:"
echo "  $OUTPUT_DIR/hod_check_stock.json"
echo "  $OUTPUT_DIR/crew_log_part.json"
echo "  $OUTPUT_DIR/hod_log_part.json"
echo "  $OUTPUT_DIR/crew_all_parts.json"
echo "  $OUTPUT_DIR/hod_all_parts.json"
echo "=========================================================================="
