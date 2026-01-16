import { test, expect } from '@playwright/test';

/**
 * E2E Acceptance Test: Context Navigation Basic Flow
 *
 * Verifies:
 * 1. Login works and redirects to /search
 * 2. Search page renders with input
 * 3. Navigation context creation (when implemented)
 * 4. Related panel (when implemented)
 * 5. Back/Forward navigation (when implemented)
 */

test.describe('Context Navigation - Basic Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Login with test credentials
    const email = process.env.TEST_USER_EMAIL || 'x@alex-short.com';
    const password = process.env.TEST_USER_PASSWORD || 'Password2!';

    await page.goto('/login');
    await page.waitForSelector('input[type="email"]', { timeout: 10000 });
    await page.fill('input[type="email"]', email);
    await page.fill('input[type="password"]', password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(search|dashboard)/, { timeout: 15000 });
    await page.waitForTimeout(1000);
  });

  test('login successful and search page loads', async ({ page }) => {
    // After login, should be on /search or /dashboard (if HOD)
    await expect(page).toHaveURL(/\/(search|dashboard)/);
    console.log('✓ Login successful, redirected to:', page.url());

    // Navigate to /search explicitly to test search page rendering
    await page.goto('/search');
    await expect(page).toHaveURL(/\/search/);

    // Search input should be visible (this verifies the Supabase client fix worked)
    const searchInput = page.locator('input[type="search"], input[placeholder*="Search" i]');
    await expect(searchInput).toBeVisible({ timeout: 10000 });

    console.log('✓ Search page rendered');
    console.log('✓ Search input visible');
  });

  test('can navigate to dashboard if HOD', async ({ page }) => {
    // Try to navigate to dashboard
    await page.goto('/dashboard');

    // Should either:
    // 1. Load dashboard (if user is HOD)
    // 2. Redirect to /search (if user is not HOD)
    await page.waitForURL(/\/(dashboard|search)/, { timeout: 10000 });

    const url = page.url();
    console.log('Dashboard navigation:', url.includes('dashboard') ? '✓ HOD access granted' : '✓ Redirected to search');
  });
});
