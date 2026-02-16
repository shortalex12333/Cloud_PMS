/**
 * Receiving "+" Button Journey Tests
 * ===================================
 *
 * Tests the global "+" entry point in SpotlightSearch for starting new receivings.
 * This is the PRIMARY entry point for the receiving journey - all crew should be able to use it.
 *
 * Roles tested: Crew (all roles), HOD, Captain
 */

import { test, expect } from '@playwright/test';
import { loginAs, TEST_USERS, openSpotlight, UserRole } from './auth.helper';

// Test configurations
const BASE_URL = process.env.STAGING_URL || 'https://app.celeste7.ai';

test.describe('Receiving "+" Button Journey', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
  });

  test.describe('UI Elements', () => {
    test('should display "Log" button in SpotlightSearch action bar', async ({ page }) => {
      await loginAs(page, 'captain');
      await page.goto(`${BASE_URL}/app`);

      // Wait for SpotlightSearch to load
      await page.waitForSelector('[data-testid="search-input"]', { timeout: 10000 });

      // Find the "Log" button in the action bar
      const logButton = page.locator('[data-testid="log-receiving-button"]');
      await expect(logButton).toBeVisible({ timeout: 5000 });

      // Should have Plus icon and "Log" text
      await expect(logButton).toContainText('Log');
    });

    test('should open receiving upload modal when "Log" button clicked', async ({ page }) => {
      await loginAs(page, 'captain');
      await page.goto(`${BASE_URL}/app`);

      // Click the Log button
      const logButton = page.locator('[data-testid="log-receiving-button"]');
      await logButton.click();

      // Dialog should open
      const dialog = page.locator('[role="dialog"]');
      await expect(dialog).toBeVisible({ timeout: 5000 });

      // Should have "Log Receiving" title
      await expect(dialog).toContainText('Log Receiving');

      // Should have description text
      await expect(dialog).toContainText('Capture or upload');
    });

    test('should show camera and upload options in modal', async ({ page }) => {
      await loginAs(page, 'captain');
      await page.goto(`${BASE_URL}/app`);

      // Open the modal
      const logButton = page.locator('[data-testid="log-receiving-button"]');
      await logButton.click();

      const dialog = page.locator('[role="dialog"]');
      await expect(dialog).toBeVisible();

      // Should have camera button
      const cameraButton = dialog.locator('button:has-text("Camera"), button:has-text("Take Photo")');
      await expect(cameraButton.first()).toBeVisible({ timeout: 5000 });

      // Should have file upload area
      const uploadArea = dialog.locator('input[type="file"], [data-testid="file-input"], .dropzone');
      await expect(uploadArea.first()).toBeAttached();
    });
  });

  test.describe('Role Access - All Crew Can Use "+"', () => {
    const roles: UserRole[] = ['crew', 'hod', 'captain'];

    for (const role of roles) {
      test(`${role} should see and click "Log" button`, async ({ page }) => {
        await loginAs(page, role);
        await page.goto(`${BASE_URL}/app`);

        // Wait for page load
        await page.waitForSelector('[data-testid="search-input"]', { timeout: 10000 });

        // Find the "Log" button
        const logButton = page.locator('[data-testid="log-receiving-button"]');
        await expect(logButton).toBeVisible({ timeout: 5000 });

        // Click should open modal
        await logButton.click();

        const dialog = page.locator('[role="dialog"]');
        await expect(dialog).toBeVisible({ timeout: 5000 });

        // Close the dialog for cleanup
        const closeButton = dialog.locator('button[aria-label="Close"], [data-testid="dialog-close"]');
        if (await closeButton.count() > 0) {
          await closeButton.first().click();
        }
      });
    }
  });

  test.describe('File Upload Flow', () => {
    test('should allow file selection in modal', async ({ page }) => {
      await loginAs(page, 'captain');
      await page.goto(`${BASE_URL}/app`);

      // Open the modal
      const logButton = page.locator('[data-testid="log-receiving-button"]');
      await logButton.click();

      const dialog = page.locator('[role="dialog"]');
      await expect(dialog).toBeVisible();

      // Find file input
      const fileInput = dialog.locator('input[type="file"]');
      await expect(fileInput).toBeAttached();

      // Accept JPEG, PNG, PDF types (per spec)
      const acceptAttr = await fileInput.getAttribute('accept');
      // May have image/jpeg, image/png, application/pdf
      expect(acceptAttr || '').toMatch(/image|pdf/i);
    });

    test('should display selected file preview', async ({ page }) => {
      await loginAs(page, 'captain');
      await page.goto(`${BASE_URL}/app`);

      // Open the modal
      const logButton = page.locator('[data-testid="log-receiving-button"]');
      await logButton.click();

      const dialog = page.locator('[role="dialog"]');
      await expect(dialog).toBeVisible();

      // Create a test file and upload
      const fileInput = dialog.locator('input[type="file"]');

      // Create a simple test image buffer (1x1 red pixel PNG)
      const testImageBuffer = Buffer.from(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg==',
        'base64'
      );

      await fileInput.setInputFiles({
        name: 'test-invoice.png',
        mimeType: 'image/png',
        buffer: testImageBuffer,
      });

      // Should show file name or preview
      const fileIndicator = dialog.locator(':text("test-invoice"), img[alt*="preview"], .preview');
      await expect(fileIndicator.first()).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('Dialog Interaction', () => {
    test('should close dialog when clicking outside or pressing Escape', async ({ page }) => {
      await loginAs(page, 'captain');
      await page.goto(`${BASE_URL}/app`);

      // Open the modal
      const logButton = page.locator('[data-testid="log-receiving-button"]');
      await logButton.click();

      let dialog = page.locator('[role="dialog"]');
      await expect(dialog).toBeVisible();

      // Press Escape to close
      await page.keyboard.press('Escape');

      // Dialog should be hidden/closed
      await expect(dialog).not.toBeVisible({ timeout: 3000 });

      // Re-open for next test
      await logButton.click();
      dialog = page.locator('[role="dialog"]');
      await expect(dialog).toBeVisible();

      // Click outside to close (click on overlay)
      const overlay = page.locator('[data-testid="dialog-overlay"], .dialog-overlay, [aria-hidden="true"]');
      if (await overlay.count() > 0) {
        await overlay.first().click({ force: true, position: { x: 10, y: 10 } });
        await expect(dialog).not.toBeVisible({ timeout: 3000 });
      }
    });
  });
});

// ============================================================================
// LEDGER INTEGRATION TESTS
// ============================================================================
test.describe('Receiving Journey - Ledger Tracking', () => {
  test('receiving_created event should be logged after successful upload', async ({ page }) => {
    // This test requires a successful file upload and receiving creation
    // which depends on the OCR service being available
    test.skip(true, 'Requires OCR service and database verification - run manually');

    await loginAs(page, 'captain');
    await page.goto(`${BASE_URL}/app`);

    // Complete the receiving journey...
    // Verify ledger entry was created via API call
  });
});
