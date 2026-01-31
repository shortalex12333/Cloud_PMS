/**
 * Example Playwright Test with JWT Refresh
 * =========================================
 *
 * This shows how to use the auth fixtures that automatically
 * handle JWT refresh before each test.
 */

import { test, expect } from './fixtures/auth';

test.describe('Receiving Lens E2E', () => {
  test('should load dashboard with valid JWT', async ({ page }) => {
    // JWT is automatically checked and refreshed before this test
    // No need to login or check JWT manually

    await page.goto('/dashboard');

    // Verify we're logged in
    await expect(page).toHaveURL(/.*dashboard/);

    // Check for user-specific content (adjust selector as needed)
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
  });

  test('should create receiving record', async ({ page }) => {
    // JWT is automatically refreshed if needed

    await page.goto('/receiving');

    // Click "Create Receiving" button
    await page.click('button:has-text("Create Receiving")');

    // Fill form
    await page.fill('input[name="vendor_name"]', 'E2E Test Vendor');
    await page.fill('input[name="vendor_reference"]', 'E2E-TEST-001');
    await page.fill('input[name="received_date"]', '2026-01-30');

    // Submit
    await page.click('button[type="submit"]:has-text("Create")');

    // Wait for success message
    await expect(page.locator('text=Receiving created successfully')).toBeVisible({ timeout: 10000 });
  });

  test('should search for parts', async ({ page }) => {
    // JWT is automatically refreshed if needed

    await page.goto('/search');

    // Type search query
    await page.fill('input[placeholder*="Search"]', 'pump');

    // Wait for results
    await expect(page.locator('[data-testid="search-results"]')).toBeVisible({ timeout: 10000 });

    // Verify results contain cards
    const cards = page.locator('[data-testid="result-card"]');
    await expect(cards).toHaveCountGreaterThan(0);
  });

  test('should handle long-running operations', async ({ page }) => {
    // This test simulates a long operation
    // JWT will be refreshed if it expires during the test

    await page.goto('/dashboard');

    // Simulate work...
    await page.waitForTimeout(1000);

    // JWT is still valid (refreshed by fixture if needed)
    await page.goto('/receiving');
    await expect(page).toHaveURL(/.*receiving/);
  });
});

test.describe('Part Lens E2E', () => {
  test('should display part microactions in search results', async ({ page }) => {
    await page.goto('/search');

    // Search for a part
    await page.fill('input[placeholder*="Search"]', 'hydraulic pump');

    // Wait for results
    await expect(page.locator('[data-testid="result-card"]')).toBeVisible({ timeout: 10000 });

    // Check that microaction buttons are present
    const firstCard = page.locator('[data-testid="result-card"]').first();

    // Verify microaction buttons (adjust based on your actual implementation)
    await expect(firstCard.locator('button:has-text("Add to Shopping List")')).toBeVisible();
    await expect(firstCard.locator('button:has-text("Receive Part")')).toBeVisible();
  });
});
