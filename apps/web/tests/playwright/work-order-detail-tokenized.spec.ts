/**
 * E2E Test: WorkOrderDetail Component (Tokenized Light/Dark Mode)
 *
 * Verifies the tokenized WorkOrderDetail component renders correctly.
 * Tests against the /test/work-order-detail page which uses mock data.
 */

import { test, expect } from '@playwright/test';

const LOCAL_URL = 'http://localhost:3000';

test.describe('WorkOrderDetail Component - Tokenized Styling', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${LOCAL_URL}/test/work-order-detail`);
  });

  test('renders without errors', async ({ page }) => {
    await expect(page).toHaveTitle(/CelesteOS|Celeste/i);
    const container = page.locator('.wo-container');
    await expect(container).toBeVisible();
  });

  test('displays header with correct format', async ({ page }) => {
    // Title
    const title = page.locator('.wo-title');
    await expect(title).toBeVisible();
    await expect(title).toContainText('Work Order #0142');

    // Subtitle with "Created on [date] by [author]." format
    const subtitle = page.locator('.wo-subtitle');
    await expect(subtitle).toBeVisible();
    await expect(subtitle).toContainText('Created on');
    await expect(subtitle).toContainText('John Doe');

    // Status indicator with dot (check DOM presence, not visibility for 8px element)
    const statusDot = page.locator('.wo-status-dot').first();
    await expect(statusDot).toHaveCount(1);

    // Status text
    const headerMeta = page.locator('.wo-header-meta');
    await expect(headerMeta).toContainText('Status');
    await expect(headerMeta).toContainText('In Progress');
    await expect(headerMeta).toContainText('Priority');
    await expect(headerMeta).toContainText('Medium');
  });

  test('displays metadata grid with columns', async ({ page }) => {
    const metadataSection = page.locator('.wo-metadata');
    await expect(metadataSection).toBeVisible();

    // Left column
    const leftCol = page.locator('.wo-metadata-col-left');
    await expect(leftCol).toBeVisible();
    await expect(leftCol).toContainText('Equipment');
    await expect(leftCol).toContainText('Category');
    await expect(leftCol).toContainText('Assigned To');

    // Divider exists in DOM (1px may not pass visibility check)
    const divider = page.locator('.wo-metadata-divider');
    await expect(divider).toHaveCount(1);

    // Right column
    const rightCol = page.locator('.wo-metadata-col-right');
    await expect(rightCol).toBeVisible();
    await expect(rightCol).toContainText('Location');
    await expect(rightCol).toContainText('Due Date');
    await expect(rightCol).toContainText('Linked Fault');
  });

  test('displays description section', async ({ page }) => {
    const descriptionHeader = page.locator('.wo-section-header', { hasText: 'Description' });
    await expect(descriptionHeader).toBeVisible();

    const descriptionText = page.locator('.wo-description-text');
    await expect(descriptionText).toBeVisible();
    await expect(descriptionText).toContainText('Inspect and repair');
  });

  test('displays evidence section with correct format', async ({ page }) => {
    const evidenceSection = page.locator('.wo-evidence-section');
    await expect(evidenceSection).toBeVisible();

    // Header should be "Evidence / Sources"
    const evidenceHeader = page.locator('.wo-section-header', { hasText: 'Evidence / Sources' });
    await expect(evidenceHeader).toBeVisible();

    // Should have 4 evidence rows
    const evidenceRows = page.locator('.wo-evidence-row');
    await expect(evidenceRows).toHaveCount(4);

    // Verify evidence format includes type and dash separator
    const evidenceText = page.locator('.wo-evidence-text').first();
    await expect(evidenceText).toContainText('Email:');
    await expect(evidenceText).toContainText('–');
  });

  test('displays activity log with entries', async ({ page }) => {
    const activitySection = page.locator('.wo-activity-section');
    await expect(activitySection).toBeVisible();

    const activityHeader = page.locator('.wo-section-header', { hasText: 'Activity' });
    await expect(activityHeader).toBeVisible();

    // Should have 2 activity entries
    const activityEntries = page.locator('.wo-activity-entry');
    await expect(activityEntries).toHaveCount(2);

    // Check format: [timestamp] Action (User)
    const activityList = page.locator('.wo-activity-list');
    await expect(activityList).toContainText('[Feb 12, 2026 10:14]');
    await expect(activityList).toContainText('Status changed');
    await expect(activityList).toContainText('(Alex Johnson)');
  });

  test('displays action bar with 3 buttons', async ({ page }) => {
    const actionBar = page.locator('.wo-action-bar');
    await expect(actionBar).toBeVisible();

    // Primary button
    const primaryBtn = page.locator('.wo-btn-primary');
    await expect(primaryBtn).toBeVisible();
    await expect(primaryBtn).toContainText('Update Status');

    // Secondary button
    const secondaryBtn = page.locator('.wo-action-bar .wo-btn-secondary');
    await expect(secondaryBtn).toBeVisible();
    await expect(secondaryBtn).toContainText('Add Evidence');

    // Danger button
    const dangerBtn = page.locator('.wo-btn-danger');
    await expect(dangerBtn).toBeVisible();
    await expect(dangerBtn).toContainText('Close Work Order');
  });

  test('mode toggle button exists', async ({ page }) => {
    // The mode toggle button should exist
    const toggleBtn = page.locator('button', { hasText: /Switch to (Dark|Light) Mode/ });
    await expect(toggleBtn).toBeVisible();
  });

  test('buttons are interactive', async ({ page }) => {
    // Primary button should be clickable
    const primaryBtn = page.locator('.wo-btn-primary');
    await expect(primaryBtn).toBeEnabled();
    await primaryBtn.click();

    // Secondary button should be clickable
    const secondaryBtn = page.locator('.wo-action-bar .wo-btn-secondary');
    await expect(secondaryBtn).toBeEnabled();
    await secondaryBtn.click();

    // Danger button should be clickable
    const dangerBtn = page.locator('.wo-btn-danger');
    await expect(dangerBtn).toBeEnabled();
    await dangerBtn.click();
  });

  test('container has proper styling', async ({ page }) => {
    const container = page.locator('.wo-container');

    // Check container has expected background
    const bgColor = await container.evaluate((el) => {
      return window.getComputedStyle(el).backgroundColor;
    });

    // Should have some background color (not transparent)
    expect(bgColor).not.toBe('rgba(0, 0, 0, 0)');

    // Check border is applied
    const borderStyle = await container.evaluate((el) => {
      return window.getComputedStyle(el).borderStyle;
    });
    expect(borderStyle).toBe('solid');

    // Check border-radius is applied
    const borderRadius = await container.evaluate((el) => {
      return window.getComputedStyle(el).borderRadius;
    });
    expect(borderRadius).toBe('16px');
  });

  test('take screenshots for visual verification', async ({ page }) => {
    // Take screenshot
    await page.screenshot({
      path: 'test-results/work-order-detail-component.png',
      fullPage: true,
    });

    // Component should remain visible
    const container = page.locator('.wo-container');
    await expect(container).toBeVisible();
  });
});
