#!/bin/bash
#
# Playwright E2E Test Setup Script
# =================================
#
# Quick setup for Playwright tests with JWT refresh
#

set -e

echo ""
echo "========================================="
echo "Playwright E2E Test Setup"
echo "========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "playwright.config.ts" ]; then
    echo "❌ Error: Must run from apps/web directory"
    echo ""
    echo "Usage:"
    echo "  cd apps/web"
    echo "  bash tests/playwright/setup.sh"
    exit 1
fi

# Step 1: Install dependencies
echo "[1/5] Installing Playwright dependencies..."
npm install --save-dev @playwright/test
npx playwright install chromium
echo "✅ Dependencies installed"
echo ""

# Step 2: Create .env.e2e if it doesn't exist
if [ ! -f "../../.env.e2e" ]; then
    echo "[2/5] Creating .env.e2e from example..."
    cp ../../.env.e2e.example ../../.env.e2e
    echo "✅ .env.e2e created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env.e2e with your test credentials:"
    echo "   - TEST_USER_EMAIL"
    echo "   - TEST_USER_PASSWORD"
    echo "   - SUPABASE_ANON_KEY"
    echo ""
    echo "Press Enter to continue after editing .env.e2e..."
    read
else
    echo "[2/5] .env.e2e already exists"
    echo "✅ Skipping"
    echo ""
fi

# Step 3: Verify environment variables
echo "[3/5] Verifying environment variables..."
source ../../.env.e2e

if [ -z "$TEST_USER_EMAIL" ]; then
    echo "❌ TEST_USER_EMAIL not set in .env.e2e"
    exit 1
fi

if [ -z "$TEST_USER_PASSWORD" ]; then
    echo "❌ TEST_USER_PASSWORD not set in .env.e2e"
    exit 1
fi

if [ -z "$SUPABASE_ANON_KEY" ]; then
    echo "❌ SUPABASE_ANON_KEY not set in .env.e2e"
    exit 1
fi

echo "✅ Environment variables verified"
echo ""

# Step 4: Run global setup to test login
echo "[4/5] Running global setup (test login)..."
npx playwright test --global-setup-only

if [ $? -eq 0 ]; then
    echo "✅ Global setup successful"
    echo ""
else
    echo "❌ Global setup failed"
    echo ""
    echo "Check:"
    echo "  - Test user credentials in .env.e2e"
    echo "  - Login page selectors in global-setup.ts"
    echo "  - Screenshot: test-results/global-setup-failure.png"
    exit 1
fi

# Step 5: Verify JWT extracted
echo "[5/5] Verifying JWT extraction..."
if [ -f "playwright/.auth/tokens.json" ]; then
    echo "✅ JWT tokens extracted"
    echo ""
    echo "JWT Details:"
    cat playwright/.auth/tokens.json | grep -E "extracted_at|expires_at" | head -2
    echo ""
else
    echo "❌ JWT tokens not found"
    echo "   Expected: playwright/.auth/tokens.json"
    exit 1
fi

# Success
echo "========================================="
echo "✅ Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Run example test:"
echo "     npx playwright test example.spec.ts"
echo ""
echo "  2. Run all tests:"
echo "     npx playwright test"
echo ""
echo "  3. Run with UI mode:"
echo "     npx playwright test --ui"
echo ""
echo "  4. Write your own tests in tests/playwright/*.spec.ts"
echo ""
echo "See tests/playwright/README.md for details."
echo ""
