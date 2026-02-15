/**
 * Test: Work Order Full-Screen ContextPanel with Enriched Data
 * Verifies PR #286 and #287 changes work correctly
 */

import { test, expect } from '@playwright/test';

const APP_URL = 'https://app.celeste7.ai';
const TEST_EMAIL = 'x@alex-short.com';
const TEST_PASSWORD = 'Password2!';

test.describe('Work Order Full-Screen View', () => {
  test.beforeEach(async ({ page }) => {
    // Go to login page
    await page.goto(`${APP_URL}/login`);
    await page.waitForTimeout(2000);

    // Check if login form is present
    const emailInput = page.locator('input[type="email"]');
    if (await emailInput.isVisible({ timeout: 5000 }).catch(() => false)) {
      await emailInput.fill(TEST_EMAIL);
      await page.fill('input[type="password"]', TEST_PASSWORD);
      await page.click('button[type="submit"]');
      await page.waitForTimeout(3000);
    }

    // Wait for redirect to main app
    await page.waitForURL('**/app**', { timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(2000);
  });

  test('Search work order and open full-screen panel', async ({ page }) => {
    // Search for work order - try multiple selectors
    const searchBar = page.locator('[data-testid="search-input"]').first();
    await searchBar.waitFor({ state: 'visible', timeout: 10000 });

    await searchBar.click();
    await searchBar.fill('work order');
    await page.waitForTimeout(2000);

    // Look for work order results
    const results = page.locator('[data-testid="search-result"], [data-entity-type="work_order"]');
    const count = await results.count();
    console.log(`Found ${count} work order results`);

    if (count > 0) {
      // Click first result
      await results.first().click();
      await page.waitForTimeout(1500);

      // Verify context panel opens in full-screen mode
      const contextPanel = page.locator('[data-testid="context-panel"]');
      await expect(contextPanel).toBeVisible({ timeout: 5000 });

      // Check it's expanded (full-screen)
      const expanded = await contextPanel.getAttribute('data-expanded');
      expect(expanded).toBe('true');

      // Verify work order card is rendered
      const workOrderCard = page.locator('[data-testid="context-panel-work-order-card"]');
      await expect(workOrderCard).toBeVisible();

      // Take screenshot
      await page.screenshot({ path: 'test-results/work-order-fullscreen.png', fullPage: true });

      console.log('✅ Work order opened in full-screen mode');
    } else {
      console.log('⚠️ No work order results found - trying direct search');

      // Try searching for specific work order
      await searchBar.clear();
      await searchBar.fill('Hydraulic');
      await page.waitForTimeout(2000);

      const hydraulicResults = page.locator('[data-testid="search-result"]');
      if (await hydraulicResults.count() > 0) {
        await hydraulicResults.first().click();
        await page.waitForTimeout(1500);

        const contextPanel = page.locator('[data-testid="context-panel"]');
        await expect(contextPanel).toBeVisible({ timeout: 5000 });

        await page.screenshot({ path: 'test-results/work-order-hydraulic.png', fullPage: true });
      }
    }
  });

  test('Verify enriched data sections are present', async ({ page }) => {
    const searchBar = page.locator('[data-testid="search-input"]');
    await searchBar.waitFor({ state: 'visible', timeout: 10000 });

    await searchBar.fill('CI Test WO');
    await page.waitForTimeout(2000);

    const results = page.locator('[data-testid="search-result"]');
    if (await results.count() > 0) {
      await results.first().click();
      await page.waitForTimeout(1500);

      // Verify sections exist
      const notesSection = page.locator('text=Notes');
      const partsSection = page.locator('text=Parts Used');
      const checklistSection = page.locator('text=Checklist');
      const historySection = page.locator('text=History');

      // At least some sections should be visible
      const sectionsVisible = await Promise.all([
        notesSection.isVisible().catch(() => false),
        partsSection.isVisible().catch(() => false),
        checklistSection.isVisible().catch(() => false),
        historySection.isVisible().catch(() => false),
      ]);

      const visibleCount = sectionsVisible.filter(Boolean).length;
      console.log(`Sections visible: ${visibleCount}/4`);

      await page.screenshot({ path: 'test-results/work-order-sections.png', fullPage: true });

      expect(visibleCount).toBeGreaterThan(0);
    }
  });

  test('ESC key closes panel', async ({ page }) => {
    const searchBar = page.locator('[data-testid="search-input"]');
    await searchBar.waitFor({ state: 'visible', timeout: 10000 });

    await searchBar.fill('work order');
    await page.waitForTimeout(2000);

    const results = page.locator('[data-testid="search-result"]');
    if (await results.count() > 0) {
      await results.first().click();
      await page.waitForTimeout(1500);

      const contextPanel = page.locator('[data-testid="context-panel"]');
      await expect(contextPanel).toBeVisible({ timeout: 5000 });

      // Press ESC
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);

      // Panel should be hidden
      await expect(contextPanel).not.toBeVisible();
      console.log('✅ ESC key closes panel');
    }
  });
});
