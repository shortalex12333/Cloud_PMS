#!/bin/bash
#
# test-auth-harness.sh - Local auth debugging harness
#
# Usage:
#   ./scripts/test-auth-harness.sh [local|preview|prod]
#
# Prerequisites:
#   - jq installed (brew install jq)
#   - .env.e2e.local file with MASTER credentials
#
# This script:
#   1. Mints a JWT from MASTER Supabase
#   2. Tests /api/debug/auth-dump to verify token validation
#   3. Tests /api/integrations/outlook/auth-url
#   4. Tests /api/integrations/outlook/status
#   5. Reports pass/fail for each

set -e

# Load environment
if [ -f ".env.e2e.local" ]; then
  export $(grep -v '^#' .env.e2e.local | xargs)
fi

# Target environment
ENV=${1:-local}
case $ENV in
  local)
    BASE_URL="http://localhost:3000"
    ;;
  preview)
    BASE_URL="${VERCEL_PREVIEW_URL:-https://preview.celeste7.ai}"
    ;;
  prod)
    BASE_URL="https://app.celeste7.ai"
    ;;
  *)
    echo "Usage: $0 [local|preview|prod]"
    exit 1
    ;;
esac

echo "============================================================"
echo "Auth Harness - Testing against: $BASE_URL"
echo "============================================================"
echo ""

# Check required env vars
if [ -z "$MASTER_SUPABASE_URL" ] || [ -z "$MASTER_SUPABASE_ANON_KEY" ]; then
  echo "ERROR: MASTER_SUPABASE_URL and MASTER_SUPABASE_ANON_KEY must be set"
  echo "Load from .env.e2e.local or export manually"
  exit 1
fi

# Step 1: Mint JWT from MASTER
echo "1. Minting JWT from MASTER Supabase..."
echo "   URL: $MASTER_SUPABASE_URL"

LOGIN_RESPONSE=$(curl -s -X POST "$MASTER_SUPABASE_URL/auth/v1/token?grant_type=password" \
  -H "apikey: $MASTER_SUPABASE_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_USER_EMAIL\",\"password\":\"$TEST_USER_PASSWORD\"}")

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')

if [ "$ACCESS_TOKEN" = "null" ] || [ -z "$ACCESS_TOKEN" ]; then
  echo "   FAIL: Could not get access token"
  echo "   Response: $LOGIN_RESPONSE"
  exit 1
fi

echo "   PASS: Got token (${#ACCESS_TOKEN} chars)"
echo ""

# Step 2: Test /api/debug/auth-dump (if available)
echo "2. Testing /api/debug/auth-dump..."
DEBUG_RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/debug/auth-dump" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

DEBUG_STATUS=$(echo "$DEBUG_RESPONSE" | tail -n1)
DEBUG_BODY=$(echo "$DEBUG_RESPONSE" | sed '$d')

if [ "$DEBUG_STATUS" = "403" ]; then
  echo "   SKIP: Debug routes disabled (403)"
elif [ "$DEBUG_STATUS" = "200" ]; then
  VALIDATED=$(echo "$DEBUG_BODY" | jq -r '.validated')
  PROJECT_MATCH=$(echo "$DEBUG_BODY" | jq -r '.projectMatch')
  JWT_PROJECT=$(echo "$DEBUG_BODY" | jq -r '.jwtProject')
  SUPABASE_PROJECT=$(echo "$DEBUG_BODY" | jq -r '.supabaseProject')

  if [ "$VALIDATED" = "true" ]; then
    echo "   PASS: Token validated"
  else
    echo "   FAIL: Token not validated"
    ERROR=$(echo "$DEBUG_BODY" | jq -r '.error')
    echo "   Error: $ERROR"
  fi

  if [ "$PROJECT_MATCH" = "true" ]; then
    echo "   PASS: JWT project matches validation project ($JWT_PROJECT)"
  else
    echo "   WARN: Project mismatch - JWT=$JWT_PROJECT, Validating=$SUPABASE_PROJECT"
  fi
else
  echo "   FAIL: Unexpected status $DEBUG_STATUS"
  echo "   Body: $DEBUG_BODY"
fi
echo ""

# Step 3: Test /api/integrations/outlook/auth-url (no token)
echo "3. Testing /api/integrations/outlook/auth-url (no token)..."
NO_TOKEN_RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/integrations/outlook/auth-url")
NO_TOKEN_STATUS=$(echo "$NO_TOKEN_RESPONSE" | tail -n1)
NO_TOKEN_BODY=$(echo "$NO_TOKEN_RESPONSE" | sed '$d')

if [ "$NO_TOKEN_STATUS" = "401" ]; then
  CODE=$(echo "$NO_TOKEN_BODY" | jq -r '.code')
  if [ "$CODE" = "missing_bearer" ]; then
    echo "   PASS: Returns 401 with code=missing_bearer"
  else
    echo "   WARN: Returns 401 but code=$CODE (expected missing_bearer)"
  fi
else
  echo "   FAIL: Expected 401, got $NO_TOKEN_STATUS"
fi
echo ""

# Step 4: Test /api/integrations/outlook/auth-url (with token)
echo "4. Testing /api/integrations/outlook/auth-url (with token)..."
AUTH_URL_RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/integrations/outlook/auth-url" \
  -H "Authorization: Bearer $ACCESS_TOKEN")
AUTH_URL_STATUS=$(echo "$AUTH_URL_RESPONSE" | tail -n1)
AUTH_URL_BODY=$(echo "$AUTH_URL_RESPONSE" | sed '$d')

if [ "$AUTH_URL_STATUS" = "200" ]; then
  HAS_URL=$(echo "$AUTH_URL_BODY" | jq -r '.url != null')
  PURPOSE=$(echo "$AUTH_URL_BODY" | jq -r '.purpose')
  if [ "$HAS_URL" = "true" ]; then
    echo "   PASS: Returns 200 with OAuth URL (purpose=$PURPOSE)"
  else
    echo "   FAIL: Returns 200 but no URL in response"
  fi
elif [ "$AUTH_URL_STATUS" = "401" ]; then
  CODE=$(echo "$AUTH_URL_BODY" | jq -r '.code')
  echo "   FAIL: Returns 401 (code=$CODE)"
  echo "   This means the JWT is not being validated correctly"
else
  echo "   FAIL: Unexpected status $AUTH_URL_STATUS"
  echo "   Body: $AUTH_URL_BODY"
fi
echo ""

# Step 5: Test /api/integrations/outlook/status (with token)
echo "5. Testing /api/integrations/outlook/status (with token)..."
STATUS_RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/integrations/outlook/status" \
  -H "Authorization: Bearer $ACCESS_TOKEN")
STATUS_STATUS=$(echo "$STATUS_RESPONSE" | tail -n1)
STATUS_BODY=$(echo "$STATUS_RESPONSE" | sed '$d')

if [ "$STATUS_STATUS" = "200" ]; then
  CONNECTED=$(echo "$STATUS_BODY" | jq -r '.connected')
  echo "   PASS: Returns 200 (connected=$CONNECTED)"
elif [ "$STATUS_STATUS" = "401" ]; then
  CODE=$(echo "$STATUS_BODY" | jq -r '.code')
  echo "   FAIL: Returns 401 (code=$CODE)"
else
  echo "   WARN: Status $STATUS_STATUS"
  echo "   Body: $STATUS_BODY"
fi
echo ""

# Summary
echo "============================================================"
echo "Summary"
echo "============================================================"
echo "Target: $BASE_URL"
echo "JWT Project: $JWT_PROJECT"
echo "Validation Project: $SUPABASE_PROJECT"
echo ""
echo "If auth-url returns 401 with valid token:"
echo "  - Check that NEXT_PUBLIC_SUPABASE_URL points to MASTER"
echo "  - The JWT is minted by MASTER, so validation must use MASTER"
echo "  - If using TENANT for validation, you'll always get 401"
