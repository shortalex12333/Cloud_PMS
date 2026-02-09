#!/bin/bash

# Deployment Verification Script - Commit 6b9292f
# Run after deployment completes (~5 minutes)

set -e

BASE="https://pipeline-core.int.celeste7.ai"
CREW_JWT=$(jq -r '.CREW.jwt' test-jwts.json)
HOD_JWT=$(jq -r '.HOD.jwt' test-jwts.json)
YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"

echo "========================================"
echo "Inventory Lens Deployment Verification"
echo "Commit: 6b9292f"
echo "Time: $(date)"
echo "========================================"
echo ""

# Test 1: Domain Detection - fuel filter
echo "✓ Test 1: Domain Detection (fuel filter)"
RESULT1=$(curl -s -X POST "$BASE/v2/search" \
  -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: $YACHT_ID" \
  -d '{"query_text":"fuel filter"}' | jq -r '.context.domain')
echo "  Result: $RESULT1"
if [ "$RESULT1" = "parts" ]; then
  echo "  Status: ✅ PASS"
else
  echo "  Status: ❌ FAIL (expected 'parts', got '$RESULT1')"
fi
echo ""

# Test 2: Fusion Normalization + Actions
echo "✓ Test 2: Fusion Normalization + Actions"
RESULT2=$(curl -s -X POST "$BASE/search" \
  -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: $YACHT_ID" \
  -d '{"query":"fuel filter"}' | jq '{domain:.context.domain,actions:(.actions|length)}')
echo "  Result: $RESULT2"
DOMAIN2=$(echo $RESULT2 | jq -r '.domain')
ACTIONS2=$(echo $RESULT2 | jq -r '.actions')
if [ "$DOMAIN2" = "parts" ] && [ "$ACTIONS2" -gt "0" ]; then
  echo "  Status: ✅ PASS"
else
  echo "  Status: ❌ FAIL (expected domain='parts' with actions>0)"
fi
echo ""

# Test 3: Domain Detection - bearing
echo "✓ Test 3: Domain Detection (bearing)"
RESULT3=$(curl -s -X POST "$BASE/v2/search" \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: $YACHT_ID" \
  -d '{"query_text":"bearing"}' | jq -r '.context.domain')
echo "  Result: $RESULT3"
if [ "$RESULT3" = "parts" ]; then
  echo "  Status: ✅ PASS"
else
  echo "  Status: ❌ FAIL (expected 'parts', got '$RESULT3')"
fi
echo ""

# Test 4: Role Gating (CREW blocked)
echo "✓ Test 4: Role Gating (CREW blocked from MUTATE)"
RESULT4=$(curl -s -w "\n%{http_code}" -X POST "$BASE/v1/actions/execute" \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action":"log_part_usage",
    "context":{"yacht_id":"'"$YACHT_ID"'"},
    "payload":{"part_id":"f7913ad1-6832-4169-b816-4538c8b7a417","quantity":1}
  }')
HTTP_CODE=$(echo "$RESULT4" | tail -n1)
ERROR_CODE=$(echo "$RESULT4" | head -n1 | jq -r '.error_code // empty')
echo "  HTTP Status: $HTTP_CODE"
echo "  Error Code: $ERROR_CODE"
if [ "$HTTP_CODE" = "403" ] && [ "$ERROR_CODE" = "FORBIDDEN" ]; then
  echo "  Status: ✅ PASS"
else
  echo "  Status: ❌ FAIL (expected HTTP 403 with error_code=FORBIDDEN)"
fi
echo ""

# Test 5: Suggestions (CREW READ-only)
echo "✓ Test 5: Suggestions Contract (CREW READ-only)"
RESULT5=$(curl -s "$BASE/v1/actions/list?q=check+stock&domain=parts" \
  -H "Authorization: Bearer $CREW_JWT" | jq '{
    total:(.actions|length),
    read:[.actions[]|select(.variant=="READ")|.action_id],
    mutate:[.actions[]|select(.variant=="MUTATE")|.action_id]
  }')
echo "  Result: $RESULT5"
MUTATE_COUNT=$(echo $RESULT5 | jq -r '.mutate | length')
if [ "$MUTATE_COUNT" = "0" ]; then
  echo "  Status: ✅ PASS"
else
  echo "  Status: ❌ FAIL (CREW should not see MUTATE actions)"
fi
echo ""

# Summary
echo "========================================"
echo "Verification Summary"
echo "========================================"
echo "Run at: $(date)"
echo ""
echo "Results:"
echo "  Test 1 (fuel filter domain): $([ "$RESULT1" = "parts" ] && echo "✅ PASS" || echo "❌ FAIL")"
echo "  Test 2 (fusion + actions): $([ "$DOMAIN2" = "parts" ] && [ "$ACTIONS2" -gt "0" ] && echo "✅ PASS" || echo "❌ FAIL")"
echo "  Test 3 (bearing domain): $([ "$RESULT3" = "parts" ] && echo "✅ PASS" || echo "❌ FAIL")"
echo "  Test 4 (CREW blocked): $([ "$HTTP_CODE" = "403" ] && echo "✅ PASS" || echo "❌ FAIL")"
echo "  Test 5 (suggestions): $([ "$MUTATE_COUNT" = "0" ] && echo "✅ PASS" || echo "❌ FAIL")"
echo ""

# Overall status
PASS_COUNT=0
[ "$RESULT1" = "parts" ] && PASS_COUNT=$((PASS_COUNT + 1))
[ "$DOMAIN2" = "parts" ] && [ "$ACTIONS2" -gt "0" ] && PASS_COUNT=$((PASS_COUNT + 1))
[ "$RESULT3" = "parts" ] && PASS_COUNT=$((PASS_COUNT + 1))
[ "$HTTP_CODE" = "403" ] && PASS_COUNT=$((PASS_COUNT + 1))
[ "$MUTATE_COUNT" = "0" ] && PASS_COUNT=$((PASS_COUNT + 1))

echo "Overall: $PASS_COUNT/5 tests passed"
echo ""

if [ "$PASS_COUNT" = "5" ]; then
  echo "🎉 DEPLOYMENT SUCCESSFUL - All tests passed!"
  exit 0
else
  echo "⚠️  DEPLOYMENT ISSUES - $(($5 - $PASS_COUNT)) test(s) failed"
  echo "    Check logs and consider rollback if critical"
  exit 1
fi
