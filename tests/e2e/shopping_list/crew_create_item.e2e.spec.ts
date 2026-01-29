/**
 * Shopping List Lens - CREW Create Item E2E Test
 *
 * Tests the complete flow of a CREW member creating a shopping list item via UI:
 * 1. Search for "add to shopping list"
 * 2. Click "Add to Shopping List" action button
 * 3. Fill in the form (item_name, quantity, source_type, etc.)
 * 4. Submit and verify success toast
 */

import { test, expect } from '@playwright/test';
import { saveScreenshot, saveArtifact } from '../../helpers/artifacts';

test.describe('Shopping List - CREW Create Item', () => {
  test.beforeEach(async ({ page }) => {
    // Login as test user (should have CREW-equivalent role)
    await page.goto('/login');

    // Fill login form
    await page.fill('input[type="email"]', process.env.TEST_USER_EMAIL || '');
    await page.fill('input[type="password"]', process.env.TEST_USER_PASSWORD || '');
    await page.click('button[type="submit"]');

    // Wait for dashboard to load
    await page.waitForURL(/\/dashboard/, { timeout: 10000 });
    await saveScreenshot(page, 'shopping_list/crew_create', 'dashboard_loaded');
  });

  test('CREW can create shopping list item via search intent', async ({ page }) => {
    const testName = 'shopping_list/crew_create_item';

    // Open search (Cmd+K or click search input)
    const searchInput = page.locator('input[placeholder*="Search"], input[type="search"]').first();
    await searchInput.click();
    await saveScreenshot(page, testName, 'search_opened');

    // Type shopping list query
    await searchInput.fill('add to shopping list');
    await page.waitForTimeout(500); // Wait for debounce + action suggestions

    await saveScreenshot(page, testName, 'query_entered');

    // Wait for action suggestions to appear
    const suggestedActions = page.locator('[data-testid="suggested-actions"]');
    await expect(suggestedActions).toBeVisible({ timeout: 5000 });

    // Look for "Add to Shopping List" button
    const addButton = page.locator('[data-testid="action-btn-create_shopping_list_item"]');
    await expect(addButton).toBeVisible();
    await expect(addButton).toContainText(/Add.*Shopping List/i);

    await saveScreenshot(page, testName, 'action_button_visible');

    // Click the action button
    await addButton.click();

    // Wait for modal to open
    const modal = page.locator('[role="dialog"][aria-modal="true"]');
    await expect(modal).toBeVisible({ timeout: 3000 });
    await expect(modal.locator('#action-modal-title')).toContainText(/Add.*Shopping List/i);

    await saveScreenshot(page, testName, 'modal_opened');

    // Fill in the form
    const itemName = `Test Item ${Date.now()}`;
    await page.fill('input#item_name', itemName);
    await page.fill('input#quantity', '5');

    // Select source_type if it's a select field, or fill if it's text
    const sourceTypeField = page.locator('#source_type, input[id*="source"]').first();
    if (await sourceTypeField.getAttribute('type') === 'text') {
      await sourceTypeField.fill('manual');
    } else {
      await sourceTypeField.selectOption('manual');
    }

    await saveScreenshot(page, testName, 'form_filled');

    // Submit the form
    const submitButton = page.locator('button[type="submit"]').filter({ hasText: /Execute/i });
    await submitButton.click();

    // Wait for success toast
    const toast = page.locator('[data-sonner-toast]').filter({ hasText: /success|completed/i });
    await expect(toast).toBeVisible({ timeout: 5000 });

    await saveScreenshot(page, testName, 'success_toast');

    // Verify modal closed
    await expect(modal).not.toBeVisible({ timeout: 2000 });

    // Save test evidence
    saveArtifact('crew_create_item_evidence.json', {
      item_name: itemName,
      quantity: 5,
      source_type: 'manual',
      success: true,
      timestamp: new Date().toISOString(),
    }, testName);
  });

  test('CREW create form validates required fields', async ({ page }) => {
    const testName = 'shopping_list/crew_create_validation';

    // Open search and trigger action
    const searchInput = page.locator('input[placeholder*="Search"], input[type="search"]').first();
    await searchInput.click();
    await searchInput.fill('add shopping item');
    await page.waitForTimeout(500);

    // Click action button
    const addButton = page.locator('[data-testid="action-btn-create_shopping_list_item"]');
    await addButton.click();

    // Wait for modal
    const modal = page.locator('[role="dialog"][aria-modal="true"]');
    await expect(modal).toBeVisible();

    // Try to submit without filling fields
    const submitButton = page.locator('button[type="submit"]').filter({ hasText: /Execute/i });
    await submitButton.click();

    // Should see validation error
    const errorMessage = page.locator('.text-red-400, [class*="error"]').first();
    await expect(errorMessage).toBeVisible({ timeout: 2000 });

    await saveScreenshot(page, testName, 'validation_error');

    // Save evidence
    saveArtifact('validation_evidence.json', {
      validation_triggered: true,
      timestamp: new Date().toISOString(),
    }, testName);
  });

  test('0×500 requirement: UI interactions do not cause 5xx errors', async ({ page }) => {
    const testName = 'shopping_list/crew_create_0x500';
    const errors: string[] = [];

    // Capture console errors
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    // Capture network errors
    page.on('response', async (response) => {
      if (response.status() >= 500) {
        errors.push(`5xx error: ${response.url()} -> ${response.status()}`);
      }
    });

    // Execute the full flow
    const searchInput = page.locator('input[placeholder*="Search"], input[type="search"]').first();
    await searchInput.click();
    await searchInput.fill('create shopping list item');
    await page.waitForTimeout(1000);

    const addButton = page.locator('[data-testid="action-btn-create_shopping_list_item"]');
    if (await addButton.isVisible()) {
      await addButton.click();

      const modal = page.locator('[role="dialog"][aria-modal="true"]');
      await expect(modal).toBeVisible();

      await page.fill('input#item_name', 'Test 0x500');
      await page.fill('input#quantity', '1');

      const submitButton = page.locator('button[type="submit"]').filter({ hasText: /Execute/i });
      await submitButton.click();

      await page.waitForTimeout(2000);
    }

    // Save evidence
    saveArtifact('0x500_evidence.json', {
      errors,
      error_count: errors.length,
      has_5xx_errors: errors.some(e => e.includes('5xx')),
      timestamp: new Date().toISOString(),
    }, testName);

    // Assert no 5xx errors
    const fivexxErrors = errors.filter(e => e.includes('5xx'));
    expect(fivexxErrors.length).toBe(0);
  });
});
