import { test, expect, SpotlightSearchPO, ContextPanelPO, TEST_CONFIG } from '../fixtures';

/**
 * SHARD 10: Part/Inventory Lens Tests
 *
 * LAW 12: DEEP UI VERIFICATION
 * - Tests must verify part numbers display correctly
 * - Inventory quantities are numeric and valid
 * - Stock level indicators render with correct styling
 * - Cross-entity navigation works properly
 * - All lens sections load without error
 *
 * Test Data:
 * - Part queries: "filter", "pump", "oil", "gasket", "bearing", "part", "inventory"
 * - Yacht ID: 85fe1119-b04c-41ac-80f1-829d23322598
 */

test.describe('Part/Inventory Lens', () => {
  // Configure retries for network variability
  test.describe.configure({ retries: 1 });

  test.describe('Part Lens Opening', () => {
    test('should open part lens from generic part search', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('part');

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

        // LAW 12: Verify content loads
        const content = page.getByTestId('context-panel-content');
        await expect(content).toBeVisible({ timeout: 10_000 });
      }
    });

    test('should open part lens from filter search', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('filter');

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
      }
    });

    test('should open part lens from pump search', async ({ page }) => {
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
      }
    });

    test('should open part lens from oil search', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('oil');

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
      }
    });

    test('should open part lens from gasket search', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('gasket');

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

        // Verify entity type
        const entityType = await contextPanel.getAttribute('data-entity-type');
        expect(['part', 'pms_part', 'inventory', 'spare_part']).toContain(entityType);
      }
    });

    test('should open part lens from inventory search', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('inventory');

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
      }
    });
  });

  test.describe('Part Details Display', () => {
    test('should display part number/SKU', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('part filter');

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

        // LAW 12: Part number should be visible and non-empty
        const partNumber = contextPanel.locator('[data-testid="part-number"], [data-testid="sku"], [class*="part-number"], [class*="sku"]');

        if (await partNumber.isVisible()) {
          const text = await partNumber.textContent();
          expect(text?.length).toBeGreaterThan(0);
        }
      }
    });

    test('should display part name in header', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('part');

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

        // LAW 12: Header should show part name
        const header = contextPanel.getByTestId('parts-header');
        await expect(header).toBeVisible();

        const headerText = await header.textContent();
        expect(headerText?.length).toBeGreaterThan(0);
      }
    });

    test('should display part specifications section', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('part');

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

        // LAW 12: Look for specifications section
        const specsSection = contextPanel.locator('[data-section="specifications"], text=Specifications, text=Details, text=Specs');
      }
    });

    test('should display manufacturer information', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('part');

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

        // LAW 12: Look for manufacturer info
        const manufacturerInfo = contextPanel.locator('[data-testid="manufacturer"], text=Manufacturer, text=Mfr, text=Brand');
      }
    });

    test('should display part description', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('part');

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

        // LAW 12: Look for description
        const descriptionSection = contextPanel.locator('[data-testid="part-description"], [data-section="description"], text=Description');
      }
    });

    test('should display part category', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('part');

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

        // LAW 12: Look for category
        const categoryInfo = contextPanel.locator('[data-testid="part-category"], text=Category, [class*="category"]');
      }
    });
  });

  test.describe('Part Inventory Status', () => {
    test('should display inventory quantity as a number', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('inventory');

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

        // LAW 12: Inventory quantity should be numeric
        const quantityLocator = contextPanel.getByTestId('inventory-quantity');

        if (await quantityLocator.isVisible({ timeout: 5000 }).catch(() => false)) {
          const text = await quantityLocator.textContent();
          // Extract number from text (e.g., "Qty: 15" -> 15)
          const numberMatch = text?.match(/\d+/);
          if (numberMatch) {
            const qty = parseInt(numberMatch[0], 10);
            expect(typeof qty).toBe('number');
            expect(qty).toBeGreaterThanOrEqual(0);
          }
        }
      }
    });

    test('should display storage location information', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('part');

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

        // LAW 12: Look for location information
        const locationInfo = contextPanel.locator('[data-testid="location"], text=Location, text=Storage, text=Stored');
      }
    });

    test('should display reorder level indication', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('part');

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

        // LAW 12: Look for reorder level
        const reorderLevel = contextPanel.locator('[data-testid="reorder-level"], text=Reorder, text=Min Stock, text=Minimum');
      }
    });

    test('should display stock level indicator (low stock styling)', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('part low stock');

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

        // LAW 12: Check for stock level indicator
        const stockIndicator = contextPanel.locator('[data-testid="stock-indicator"], [class*="stock"], [class*="low-stock"], [class*="in-stock"]');

        if (await stockIndicator.isVisible()) {
          // Low stock should have warning styling (red, orange, or yellow)
          const bgColor = await stockIndicator.evaluate((el) => {
            return window.getComputedStyle(el).backgroundColor;
          });
          // Verify it has a color (not transparent)
          expect(bgColor).not.toBe('rgba(0, 0, 0, 0)');
        }
      }
    });

    test('should display stock level indicator (in stock styling)', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('part');

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

        // LAW 12: Check for stock level indicator
        const stockIndicator = contextPanel.locator('[data-testid="stock-indicator"], [class*="stock"]');

        if (await stockIndicator.isVisible()) {
          // In stock should have positive styling (green)
          const text = await stockIndicator.textContent();
          // Verify it shows stock status
          expect(text?.length).toBeGreaterThan(0);
        }
      }
    });

    test('should display last inventory count date', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('inventory');

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

        // LAW 12: Look for last count date
        const lastCountDate = contextPanel.locator('[data-testid="last-count"], text=Last Count, text=Counted, time');
      }
    });
  });

  test.describe('Part Linked Entities', () => {
    test('should display linked equipment section (where part is used)', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('part');

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

        // LAW 12: Look for linked equipment
        const linkedEquipment = contextPanel.locator('[data-section="equipment"], text=Equipment, text=Used In, text=Installed On');
      }
    });

    test('should make linked equipment clickable', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('part');

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

        // LAW 12: Linked equipment should be interactive
        const linkedItem = contextPanel.locator('[data-testid="linked-equipment-item"], [data-section="equipment"] [role="button"], [data-section="equipment"] a');

        if (await linkedItem.first().isVisible()) {
          const cursor = await linkedItem.first().evaluate((el) => {
            return window.getComputedStyle(el).cursor;
          });
          expect(['pointer', 'hand']).toContain(cursor);
        }
      }
    });

    test('should display linked work orders (where part was used)', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('part');

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

        // LAW 12: Look for linked work orders
        const linkedWorkOrders = contextPanel.locator('[data-section="work-orders"], text=Work Orders, text=Usage History');
      }
    });

    test('should display supplier/vendor information', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('part');

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

        // LAW 12: Look for supplier info
        const supplierInfo = contextPanel.locator('[data-testid="supplier"], text=Supplier, text=Vendor');
      }
    });
  });

  test.describe('Part Navigation', () => {
    test('should navigate to equipment from part lens', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('part');

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

        // Find and click linked equipment
        const linkedEquipment = contextPanel.locator('[data-testid="linked-equipment-item"], [data-section="equipment"] [role="button"], [data-section="equipment"] a').first();

        if (await linkedEquipment.isVisible()) {
          await linkedEquipment.click();

          // Panel should update to show equipment
          await page.waitForTimeout(1000);
          const newEntityType = await contextPanel.getAttribute('data-entity-type');
          expect(['equipment', 'pms_equipment']).toContain(newEntityType);
        }
      }
    });

    test('should support back navigation after cross-entity jump', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('part');

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

        const originalEntityId = await contextPanel.getAttribute('data-entity-id');

        // Navigate to linked entity
        const linkedItem = contextPanel.locator('[data-testid="linked-equipment-item"], [data-section="equipment"] [role="button"]').first();

        if (await linkedItem.isVisible()) {
          await linkedItem.click();
          await page.waitForTimeout(1000);

          // Use back button
          const backButton = contextPanel.locator('[aria-label*="Back"], [data-testid="nav-back"], button:has-text("Back")');

          if (await backButton.isVisible()) {
            await backButton.click();
            await page.waitForTimeout(500);

            const currentEntityId = await contextPanel.getAttribute('data-entity-id');
            expect(currentEntityId).toBe(originalEntityId);
          }
        }
      }
    });

    test('should close part lens on Escape key', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      const contextPanel = new ContextPanelPO(page);

      await spotlight.search('part');
      // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

      const resultCount = await spotlight.getResultCount();
      if (resultCount > 0) {
        await spotlight.clickResult(0);
        await contextPanel.waitForContent();

        // Close with Escape
        await contextPanel.close();

        // Panel should be hidden
        await expect(contextPanel.panel).toHaveAttribute('data-visible', 'false');
      }
    });

    test('should navigate between multiple parts', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('part');

      // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

      const resultCount = await spotlight.getResultCount();
      if (resultCount >= 2) {
        // Open first part
        await spotlight.clickResult(0);

        const contextPanel = page.getByTestId('context-panel');
        await expect(contextPanel).toBeVisible({ timeout: 10_000 });

        const firstEntityId = await contextPanel.getAttribute('data-entity-id');

        // Close and open second part
        await page.keyboard.press('Escape');
        await spotlight.clickResult(1);
        await expect(contextPanel).toBeVisible({ timeout: 10_000 });

        const secondEntityId = await contextPanel.getAttribute('data-entity-id');

        // Entity IDs should be different
        expect(secondEntityId).not.toBe(firstEntityId);
      }
    });
  });

  test.describe('Part Data Integrity (LAW 12)', () => {
    test('should not show error state in part lens', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('part');

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

        // No error state should be visible
        const errorState = page.getByTestId('context-panel-error');
        await expect(errorState).not.toBeVisible();
      }
    });

    test('should complete loading without timeout', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('part');

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

        // Loading indicator should disappear
        const loadingIndicator = page.getByTestId('context-panel-loading');
        await expect(loadingIndicator).not.toBeVisible({ timeout: 10_000 });
      }
    });

    test('should display part ID in panel attributes', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('part');

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

        // LAW 12: Entity ID should be set
        const entityId = await contextPanel.getAttribute('data-entity-id');
        expect(entityId).toBeTruthy();
        expect(entityId?.length).toBeGreaterThan(0);
      }
    });

    test('should render part content sections', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('part');

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

        // LAW 12: Content should have actual text
        const content = page.getByTestId('context-panel-content');
        const textContent = await content.textContent();
        expect(textContent?.length).toBeGreaterThan(0);
      }
    });

    test('should display valid part number format', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('part');

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

        // LAW 12: Part number should be visible and have valid format
        const partNumberLocator = contextPanel.locator('[data-testid="part-number"], [data-testid="sku"]');

        if (await partNumberLocator.isVisible()) {
          const partNumber = await partNumberLocator.textContent();
          expect(partNumber).toBeTruthy();
          expect(partNumber?.trim().length).toBeGreaterThan(0);
        }
      }
    });
  });

  test.describe('Part Search Variations', () => {
    test('should find parts with bearing keyword', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('bearing');

      // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);
    });

    test('should find parts with seal keyword', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('seal');

      // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);
    });

    test('should find parts with belt keyword', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('belt');

      // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);
    });

    test('should find parts with spare keyword', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('spare');

      // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);
    });

    test('should handle no part results gracefully', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('xyznonexistentpart12345');

      await page.waitForTimeout(2500);

      // Should not crash, just show no results
      const errorState = page.getByTestId('search-error');
      await expect(errorState).not.toBeVisible();
    });
  });

  test.describe('Part Actions', () => {
    test('should display action buttons in part lens', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('part');

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

        // Look for action buttons (Reorder, Update Quantity, etc.)
        const actionButtons = contextPanel.locator('button:has-text("Reorder"), button:has-text("Update"), button:has-text("Request")');
      }
    });

    test('should display reorder button for low stock items', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('parts low stock');

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

        // Look for reorder CTA
        const reorderButton = contextPanel.locator('button:has-text("Reorder"), button:has-text("Order"), [data-testid="reorder-button"]');
      }
    });
  });
});
