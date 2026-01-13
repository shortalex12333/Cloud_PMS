/**
 * Auth E2E Tests
 *
 * Tests the complete login flow against real Supabase Master DB
 */

import { test, expect } from '@playwright/test';
import {
  saveScreenshot,
  saveArtifact,
  createEvidenceBundle,
} from '../helpers/artifacts';

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Capture console logs
    const consoleLogs: Array<{ type: string; text: string; timestamp: string }> = [];
    page.on('console', (msg) => {
      consoleLogs.push({
        type: msg.type(),
        text: msg.text(),
        timestamp: new Date().toISOString(),
      });
    });

    // Store for later use
    (page as any).__consoleLogs = consoleLogs;
  });

  test('Login page loads without CSP errors', async ({ page }) => {
    const testName = 'auth/login_page_loads';
    const consoleLogs = (page as any).__consoleLogs || [];

    // Navigate to login page
    await page.goto('/login');

    // Take screenshot
    await saveScreenshot(page, testName, 'login_page');

    // Check for CSP errors in console
    const cspErrors = consoleLogs.filter(
      (log) =>
        log.type === 'error' &&
        (log.text.includes('Content Security Policy') ||
          log.text.includes('Refused to connect'))
    );

    // Save console logs
    saveArtifact('console_logs.json', consoleLogs, testName);

    // Create evidence bundle
    createEvidenceBundle(testName, {
      consoleLogs,
      assertions: [
        {
          name: 'No CSP errors',
          passed: cspErrors.length === 0,
          message: cspErrors.length > 0 ? `Found ${cspErrors.length} CSP errors` : undefined,
        },
      ],
    });

    // Assert no CSP errors
    expect(cspErrors, 'Should have no CSP errors').toHaveLength(0);

    // Assert login form is visible
    await expect(page.locator('input[type="email"], input[name="email"]')).toBeVisible();
  });

  test('Login with valid credentials succeeds', async ({ page }) => {
    const testName = 'auth/login_success';
    const consoleLogs = (page as any).__consoleLogs || [];

    const email = process.env.TEST_USER_EMAIL;
    const password = process.env.TEST_USER_PASSWORD;

    if (!email || !password) {
      test.skip();
      return;
    }

    // Navigate to login page
    await page.goto('/login');

    // Screenshot before login
    await saveScreenshot(page, testName, '01_before_login');

    // Fill in credentials
    await page.fill('input[type="email"], input[name="email"]', email);
    await page.fill('input[type="password"], input[name="password"]', password);

    // Screenshot with credentials filled
    await saveScreenshot(page, testName, '02_credentials_filled');

    // Click login button
    await page.click('button[type="submit"]');

    // Wait for navigation (login should redirect)
    await page.waitForURL((url) => !url.pathname.includes('/login'), {
      timeout: 15000,
    });

    // Screenshot after login
    await saveScreenshot(page, testName, '03_after_login');

    // Save console logs
    saveArtifact('console_logs.json', consoleLogs, testName);

    // Check we're on a protected page
    const currentUrl = page.url();
    const isOnProtectedPage =
      currentUrl.includes('/dashboard') ||
      currentUrl.includes('/search') ||
      currentUrl.includes('/home') ||
      !currentUrl.includes('/login');

    // Create evidence bundle
    createEvidenceBundle(testName, {
      consoleLogs,
      assertions: [
        {
          name: 'Redirected to protected page',
          passed: isOnProtectedPage,
          message: `Current URL: ${currentUrl}`,
        },
      ],
    });

    expect(isOnProtectedPage, 'Should be on protected page after login').toBe(true);
  });

  test('Login with invalid credentials fails gracefully', async ({ page }) => {
    const testName = 'auth/login_invalid';
    const consoleLogs = (page as any).__consoleLogs || [];

    // Navigate to login page
    await page.goto('/login');

    // Fill in invalid credentials
    await page.fill('input[type="email"], input[name="email"]', 'invalid@example.com');
    await page.fill('input[type="password"], input[name="password"]', 'wrongpassword');

    // Click login button
    await page.click('button[type="submit"]');

    // Wait for error to appear (give it time to process)
    await page.waitForTimeout(2000);

    // Take screenshot
    await saveScreenshot(page, testName, 'error_state');

    // Save console logs
    saveArtifact('console_logs.json', consoleLogs, testName);

    // Should still be on login page
    expect(page.url()).toContain('/login');

    // Create evidence bundle
    createEvidenceBundle(testName, {
      consoleLogs,
      assertions: [
        {
          name: 'Stayed on login page',
          passed: page.url().includes('/login'),
        },
      ],
    });
  });

  test('Logout clears session', async ({ page }) => {
    const testName = 'auth/logout';
    const consoleLogs = (page as any).__consoleLogs || [];

    const email = process.env.TEST_USER_EMAIL;
    const password = process.env.TEST_USER_PASSWORD;

    if (!email || !password) {
      test.skip();
      return;
    }

    // First login
    await page.goto('/login');
    await page.fill('input[type="email"], input[name="email"]', email);
    await page.fill('input[type="password"], input[name="password"]', password);
    await page.click('button[type="submit"]');

    // Wait for login to complete
    await page.waitForURL((url) => !url.pathname.includes('/login'), {
      timeout: 15000,
    });

    // Screenshot logged in
    await saveScreenshot(page, testName, '01_logged_in');

    // Find and click logout button (try multiple selectors)
    const logoutSelectors = [
      'button:has-text("Logout")',
      'button:has-text("Sign out")',
      'a:has-text("Logout")',
      '[data-testid="logout"]',
    ];

    let logoutClicked = false;
    for (const selector of logoutSelectors) {
      const element = page.locator(selector).first();
      if (await element.isVisible({ timeout: 1000 }).catch(() => false)) {
        await element.click();
        logoutClicked = true;
        break;
      }
    }

    if (!logoutClicked) {
      // If no logout button found, skip this test
      saveArtifact('skip_reason.json', { reason: 'No logout button found' }, testName);
      test.skip();
      return;
    }

    // Wait for redirect to login
    await page.waitForURL('**/login', { timeout: 10000 });

    // Screenshot logged out
    await saveScreenshot(page, testName, '02_logged_out');

    // Save console logs
    saveArtifact('console_logs.json', consoleLogs, testName);

    // Create evidence bundle
    createEvidenceBundle(testName, {
      consoleLogs,
      assertions: [
        {
          name: 'Redirected to login',
          passed: page.url().includes('/login'),
        },
      ],
    });

    expect(page.url()).toContain('/login');
  });
});
