# Playwright E2E Tests with JWT Refresh

**Date**: 2026-01-30
**Purpose**: End-to-end tests with automatic JWT token refresh

---

## Overview

This test suite provides:
- ✅ **Automatic JWT refresh** - Tokens refreshed before expiry
- ✅ **Global authentication** - Login once, reuse across all tests
- ✅ **JWT validation** - Checks token expiry before each test
- ✅ **Error handling** - Clear failures if JWT expires or refresh fails

---

## Setup

### 1. Install Dependencies

```bash
cd apps/web
npm install
npx playwright install chromium
```

### 2. Configure Environment

```bash
# Copy example file
cp ../../.env.e2e.example ../../.env.e2e

# Edit .env.e2e with your values
nano ../../.env.e2e
```

**Required variables**:
```env
BASE_URL=https://app.celeste7.ai
TEST_USER_EMAIL=test@yacht.com
TEST_USER_PASSWORD=your_password
SUPABASE_URL=https://qvzmkaamzaqxpzbewjxe.supabase.co
SUPABASE_ANON_KEY=your_anon_key
```

### 3. Create Test User

**Important**: Use a dedicated test user, NOT a production account.

**Option A: Create via Supabase Dashboard**
1. Go to MASTER Supabase → Authentication → Users
2. Create new user: `test@yacht.com`
3. Set password
4. Assign to test yacht in `user_accounts` table

**Option B: Create via SQL**
```sql
-- In MASTER Supabase
INSERT INTO auth.users (email, encrypted_password, email_confirmed_at)
VALUES (
  'test@yacht.com',
  crypt('your_password', gen_salt('bf')),
  NOW()
);

-- Get user_id
SELECT id FROM auth.users WHERE email = 'test@yacht.com';

-- Assign to yacht
INSERT INTO user_accounts (id, yacht_id, status)
VALUES ('<user_id>', '<yacht_id>', 'active');
```

Then create role in TENANT DB:
```sql
-- In TENANT Supabase
INSERT INTO auth_users_roles (user_id, yacht_id, role, is_active)
VALUES ('<user_id>', '<yacht_id>', 'chief_engineer', true);
```

---

## How It Works

### Global Setup (Runs Once)

**File**: `global-setup.ts`

1. Launches browser
2. Logs in to application
3. Extracts JWT from localStorage
4. Logs JWT expiry time
5. Saves auth state to `playwright/.auth/user.json`
6. All tests reuse this auth state ✅

**Output**:
```
========================================
Playwright Global Setup - Authentication
========================================

🌐 Base URL: https://app.celeste7.ai
👤 Test User: test@yacht.com

🔐 Logging in...
⏳ Waiting for authentication...
✅ Login successful

🔑 Extracting JWT tokens...
✅ JWT tokens extracted

✅ VALID Access Token:
  User: test@yacht.com (89b1262c-ff59-4591-b954-757cdf3d609d)
  Expires in: 59m 45s
  Issued at: 2026-01-30T10:00:00.000Z
  Expires at: 2026-01-30T11:00:00.000Z

✅ JWT valid for 59m 45s

💾 Auth state saved to: playwright/.auth/user.json
💾 Tokens saved to: playwright/.auth/tokens.json

========================================
✅ Global Setup Complete
========================================
```

### Auth Fixture (Runs Before Each Test)

**File**: `fixtures/auth.ts`

1. Checks JWT expiry before test starts
2. If JWT expires in <5 minutes → Refreshes using refresh token
3. Logs JWT status for debugging
4. Test runs with valid JWT ✅

**Output**:
```
✅ JWT valid for 45m 30s
```

or if refreshing:

```
⚠️  JWT expiring in 3m 20s, refreshing...
🔄 Refreshing JWT...
✅ JWT refreshed successfully
✅ VALID Refreshed JWT:
  User: test@yacht.com (89b1262c-ff59-4591-b954-757cdf3d609d)
  Expires in: 59m 50s
```

---

## Running Tests

### All Tests

```bash
cd apps/web
npm run test:e2e
```

or directly:

```bash
npx playwright test
```

### Specific Test File

```bash
npx playwright test example.spec.ts
```

### With UI Mode (Interactive)

```bash
npx playwright test --ui
```

### Debug Mode

```bash
npx playwright test --debug
```

### Headed Mode (See Browser)

```bash
npx playwright test --headed
```

---

## Writing Tests

### Basic Test (with JWT refresh)

```typescript
import { test, expect } from './fixtures/auth';

test('my test', async ({ page }) => {
  // JWT is automatically checked and refreshed before this runs

  await page.goto('/dashboard');

  // Your test logic...
  await expect(page).toHaveURL(/.*dashboard/);
});
```

### Test Without JWT Refresh (rare)

```typescript
import { test as baseTest, expect } from '@playwright/test';

baseTest('test without auth', async ({ page }) => {
  // This test does NOT use auth fixture
  // Useful for testing login page, public pages, etc.

  await page.goto('/login');
});
```

---

## File Structure

```
apps/web/tests/playwright/
├── README.md                   # This file
├── global-setup.ts             # Login once before all tests
├── fixtures/
│   └── auth.ts                 # JWT refresh fixture
├── utils/
│   └── jwt.ts                  # JWT utility functions
└── *.spec.ts                   # Your test files

playwright/.auth/               # Generated auth files
├── user.json                   # Full auth state (cookies, localStorage)
└── tokens.json                 # JWT tokens for inspection
```

---

## Troubleshooting

### Problem: "No JWT found in localStorage"

**Cause**: Global setup failed to extract JWT

**Fix**:
1. Check login page selectors in `global-setup.ts`
2. Verify test credentials in `.env.e2e`
3. Check console output from global setup
4. Look at screenshot: `test-results/global-setup-failure.png`

**Debug**:
```bash
# Run global setup manually
npx playwright test --global-setup-only
```

---

### Problem: "JWT expired" during test

**Cause**: JWT expired and refresh failed

**Fix**:
1. Check `SUPABASE_ANON_KEY` in `.env.e2e`
2. Verify Supabase URL is correct
3. Check refresh token is valid

**Debug**:
```typescript
// Add to test to see JWT status
test('debug jwt', async ({ page }) => {
  const session = await page.evaluate(() => {
    const key = Object.keys(localStorage).find(k => k.includes('supabase'));
    return localStorage.getItem(key);
  });
  console.log('Session:', session);
});
```

---

### Problem: Tests pass individually but fail in suite

**Cause**: JWT expires during long test run

**Fix**:
1. JWT refresh should handle this automatically
2. Check auth fixture is being used: `import { test } from './fixtures/auth'`
3. Verify refresh token is valid

**Workaround**: Run tests with more workers (parallel):
```typescript
// playwright.config.ts
workers: 4, // Run 4 tests in parallel
```

---

### Problem: "Supabase refresh endpoint failed"

**Cause**: Invalid refresh token or Supabase config

**Fix**:
1. Verify `SUPABASE_URL` in `.env.e2e`
2. Verify `SUPABASE_ANON_KEY` is correct
3. Check test user has valid session

**Debug**:
```bash
# Check tokens file
cat playwright/.auth/tokens.json
```

---

## JWT Expiry Details

### Default Supabase JWT Expiry

- **Access Token**: 1 hour (3600 seconds)
- **Refresh Token**: 30 days

### What Happens

**0-55 minutes**: JWT valid, tests run normally
**55-60 minutes**: JWT expiring soon (⚠️ warning logged)
**60+ minutes**: JWT expired, fixture refreshes automatically

### Long Test Suites (>1 hour)

The auth fixture automatically refreshes JWT if:
- Test starts and JWT expires in <5 minutes
- Refresh uses the refresh token (valid for 30 days)
- New JWT issued with fresh 1-hour expiry

**Result**: Tests can run indefinitely (up to 30 days) ✅

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: 18

      - name: Install dependencies
        run: |
          cd apps/web
          npm install
          npx playwright install --with-deps chromium

      - name: Create .env.e2e
        run: |
          cat > .env.e2e << EOF
          BASE_URL=${{ secrets.BASE_URL }}
          TEST_USER_EMAIL=${{ secrets.TEST_USER_EMAIL }}
          TEST_USER_PASSWORD=${{ secrets.TEST_USER_PASSWORD }}
          SUPABASE_URL=${{ secrets.SUPABASE_URL }}
          SUPABASE_ANON_KEY=${{ secrets.SUPABASE_ANON_KEY }}
          CI=true
          EOF

      - name: Run E2E tests
        run: cd apps/web && npm run test:e2e

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: apps/web/playwright-report/
```

**Required GitHub Secrets**:
- `BASE_URL`
- `TEST_USER_EMAIL`
- `TEST_USER_PASSWORD`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`

---

## Best Practices

### ✅ DO

- Use dedicated test user (not production account)
- Import from `./fixtures/auth` for authenticated tests
- Check JWT status in CI logs
- Use `--headed` mode for debugging
- Take screenshots on failure (`screenshot: 'only-on-failure'`)

### ❌ DON'T

- Don't commit `.env.e2e` (contains passwords)
- Don't use production data in tests
- Don't skip global setup (tests will fail)
- Don't manually login in tests (wastes time)

---

## Next Steps

1. ✅ Set up `.env.e2e` with test credentials
2. ✅ Create test user in Supabase
3. ✅ Run global setup: `npx playwright test --global-setup-only`
4. ✅ Verify JWT extracted: `cat playwright/.auth/tokens.json`
5. ✅ Run example test: `npx playwright test example.spec.ts`
6. ✅ Write your own tests in `*.spec.ts` files

---

**Questions?** See Playwright docs: https://playwright.dev
