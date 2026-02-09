#!/bin/bash
# Manual test for CRITICAL RBAC fix (can run before full deployment)

set -e

echo "============================================"
echo "MANUAL RBAC FIX TEST"
echo "============================================"
echo ""

API_BASE="${API_BASE:-https://pipeline-core.int.celeste7.ai}"
YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"

if [ ! -f "test-jwts.json" ]; then
    echo "ERROR: test-jwts.json not found"
    exit 1
fi

CREW_JWT=$(jq -r '.CREW.jwt' test-jwts.json)

echo "Testing: Crew user creates DECK work order"
echo "API: $API_BASE"
echo ""

RESULT=$(curl -s -w "\nHTTP:%{http_code}" -X POST "$API_BASE/v1/actions/execute" \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d "{
    \"action\": \"create_work_order\",
    \"context\": {
      \"yacht_id\": \"$YACHT_ID\"
    },
    \"payload\": {
      \"title\": \"Manual RBAC Test - DECK Work Order\",
      \"department\": \"deck\",
      \"priority\": \"medium\",
      \"description\": \"Testing department RBAC fix after deployment\"
    }
  }")

HTTP_CODE=$(echo "$RESULT" | grep "HTTP:" | cut -d':' -f2)
RESPONSE=$(echo "$RESULT" | grep -v "HTTP:")

echo "Response:"
echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
echo ""
echo "HTTP Status: $HTTP_CODE"
echo ""

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
    echo "✅ SUCCESS: RBAC fix is working!"
    echo "   Crew user can create work orders in their department"
    exit 0
elif [ "$HTTP_CODE" = "403" ]; then
    echo "❌ FAILURE: RBAC fix NOT working"
    echo "   Crew user still blocked (403 Forbidden)"
    echo "   This means old code is still deployed"
    exit 1
else
    echo "⚠️  UNEXPECTED: HTTP $HTTP_CODE"
    echo "   Review response above"
    exit 1
fi
