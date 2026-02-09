#!/bin/bash
# Authenticate test users and get fresh JWT tokens

SUPABASE_URL="https://qvzmkaamzaqxpzbewjxe.supabase.co"
SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM5NzkwNDYsImV4cCI6MjA3OTU1NTA0Nn0.MMzzsRkvbug-u19GBUnD0qLDtMVWEbOf6KE8mAADaxw"
PASSWORD="Password2!"

# Authenticate HOD
echo "Authenticating HOD user..."
HOD_AUTH=$(curl -s -X POST "${SUPABASE_URL}/auth/v1/token?grant_type=password" \
  -H "apikey: ${SUPABASE_ANON_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"hod.test@alex-short.com\",\"password\":\"${PASSWORD}\"}")

HOD_JWT=$(echo "$HOD_AUTH" | jq -r '.access_token // empty')

if [ -z "$HOD_JWT" ] || [ "$HOD_JWT" = "null" ]; then
  echo "❌ HOD authentication failed"
  echo "$HOD_AUTH" | jq '.'
  exit 1
else
  echo "✅ HOD authenticated"
fi

# Authenticate CREW
echo "Authenticating CREW user..."
CREW_AUTH=$(curl -s -X POST "${SUPABASE_URL}/auth/v1/token?grant_type=password" \
  -H "apikey: ${SUPABASE_ANON_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"crew.test@alex-short.com\",\"password\":\"${PASSWORD}\"}")

CREW_JWT=$(echo "$CREW_AUTH" | jq -r '.access_token // empty')

if [ -z "$CREW_JWT" ] || [ "$CREW_JWT" = "null" ]; then
  echo "❌ CREW authentication failed"
  echo "$CREW_AUTH" | jq '.'
  exit 1
else
  echo "✅ CREW authenticated"
fi

# Update test-jwts.json
echo "Updating test-jwts.json..."
jq --arg hod_jwt "$HOD_JWT" --arg crew_jwt "$CREW_JWT" \
  '.HOD.jwt = $hod_jwt | .CREW.jwt = $crew_jwt' \
  test-jwts.json > test-jwts.json.tmp && mv test-jwts.json.tmp test-jwts.json

echo "✅ Fresh tokens saved to test-jwts.json"
