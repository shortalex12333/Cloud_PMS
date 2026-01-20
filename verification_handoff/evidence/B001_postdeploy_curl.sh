#!/bin/bash
# B001 Post-Deploy Verification Script
# This script verifies the B001 fix is working
# Run AFTER deploying commit 57ce457 to Render
#
# Expected output: Bootstrap response with yacht_id, yacht_name, etc.

set -e

SUPABASE_URL="https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE"
PIPELINE_URL="https://pipeline-core.int.celeste7.ai"
TEST_EMAIL="x@alex-short.com"
TEST_PASSWORD="Password2!"
EXPECTED_YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"
EXPECTED_USER_ID="a35cad0b-02ff-4287-b6e4-17c96fa6a424"

echo "=== B001 POST-DEPLOY VERIFICATION ==="
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Fix Commit: 57ce457"
echo ""

# Step 1: Login to Supabase
echo "1. Logging in to Supabase..."
LOGIN_RESPONSE=$(curl -s -X POST "${SUPABASE_URL}/auth/v1/token?grant_type=password" \
  -H "apikey: ${SUPABASE_ANON_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${TEST_EMAIL}\",\"password\":\"${TEST_PASSWORD}\"}")

JWT=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token // empty')

if [ -z "$JWT" ]; then
  echo "ERROR: Failed to get JWT from Supabase"
  echo "$LOGIN_RESPONSE" | jq .
  exit 1
fi

echo "   JWT obtained: ${JWT:0:50}..."
echo ""

# Step 2: Verify JWT contains yacht_id claim
echo "2. Verifying JWT contains yacht_id claim..."
JWT_PAYLOAD=$(echo "$JWT" | cut -d'.' -f2 | base64 -d 2>/dev/null || echo "$JWT" | cut -d'.' -f2 | base64 -D 2>/dev/null)
JWT_YACHT_ID=$(echo "$JWT_PAYLOAD" | jq -r '.yacht_id // empty')

if [ "$JWT_YACHT_ID" = "$EXPECTED_YACHT_ID" ]; then
  echo "   ✅ JWT contains correct yacht_id: $JWT_YACHT_ID"
else
  echo "   ⚠️  JWT yacht_id mismatch or missing: $JWT_YACHT_ID"
fi
echo ""

# Step 3: Call bootstrap endpoint
echo "3. Calling /v1/bootstrap..."
BOOTSTRAP_RESPONSE=$(curl -s -X POST "${PIPELINE_URL}/v1/bootstrap" \
  -H "Authorization: Bearer ${JWT}" \
  -H "Content-Type: application/json")

echo "   Response:"
echo "$BOOTSTRAP_RESPONSE" | jq .
echo ""

# Step 4: Validate response
echo "4. Validating response..."

if echo "$BOOTSTRAP_RESPONSE" | grep -q "Signature verification failed"; then
  echo "=== B001 STILL ACTIVE ==="
  echo "❌ FAILED: Still getting signature verification error"
  echo ""
  echo "TROUBLESHOOTING:"
  echo "1. Verify Render deployed commit 57ce457"
  echo "2. Check TENANT_SUPABASE_JWT_SECRET is set in Render env vars"
  echo "3. Verify the secret value matches Supabase project JWT secret"
  exit 1
fi

RESPONSE_YACHT_ID=$(echo "$BOOTSTRAP_RESPONSE" | jq -r '.yacht_id // empty')
RESPONSE_USER_ID=$(echo "$BOOTSTRAP_RESPONSE" | jq -r '.user_id // empty')

if [ "$RESPONSE_YACHT_ID" = "$EXPECTED_YACHT_ID" ] && [ "$RESPONSE_USER_ID" = "$EXPECTED_USER_ID" ]; then
  echo "=== B001 FIXED ==="
  echo "✅ Bootstrap returned correct yacht_id: $RESPONSE_YACHT_ID"
  echo "✅ Bootstrap returned correct user_id: $RESPONSE_USER_ID"
  echo "✅ JWT signature verification working"
  echo ""
  echo "B001 is resolved. Proceed with remaining verification phases."
  exit 0
else
  echo "=== PARTIAL SUCCESS ==="
  echo "JWT verification passed but response validation issues:"
  echo "   yacht_id: expected=$EXPECTED_YACHT_ID, got=$RESPONSE_YACHT_ID"
  echo "   user_id: expected=$EXPECTED_USER_ID, got=$RESPONSE_USER_ID"
  exit 1
fi
