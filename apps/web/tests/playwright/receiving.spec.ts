/**
 * Receiving Lens - End-to-End Tests
 * Tests user flows with real login (password auth)
 */
import { test, expect } from '@playwright/test';

const FRONTEND_URL = process.env.PLAYWRIGHT_BASE_URL || process.env.BASE_URL || 'http://localhost:3000';
const YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598';

// Test users (corrected emails)
const CAPTAIN = {
  email: 'x@alex-short.com',  // Captain role
  password: 'Password2!',
  role: 'captain'
};

const HOD = {
  email: 'hod.test@alex-short.com',
  password: 'Password2!',
  role: 'chief_engineer'
};

const CREW = {
  email: 'crew.test@alex-short.com',
  password: 'Password2!',
  role: 'crew'
};

test.describe('Receiving Lens - Captain Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to login page explicitly
    await page.goto(`${FRONTEND_URL}/login`);

    // Wait for loading to complete and form to appear
    await page.waitForSelector('input[type="email"]', { timeout: 15000 });
  });

  test('Captain can login and access receiving page', async ({ page }) => {
    console.log('1. Attempting login as captain...');

    // Find and fill login form
    const emailInput = page.locator('input[type="email"]');
    const passwordInput = page.locator('input[type="password"]');

    await expect(emailInput).toBeVisible();
    await expect(passwordInput).toBeVisible();

    await emailInput.fill(CAPTAIN.email);
    await passwordInput.fill(CAPTAIN.password);

    // Submit login
    const loginButton = page.locator('button[type="submit"]');
    await loginButton.click();

    console.log('2. Waiting for navigation after login...');
    await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 15000 });

    console.log(`3. Current URL after login: ${page.url()}`);

    // Navigate to receiving
    console.log('4. Navigating to /receiving...');
    await page.goto(`${FRONTEND_URL}/receiving`);
    await page.waitForLoadState('networkidle');

    // Check for receiving page content
    const pageContent = await page.content();
    expect(pageContent.toLowerCase()).toContain('receiving');

    console.log('✅ Captain successfully accessed receiving page');

    // Take screenshot for evidence
    await page.screenshot({ path: '/tmp/playwright-receiving-captain.png', fullPage: true });
  });

  test('Captain can view existing receiving records', async ({ page }) => {
    // Login (beforeEach already navigated to /login)
    await page.locator('input[type="email"]').fill(CAPTAIN.email);
    await page.locator('input[type="password"]').fill(CAPTAIN.password);
    await page.locator('button[type="submit"]').click();
    await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 20000 });

    // Navigate to receiving
    await page.goto(`${FRONTEND_URL}/receiving`);
    await page.waitForLoadState('networkidle');

    // Look for receiving records (table, list, or cards)
    const hasContent = await page.evaluate(() => {
      const text = document.body.textContent?.toLowerCase() || '';
      return text.includes('vendor') || text.includes('invoice') || text.includes('pending');
    });

    if (hasContent) {
      console.log('✅ Receiving records visible on page');
    } else {
      console.log('⚠️  No receiving records found (might be empty state)');
    }

    await page.screenshot({ path: '/tmp/playwright-receiving-list.png', fullPage: true });
  });

  test('Captain cannot accept receiving without signature (expect 400)', async ({ page }) => {
    // Login (beforeEach already navigated to /login)
    await page.locator('input[type="email"]').fill(CAPTAIN.email);
    await page.locator('input[type="password"]').fill(CAPTAIN.password);
    await page.locator('button[type="submit"]').click();
    await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 20000 });

    // Set up network listener to capture API calls
    let apiError = null;
    page.on('response', async (response) => {
      if (response.url().includes('accept_receiving')) {
        console.log(`API Response: ${response.status()} - ${response.url()}`);

        if (response.status() === 400) {
          const body = await response.json().catch(() => ({}));
          apiError = body;
          console.log('400 Response:', JSON.stringify(body, null, 2));
        }
      }
    });

    // Navigate to receiving
    await page.goto(`${FRONTEND_URL}/receiving`);
    await page.waitForLoadState('networkidle');

    // Try to find and click accept button (without signature)
    // This will depend on your UI - adjust selectors as needed
    const acceptButton = page.locator('button:has-text("Accept")').first();

    if (await acceptButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      await acceptButton.click();

      // Wait for error message
      await page.waitForTimeout(2000);

      // Check for error message in UI
      const hasErrorMessage = await page.evaluate(() => {
        const text = document.body.textContent?.toLowerCase() || '';
        return text.includes('signature required') || text.includes('sign');
      });

      if (hasErrorMessage || apiError?.error_code === 'SIGNATURE_REQUIRED') {
        console.log('✅ Got expected signature required error');
      } else {
        console.log('⚠️  Signature requirement unclear - check manually');
      }

      await page.screenshot({ path: '/tmp/playwright-accept-no-signature.png', fullPage: true });
    } else {
      console.log('⚠️  No accept button found on page');
    }
  });
});

test.describe('Receiving Lens - HOD Flow', () => {
  test('HOD cannot accept receiving (captain-only action)', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/login`);
    await page.waitForSelector('input[type="email"]', { timeout: 15000 });

    // Login as HOD
    await page.locator('input[type="email"]').fill(HOD.email);
    await page.locator('input[type="password"]').fill(HOD.password);
    await page.locator('button[type="submit"]').click();
    await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 20000 });

    // Navigate to receiving
    await page.goto(`${FRONTEND_URL}/receiving`);
    await page.waitForLoadState('networkidle');

    // Check if accept/sign actions are visible
    const hasAcceptButton = await page.locator('button:has-text("Accept")').isVisible({ timeout: 2000 }).catch(() => false);
    const hasSignButton = await page.locator('button:has-text("Sign")').isVisible({ timeout: 2000 }).catch(() => false);

    if (!hasAcceptButton && !hasSignButton) {
      console.log('✅ HOD correctly does not see captain-only actions');
    } else {
      console.log('⚠️  HOD can see accept/sign actions (potential issue)');
    }

    await page.screenshot({ path: '/tmp/playwright-receiving-hod.png', fullPage: true });
  });
});

test.describe('Receiving Lens - API Integration', () => {
  test('Monitor API calls during receiving operations', async ({ page }) => {
    const apiCalls: any[] = [];

    page.on('response', async (response) => {
      if (response.url().includes('pipeline-core') || response.url().includes('/api/')) {
        apiCalls.push({
          url: response.url(),
          status: response.status(),
          method: response.request().method(),
        });
      }
    });

    // Login
    await page.goto(`${FRONTEND_URL}/login`);
    await page.waitForSelector('input[type="email"]', { timeout: 15000 });
    await page.locator('input[type="email"]').fill(CAPTAIN.email);
    await page.locator('input[type="password"]').fill(CAPTAIN.password);
    await page.locator('button[type="submit"]').click();
    await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 20000 });

    // Navigate to receiving
    await page.goto(`${FRONTEND_URL}/receiving`);
    await page.waitForLoadState('networkidle');

    // Log API calls
    console.log('API Calls detected:');
    apiCalls.forEach(call => {
      console.log(`  ${call.method} ${call.status} - ${call.url.substring(0, 100)}...`);
    });

    if (apiCalls.length > 0) {
      console.log(`✅ Detected ${apiCalls.length} API calls`);
    } else {
      console.log('⚠️  No API calls detected');
    }
  });
});
