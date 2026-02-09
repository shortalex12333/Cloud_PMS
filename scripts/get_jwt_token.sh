#!/bin/bash
# Helper script to get JWT token from Supabase auth
# Usage: ./scripts/get_jwt_token.sh <email> <password>

set -e

EMAIL="${1:-x@alex-short.com}"
PASSWORD="${2:-Password2!}"

# Tenant 1 Supabase configuration
SUPABASE_URL="https://vzsohavtuotocgrfkfyd.supabase.co"
SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzIyMDA0NTQsImV4cCI6MjA0Nzc3NjQ1NH0.FG6yKuhfN7LW7pqLGhbQs0ZV7xz1J5xX_LcUQ5DqO_w"

echo "Logging in as: $EMAIL"
echo ""

# Create payload file
cat > /tmp/auth_payload_$$.json << EOF
{"email":"$EMAIL","password":"$PASSWORD"}
EOF

# Make request
RESPONSE=$(curl -s -X POST "${SUPABASE_URL}/auth/v1/token?grant_type=password" \
  -H "Content-Type: application/json" \
  -H "apikey: ${SUPABASE_ANON_KEY}" \
  -d @/tmp/auth_payload_$$.json)

# Clean up
rm -f /tmp/auth_payload_$$.json

# Parse response
ACCESS_TOKEN=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('access_token', ''))" 2>/dev/null || echo "")

if [ -n "$ACCESS_TOKEN" ]; then
    echo "✓ Login successful!"
    echo ""
    echo "JWT Token:"
    echo "$ACCESS_TOKEN"
    echo ""
    echo "To use this token, run:"
    echo "  export TEST_JWT_TOKEN=\"$ACCESS_TOKEN\""
    echo "  ./scripts/test_handover_workflow.sh"
else
    echo "✗ Login failed"
    echo ""
    echo "Response:"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    exit 1
fi
