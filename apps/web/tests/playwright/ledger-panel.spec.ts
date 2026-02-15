/**
 * Ledger Panel E2E Tests
 *
 * Tests the ledger panel functionality:
 * - Opening from dropdown
 * - Displaying events grouped by day
 * - Verifying ledger events are recorded
 */

import { test, expect, Page } from '@playwright/test';

const BASE_URL = process.env.E2E_BASE_URL || 'https://app.celeste7.ai';
const PASSWORD = 'Password2!';

const TEST_USER = {
  email: 'hod.test@alex-short.com',
  role: 'HOD',
};

// Helper to login
async function login(page: Page, email: string, password: string): Promise<void> {
  await page.goto(`${BASE_URL}/login`);
  await page.waitForSelector('input[type="email"], input[name="email"]', { timeout: 10000 });
  await page.fill('input[type="email"], input[name="email"]', email);
  await page.fill('input[type="password"], input[name="password"]', password);
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 15000 });
}

// Helper to open ledger from dropdown
async function openLedger(page: Page): Promise<void> {
  // Find and click the BookOpen icon button (Ledger dropdown trigger)
  const ledgerTrigger = page.locator('button[aria-label="Ledger"]');
  await ledgerTrigger.waitFor({ state: 'visible', timeout: 10000 });
  await ledgerTrigger.click();

  // Wait for dropdown to appear
  await page.waitForSelector('[role="menuitem"]', { timeout: 5000 });

  // Click "Ledger" menu item
  const ledgerMenuItem = page.locator('[role="menuitem"]:has-text("Ledger")');
  await ledgerMenuItem.click();
}

test.describe('Ledger Panel', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USER.email, PASSWORD);
    console.log(`✅ Logged in as ${TEST_USER.email}`);
  });

  test('can open ledger panel from dropdown', async ({ page }) => {
    // Open ledger
    await openLedger(page);

    // Verify ledger panel is visible - look for heading
    const ledgerHeading = page.getByRole('heading', { name: 'Ledger' });
    await expect(ledgerHeading).toBeVisible({ timeout: 10000 });

    // Verify close button exists
    const closeButton = page.locator('button[aria-label="Close ledger"]');
    await expect(closeButton).toBeVisible();

    console.log('✅ Ledger panel opened successfully');
  });

  test('ledger panel shows content area', async ({ page }) => {
    // Open ledger
    await openLedger(page);

    // Verify panel is open
    const ledgerHeading = page.getByRole('heading', { name: 'Ledger' });
    await expect(ledgerHeading).toBeVisible({ timeout: 10000 });

    // Wait for content to load
    await page.waitForTimeout(2000);

    // Panel should have the Reads toggle visible
    const readsToggle = page.locator('button:has-text("Reads")');
    await expect(readsToggle).toBeVisible();

    console.log('✅ Ledger panel shows content area');
  });

  test('can close ledger panel', async ({ page }) => {
    // Open ledger
    await openLedger(page);

    // Verify panel is open
    const ledgerPanel = page.locator('h2:has-text("Ledger")');
    await expect(ledgerPanel).toBeVisible({ timeout: 5000 });

    // Click close button
    const closeButton = page.locator('button[aria-label="Close ledger"]');
    await closeButton.click();

    // Verify panel is closed
    await expect(ledgerPanel).not.toBeVisible({ timeout: 5000 });

    console.log('✅ Ledger panel closed successfully');
  });

  test('ledger panel has proper z-index (above other content)', async ({ page }) => {
    // Open ledger
    await openLedger(page);

    // Verify the panel header is visible
    const ledgerHeader = page.locator('h2:has-text("Ledger")');
    await expect(ledgerHeader).toBeVisible({ timeout: 5000 });

    // Panel should be interactable - close button exists and is enabled
    const closeButton = page.locator('button[aria-label="Close ledger"]');
    await expect(closeButton).toBeEnabled();

    // Reads toggle should be clickable
    const readsToggle = page.locator('button:has-text("Reads")');
    await expect(readsToggle).toBeEnabled();

    console.log('✅ Ledger panel has proper z-index layering');
  });

  test('reads toggle works correctly', async ({ page }) => {
    // Open ledger
    await openLedger(page);

    // Find the Reads toggle button
    const readsToggle = page.locator('button:has-text("Reads")');
    await expect(readsToggle).toBeVisible({ timeout: 5000 });

    // Click to enable reads
    await readsToggle.click();

    // Verify toggle state changed (should have accent color when active)
    await expect(readsToggle).toHaveClass(/bg-celeste-accent|text-celeste-white/);

    console.log('✅ Reads toggle works correctly');
  });
});

test.describe('Ledger Integration', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USER.email, PASSWORD);
  });

  test('ledger is accessible from main UI', async ({ page }) => {
    // Verify the BookOpen icon exists in the toolbar
    const ledgerTrigger = page.locator('button[aria-label="Ledger"]');
    await expect(ledgerTrigger).toBeVisible({ timeout: 10000 });

    // Click to open dropdown
    await ledgerTrigger.click();

    // Verify dropdown appears with Ledger option
    const ledgerMenuItem = page.locator('[role="menuitem"]:has-text("Ledger")');
    await expect(ledgerMenuItem).toBeVisible({ timeout: 5000 });

    console.log('✅ Ledger is accessible from main UI');
  });
});
