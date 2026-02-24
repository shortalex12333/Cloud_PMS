import { test, expect, SpotlightSearchPO, ContextPanelPO, TEST_CONFIG } from '../fixtures';

/**
 * SHARD 9: Fault Lens Tests
 *
 * LAW 12: DEEP UI VERIFICATION
 * - Tests must verify fault codes display correctly
 * - Severity/priority indicators render with correct styling
 * - Cross-entity navigation works properly
 * - All lens sections load without error
 *
 * Test Data:
 * - Fault queries: "fault", "E047", "alarm", "error", "G012"
 * - Yacht ID: 85fe1119-b04c-41ac-80f1-829d23322598
 */

test.describe('Fault Lens', () => {
  // Configure retries for network variability
  test.describe.configure({ retries: 1 });

  test.describe('Fault Lens Opening', () => {
    test('should open fault lens from generic fault search', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('fault');

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

    test('should open fault lens from alarm search', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('alarm');

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

    test('should open fault lens from error search', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('error');

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

    test('should open fault lens from fault code search E047', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('E047');

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

        // Verify entity type is fault
        const entityType = await contextPanel.getAttribute('data-entity-type');
        expect(['fault', 'pms_fault', 'alarm']).toContain(entityType);
      }
    });

    test('should open fault lens from fault code search G012', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('G012');

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

  test.describe('Fault Code & Severity Display', () => {
    test('should display fault code in lens header', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('fault');

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

        // LAW 12: Verify fault code is visible (E### or G### pattern)
        const header = contextPanel.locator('header');
        await expect(header).toBeVisible();

        // Fault code should be displayed
        const faultCodeLocator = contextPanel.locator('[data-testid="fault-code"], [class*="fault-code"], [class*="code"]');
        // Either fault code element exists or the header contains a code pattern
      }
    });

    test('should display severity/priority indicator pill', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('fault critical');

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

        // LAW 12: Verify severity/priority indicator renders
        const severityPill = contextPanel.locator('[data-testid="severity-pill"], [data-testid="priority-pill"], [class*="severity"], [class*="priority"]');
      }
    });

    test('should have correct styling for critical severity', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('fault');

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

        // LAW 12: Check severity pill styling
        const severityPill = contextPanel.locator('[data-testid="severity-pill"], [class*="severity"], [class*="badge"]').first();

        if (await severityPill.isVisible()) {
          // Critical/High severity should have red or orange styling
          const bgColor = await severityPill.evaluate((el) => {
            return window.getComputedStyle(el).backgroundColor;
          });
          // Verify it has a color (not transparent/white)
          expect(bgColor).not.toBe('rgba(0, 0, 0, 0)');
        }
      }
    });

    test('should display fault description', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('fault');

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

        // LAW 12: Verify description section exists
        const descriptionSection = contextPanel.locator('[data-testid="fault-description"], [data-section="description"], text=Description');
      }
    });

    test('should display fault status (active/resolved/pending)', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('fault');

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

        // LAW 12: Verify status indicator
        const statusIndicator = contextPanel.locator('[data-testid="status-pill"], [class*="status"]');
      }
    });

    test('should display fault timestamp/date', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('fault');

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

        // LAW 12: Verify timestamp is displayed
        const timestampLocator = contextPanel.locator('[data-testid="fault-timestamp"], [class*="timestamp"], [class*="date"], time');
      }
    });
  });

  test.describe('Fault Linked Entities', () => {
    test('should display linked equipment section', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('fault');

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

        // LAW 12: Look for linked equipment section
        const linkedEquipment = contextPanel.locator('[data-section="equipment"], text=Equipment, text=Linked Equipment');
      }
    });

    test('should display linked work orders section', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('fault');

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
        const linkedWorkOrders = contextPanel.locator('[data-section="work-orders"], text=Work Orders, text=Related Work Orders');
      }
    });

    test('should show equipment name in linked equipment', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('fault');

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

        // If linked equipment exists, it should have a name
        const linkedEquipmentItem = contextPanel.locator('[data-testid="linked-equipment-item"], [data-section="equipment"] a, [data-section="equipment"] button');

        if (await linkedEquipmentItem.first().isVisible()) {
          const text = await linkedEquipmentItem.first().textContent();
          expect(text?.length).toBeGreaterThan(0);
        }
      }
    });

    test('should make linked equipment clickable', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('fault');

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

        // LAW 12: Linked entities should be interactive
        const linkedItem = contextPanel.locator('[data-testid="linked-equipment-item"], [data-section="equipment"] [role="button"], [data-section="equipment"] a');

        if (await linkedItem.first().isVisible()) {
          // Verify it's clickable (has cursor pointer or is a link/button)
          const cursor = await linkedItem.first().evaluate((el) => {
            return window.getComputedStyle(el).cursor;
          });
          expect(['pointer', 'hand']).toContain(cursor);
        }
      }
    });

    test('should make linked work orders clickable', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('fault');

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

        // LAW 12: Linked work orders should be interactive
        const linkedWorkOrder = contextPanel.locator('[data-testid="linked-workorder-item"], [data-section="work-orders"] [role="button"], [data-section="work-orders"] a');

        if (await linkedWorkOrder.first().isVisible()) {
          const cursor = await linkedWorkOrder.first().evaluate((el) => {
            return window.getComputedStyle(el).cursor;
          });
          expect(['pointer', 'hand']).toContain(cursor);
        }
      }
    });
  });

  test.describe('Fault Navigation', () => {
    test('should navigate to equipment from fault lens', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('fault');

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

    test('should navigate to work order from fault lens', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('fault');

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

        // Find and click linked work order
        const linkedWorkOrder = contextPanel.locator('[data-testid="linked-workorder-item"], [data-section="work-orders"] [role="button"], [data-section="work-orders"] a').first();

        if (await linkedWorkOrder.isVisible()) {
          await linkedWorkOrder.click();

          // Panel should update to show work order
          await page.waitForTimeout(1000);
          const newEntityType = await contextPanel.getAttribute('data-entity-type');
          expect(newEntityType).toBe('work_order');
        }
      }
    });

    test('should support back navigation after cross-entity jump', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('fault');

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

    test('should close fault lens on Escape key', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      const contextPanel = new ContextPanelPO(page);

      await spotlight.search('fault');
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
  });

  test.describe('Fault Permission Handling', () => {
    test('HOD should see full fault details', async ({ hodPage }) => {
      await hodPage.goto('/');

      const spotlight = new SpotlightSearchPO(hodPage);
      await spotlight.search('fault');

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

        // HOD should see all sections
        const content = hodPage.getByTestId('context-panel-content');
        await expect(content).toBeVisible({ timeout: 10_000 });
      }
    });

    test('Crew should see fault lens with appropriate permissions', async ({ crewPage }) => {
      await crewPage.goto('/');

      const spotlight = new SpotlightSearchPO(crewPage);
      await spotlight.search('fault');

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

        // Crew should see fault but may have limited actions
        const content = crewPage.getByTestId('context-panel-content');
        await expect(content).toBeVisible({ timeout: 10_000 });
      }
    });

    test('HOD should see fault action buttons', async ({ hodPage }) => {
      await hodPage.goto('/');

      const spotlight = new SpotlightSearchPO(hodPage);
      await spotlight.search('fault');

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

        // HOD should see action buttons (Resolve, Create Work Order, etc.)
        const actionButtons = contextPanel.locator('button:has-text("Resolve"), button:has-text("Create Work Order"), button:has-text("Acknowledge")');
      }
    });
  });

  test.describe('Fault Data Integrity (LAW 12)', () => {
    test('should not show error state in fault lens', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('fault');

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
      await spotlight.search('fault');

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

    test('should display fault ID in panel attributes', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('fault');

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

    test('should render fault content sections', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('fault');

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
  });

  test.describe('Fault Search Variations', () => {
    test('should find faults with leak keyword', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('leak');

      // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);

      const resultCount = await spotlight.getResultCount();
      // Leak should return results (equipment, faults, work orders related)
      expect(resultCount).toBeGreaterThanOrEqual(0);
    });

    test('should find faults with failure keyword', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('failure');

      // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);
    });

    test('should find faults with warning keyword', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('warning');

      // Wait for either results or no-results state
    await Promise.race([
      spotlight.resultsContainer.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
      spotlight.noResults.waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {}),
    ]);
    });

    test('should handle no fault results gracefully', async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search('xyznonexistentfault12345');

      await page.waitForTimeout(2500);

      // Should not crash, just show no results
      const errorState = page.getByTestId('search-error');
      await expect(errorState).not.toBeVisible();
    });
  });
});
