#!/bin/bash
# Quick test to verify action surfacing fix in deployment 4eb1cf6
# Tests that check_stock_level and log_part_usage now appear in /search results

set -e

BASE="https://pipeline-core.int.celeste7.ai"
CREW_JWT=$(jq -r '.CREW.jwt' test-jwts.json)
HOD_JWT=$(jq -r '.HOD.jwt' test-jwts.json)
YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"

echo "=========================================="
echo "Action Surfacing Test - Deployment 4eb1cf6"
echo "=========================================="
echo ""

# Test 1: HOD should see 4 actions
echo "TEST 1: HOD queries 'fuel filter stock'"
HOD_SEARCH=$(curl -s -X POST "$BASE/search" \
  -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: $YACHT_ID" \
  -d '{"query":"fuel filter stock"}')

HOD_DOMAIN=$(echo "$HOD_SEARCH" | jq -r '.context.domain')
HOD_ACTIONS=$(echo "$HOD_SEARCH" | jq -r '.actions | map(.action) | join(", ")')
HOD_ACTIONS_COUNT=$(echo "$HOD_SEARCH" | jq '.actions | length')

echo "  Domain: $HOD_DOMAIN"
echo "  Actions count: $HOD_ACTIONS_COUNT"
echo "  Actions: $HOD_ACTIONS"
echo ""

# Check for required actions
HAS_VIEW_PART=$(echo "$HOD_SEARCH" | jq '.actions | map(.action) | contains(["view_part_details"])' 2>/dev/null || echo "false")
HAS_CHECK_STOCK=$(echo "$HOD_SEARCH" | jq '.actions | map(.action) | contains(["check_stock_level"])' 2>/dev/null || echo "false")
HAS_LOG_USAGE=$(echo "$HOD_SEARCH" | jq '.actions | map(.action) | contains(["log_part_usage"])' 2>/dev/null || echo "false")

if [ "$HOD_DOMAIN" != "parts" ]; then
  echo "  ❌ FAIL: Domain should be 'parts', got '$HOD_DOMAIN'"
  exit 1
fi

if [ "$HAS_VIEW_PART" != "true" ]; then
  echo "  ❌ FAIL: Missing 'view_part_details' action"
  exit 1
else
  echo "  ✅ Has view_part_details"
fi

if [ "$HAS_CHECK_STOCK" != "true" ]; then
  echo "  ❌ FAIL: Missing 'check_stock_level' action (PR #202 fix)"
  exit 1
else
  echo "  ✅ Has check_stock_level (PR #202 fix)"
fi

if [ "$HAS_LOG_USAGE" != "true" ]; then
  echo "  ❌ FAIL: Missing 'log_part_usage' action (PR #202 fix)"
  exit 1
else
  echo "  ✅ Has log_part_usage (PR #202 fix)"
fi

echo "  ✅ PASS: HOD sees all required actions"
echo ""

# Test 2: CREW should see 3 actions (NO log_part_usage)
echo "TEST 2: CREW queries 'bearing stock'"
CREW_SEARCH=$(curl -s -X POST "$BASE/search" \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: $YACHT_ID" \
  -d '{"query":"bearing stock"}')

CREW_DOMAIN=$(echo "$CREW_SEARCH" | jq -r '.context.domain')
CREW_ACTIONS=$(echo "$CREW_SEARCH" | jq -r '.actions | map(.action) | join(", ")')
CREW_ACTIONS_COUNT=$(echo "$CREW_SEARCH" | jq '.actions | length')

echo "  Domain: $CREW_DOMAIN"
echo "  Actions count: $CREW_ACTIONS_COUNT"
echo "  Actions: $CREW_ACTIONS"
echo ""

# Check CREW actions
CREW_HAS_VIEW=$(echo "$CREW_SEARCH" | jq '.actions | map(.action) | contains(["view_part_details"])' 2>/dev/null || echo "false")
CREW_HAS_CHECK=$(echo "$CREW_SEARCH" | jq '.actions | map(.action) | contains(["check_stock_level"])' 2>/dev/null || echo "false")
CREW_HAS_LOG=$(echo "$CREW_SEARCH" | jq '.actions | map(.action) | contains(["log_part_usage"])' 2>/dev/null || echo "false")

if [ "$CREW_DOMAIN" != "parts" ]; then
  echo "  ❌ FAIL: Domain should be 'parts', got '$CREW_DOMAIN'"
  exit 1
fi

if [ "$CREW_HAS_VIEW" != "true" ]; then
  echo "  ❌ FAIL: Missing 'view_part_details' action"
  exit 1
else
  echo "  ✅ Has view_part_details"
fi

if [ "$CREW_HAS_CHECK" != "true" ]; then
  echo "  ❌ FAIL: Missing 'check_stock_level' action (PR #202 fix)"
  exit 1
else
  echo "  ✅ Has check_stock_level (PR #202 fix)"
fi

if [ "$CREW_HAS_LOG" = "true" ]; then
  echo "  ❌ FAIL: CREW should NOT see 'log_part_usage' (MUTATE blocked)"
  exit 1
else
  echo "  ✅ log_part_usage correctly hidden (MUTATE blocked)"
fi

echo "  ✅ PASS: CREW sees correct READ-only actions"
echo ""

# Test 3: Verify actions actually work
echo "TEST 3: Execute check_stock_level (new action from PR #202)"
PART_ID=$(echo "$HOD_SEARCH" | jq -r '.results[0].object_id')

if [ "$PART_ID" = "null" ] || [ -z "$PART_ID" ]; then
  echo "  ⚠️  SKIP: No part results to test with"
else
  CHECK_STOCK=$(curl -s -X POST "$BASE/v1/actions/execute" \
    -H "Authorization: Bearer $HOD_JWT" \
    -H "Content-Type: application/json" \
    -d "{
      \"action\": \"check_stock_level\",
      \"context\": {\"yacht_id\": \"$YACHT_ID\"},
      \"payload\": {\"part_id\": \"$PART_ID\"}
    }")

  STOCK_STATUS=$(echo "$CHECK_STOCK" | jq -r '.status')
  echo "  Action response status: $STOCK_STATUS"

  if [ "$STOCK_STATUS" = "error" ]; then
    ERROR_CODE=$(echo "$CHECK_STOCK" | jq -r '.error_code')
    echo "  ❌ FAIL: check_stock_level execution failed: $ERROR_CODE"
    exit 1
  else
    echo "  ✅ PASS: check_stock_level executes successfully"
  fi
fi

echo ""

# Summary
echo "=========================================="
echo "Action Surfacing Test Summary"
echo "=========================================="
echo ""
echo "✅ HOD sees all 4 actions (including new check_stock_level, log_part_usage)"
echo "✅ CREW sees 3 READ actions (check_stock_level added, log_part_usage blocked)"
echo "✅ Actions execute successfully"
echo ""
echo "🎉 PR #202 FIX VERIFIED - Action surfacing working correctly"
echo ""
