#!/bin/bash
# Setup script for deployment v2026.02.09.003 E2E tests

set -e

echo "=========================================================================="
echo "DEPLOYMENT v2026.02.09.003 - E2E TEST SETUP"
echo "=========================================================================="
echo ""

# Check environment variables
echo "Checking environment variables..."
echo ""

MISSING_VARS=()

if [ -z "$MASTER_SUPABASE_ANON_KEY" ]; then
  echo "❌ MASTER_SUPABASE_ANON_KEY not set"
  MISSING_VARS+=("MASTER_SUPABASE_ANON_KEY")
else
  echo "✅ MASTER_SUPABASE_ANON_KEY set"
fi

if [ -z "$CREW_PASSWORD" ]; then
  echo "❌ CREW_PASSWORD not set"
  MISSING_VARS+=("CREW_PASSWORD")
else
  echo "✅ CREW_PASSWORD set"
fi

if [ -z "$HOD_PASSWORD" ]; then
  echo "❌ HOD_PASSWORD not set"
  MISSING_VARS+=("HOD_PASSWORD")
else
  echo "✅ HOD_PASSWORD set"
fi

if [ -z "$CAPTAIN_PASSWORD" ]; then
  echo "❌ CAPTAIN_PASSWORD not set"
  MISSING_VARS+=("CAPTAIN_PASSWORD")
else
  echo "✅ CAPTAIN_PASSWORD set"
fi

if [ -z "$APP_URL" ]; then
  echo "⚠️  APP_URL not set (will use default)"
else
  echo "✅ APP_URL set: $APP_URL"
fi

echo ""

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
  echo "=========================================================================="
  echo "MISSING ENVIRONMENT VARIABLES"
  echo "=========================================================================="
  echo ""
  echo "Please set these variables:"
  echo ""
  for var in "${MISSING_VARS[@]}"; do
    echo "  export $var=\"your-value\""
  done
  echo ""
  echo "Then re-run this script."
  echo ""
  exit 1
fi

# Check Playwright installed
echo "=========================================================================="
echo "Checking Playwright installation..."
echo "=========================================================================="
echo ""

if ! command -v npx &> /dev/null; then
  echo "❌ npx not found - please install Node.js"
  exit 1
fi

if ! npx playwright --version &> /dev/null; then
  echo "⚠️  Playwright not installed"
  echo ""
  echo "Installing Playwright..."
  npm install -D @playwright/test
  npx playwright install
else
  echo "✅ Playwright installed: $(npx playwright --version)"
fi

echo ""

# Check test users exist
echo "=========================================================================="
echo "Checking test users..."
echo "=========================================================================="
echo ""

echo "Test users that must exist:"
echo "  - crew.tenant@alex-short.com (deck department)"
echo "  - hod.tenant@alex-short.com (engineering department)"
echo "  - captain.tenant@alex-short.com"
echo ""
echo "These should be provisioned in:"
echo "  - MASTER: user_accounts table"
echo "  - TENANT: auth_users_roles table"
echo ""

# Summary
echo "=========================================================================="
echo "SETUP COMPLETE"
echo "=========================================================================="
echo ""
echo "You can now run tests:"
echo ""
echo "  # Run all deployment tests"
echo "  npx playwright test tests/e2e/deployment-v2026-02-09-003/"
echo ""
echo "  # Run specific test"
echo "  npx playwright test tests/e2e/deployment-v2026-02-09-003/work-orders-rbac.spec.ts"
echo ""
echo "  # Run with UI"
echo "  npx playwright test tests/e2e/deployment-v2026-02-09-003/ --ui"
echo ""
echo "  # Run headed (watch browser)"
echo "  npx playwright test tests/e2e/deployment-v2026-02-09-003/ --headed"
echo ""
echo "=========================================================================="
