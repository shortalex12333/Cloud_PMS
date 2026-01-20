#!/bin/bash
# B001 Pre-Deploy Verification Script
# This script demonstrates the B001 error (JWT signature mismatch)
# Run BEFORE deploying the fix to document the broken state
#
# Expected output: {"detail":"Invalid token: Signature verification failed"}

set -e

SUPABASE_URL="https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE"
PIPELINE_URL="https://pipeline-core.int.celeste7.ai"
TEST_EMAIL="x@alex-short.com"
TEST_PASSWORD="Password2!"

echo "=== B001 PRE-DEPLOY VERIFICATION ==="
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
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

# Step 2: Call bootstrap endpoint
echo "2. Calling /v1/bootstrap..."
BOOTSTRAP_RESPONSE=$(curl -s -X POST "${PIPELINE_URL}/v1/bootstrap" \
  -H "Authorization: Bearer ${JWT}" \
  -H "Content-Type: application/json")

echo "   Response:"
echo "$BOOTSTRAP_RESPONSE" | jq .
echo ""

# Step 3: Check for B001 error
if echo "$BOOTSTRAP_RESPONSE" | grep -q "Signature verification failed"; then
  echo "=== B001 CONFIRMED ==="
  echo "Error: Invalid token: Signature verification failed"
  echo "This confirms the JWT secret mismatch between Supabase and Render."
  exit 0
else
  echo "=== UNEXPECTED RESULT ==="
  echo "Did not receive expected B001 error."
  echo "Either B001 is already fixed, or there's a different issue."
  exit 1
fi
