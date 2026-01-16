#!/bin/bash
# ============================================================================
# E2E Environment Verification Script
# ============================================================================
# Verifies all required environment variables are set and services are reachable
# Fails fast with actionable error messages
# ============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=============================================="
echo "E2E Environment Verification"
echo "=============================================="
echo ""

# Load .env.e2e.local if it exists
if [ -f ".env.e2e.local" ]; then
    echo "Loading .env.e2e.local..."
    export $(grep -v '^#' .env.e2e.local | xargs)
elif [ -f ".env.e2e" ]; then
    echo "Loading .env.e2e..."
    export $(grep -v '^#' .env.e2e | xargs)
else
    echo -e "${YELLOW}Warning: No .env.e2e.local or .env.e2e found${NC}"
    echo "Using environment variables from shell..."
fi

ERRORS=0

# ----------------------------------------------------------------------------
# Required Variables Check
# ----------------------------------------------------------------------------

check_var() {
    local var_name=$1
    local var_value="${!var_name}"

    if [ -z "$var_value" ]; then
        echo -e "${RED}MISSING: $var_name${NC}"
        ERRORS=$((ERRORS + 1))
        return 1
    else
        # Mask secrets in output
        if [[ "$var_name" == *"KEY"* ]] || [[ "$var_name" == *"PASSWORD"* ]] || [[ "$var_name" == *"SECRET"* ]]; then
            echo -e "${GREEN}OK: $var_name${NC} = ${var_value:0:10}..."
        else
            echo -e "${GREEN}OK: $var_name${NC} = $var_value"
        fi
        return 0
    fi
}

echo ""
echo "--- Checking Required Variables ---"
echo ""

# Master Supabase
check_var "MASTER_SUPABASE_URL"
check_var "MASTER_SUPABASE_ANON_KEY"
check_var "MASTER_SUPABASE_SERVICE_ROLE_KEY"

# Tenant Supabase
check_var "TENANT_SUPABASE_URL"
check_var "TENANT_SUPABASE_SERVICE_ROLE_KEY"

# Backend API
check_var "RENDER_API_URL"

# Frontend
check_var "VERCEL_PROD_URL"

# Test User
check_var "TEST_USER_EMAIL"
check_var "TEST_USER_PASSWORD"
check_var "TEST_USER_YACHT_ID"

echo ""

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}=============================================="
    echo "FAILED: $ERRORS required variables missing"
    echo "=============================================="
    echo ""
    echo "Fix: Copy .env.e2e.example to .env.e2e.local and fill in values"
    echo -e "${NC}"
    exit 1
fi

# ----------------------------------------------------------------------------
# URL Format Validation
# ----------------------------------------------------------------------------

echo "--- Validating URL Formats ---"
echo ""

validate_url() {
    local var_name=$1
    local var_value="${!var_name}"

    # Check for trailing slash
    if [[ "$var_value" == */ ]]; then
        echo -e "${RED}ERROR: $var_name has trailing slash${NC}"
        ERRORS=$((ERRORS + 1))
        return 1
    fi

    # Check for https (production)
    if [[ "$var_value" != https://* ]] && [[ "$var_value" != http://localhost* ]]; then
        echo -e "${YELLOW}WARNING: $var_name is not HTTPS (OK for localhost)${NC}"
    fi

    echo -e "${GREEN}OK: $var_name format valid${NC}"
    return 0
}

validate_url "MASTER_SUPABASE_URL"
validate_url "TENANT_SUPABASE_URL"
validate_url "RENDER_API_URL"
validate_url "VERCEL_PROD_URL"

echo ""

# ----------------------------------------------------------------------------
# Service Reachability Check
# ----------------------------------------------------------------------------

echo "--- Checking Service Reachability ---"
echo ""

check_endpoint() {
    local name=$1
    local url=$2
    local expected_status=${3:-200}
    local extra_headers=${4:-""}

    echo -n "Checking $name... "

    if [ -n "$extra_headers" ]; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 -H "$extra_headers" "$url" 2>/dev/null || echo "000")
    else
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$url" 2>/dev/null || echo "000")
    fi

    if [ "$HTTP_CODE" == "$expected_status" ] || [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "301" ] || [ "$HTTP_CODE" == "302" ]; then
        echo -e "${GREEN}OK (HTTP $HTTP_CODE)${NC}"
        return 0
    else
        echo -e "${RED}FAILED (HTTP $HTTP_CODE)${NC}"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# Check Master Supabase health (requires apikey header)
check_endpoint "Master Supabase" "$MASTER_SUPABASE_URL/rest/v1/" "200" "apikey: $MASTER_SUPABASE_ANON_KEY"

# Check Tenant Supabase health (requires apikey header)
check_endpoint "Tenant Supabase" "$TENANT_SUPABASE_URL/rest/v1/" "200" "apikey: $TENANT_SUPABASE_SERVICE_ROLE_KEY"

# Check Render backend health
check_endpoint "Render Backend" "$RENDER_API_URL/health"

# Check Vercel frontend
check_endpoint "Vercel Frontend" "$VERCEL_PROD_URL"

echo ""

# ----------------------------------------------------------------------------
# Authentication Test
# ----------------------------------------------------------------------------

echo "--- Testing Authentication ---"
echo ""

echo -n "Testing Supabase login... "

LOGIN_RESPONSE=$(curl -s -X POST "$MASTER_SUPABASE_URL/auth/v1/token?grant_type=password" \
    -H "apikey: $MASTER_SUPABASE_ANON_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$TEST_USER_EMAIL\",\"password\":\"$TEST_USER_PASSWORD\"}" 2>/dev/null)

if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
    echo -e "${GREEN}OK (got access_token)${NC}"

    # Extract token for further tests
    ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
else
    echo -e "${RED}FAILED${NC}"
    echo "Response: $LOGIN_RESPONSE"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# ----------------------------------------------------------------------------
# Bootstrap RPC Test
# ----------------------------------------------------------------------------

if [ -n "$ACCESS_TOKEN" ]; then
    echo "--- Testing Bootstrap RPC ---"
    echo ""

    echo -n "Testing get_my_bootstrap()... "

    BOOTSTRAP_RESPONSE=$(curl -s -X POST "$MASTER_SUPABASE_URL/rest/v1/rpc/get_my_bootstrap" \
        -H "apikey: $MASTER_SUPABASE_ANON_KEY" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" 2>/dev/null)

    if echo "$BOOTSTRAP_RESPONSE" | grep -q "yacht_id"; then
        echo -e "${GREEN}OK (got yacht_id)${NC}"

        # Verify yacht_id matches expected
        RETURNED_YACHT=$(echo "$BOOTSTRAP_RESPONSE" | grep -o '"yacht_id":"[^"]*"' | cut -d'"' -f4)
        if [ "$RETURNED_YACHT" == "$TEST_USER_YACHT_ID" ]; then
            echo -e "${GREEN}OK: yacht_id matches expected ($RETURNED_YACHT)${NC}"
        else
            echo -e "${YELLOW}WARNING: yacht_id mismatch. Expected: $TEST_USER_YACHT_ID, Got: $RETURNED_YACHT${NC}"
        fi
    else
        echo -e "${RED}FAILED${NC}"
        echo "Response: $BOOTSTRAP_RESPONSE"
        ERRORS=$((ERRORS + 1))
    fi

    echo ""
fi

# ----------------------------------------------------------------------------
# Search Endpoint Test
# ----------------------------------------------------------------------------

if [ -n "$ACCESS_TOKEN" ]; then
    echo "--- Testing Search Endpoint ---"
    echo ""

    echo -n "Testing /search endpoint... "

    SEARCH_RESPONSE=$(curl -s -X POST "$RENDER_API_URL/search" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"query": "test", "limit": 1}' 2>/dev/null)

    if echo "$SEARCH_RESPONSE" | grep -q "success"; then
        echo -e "${GREEN}OK (got response)${NC}"
    else
        echo -e "${RED}FAILED${NC}"
        echo "Response: $SEARCH_RESPONSE"
        ERRORS=$((ERRORS + 1))
    fi

    echo ""
fi

# ----------------------------------------------------------------------------
# Final Summary
# ----------------------------------------------------------------------------

echo "=============================================="

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}ALL CHECKS PASSED${NC}"
    echo "=============================================="
    echo ""
    echo "Environment is ready for E2E tests."
    echo "Run: npm run test:e2e"
    exit 0
else
    echo -e "${RED}$ERRORS CHECK(S) FAILED${NC}"
    echo "=============================================="
    echo ""
    echo "Fix the issues above before running tests."
    exit 1
fi
