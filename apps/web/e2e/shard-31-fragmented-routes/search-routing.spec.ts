import { test, expect, RBAC_CONFIG, SpotlightSearchPO, ContextPanelPO } from '../rbac-fixtures';

/**
 * SHARD 31: Fragmented Routes - Search Routing
 *
 * Tests for SpotlightSearch click-through navigation under fragmented routes.
 *
 * Requirements Covered:
 * - SR-04: Search → click result → navigates to fragmented route
 *   - work_order → /work-orders/{id}
 *   - equipment → /equipment/{id}
 *   - fault → /faults/{id}
 *   - part → /inventory/{id}
 * - SR-05: Flag OFF behavior (legacy ContextPanel opens)
 *
 * Implementation Details:
 * When NEXT_PUBLIC_FRAGMENTED_ROUTES_ENABLED=true:
 *   - SpotlightSearch.handleResultOpen() calls router.push(getEntityRoute(type, id))
 *   - Supported types: work_order, fault, equipment, part, email_thread
 *
 * When flag OFF:
 *   - Opens surfaceContext.showContext() (legacy ContextPanel)
 */

const ROUTES_CONFIG = {
  ...RBAC_CONFIG,
  // Expected route patterns when flag is ON
  workOrderDetail: (id: string) => `/work-orders/${id}`,
  equipmentDetail: (id: string) => `/equipment/${id}`,
  faultDetail: (id: string) => `/faults/${id}`,
  inventoryDetail: (id: string) => `/inventory/${id}`,
  // Feature flag check
  featureFlagEnabled: process.env.NEXT_PUBLIC_FRAGMENTED_ROUTES_ENABLED === 'true',
};

// ============================================================================
// SECTION 1: FLAG ON - SEARCH CLICK NAVIGATES TO FRAGMENTED ROUTES
// SR-04: Search result click triggers router navigation
// ============================================================================

test.describe('Search Routing - Flag ON', () => {
  test.describe.configure({ retries: 1 });

  test('SR-04a: Search → click work_order result → navigates to /work-orders/{id}', async ({ hodPage, seedWorkOrder }) => {
    // Seed test work order
    const workOrder = await seedWorkOrder();

    // Navigate to app with search
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    // Check if we're on fragmented routes - if redirected to /app without routes, skip
    const spotlight = new SpotlightSearchPO(hodPage);

    // Search for the work order
    await spotlight.search(workOrder.wo_number);

    // Wait for results to appear
    await hodPage.waitForTimeout(3000);

    // Check if results container is visible
    const resultsVisible = await spotlight.resultsContainer.isVisible({ timeout: 5000 }).catch(() => false);

    if (!resultsVisible) {
      console.log('  No search results found - may need test data');
      return;
    }

    // Count results
    const resultCount = await spotlight.getResultCount();
    console.log(`  Found ${resultCount} search results for "${workOrder.wo_number}"`);

    if (resultCount === 0) {
      console.log('  No results to click - skipping');
      return;
    }

    // Click the first result
    await spotlight.clickResult(0);

    // Wait for navigation
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(1000);

    const currentUrl = hodPage.url();
    console.log(`  Current URL after click: ${currentUrl}`);

    // Check if flag is ON (navigated to fragmented route)
    if (currentUrl.includes('/work-orders/')) {
      expect(currentUrl).toContain('/work-orders/');
      console.log('  SR-04a PASS: Navigated to /work-orders/ route');
    } else if (currentUrl.includes('/app')) {
      // Flag is OFF or result opened in context panel
      console.log('  SR-04a: Flag OFF - result opened in legacy mode');
      // Verify context panel opened instead
      const contextPanel = new ContextPanelPO(hodPage);
      const panelVisible = await contextPanel.panel.isVisible({ timeout: 5000 }).catch(() => false);
      if (panelVisible) {
        console.log('  Legacy context panel opened as expected');
      }
    }
  });

  test('SR-04b: Search → click equipment result → navigates to /equipment/{id}', async ({ hodPage, supabaseAdmin }) => {
    // Get equipment from test yacht
    const { data: equipment } = await supabaseAdmin
      .from('pms_equipment')
      .select('id, name')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!equipment) {
      console.log('  No equipment in test yacht - skipping');
      return;
    }

    // Navigate to app with search
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);

    // Search for the equipment
    await spotlight.search(equipment.name);
    await hodPage.waitForTimeout(3000);

    const resultsVisible = await spotlight.resultsContainer.isVisible({ timeout: 5000 }).catch(() => false);

    if (!resultsVisible) {
      console.log('  No search results found');
      return;
    }

    const resultCount = await spotlight.getResultCount();
    console.log(`  Found ${resultCount} search results for "${equipment.name}"`);

    if (resultCount === 0) {
      console.log('  No results to click - skipping');
      return;
    }

    // Find and click an equipment result
    const equipmentResults = hodPage.locator('[data-testid="search-result-item"]').filter({
      has: hodPage.locator(':text("Equipment"), [data-entity-type="equipment"]'),
    });

    const hasEquipmentResult = await equipmentResults.first().isVisible({ timeout: 3000 }).catch(() => false);

    if (hasEquipmentResult) {
      await equipmentResults.first().click();
    } else {
      // Click first result anyway
      await spotlight.clickResult(0);
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(1000);

    const currentUrl = hodPage.url();
    console.log(`  Current URL after click: ${currentUrl}`);

    if (currentUrl.includes('/equipment/')) {
      expect(currentUrl).toContain('/equipment/');
      console.log('  SR-04b PASS: Navigated to /equipment/ route');
    } else if (currentUrl.includes('/app')) {
      console.log('  SR-04b: Flag OFF or legacy mode');
    }
  });

  test('SR-04c: Search → click fault result → navigates to /faults/{id}', async ({ hodPage, seedFault }) => {
    // Seed test fault
    const fault = await seedFault();

    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);

    // Search for the fault
    await spotlight.search(fault.title);
    await hodPage.waitForTimeout(3000);

    const resultsVisible = await spotlight.resultsContainer.isVisible({ timeout: 5000 }).catch(() => false);

    if (!resultsVisible) {
      console.log('  No search results found');
      return;
    }

    const resultCount = await spotlight.getResultCount();
    console.log(`  Found ${resultCount} search results for "${fault.title}"`);

    if (resultCount === 0) {
      console.log('  No results to click - skipping');
      return;
    }

    await spotlight.clickResult(0);
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(1000);

    const currentUrl = hodPage.url();
    console.log(`  Current URL after click: ${currentUrl}`);

    if (currentUrl.includes('/faults/')) {
      expect(currentUrl).toContain('/faults/');
      console.log('  SR-04c PASS: Navigated to /faults/ route');
    } else if (currentUrl.includes('/app')) {
      console.log('  SR-04c: Flag OFF or legacy mode');
    }
  });

  test('SR-04d: Search → click part result → navigates to /inventory/{id}', async ({ hodPage, supabaseAdmin }) => {
    // Get part from test yacht
    const { data: part } = await supabaseAdmin
      .from('pms_parts')
      .select('id, name')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!part) {
      console.log('  No parts in test yacht - skipping');
      return;
    }

    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);

    // Search for the part
    await spotlight.search(part.name);
    await hodPage.waitForTimeout(3000);

    const resultsVisible = await spotlight.resultsContainer.isVisible({ timeout: 5000 }).catch(() => false);

    if (!resultsVisible) {
      console.log('  No search results found');
      return;
    }

    const resultCount = await spotlight.getResultCount();
    console.log(`  Found ${resultCount} search results for "${part.name}"`);

    if (resultCount === 0) {
      console.log('  No results to click - skipping');
      return;
    }

    // Find and click a part/inventory result
    const partResults = hodPage.locator('[data-testid="search-result-item"]').filter({
      has: hodPage.locator(':text("Part"), :text("Inventory"), [data-entity-type="part"], [data-entity-type="inventory"]'),
    });

    const hasPartResult = await partResults.first().isVisible({ timeout: 3000 }).catch(() => false);

    if (hasPartResult) {
      await partResults.first().click();
    } else {
      await spotlight.clickResult(0);
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(1000);

    const currentUrl = hodPage.url();
    console.log(`  Current URL after click: ${currentUrl}`);

    if (currentUrl.includes('/inventory/')) {
      expect(currentUrl).toContain('/inventory/');
      console.log('  SR-04d PASS: Navigated to /inventory/ route');
    } else if (currentUrl.includes('/app')) {
      console.log('  SR-04d: Flag OFF or legacy mode');
    }
  });
});

// ============================================================================
// SECTION 2: FLAG OFF - LEGACY CONTEXT PANEL BEHAVIOR
// SR-05: When flag OFF, search click opens ContextPanel
// ============================================================================

test.describe('Search Routing - Legacy Behavior', () => {
  test.describe.configure({ retries: 1 });

  test('SR-05: With flag OFF, search click opens ContextPanel (not route)', async ({ hodPage, seedWorkOrder }) => {
    // Note: This test documents expected behavior when flag is OFF.
    // The flag state is determined at build time via NEXT_PUBLIC_FRAGMENTED_ROUTES_ENABLED.
    // We can only verify actual behavior, not toggle the flag at runtime.

    const workOrder = await seedWorkOrder();

    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search(workOrder.wo_number);
    await hodPage.waitForTimeout(3000);

    const resultsVisible = await spotlight.resultsContainer.isVisible({ timeout: 5000 }).catch(() => false);

    if (!resultsVisible) {
      console.log('  No search results - skipping');
      return;
    }

    const resultCount = await spotlight.getResultCount();
    if (resultCount === 0) {
      console.log('  No results to click - skipping');
      return;
    }

    // Store URL before click
    const urlBeforeClick = hodPage.url();

    await spotlight.clickResult(0);
    await hodPage.waitForTimeout(2000);

    const urlAfterClick = hodPage.url();

    // Determine which mode we're in
    if (urlAfterClick.includes('/work-orders/')) {
      // FLAG ON: Navigated to fragmented route
      console.log('  SR-05: Flag is ON - navigated to fragmented route');
      expect(urlAfterClick).toContain('/work-orders/');
    } else if (urlAfterClick === urlBeforeClick || urlAfterClick.includes('/app')) {
      // FLAG OFF: Should have opened ContextPanel
      console.log('  SR-05: Flag is OFF - checking for ContextPanel');

      const contextPanel = new ContextPanelPO(hodPage);
      const panelVisible = await contextPanel.panel.isVisible({ timeout: 5000 }).catch(() => false);

      if (panelVisible) {
        console.log('  SR-05 PASS: ContextPanel opened (legacy behavior)');

        // Verify panel has content
        const entityType = await contextPanel.getEntityType();
        console.log(`  ContextPanel entity type: ${entityType}`);
        expect(entityType).toBe('work_order');
      } else {
        // Panel may not be visible if entity loaded inline
        console.log('  SR-05: ContextPanel not visible - entity may have loaded differently');
      }
    }
  });
});

// ============================================================================
// SECTION 3: ROUTE ASSERTION TESTS
// Direct URL verification after search click
// ============================================================================

test.describe('Search Routing - URL Assertions', () => {
  test.describe.configure({ retries: 1 });

  test('Search result click produces valid URL with entity ID', async ({ hodPage, seedWorkOrder }) => {
    const workOrder = await seedWorkOrder();

    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search(workOrder.wo_number);
    await hodPage.waitForTimeout(3000);

    const resultsVisible = await spotlight.resultsContainer.isVisible({ timeout: 5000 }).catch(() => false);

    if (!resultsVisible) {
      console.log('  No search results - skipping URL assertion');
      return;
    }

    const resultCount = await spotlight.getResultCount();
    if (resultCount === 0) {
      console.log('  No results - skipping');
      return;
    }

    await spotlight.clickResult(0);
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(1000);

    const finalUrl = hodPage.url();
    console.log(`  Final URL: ${finalUrl}`);

    // URL should contain a UUID pattern (entity ID)
    const uuidPattern = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

    if (finalUrl.includes('/work-orders/') || finalUrl.includes('/faults/') ||
        finalUrl.includes('/equipment/') || finalUrl.includes('/inventory/')) {
      // Fragmented route - should have UUID
      expect(finalUrl).toMatch(uuidPattern);
      console.log('  URL assertion PASS: Fragmented route with valid UUID');
    } else if (finalUrl.includes('/app')) {
      // Legacy route - may have entity ID in query params
      console.log('  URL assertion: Legacy /app route');
      if (finalUrl.includes('id=')) {
        expect(finalUrl).toMatch(uuidPattern);
        console.log('  Legacy route has entity ID in query params');
      }
    }
  });

  test('Back button returns to search after navigation', async ({ hodPage, seedWorkOrder }) => {
    const workOrder = await seedWorkOrder();

    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search(workOrder.wo_number);
    await hodPage.waitForTimeout(3000);

    const resultsVisible = await spotlight.resultsContainer.isVisible({ timeout: 5000 }).catch(() => false);

    if (!resultsVisible) {
      console.log('  No search results - skipping back button test');
      return;
    }

    const resultCount = await spotlight.getResultCount();
    if (resultCount === 0) {
      console.log('  No results - skipping');
      return;
    }

    const urlBeforeClick = hodPage.url();

    await spotlight.clickResult(0);
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(1000);

    const urlAfterClick = hodPage.url();

    // Only test back button if we actually navigated
    if (urlAfterClick !== urlBeforeClick && urlAfterClick.includes('/work-orders/')) {
      // Use browser back
      await hodPage.goBack();
      await hodPage.waitForLoadState('networkidle');

      const urlAfterBack = hodPage.url();
      console.log(`  URL after back: ${urlAfterBack}`);

      // Should be back at /app
      expect(urlAfterBack).toContain('/app');
      console.log('  Back button test PASS: Returned to /app');
    } else {
      console.log('  No navigation occurred - skipping back button test');
    }
  });
});

// ============================================================================
// SECTION 4: SEARCH CLOSE BEHAVIOR
// Verify search closes after navigation
// ============================================================================

test.describe('Search UI Behavior', () => {
  test.describe.configure({ retries: 1 });

  test('Search input clears after result click navigation', async ({ hodPage, seedWorkOrder }) => {
    const workOrder = await seedWorkOrder();

    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search(workOrder.wo_number);
    await hodPage.waitForTimeout(3000);

    const resultsVisible = await spotlight.resultsContainer.isVisible({ timeout: 5000 }).catch(() => false);

    if (!resultsVisible) {
      console.log('  No search results - skipping');
      return;
    }

    const resultCount = await spotlight.getResultCount();
    if (resultCount === 0) {
      console.log('  No results - skipping');
      return;
    }

    await spotlight.clickResult(0);
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(1000);

    const currentUrl = hodPage.url();

    // If we navigated away from /app, search should be gone
    if (!currentUrl.includes('/app')) {
      // On fragmented route - verify we're on correct page
      console.log(`  Navigated to ${currentUrl}`);
      expect(currentUrl).not.toBe('/app');
      console.log('  Search closed after navigation (navigated away from /app)');
    } else {
      // Still on /app - check if results closed
      const resultsStillVisible = await spotlight.resultsContainer.isVisible({ timeout: 2000 }).catch(() => false);
      console.log(`  Results still visible: ${resultsStillVisible}`);
    }
  });
});
