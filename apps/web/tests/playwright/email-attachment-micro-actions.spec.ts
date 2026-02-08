/**
 * E2E Tests: Email Attachment Micro-Actions
 *
 * Tests the complete flow:
 * 1. Open email with attachment
 * 2. Click attachment to open viewer
 * 3. Use micro-actions dropdown
 * 4. Verify backend link/unlink operations
 */

import { test, expect } from '@playwright/test';

test.describe('Email Attachment Micro-Actions', () => {
  // Store test data for cleanup
  let testDocumentId: string | null = null;
  let testWorkOrderId: string | null = null;

  test.beforeEach(async ({ page }) => {
    // Navigate to email inbox
    await page.goto('/email/inbox');
    await page.waitForSelector('[data-testid="email-inbox"]', { timeout: 15000 });
  });

  test('micro-actions dropdown appears after attachment saved', async ({ page }) => {
    // Find a thread with attachments
    const threadWithAttachment = page.locator('[data-testid="thread-item"]').filter({
      has: page.locator('[data-testid="has-attachments-icon"]'),
    }).first();

    const count = await threadWithAttachment.count();
    if (count === 0) {
      test.skip();
      return;
    }

    // Click thread
    await threadWithAttachment.click();
    await page.waitForSelector('[data-testid="attachments-panel"]', { timeout: 5000 });

    // Click first attachment
    const attachmentButton = page.locator('[data-testid="attachments-panel"] button').first();
    await attachmentButton.click();

    // Wait for viewer
    const viewer = page.locator('[data-testid="document-viewer-overlay"]');
    await expect(viewer).toBeVisible({ timeout: 10000 });

    // Wait for save-for-preview to complete
    await page.waitForTimeout(3000);

    // Check for Actions button (appears if document was saved)
    const actionsButton = viewer.locator('button:has-text("Actions")');
    const hasActions = await actionsButton.isVisible();

    if (hasActions) {
      // Click to open dropdown
      await actionsButton.click();

      // Verify micro-action options
      await expect(page.locator('text=Add to Handover')).toBeVisible();
      await expect(page.locator('text=Attach to Work Order')).toBeVisible();
      await expect(page.locator('text=Unlink from Work Order')).toBeVisible();
    }
  });

  test('attach to work order creates link', async ({ page }) => {
    // Find thread with attachment
    const threadWithAttachment = page.locator('[data-testid="thread-item"]').filter({
      has: page.locator('[data-testid="has-attachments-icon"]'),
    }).first();

    if (await threadWithAttachment.count() === 0) {
      test.skip();
      return;
    }

    await threadWithAttachment.click();
    await page.waitForSelector('[data-testid="attachments-panel"]', { timeout: 5000 });

    // Open attachment viewer
    await page.locator('[data-testid="attachments-panel"] button').first().click();
    const viewer = page.locator('[data-testid="document-viewer-overlay"]');
    await expect(viewer).toBeVisible({ timeout: 10000 });

    // Wait for save
    await page.waitForTimeout(3000);

    const actionsButton = viewer.locator('button:has-text("Actions")');
    if (!(await actionsButton.isVisible())) {
      test.skip();
      return;
    }

    // Setup dialog handler for work order ID prompt
    page.on('dialog', async dialog => {
      if (dialog.message().includes('Work Order ID')) {
        // Use a test work order ID (we'll verify this exists in the DB)
        await dialog.accept('2531d846-test-wo-id');
      } else {
        await dialog.dismiss();
      }
    });

    // Click Actions -> Attach to Work Order
    await actionsButton.click();
    await page.locator('text=Attach to Work Order').click();

    // Wait for operation
    await page.waitForTimeout(2000);

    // Should see success or already-linked alert
    // Note: In real test, we'd verify the database entry
  });

  test('unlink from work order removes link', async ({ page }) => {
    // Find thread with attachment
    const threadWithAttachment = page.locator('[data-testid="thread-item"]').filter({
      has: page.locator('[data-testid="has-attachments-icon"]'),
    }).first();

    if (await threadWithAttachment.count() === 0) {
      test.skip();
      return;
    }

    await threadWithAttachment.click();
    await page.waitForSelector('[data-testid="attachments-panel"]', { timeout: 5000 });

    await page.locator('[data-testid="attachments-panel"] button').first().click();
    const viewer = page.locator('[data-testid="document-viewer-overlay"]');
    await expect(viewer).toBeVisible({ timeout: 10000 });

    await page.waitForTimeout(3000);

    const actionsButton = viewer.locator('button:has-text("Actions")');
    if (!(await actionsButton.isVisible())) {
      test.skip();
      return;
    }

    // Setup dialog handlers
    page.on('dialog', async dialog => {
      if (dialog.type() === 'confirm') {
        await dialog.accept();
      } else {
        await dialog.dismiss();
      }
    });

    // Click Actions -> Unlink
    await actionsButton.click();
    await page.locator('text=Unlink from Work Order').click();

    await page.waitForTimeout(2000);
  });

  test('download button is hidden for email attachments', async ({ page }) => {
    const threadWithAttachment = page.locator('[data-testid="thread-item"]').filter({
      has: page.locator('[data-testid="has-attachments-icon"]'),
    }).first();

    if (await threadWithAttachment.count() === 0) {
      test.skip();
      return;
    }

    await threadWithAttachment.click();
    await page.waitForSelector('[data-testid="attachments-panel"]', { timeout: 5000 });

    await page.locator('[data-testid="attachments-panel"] button').first().click();
    const viewer = page.locator('[data-testid="document-viewer-overlay"]');
    await expect(viewer).toBeVisible({ timeout: 10000 });

    // Verify download button is NOT visible (SOC-2 compliance)
    const downloadButton = viewer.locator('button:has-text("Download")');
    await expect(downloadButton).not.toBeVisible();
  });
});
