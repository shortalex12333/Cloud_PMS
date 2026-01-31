#!/bin/bash
# =============================================================================
# JWT TOKEN GENERATOR
# =============================================================================
# Purpose: Generate JWT tokens for all test users
# Usage: ./03_generate_jwt_tokens.sh
# Output: JWT tokens saved to .env.test file
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Supabase Master DB (for auth)
MASTER_SUPABASE_URL="https://qvzmkaamzaqxpzbewjxe.supabase.co"
MASTER_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM5NzkwNDYsImV4cCI6MjA3OTU1NTA0Nn0.MMzzsRkvbug-u19GBUnD0qLDtMVWEbOf6KE8mAADaxw"

# Test users
declare -A USERS=(
    ["JOHN_DECK"]="john.deck@test.celeste7.ai:TestDeck123!"
    ["SARAH_DECK"]="sarah.deck@test.celeste7.ai:TestDeck123!"
    ["HOD_DECK"]="hod.deck@test.celeste7.ai:TestHOD123!"
    ["TOM_ENGINE"]="tom.engine@test.celeste7.ai:TestEngine123!"
    ["HOD_ENGINE"]="hod.engine@test.celeste7.ai:TestHOD123!"
    ["CAPTAIN"]="captain@test.celeste7.ai:TestCaptain123!"
)

echo -e "${BLUE}========================================================================"
echo "JWT TOKEN GENERATOR"
echo "========================================================================${NC}"
echo ""

# Output file
OUTPUT_FILE="tests/setup/.env.test"
echo "# Generated JWT Tokens for Test Users" > "$OUTPUT_FILE"
echo "# Generated: $(date)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Function to get JWT token
get_jwt_token() {
    local email=$1
    local password=$2
    local var_name=$3

    echo -e "${YELLOW}Generating token for: ${email}${NC}"

    response=$(curl -s -X POST "${MASTER_SUPABASE_URL}/auth/v1/token?grant_type=password" \
        -H "apikey: ${MASTER_ANON_KEY}" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"${email}\",\"password\":\"${password}\"}")

    # Check if request was successful
    if echo "$response" | jq -e '.access_token' > /dev/null 2>&1; then
        access_token=$(echo "$response" | jq -r '.access_token')
        user_id=$(echo "$response" | jq -r '.user.id')
        user_role=$(echo "$response" | jq -r '.user.user_metadata.role')
        user_dept=$(echo "$response" | jq -r '.user.user_metadata.department')

        echo -e "${GREEN}✅ Success${NC}"
        echo "   User ID: ${user_id}"
        echo "   Role: ${user_role}"
        echo "   Department: ${user_dept}"
        echo "   Token: ${access_token:0:50}..."
        echo ""

        # Save to file
        echo "# ${email} (${user_role}, ${user_dept})" >> "$OUTPUT_FILE"
        echo "${var_name}_JWT=\"${access_token}\"" >> "$OUTPUT_FILE"
        echo "${var_name}_USER_ID=\"${user_id}\"" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"

        return 0
    else
        error_msg=$(echo "$response" | jq -r '.msg // .error_description // "Unknown error"')
        echo -e "${RED}❌ Failed: ${error_msg}${NC}"
        echo ""
        return 1
    fi
}

# Generate tokens for all users
success_count=0
fail_count=0

for var_name in "${!USERS[@]}"; do
    IFS=':' read -r email password <<< "${USERS[$var_name]}"

    if get_jwt_token "$email" "$password" "$var_name"; then
        ((success_count++))
    else
        ((fail_count++))
    fi
done

echo -e "${BLUE}========================================================================"
echo "SUMMARY"
echo "========================================================================${NC}"
echo -e "Success: ${GREEN}${success_count}${NC}"
echo -e "Failed:  ${RED}${fail_count}${NC}"
echo ""

if [ $success_count -eq 6 ]; then
    echo -e "${GREEN}✅ All tokens generated successfully!${NC}"
    echo ""
    echo "Tokens saved to: ${OUTPUT_FILE}"
    echo ""
    echo "To use in tests:"
    echo "  source tests/setup/.env.test"
    echo "  curl -H \"Authorization: Bearer \$JOHN_DECK_JWT\" ..."
    echo ""
    exit 0
else
    echo -e "${RED}❌ Some tokens failed to generate${NC}"
    echo "Please check if test users were created correctly."
    echo "Run: psql \$MASTER_DB_URL -f tests/setup/01_create_test_users.sql"
    echo ""
    exit 1
fi
