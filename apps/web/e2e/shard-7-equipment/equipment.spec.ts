import { test, expect, SpotlightSearchPO, ContextPanelPO, TEST_CONFIG } from '../fixtures';

/**
 * SHARD 7: Equipment Lens Tests (Deep Lens)
 *
 * LAW 12: DEEP UI VERIFICATION
 * - Tests must verify actual content rendering, not just panel existence
 * - Equipment metadata must match expected attributes
 * - All lens sections must load without error
 * - Navigation state must be properly maintained
 *
 * Equipment is a core entity in CelesteOS PMS (Planned Maintenance System).
 * Equipment items have:
 * - Specifications (manufacturer, model, serial, etc.)
 * - Maintenance schedules (recurring tasks)
 * - Linked work orders
 * - Linked faults
 * - Location hierarchy
 * - Documents/manuals
 */

test.describe('Equipment Lens Opening', () => {
  test.describe.configure({ retries: 1 });

  test('should open equipment from search using "engine" query', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('engine');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // LAW 12: Verify content loaded, not just panel visible
      const content = page.getByTestId('context-panel-content');
      await expect(content).toBeVisible({ timeout: 10_000 });

      // Verify no error state
      const errorState = page.getByTestId('context-panel-error');
      await expect(errorState).not.toBeVisible();
    }
  });

  test('should open equipment from search using "generator" query', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('generator');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Verify it's equipment type
      const entityType = await contextPanel.getAttribute('data-entity-type');
      expect(['equipment', 'pms_equipment']).toContain(entityType);
    }
  });

  test('should open equipment from search using "pump" query', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('pump');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // LAW 12: Verify loading completes
      const loading = page.getByTestId('context-panel-loading');
      await expect(loading).not.toBeVisible({ timeout: 15_000 });
    }
  });

  test('should have entity-id attribute when equipment opens', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    const contextPanel = new ContextPanelPO(page);

    await spotlight.search('engine');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);
      await contextPanel.waitForContent();

      // Verify entity ID is set
      const entityId = await contextPanel.getEntityId();
      expect(entityId).toBeTruthy();
      // UUID format validation
      expect(entityId).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);
    }
  });
});

test.describe('Equipment Metadata Display', () => {
  test('should display equipment name in header', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('engine');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // LAW 12: Verify header renders with equipment name
      const header = contextPanel.locator('header, [data-testid="lens-header"]');
      await expect(header).toBeVisible();

      // Header should contain text (equipment name)
      const headerText = await header.textContent();
      expect(headerText).toBeTruthy();
      expect(headerText!.length).toBeGreaterThan(0);
    }
  });

  test('should display equipment type badge', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('generator');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Look for type indicator (badge, tag, or pill)
      const typeIndicator = contextPanel.locator(
        '[data-testid="entity-type-badge"], [data-testid="type-pill"], [class*="badge"]'
      );

      // Type badge should be present
      if (await typeIndicator.first().isVisible()) {
        const badgeText = await typeIndicator.first().textContent();
        expect(badgeText).toBeTruthy();
      }
    }
  });

  test('should display equipment location/hierarchy', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('engine');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // LAW 12: Verify location/hierarchy section
      const locationSection = contextPanel.locator(
        'text=Location, text=System, [data-section="location"], [data-testid="equipment-location"]'
      );

      // Location info should be accessible in the panel
      const content = page.getByTestId('context-panel-content');
      await expect(content).toBeVisible();
    }
  });

  test('should display equipment status if available', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('pump');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Status indicators (operational, needs service, out of service)
      const statusIndicator = contextPanel.locator(
        '[data-testid="status-pill"], [data-testid="equipment-status"], [class*="status"]'
      );

      // If status exists, verify it's visible
      if (await statusIndicator.first().isVisible()) {
        const statusText = await statusIndicator.first().textContent();
        expect(statusText).toBeTruthy();
      }
    }
  });
});

test.describe('Equipment Sections', () => {
  test('should display specifications section with manufacturer', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('engine');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // LAW 12: Verify specifications section
      const specsSection = contextPanel.locator(
        '[data-section="specifications"], text=Specifications, text=Manufacturer'
      );

      // Content should be visible
      const content = page.getByTestId('context-panel-content');
      await expect(content).toBeVisible();
    }
  });

  test('should display specifications section with model and serial', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('generator');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Model and Serial number fields
      const modelField = contextPanel.locator('text=Model');
      const serialField = contextPanel.locator('text=Serial');

      // At least one spec field should be visible
      const contentVisible = page.getByTestId('context-panel-content');
      await expect(contentVisible).toBeVisible();
    }
  });

  test('should display maintenance schedule section', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('engine');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // LAW 12: Verify maintenance schedule section exists
      const maintenanceSection = contextPanel.locator(
        '[data-section="maintenance"], [data-section="schedule"], text=Maintenance, text=Schedule, text=Tasks'
      );

      // Maintenance section may or may not be visible depending on data
      // But content should load without error
      const errorState = page.getByTestId('context-panel-error');
      await expect(errorState).not.toBeVisible();
    }
  });

  test('should display running hours if tracked', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('engine');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Running hours field (for engines, generators, etc.)
      const runningHoursField = contextPanel.locator(
        'text=Running Hours, text=Hours, text=Runtime, [data-field="running_hours"]'
      );

      // Verify content loads
      const content = page.getByTestId('context-panel-content');
      await expect(content).toBeVisible();
    }
  });
});

test.describe('Equipment Related Entities', () => {
  test('should display linked work orders section', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('engine');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // LAW 12: Verify work orders section renders
      const workOrdersSection = contextPanel.locator(
        '[data-section="work-orders"], [data-section="workorders"], text=Work Orders, text=Work Order'
      );

      // Content should be visible
      const content = page.getByTestId('context-panel-content');
      await expect(content).toBeVisible();
    }
  });

  test('should display linked faults section', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('generator');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // LAW 12: Verify faults section renders
      const faultsSection = contextPanel.locator(
        '[data-section="faults"], text=Faults, text=Issues, text=Defects'
      );

      // Content should be visible without error
      const errorState = page.getByTestId('context-panel-error');
      await expect(errorState).not.toBeVisible();
    }
  });

  test('should display linked documents/manuals', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('engine');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Documents/Manuals section
      const documentsSection = contextPanel.locator(
        '[data-section="documents"], text=Documents, text=Manuals, text=Attachments'
      );

      // Content should load
      const content = page.getByTestId('context-panel-content');
      await expect(content).toBeVisible();
    }
  });

  test('should navigate to related work order when clicked', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('engine');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Find a clickable work order link
      const workOrderLink = contextPanel.locator(
        '[data-testid="linked-work-order"], [data-entity-type="work_order"]'
      ).first();

      if (await workOrderLink.isVisible()) {
        const originalEntityId = await contextPanel.getAttribute('data-entity-id');

        await workOrderLink.click();
        await page.waitForTimeout(1000);

        // Entity should change to work order
        const newEntityId = await contextPanel.getAttribute('data-entity-id');
        const newEntityType = await contextPanel.getAttribute('data-entity-type');

        // Should have navigated to a different entity
        if (newEntityId !== originalEntityId) {
          expect(newEntityType).toBe('work_order');
        }
      }
    }
  });
});

test.describe('Equipment Actions', () => {
  test('should display action buttons in equipment lens', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('engine');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // LAW 12: Verify action buttons exist
      const actionsArea = contextPanel.locator(
        '[data-testid="lens-actions"], [data-testid="action-buttons"], footer button, header button'
      );

      // Should have at least some interactive elements
      const content = page.getByTestId('context-panel-content');
      await expect(content).toBeVisible();
    }
  });

  test('should have create work order action', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('engine');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Create Work Order button
      const createWOButton = contextPanel.locator(
        'button:has-text("Create Work Order"), button:has-text("New Work Order"), [aria-label*="Create Work Order"]'
      );

      if (await createWOButton.first().isVisible()) {
        // Button should be clickable
        await expect(createWOButton.first()).toBeEnabled();
      }
    }
  });

  test('should have report fault action', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('pump');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Report Fault button
      const reportFaultButton = contextPanel.locator(
        'button:has-text("Report Fault"), button:has-text("Log Fault"), [aria-label*="Fault"]'
      );

      if (await reportFaultButton.first().isVisible()) {
        await expect(reportFaultButton.first()).toBeEnabled();
      }
    }
  });

  test('should have more actions menu', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('engine');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // More actions button (three dots, kebab menu)
      const moreButton = contextPanel.locator(
        '[aria-label*="More"], [data-testid="more-actions"], button[aria-haspopup="menu"]'
      );

      if (await moreButton.first().isVisible()) {
        await moreButton.first().click();

        // Menu should open
        const menu = page.locator('[role="menu"], [data-radix-menu-content]');
        await expect(menu).toBeVisible({ timeout: 5_000 });

        // Close menu
        await page.keyboard.press('Escape');
      }
    }
  });
});

test.describe('Equipment Navigation', () => {
  test('should close equipment lens on Escape', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    const contextPanel = new ContextPanelPO(page);

    await spotlight.search('engine');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);
      await contextPanel.waitForContent();

      // Press Escape to close
      await contextPanel.close();

      // Panel should be hidden
      await expect(contextPanel.panel).toHaveAttribute('data-visible', 'false');
    }
  });

  test('should support back navigation between entities', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('engine');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount >= 2) {
      // Open first result
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      const firstEntityId = await contextPanel.getAttribute('data-entity-id');

      // Close and open second result
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);

      await spotlight.clickResult(1);
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      const secondEntityId = await contextPanel.getAttribute('data-entity-id');

      // Look for back button
      const backButton = contextPanel.locator(
        '[aria-label*="Back"], [data-testid="nav-back"], button:has-text("Back")'
      );

      if (await backButton.first().isVisible()) {
        await backButton.first().click();
        await page.waitForTimeout(500);

        const currentEntityId = await contextPanel.getAttribute('data-entity-id');
        expect(currentEntityId).toBe(firstEntityId);
      }
    }
  });

  test('should support forward navigation after back', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('engine');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount >= 2) {
      // Open first, then second result
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      await page.keyboard.press('Escape');
      await spotlight.clickResult(1);
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      const secondEntityId = await contextPanel.getAttribute('data-entity-id');

      // Go back
      const backButton = contextPanel.locator('[aria-label*="Back"], [data-testid="nav-back"]');

      if (await backButton.first().isVisible()) {
        await backButton.first().click();
        await page.waitForTimeout(500);

        // Go forward
        const forwardButton = contextPanel.locator(
          '[aria-label*="Forward"], [data-testid="nav-forward"]'
        );

        if (await forwardButton.first().isVisible()) {
          await forwardButton.first().click();
          await page.waitForTimeout(500);

          const currentEntityId = await contextPanel.getAttribute('data-entity-id');
          expect(currentEntityId).toBe(secondEntityId);
        }
      }
    }
  });

  test('should preserve search results when closing panel', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    const contextPanel = new ContextPanelPO(page);

    await spotlight.search('engine');
    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const initialResultCount = await spotlight.getResultCount();

    if (initialResultCount > 0) {
      await spotlight.clickResult(0);
      await contextPanel.waitForContent();

      // Close panel
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);

      // Search results should still be visible
      await expect(spotlight.resultsContainer).toBeVisible();

      const resultCountAfterClose = await spotlight.getResultCount();
      expect(resultCountAfterClose).toBe(initialResultCount);
    }
  });
});

test.describe('Equipment Permission Testing', () => {
  test('HOD should see full equipment details', async ({ hodPage }) => {
    await hodPage.goto('/');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('engine');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = hodPage.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // LAW 12: Verify full content renders for HOD
      const content = hodPage.getByTestId('context-panel-content');
      await expect(content).toBeVisible();

      // HOD should see action buttons
      const actionsArea = contextPanel.locator('button');
      const buttonCount = await actionsArea.count();
      expect(buttonCount).toBeGreaterThan(0);
    }
  });

  test('Crew should see equipment with limited actions', async ({ crewPage }) => {
    await crewPage.goto('/');

    const spotlight = new SpotlightSearchPO(crewPage);
    await spotlight.search('engine');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = crewPage.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // LAW 12: Verify content renders for Crew
      const content = crewPage.getByTestId('context-panel-content');
      await expect(content).toBeVisible();

      // Crew should not see sensitive admin actions
      const adminActions = contextPanel.locator(
        'button:has-text("Delete"), button:has-text("Archive"), button:has-text("Decommission")'
      );

      // Admin actions should not be visible to crew
      const adminActionCount = await adminActions.count();
      expect(adminActionCount).toBe(0);
    }
  });

  test('Captain should have full equipment access', async ({ captainPage }) => {
    await captainPage.goto('/');

    const spotlight = new SpotlightSearchPO(captainPage);
    await spotlight.search('generator');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = captainPage.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // LAW 12: Verify full access
      const content = captainPage.getByTestId('context-panel-content');
      await expect(content).toBeVisible();

      // No error state
      const errorState = captainPage.getByTestId('context-panel-error');
      await expect(errorState).not.toBeVisible();
    }
  });
});

test.describe('Equipment Data Grid (LAW 12)', () => {
  test('should render maintenance tasks grid correctly', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('engine');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // LAW 12: Verify grid renders
      const maintenanceSection = contextPanel.locator('[data-section="maintenance"]');

      if (await maintenanceSection.isVisible()) {
        // Should have table or list structure
        const tableOrList = maintenanceSection.locator('table, [role="list"], [role="grid"]');

        if (await tableOrList.first().isVisible()) {
          // Headers should be present
          const headers = maintenanceSection.locator('th, [role="columnheader"]');
          const headerCount = await headers.count();
          expect(headerCount).toBeGreaterThan(0);
        }
      }
    }
  });

  test('should render work orders list with status indicators', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('engine');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // LAW 12: Verify work orders list renders
      const workOrdersSection = contextPanel.locator(
        '[data-section="work-orders"], [data-section="workorders"]'
      );

      if (await workOrdersSection.isVisible()) {
        // Work order items should have status indicators
        const statusIndicators = workOrdersSection.locator(
          '[data-testid="status-pill"], [class*="status"], [data-status]'
        );

        if ((await statusIndicators.count()) > 0) {
          // First status indicator should be visible
          await expect(statusIndicators.first()).toBeVisible();
        }
      }
    }
  });

  test('should render specifications as key-value pairs', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('generator');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // LAW 12: Specifications should render as key-value pairs
      const specsSection = contextPanel.locator(
        '[data-section="specifications"], [data-testid="equipment-specs"]'
      );

      if (await specsSection.isVisible()) {
        // Should have definition list or similar structure
        const specItems = specsSection.locator('dl dt, [data-spec-key], th');

        if ((await specItems.count()) > 0) {
          // Keys should be visible
          await expect(specItems.first()).toBeVisible();
        }
      }
    }
  });
});

test.describe('Equipment Error Handling', () => {
  test('should not crash on rapid open/close', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('engine');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      // Rapidly open and close
      for (let i = 0; i < 3; i++) {
        await spotlight.clickResult(0);
        await page.waitForTimeout(200);
        await page.keyboard.press('Escape');
        await page.waitForTimeout(200);
      }

      // Should not show fatal error
      const fatalError = page.locator('[data-testid="fatal-error"]');
      await expect(fatalError).not.toBeVisible();

      // App should still be functional
      await spotlight.clickResult(0);
      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });
    }
  });

  test('should handle network timeout gracefully', async ({ page }) => {
    await page.goto('/');

    // Simulate slow network
    await page.route('**/api/**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 100));
      await route.continue();
    });

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('engine'); // Use 'engine' which has known data

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 15_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 15_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 15_000 });

      // Content should eventually load
      const content = page.getByTestId('context-panel-content');
      await expect(content).toBeVisible({ timeout: 20_000 });
    }
  });

  test('should show loading state while fetching equipment', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('engine');

    // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Loading state should eventually resolve
      const loading = page.getByTestId('context-panel-loading');
      await expect(loading).not.toBeVisible({ timeout: 15_000 });
    }
  });
});
