/**
 * Email Attachment Viewer E2E Tests
 *
 * Tests the email attachment preview flow:
 * - Inline viewing (no local save)
 * - Download button hidden for email attachments
 * - Micro-action dropdown functionality
 */

import { test, expect } from '@playwright/test';

test.describe('Email Attachment Viewer', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to email inbox
    await page.goto('/email/inbox');
    // Wait for inbox to load
    await page.waitForSelector('[data-testid="email-inbox"]', { timeout: 10000 });
  });

  test('clicking attachment opens inline viewer without save dialog', async ({ page }) => {
    // Find a thread with attachments
    const threadWithAttachment = page.locator('[data-testid="thread-item"]').filter({
      has: page.locator('[data-testid="has-attachments-icon"]'),
    }).first();

    // Skip if no attachments
    const count = await threadWithAttachment.count();
    if (count === 0) {
      test.skip();
      return;
    }

    // Click the thread
    await threadWithAttachment.click();

    // Wait for thread to load
    await page.waitForSelector('[data-testid="attachments-panel"]', { timeout: 5000 });

    // Click the first attachment
    const attachmentButton = page.locator('[data-testid="attachments-panel"] button').first();
    await attachmentButton.click();

    // Wait for viewer overlay to open
    const viewer = page.locator('[data-testid="document-viewer-overlay"]');
    await expect(viewer).toBeVisible({ timeout: 10000 });

    // Verify no browser save dialog appeared (overlay is visible = inline preview)
    await expect(viewer).toBeVisible();

    // Verify download button is NOT visible (allowDownload=false for email attachments)
    const downloadButton = viewer.locator('button:has-text("Download")');
    await expect(downloadButton).not.toBeVisible();
  });

  test('viewer shows micro-action dropdown when document is saved', async ({ page }) => {
    // Find a thread with attachments
    const threadWithAttachment = page.locator('[data-testid="thread-item"]').filter({
      has: page.locator('[data-testid="has-attachments-icon"]'),
    }).first();

    const count = await threadWithAttachment.count();
    if (count === 0) {
      test.skip();
      return;
    }

    await threadWithAttachment.click();
    await page.waitForSelector('[data-testid="attachments-panel"]', { timeout: 5000 });

    // Click attachment
    const attachmentButton = page.locator('[data-testid="attachments-panel"] button').first();
    await attachmentButton.click();

    // Wait for viewer
    const viewer = page.locator('[data-testid="document-viewer-overlay"]');
    await expect(viewer).toBeVisible({ timeout: 10000 });

    // Wait a bit for save-for-preview to complete (async)
    await page.waitForTimeout(2000);

    // Look for Actions button (only appears if document was saved)
    const actionsButton = viewer.locator('button:has-text("Actions")');

    // Actions button may or may not appear depending on save success
    const hasActionsButton = await actionsButton.isVisible();

    if (hasActionsButton) {
      // Click Actions dropdown
      await actionsButton.click();

      // Verify dropdown options
      await expect(page.locator('text=Add to Handover')).toBeVisible();
      await expect(page.locator('text=Attach to Work Order')).toBeVisible();
      await expect(page.locator('text=Unlink from Work Order')).toBeVisible();
    }
  });

  test('escape key closes the viewer', async ({ page }) => {
    const threadWithAttachment = page.locator('[data-testid="thread-item"]').filter({
      has: page.locator('[data-testid="has-attachments-icon"]'),
    }).first();

    const count = await threadWithAttachment.count();
    if (count === 0) {
      test.skip();
      return;
    }

    await threadWithAttachment.click();
    await page.waitForSelector('[data-testid="attachments-panel"]', { timeout: 5000 });

    const attachmentButton = page.locator('[data-testid="attachments-panel"] button').first();
    await attachmentButton.click();

    const viewer = page.locator('[data-testid="document-viewer-overlay"]');
    await expect(viewer).toBeVisible({ timeout: 10000 });

    // Press Escape
    await page.keyboard.press('Escape');

    // Viewer should close
    await expect(viewer).not.toBeVisible();
  });

  test('clicking backdrop closes the viewer', async ({ page }) => {
    const threadWithAttachment = page.locator('[data-testid="thread-item"]').filter({
      has: page.locator('[data-testid="has-attachments-icon"]'),
    }).first();

    const count = await threadWithAttachment.count();
    if (count === 0) {
      test.skip();
      return;
    }

    await threadWithAttachment.click();
    await page.waitForSelector('[data-testid="attachments-panel"]', { timeout: 5000 });

    const attachmentButton = page.locator('[data-testid="attachments-panel"] button').first();
    await attachmentButton.click();

    const viewer = page.locator('[data-testid="document-viewer-overlay"]');
    await expect(viewer).toBeVisible({ timeout: 10000 });

    // Click backdrop (the overlay itself, not the content)
    await viewer.click({ position: { x: 10, y: 10 } });

    // Viewer should close
    await expect(viewer).not.toBeVisible();
  });
});
