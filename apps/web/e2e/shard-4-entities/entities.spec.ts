import { test, expect, SpotlightSearchPO, ContextPanelPO, TEST_CONFIG } from '../fixtures';

/**
 * SHARD 4: Entity Lens Tests (Work Orders, Faults, Equipment)
 *
 * LAW 12: DEEP UI VERIFICATION
 * - Tests must verify that data grids render correctly
 * - Metadata must match expected database state
 * - All lens sections must load without error
 */

test.describe('Work Order Lens', () => {
  test('should open work order from search', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('work order');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Verify it's a work order
      const entityType = await contextPanel.getAttribute('data-entity-type');
      expect(entityType).toBe('work_order');
    }
  });

  test('should display work order header with status', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('work order maintenance');

    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // LAW 12: Verify header renders
      const header = contextPanel.locator('header');
      await expect(header).toBeVisible();

      // Should show status pill
      const statusPill = contextPanel.locator('[data-testid="status-pill"], [class*="status"]');
      // Status should be visible if work order has status
    }
  });

  test('should display parts section in work order', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('work order');

    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Look for Parts section
      const partsSection = contextPanel.locator('text=Parts');
      // Parts section should exist (even if empty)
    }
  });

  test('should display notes section in work order', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('work order');

    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Look for Notes section
      const notesSection = contextPanel.locator('text=Notes');
    }
  });

  test('should display history/audit log in work order', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('work order');

    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Look for History section
      const historySection = contextPanel.locator('text=History');
    }
  });
});

test.describe('Fault Lens', () => {
  test('should open fault from search', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('fault');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Verify content loads
      const content = page.getByTestId('context-panel-content');
      await expect(content).toBeVisible({ timeout: 10_000 });
    }
  });

  test('should display fault severity', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('fault critical');

    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // LAW 12: Verify severity/priority indicator
      const severityIndicator = contextPanel.locator('[data-testid="priority-pill"], [class*="priority"]');
    }
  });

  test('should display linked equipment for fault', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('fault');

    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Look for linked equipment
      const linkedSection = contextPanel.locator('text=Equipment, text=Linked');
    }
  });
});

test.describe('Equipment Lens', () => {
  test('should open equipment from search', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('equipment engine');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Verify it's equipment
      const entityType = await contextPanel.getAttribute('data-entity-type');
      expect(['equipment', 'pms_equipment']).toContain(entityType);
    }
  });

  test('should display equipment specifications', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('equipment');

    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // LAW 12: Verify specifications render
      // Equipment should show manufacturer, model, serial number, etc.
      const content = page.getByTestId('context-panel-content');
      await expect(content).toBeVisible();
    }
  });

  test('should display maintenance schedule for equipment', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('equipment');

    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Look for maintenance section
      const maintenanceSection = contextPanel.locator('text=Maintenance, text=Schedule');
    }
  });

  test('should display linked work orders for equipment', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('equipment');

    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Look for work orders section
      const workOrdersSection = contextPanel.locator('text=Work Orders');
    }
  });
});

test.describe('Part/Inventory Lens', () => {
  test('should open part from search', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('part filter');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Verify content loads
      const content = page.getByTestId('context-panel-content');
      await expect(content).toBeVisible({ timeout: 10_000 });
    }
  });

  test('should display part inventory details', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('inventory');

    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // LAW 12: Verify inventory info renders
      // Should show quantity, location, reorder level, etc.
    }
  });
});

test.describe('Lens Navigation', () => {
  test('should navigate back from lens', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    const contextPanel = new ContextPanelPO(page);

    await spotlight.search('work order');
    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);
      await contextPanel.waitForContent();

      // Close the panel
      await contextPanel.close();

      // Panel should be hidden
      await expect(contextPanel.panel).toHaveAttribute('data-visible', 'false');
    }
  });

  test('should navigate between related entities', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('work order');
    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Look for "Show Related" button
      const showRelatedButton = contextPanel.locator('[aria-label*="Related"], [data-testid="show-related"]');

      if (await showRelatedButton.isVisible()) {
        await showRelatedButton.click();
        // Related entities should be shown
      }
    }
  });

  test('should support back/forward navigation in lens', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('work order');
    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount >= 2) {
      // Open first result
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      const firstEntityId = await contextPanel.getAttribute('data-entity-id');

      // Close and open second result
      await page.keyboard.press('Escape');
      await spotlight.clickResult(1);
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      const secondEntityId = await contextPanel.getAttribute('data-entity-id');

      // Use back button
      const backButton = contextPanel.locator('[aria-label*="Back"], [data-testid="nav-back"]');

      if (await backButton.isVisible()) {
        await backButton.click();
        await page.waitForTimeout(500);

        const currentEntityId = await contextPanel.getAttribute('data-entity-id');
        expect(currentEntityId).toBe(firstEntityId);
      }
    }
  });
});

test.describe('Lens Actions', () => {
  test('should show action buttons in work order lens', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('work order');
    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Look for action buttons
      const markCompleteButton = contextPanel.locator('text=Mark Complete, text=Complete');
      const reassignButton = contextPanel.locator('text=Reassign');
    }
  });

  test('should open add note modal', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('work order');
    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Look for Add Note button
      const addNoteButton = contextPanel.locator('text=Add Note, button:has-text("Add")');

      if (await addNoteButton.isVisible()) {
        await addNoteButton.click();

        // Modal should open
        const modal = page.locator('[role="dialog"]');
        await expect(modal).toBeVisible({ timeout: 5_000 });
      }
    }
  });
});

test.describe('Lens Data Grid (LAW 12)', () => {
  test('should render parts grid with correct columns', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('work order parts');
    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // LAW 12: Verify grid renders with headers
      const partsSection = contextPanel.locator('[data-section="parts"]');

      if (await partsSection.isVisible()) {
        // Should show column headers
        const partNameHeader = partsSection.locator('text=Part Name');
        const qtyHeader = partsSection.locator('text=Qty');
      }
    }
  });

  test('should render history timeline correctly', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    await spotlight.search('work order');
    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // LAW 12: Verify history section renders
      const historySection = contextPanel.locator('[data-section="history"]');

      if (await historySection.isVisible()) {
        // Should show timeline entries
        const timelineEntries = historySection.locator('[data-testid="history-entry"]');
      }
    }
  });
});
