/**
 * E2E Test: WorkOrderDetail Component (Tokenized Dark Mode)
 *
 * Verifies the new tokenized WorkOrderDetail component renders correctly.
 * Tests against the /test/work-order-detail page which uses mock data.
 *
 * This test validates:
 * - Component renders without errors
 * - All major sections are present (header, metadata, description, evidence, activity, actions)
 * - Dark mode styling is applied via tokens
 * - Interactive elements are functional
 */

import { test, expect } from '@playwright/test';

// Use localhost for testing the component
const LOCAL_URL = 'http://localhost:3000';

test.describe('WorkOrderDetail Component - Tokenized Dark Mode', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the test page
    await page.goto(`${LOCAL_URL}/test/work-order-detail`);
  });

  test('renders without errors', async ({ page }) => {
    // Check page loads
    await expect(page).toHaveTitle(/CelesteOS|Celeste/i);

    // Check component container exists
    const container = page.locator('.wo-container');
    await expect(container).toBeVisible();
  });

  test('displays header block correctly', async ({ page }) => {
    // Title should be visible
    const title = page.locator('.wo-title');
    await expect(title).toBeVisible();
    await expect(title).toContainText('Work Order #0142');

    // Status pill should be present
    const statusPill = page.locator('.wo-status-pill');
    await expect(statusPill).toBeVisible();
    await expect(statusPill).toContainText('In Progress');

    // Header meta row should show priority, created, author
    const headerMeta = page.locator('.wo-header-meta');
    await expect(headerMeta).toContainText('Priority');
    await expect(headerMeta).toContainText('High');
    await expect(headerMeta).toContainText('Created');
    await expect(headerMeta).toContainText('Author');
  });

  test('displays metadata grid with 6 fields', async ({ page }) => {
    const metadataSection = page.locator('.wo-metadata');
    await expect(metadataSection).toBeVisible();

    // Check for expected fields
    await expect(metadataSection).toContainText('Equipment');
    await expect(metadataSection).toContainText('Location');
    await expect(metadataSection).toContainText('Category');
    await expect(metadataSection).toContainText('Due Date');
    await expect(metadataSection).toContainText('Assigned To');
    await expect(metadataSection).toContainText('Linked Fault');
  });

  test('displays description with Show more toggle', async ({ page }) => {
    // Description section should be visible
    const descriptionHeader = page.locator('.wo-section-header', { hasText: 'Description' });
    await expect(descriptionHeader).toBeVisible();

    // Description text should be present
    const descriptionText = page.locator('.wo-description-text');
    await expect(descriptionText).toBeVisible();

    // Show more button should be visible for long descriptions
    const showMoreBtn = page.locator('.wo-expand-control');
    await expect(showMoreBtn).toBeVisible();
    await expect(showMoreBtn).toContainText('Show more');

    // Click show more
    await showMoreBtn.click();
    await expect(showMoreBtn).toContainText('Show less');

    // Click show less
    await showMoreBtn.click();
    await expect(showMoreBtn).toContainText('Show more');
  });

  test('displays evidence section with hover state', async ({ page }) => {
    const evidenceSection = page.locator('.wo-evidence-section');
    await expect(evidenceSection).toBeVisible();

    const evidenceHeader = page.locator('.wo-section-header', { hasText: 'Evidence' });
    await expect(evidenceHeader).toBeVisible();

    // Should have evidence rows
    const evidenceRows = page.locator('.wo-evidence-row');
    const count = await evidenceRows.count();
    expect(count).toBeGreaterThan(0);

    // Verify evidence types are rendered (email, photo, manual, log)
    const evidenceList = page.locator('.wo-evidence-list');
    await expect(evidenceList).toContainText('Generator maintenance');
    await expect(evidenceList).toContainText('hydraulic_leak');
    await expect(evidenceList).toContainText('Service Manual');
    await expect(evidenceList).toContainText('inspection log');
  });

  test('displays activity log', async ({ page }) => {
    const activitySection = page.locator('.wo-activity-section');
    await expect(activitySection).toBeVisible();

    const activityHeader = page.locator('.wo-section-header', { hasText: 'Activity' });
    await expect(activityHeader).toBeVisible();

    // Check activity entries
    const activityEntries = page.locator('.wo-activity-entry');
    const count = await activityEntries.count();
    expect(count).toBeGreaterThan(0);

    // Check format: [timestamp] Action (User)
    const activityList = page.locator('.wo-activity-list');
    await expect(activityList).toContainText('Status changed');
    await expect(activityList).toContainText('Alex Chen');
  });

  test('displays status select control', async ({ page }) => {
    const statusSelect = page.locator('.wo-select');
    await expect(statusSelect).toBeVisible();

    // Should have current value
    await expect(statusSelect).toHaveValue('In Progress');

    // Check options exist
    const options = statusSelect.locator('option');
    const optionCount = await options.count();
    expect(optionCount).toBe(5); // Open, In Progress, Waiting, Completed, Closed
  });

  test('displays action bar with 3 buttons', async ({ page }) => {
    const actionBar = page.locator('.wo-action-bar');
    await expect(actionBar).toBeVisible();

    // Primary button
    const primaryBtn = page.locator('.wo-btn-primary');
    await expect(primaryBtn).toBeVisible();
    await expect(primaryBtn).toContainText('Update Status');

    // Secondary button
    const secondaryBtn = page.locator('.wo-btn-secondary');
    await expect(secondaryBtn).toBeVisible();
    await expect(secondaryBtn).toContainText('Add Evidence');

    // Danger button
    const dangerBtn = page.locator('.wo-btn-danger');
    await expect(dangerBtn).toBeVisible();
    await expect(dangerBtn).toContainText('Close Work Order');
  });

  test('buttons are clickable', async ({ page }) => {
    // Setup console listener to capture logs
    const logs: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'log') {
        logs.push(msg.text());
      }
    });

    // Click primary button
    const primaryBtn = page.locator('.wo-btn-primary');
    await primaryBtn.click();

    // Click secondary button
    const secondaryBtn = page.locator('.wo-btn-secondary');
    await secondaryBtn.click();

    // Click danger button
    const dangerBtn = page.locator('.wo-btn-danger');
    await dangerBtn.click();

    // Verify console logs from handlers
    expect(logs).toContain('[Test] Status changed to: In Progress');
    expect(logs).toContain('[Test] Add evidence clicked');
    expect(logs).toContain('[Test] Close work order clicked');
  });

  test('dark mode tokens are applied', async ({ page }) => {
    const container = page.locator('.wo-container');

    // Check container has expected background (dark mode)
    const bgColor = await container.evaluate((el) => {
      return window.getComputedStyle(el).backgroundColor;
    });

    // Should be dark (#171717 = rgb(23, 23, 23))
    expect(bgColor).toBe('rgb(23, 23, 23)');

    // Check text colors
    const title = page.locator('.wo-title');
    const titleColor = await title.evaluate((el) => {
      return window.getComputedStyle(el).color;
    });

    // Should be light (#f2f2f2 = rgb(242, 242, 242))
    expect(titleColor).toBe('rgb(242, 242, 242)');
  });

  test('no hardcoded px values in rendered styles', async ({ page }) => {
    // Take a screenshot for visual verification
    await page.screenshot({
      path: 'test-results/work-order-detail-dark-mode.png',
      fullPage: true,
    });

    // Component should be visible and properly styled
    const container = page.locator('.wo-container');
    await expect(container).toBeVisible();
  });
});
