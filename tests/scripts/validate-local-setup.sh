#!/usr/bin/env bash
# Validation Script for Local Testing Setup
# Checks database, users, search, and action endpoints

set -e

echo "========================================="
echo "Validating Local Testing Setup"
echo "========================================="
echo ""

# Load environment variables
if [ -f .env.e2e.local ]; then
  export $(cat .env.e2e.local | grep -v '^#' | xargs)
fi

YACHT_ID="${YACHT_ID:-85fe1119-b04c-41ac-80f1-829d23322598}"
BASE_URL="${PLAYWRIGHT_BASE_URL:-https://app.celeste7.ai}"

echo "✓ Configuration loaded"
echo "  - Yacht ID: $YACHT_ID"
echo "  - Base URL: $BASE_URL"
echo ""

# ==============================================================================
# 1. CHECK TEST USERS
# ==============================================================================
echo "1. Checking Test Users..."
echo "-------------------------------------------"

# Test users (compatible with bash 3.2)
test_user() {
  local role=$1
  local email=$2
  local password=$3

  if [ -z "$email" ] || [ -z "$password" ]; then
    echo "  ✗ $role: Missing credentials"
    return
  fi

  # Attempt login via Supabase directly (not Next.js API)
  response=$(curl -s -w "\n%{http_code}" -X POST "$MASTER_SUPABASE_URL/auth/v1/token?grant_type=password" \
    -H "Content-Type: application/json" \
    -H "apikey: $MASTER_SUPABASE_ANON_KEY" \
    -d "{\"email\":\"$email\",\"password\":\"$password\"}" 2>&1)

  http_code=$(echo "$response" | tail -n 1)
  body=$(echo "$response" | sed '$d')  # Remove last line (BSD compatible)

  if [ "$http_code" = "200" ]; then
    echo "  ✓ $role ($email): Authenticated"

    # Extract JWT token
    if command -v jq &> /dev/null; then
      jwt=$(echo "$body" | jq -r '.access_token // empty')
    else
      # Fallback without jq
      jwt=$(echo "$body" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    fi

    if [ -n "$jwt" ] && [ "$jwt" != "null" ]; then
      # Store token for later use
      eval "export ${role}_JWT='$jwt'"
      echo "    JWT: ${jwt:0:20}..."
    fi
  else
    echo "  ✗ $role ($email): Failed (HTTP $http_code)"
    if command -v jq &> /dev/null; then
      echo "    Response: $(echo "$body" | jq -c '.' 2>/dev/null || echo "$body")"
    else
      echo "    Response: $body"
    fi
  fi
}

# Test each role
test_user "CREW" "$CREW_EMAIL" "$CREW_PASSWORD"
test_user "HOD" "$HOD_EMAIL" "$HOD_PASSWORD"
test_user "CAPTAIN" "$CAPTAIN_EMAIL" "$CAPTAIN_PASSWORD"
test_user "CHIEF_ENGINEER" "$CHIEF_ENGINEER_EMAIL" "$CHIEF_ENGINEER_PASSWORD"

echo ""

# ==============================================================================
# 2. CHECK DATABASE PARTS
# ==============================================================================
echo "2. Checking Database Parts..."
echo "-------------------------------------------"

if [ -n "$HOD_JWT" ]; then
  # Use HOD token for database queries
  response=$(curl -s -X POST "$BASE_URL/api/search/fallback" \
    -H "Authorization: Bearer $HOD_JWT" \
    -H "Content-Type: application/json" \
    -d "{\"query\":\"fuel filter\",\"yacht_id\":\"$YACHT_ID\",\"limit\":5}")

  result_count=$(echo "$response" | jq -r '.total_count // 0')

  if [ "$result_count" -gt 0 ]; then
    echo "  ✓ Found $result_count parts matching 'fuel filter'"
    echo "$response" | jq -r '.results[] | "    - \(.title) (ID: \(.id))"'
  else
    echo "  ✗ No parts found matching 'fuel filter'"
    echo "  Response: $(echo "$response" | jq -c '.')"
  fi
else
  echo "  ⚠ Skipping (no HOD JWT available)"
fi

echo ""

# ==============================================================================
# 3. CHECK SEARCH ENDPOINTS
# ==============================================================================
echo "3. Checking Search Endpoints..."
echo "-------------------------------------------"

if [ -n "$HOD_JWT" ]; then
  # Test fallback search
  response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/search/fallback" \
    -H "Authorization: Bearer $HOD_JWT" \
    -H "Content-Type: application/json" \
    -d "{\"query\":\"fuel filter stock\",\"yacht_id\":\"$YACHT_ID\",\"limit\":10}")

  http_code=$(echo "$response" | tail -n 1)
  body=$(echo "$response" | sed '$d')

  if [ "$http_code" = "200" ]; then
    result_count=$(echo "$body" | jq -r '.total_count // 0')
    echo "  ✓ Fallback search working: $result_count results"
  else
    echo "  ✗ Fallback search failed (HTTP $http_code)"
    echo "    Response: $(echo "$body" | jq -c '.')"
  fi
else
  echo "  ⚠ Skipping (no HOD JWT available)"
fi

echo ""

# ==============================================================================
# 4. CHECK ACTION EXECUTION ENDPOINTS
# ==============================================================================
echo "4. Checking Action Execution Endpoints..."
echo "-------------------------------------------"

if [ -n "$HOD_JWT" ]; then
  # Test check_part_stock action
  response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/actions/execute" \
    -H "Authorization: Bearer $HOD_JWT" \
    -H "Content-Type: application/json" \
    -d "{\"action\":\"check_part_stock\",\"context\":{\"yacht_id\":\"$YACHT_ID\"},\"payload\":{\"part_id\":\"test-part-id\"}}")

  http_code=$(echo "$response" | tail -n1)

  if [ "$http_code" = "200" ] || [ "$http_code" = "404" ]; then
    echo "  ✓ Action execution endpoint responding (HTTP $http_code)"
  elif [ "$http_code" = "401" ]; then
    echo "  ⚠ Action execution requires authentication (HTTP 401)"
  else
    echo "  ✗ Action execution failed (HTTP $http_code)"
  fi
else
  echo "  ⚠ Skipping (no HOD JWT available)"
fi

echo ""

# ==============================================================================
# 5. SUMMARY
# ==============================================================================
echo "========================================="
echo "Validation Summary"
echo "========================================="

# Count authenticated users
auth_count=0
for role in CREW HOD CAPTAIN CHIEF_ENGINEER; do
  jwt_var="${role}_JWT"
  if [ -n "$(eval echo \$${jwt_var})" ]; then
    auth_count=$((auth_count + 1))
  fi
done

echo "✓ Test users authenticated: $auth_count/4"

if [ "$auth_count" -eq 4 ]; then
  echo "✓ All test users working"
elif [ "$auth_count" -ge 2 ]; then
  echo "⚠ Some test users working (minimum for basic tests)"
else
  echo "✗ Insufficient test users authenticated"
  exit 1
fi

echo ""
echo "Next steps:"
echo "1. Run E2E tests: npm run test:e2e -- tests/e2e/inventory-lens-6hr-live-test.spec.ts"
echo "2. Check test results: npx playwright show-report"
echo "3. If failures, check: test-results/artifacts/**/error-context.md"
echo ""
