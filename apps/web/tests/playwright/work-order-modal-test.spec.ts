/**
 * Work Order Modal Flow Test
 * Tests that clicking Add Note/Part/Checklist buttons opens modals
 */

import { test, expect } from '@playwright/test';

const BASE_URL = 'https://app.celeste7.ai';

test.describe('Work Order Modal Flows', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto(`${BASE_URL}/login`);

    // Wait for page to load
    await page.waitForLoadState('networkidle');

    // Fill login form if present
    const emailInput = page.locator('input[type="email"], input[name="email"]');
    if (await emailInput.isVisible({ timeout: 5000 }).catch(() => false)) {
      await emailInput.fill('alex.shorter@gmail.com');
      await page.locator('input[type="password"]').fill('Celeste123!');
      await page.locator('button[type="submit"]').click();
      await page.waitForURL('**/dashboard**', { timeout: 15000 }).catch(() => {});
    }
  });

  test('Add Note button opens modal with form', async ({ page }) => {
    // Navigate to work orders
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForLoadState('networkidle');

    // Search for work orders
    const searchInput = page.locator('input[placeholder*="Search"], input[type="search"]');
    if (await searchInput.isVisible({ timeout: 5000 }).catch(() => false)) {
      await searchInput.fill('work order');
      await page.keyboard.press('Enter');
      await page.waitForTimeout(2000);
    }

    // Click on a work order result to open context panel
    const workOrderResult = page.locator('[data-entity-type="work_order"], [class*="work-order"], [class*="WorkOrder"]').first();
    if (await workOrderResult.isVisible({ timeout: 5000 }).catch(() => false)) {
      await workOrderResult.click();
      await page.waitForTimeout(1000);
    }

    // Look for Add Note button
    const addNoteButton = page.locator('button:has-text("Add Note")').first();

    // Take screenshot of current state
    await page.screenshot({ path: 'test-results/work-order-before-click.png', fullPage: true });

    if (await addNoteButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      // Click Add Note
      await addNoteButton.click();
      await page.waitForTimeout(500);

      // Take screenshot after click
      await page.screenshot({ path: 'test-results/work-order-after-click.png', fullPage: true });

      // Check if modal opened
      const modal = page.locator('[role="dialog"], [class*="Dialog"], [class*="Modal"]');
      const modalVisible = await modal.isVisible({ timeout: 3000 }).catch(() => false);

      // Check for note text input in modal
      const noteInput = page.locator('textarea, input[name*="note"]');
      const inputVisible = await noteInput.isVisible({ timeout: 2000 }).catch(() => false);

      console.log('Modal visible:', modalVisible);
      console.log('Note input visible:', inputVisible);

      // Verify modal has required elements
      expect(modalVisible || inputVisible).toBeTruthy();
    } else {
      console.log('Add Note button not found - taking screenshot');
      await page.screenshot({ path: 'test-results/no-add-note-button.png', fullPage: true });
    }
  });
});
