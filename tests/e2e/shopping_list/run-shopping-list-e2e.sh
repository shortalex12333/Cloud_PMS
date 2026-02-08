#!/bin/bash
#
# Shopping List E2E Tests Runner
# ===============================
# Runs Playwright E2E tests for Shopping List lens with fresh JWT sign-in.
#
# Usage:
#   ./run-shopping-list-e2e.sh [local|production]
#
# Prerequisites:
#   - Node.js and npm installed
#   - Playwright installed: npx playwright install
#   - Frontend running (local mode) or deployed (production mode)
#

set -e

# Determine environment
ENV=${1:-local}

case $ENV in
  local)
    export BASE_URL="http://localhost:3000"
    ;;
  production)
    export BASE_URL="https://app.celeste7.ai"
    ;;
  *)
    echo "Usage: $0 [local|production]"
    exit 1
    ;;
esac

# Test user credentials
export TEST_CREW_USER_EMAIL="crew.test@alex-short.com"
export TEST_HOD_USER_EMAIL="hod.test@alex-short.com"
export TEST_CAPTAIN_USER_EMAIL="x@alex-short.com"
export ALL_TEST_USER_PASSWORD="Password2!"
export TEST_YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"

echo "============================================================"
echo "Shopping List E2E Tests"
echo "============================================================"
echo "Environment: $ENV"
echo "Base URL: $BASE_URL"
echo "Yacht ID: $TEST_YACHT_ID"
echo ""
echo "Test Users:"
echo "  CREW:    $TEST_CREW_USER_EMAIL"
echo "  HOD:     $TEST_HOD_USER_EMAIL"
echo "  CAPTAIN: $TEST_CAPTAIN_USER_EMAIL"
echo "============================================================"
echo ""

# Navigate to project root
cd "$(dirname "$0")/../../.."

# Clean previous auth states
echo "🧹 Cleaning previous authentication states..."
rm -rf tests/e2e/shopping_list/.auth/*.json
rm -rf tests/e2e/shopping_list/.auth/*.txt
rm -rf tests/e2e/shopping_list/screenshots/*
mkdir -p tests/e2e/shopping_list/.auth
mkdir -p tests/e2e/shopping_list/screenshots

# Run authentication setup
echo ""
echo "🔐 Step 1: Authenticate test users and obtain fresh JWTs..."
echo ""
npx playwright test tests/e2e/shopping_list/auth.setup.ts \
  --config=playwright.config.ts \
  --project=chromium

if [ $? -ne 0 ]; then
  echo ""
  echo "❌ Authentication failed. Please check:"
  echo "   1. Frontend is running on $BASE_URL"
  echo "   2. Test users exist with correct passwords"
  echo "   3. Login page is accessible"
  exit 1
fi

echo ""
echo "✅ Authentication complete. JWTs saved."
echo ""

# Display saved JWTs (first 50 chars)
echo "📋 Saved JWTs:"
for role in crew hod captain; do
  jwt_file="tests/e2e/shopping_list/.auth/${role}-jwt.txt"
  if [ -f "$jwt_file" ]; then
    jwt_preview=$(head -c 50 "$jwt_file")
    echo "   ${role^^}: ${jwt_preview}..."
  fi
done
echo ""

# Run Shopping List E2E tests
echo "🧪 Step 2: Running Shopping List E2E tests..."
echo ""
npx playwright test tests/e2e/shopping_list/role_based_actions.e2e.spec.ts \
  --config=playwright.config.ts \
  --project=chromium \
  --reporter=list,html

TEST_EXIT_CODE=$?

echo ""
echo "============================================================"
if [ $TEST_EXIT_CODE -eq 0 ]; then
  echo "✅ All Shopping List E2E tests passed!"
else
  echo "❌ Some tests failed. See report above."
fi
echo "============================================================"
echo ""

# Display results location
echo "📊 Test Results:"
echo "   Screenshots: tests/e2e/shopping_list/screenshots/"
echo "   Auth States: tests/e2e/shopping_list/.auth/"
echo "   HTML Report: playwright-report/index.html"
echo ""

# Open HTML report (optional)
if [ $TEST_EXIT_CODE -eq 0 ]; then
  read -p "Open HTML report in browser? (y/n) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    npx playwright show-report
  fi
fi

exit $TEST_EXIT_CODE
