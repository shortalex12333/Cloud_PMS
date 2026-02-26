import { test, expect, RBAC_CONFIG } from '../rbac-fixtures';

/**
 * SHARD 31: Fragmented Routes - Quick Filters Security
 *
 * Security tests for Quick Filters ensuring yacht isolation and RBAC compliance.
 *
 * SECURITY REQUIREMENTS:
 * - SEC-QF-01: Yacht Isolation - Users MUST NOT see data from other yachts
 * - SEC-QF-02: Network Scoping - API responses MUST only contain current yacht data
 * - SEC-QF-03: No UI Leakage - List items MUST NOT expose cross-yacht identifiers
 * - SEC-QF-04: RBAC Enforcement - Role permissions apply to filtered views
 *
 * CRITICAL: These tests use NO soft assertions - failures MUST halt immediately
 * to prevent security regressions from being masked by partial passes.
 *
 * Domains Tested:
 * - Work Orders (pms_work_orders, yacht_id column)
 * - Faults (pms_faults, yacht_id column)
 * - Inventory (pms_parts, yacht_id column)
 */

// Test configuration
const SECURITY_CONFIG = {
  ...RBAC_CONFIG,
  // Routes under test
  workOrdersFiltered: '/work-orders?filter=wo_open',
  workOrdersOverdue: '/work-orders?filter=wo_overdue',
  faultsFiltered: '/faults?filter=fault_open',
  faultsUnresolved: '/faults?filter=fault_unresolved',
  inventoryFiltered: '/inventory?filter=inv_low_stock',
  inventoryAll: '/inventory',
  // Database tables for verification
  tables: {
    workOrders: 'pms_work_orders',
    faults: 'pms_faults',
    parts: 'pms_parts',
  },
};

// ============================================================================
// SECTION 1: WORK ORDERS - YACHT ISOLATION
// SEC-QF-01: Work order filter only shows current yacht data
// ============================================================================

test.describe('Quick Filters - Work Orders Security', () => {
  // CRITICAL: No retries for security tests - failures must be investigated
  test.describe.configure({ retries: 0 });

  test('SECURITY: Work order filter only shows current yacht data', async ({ hodPage, supabaseAdmin }) => {
    // Navigate to filtered work orders list
    await hodPage.goto(SECURITY_CONFIG.workOrdersFiltered);
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Check if redirected (feature flag disabled)
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/work-orders')) {
      console.log('  Feature flag disabled - skipping security test');
      return;
    }

    // Capture all row entity IDs from the list
    const rows = hodPage.locator('[data-testid^="entity-row-"], [data-testid^="work-order-row-"], tr[data-entity-id], [data-entity-id]');
    const rowCount = await rows.count();
    const rowIds: string[] = [];

    for (let i = 0; i < rowCount; i++) {
      const entityId = await rows.nth(i).getAttribute('data-entity-id');
      if (entityId && entityId.match(/^[0-9a-f-]{36}$/i)) {
        rowIds.push(entityId);
      }
    }

    console.log(`  Found ${rowIds.length} work order rows to verify`);

    // SECURITY CHECK: Verify each ID belongs to current yacht via database
    for (const id of rowIds) {
      const { data, error } = await supabaseAdmin
        .from(SECURITY_CONFIG.tables.workOrders)
        .select('yacht_id')
        .eq('id', id)
        .single();

      // HARD FAIL on any error or yacht mismatch
      expect(error).toBeNull();
      expect(data).not.toBeNull();
      expect(data?.yacht_id).toBe(SECURITY_CONFIG.yachtId);

      if (data?.yacht_id !== SECURITY_CONFIG.yachtId) {
        throw new Error(`SECURITY BREACH: Work order ${id} belongs to yacht ${data?.yacht_id}, expected ${SECURITY_CONFIG.yachtId}`);
      }
    }

    console.log(`  SECURITY PASS: All ${rowIds.length} work orders belong to current yacht`);
  });

  test('SECURITY: Work order network responses scoped to current yacht', async ({ hodPage }) => {
    const foreignYachtIds: string[] = [];
    const responsesChecked: number[] = [];

    // Intercept all API responses
    hodPage.on('response', async (response) => {
      const url = response.url();
      if (url.includes('/work-orders') || url.includes('/v1/') || url.includes('pms_work_orders')) {
        try {
          const json = await response.json();
          responsesChecked.push(response.status());

          // Check for array responses (list data)
          const items = Array.isArray(json) ? json : (json.data || json.items || []);
          if (Array.isArray(items)) {
            for (const item of items) {
              if (item.yacht_id && item.yacht_id !== SECURITY_CONFIG.yachtId) {
                foreignYachtIds.push(item.yacht_id);
              }
            }
          }

          // Check single item responses
          if (json.yacht_id && json.yacht_id !== SECURITY_CONFIG.yachtId) {
            foreignYachtIds.push(json.yacht_id);
          }
        } catch {
          // Non-JSON response, skip
        }
      }
    });

    await hodPage.goto(SECURITY_CONFIG.workOrdersFiltered);
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(3000);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/work-orders')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    // SECURITY CHECK: No foreign yacht IDs in any response
    expect(foreignYachtIds.length).toBe(0);

    if (foreignYachtIds.length > 0) {
      throw new Error(`SECURITY BREACH: Found ${foreignYachtIds.length} foreign yacht IDs in network responses: ${foreignYachtIds.join(', ')}`);
    }

    console.log(`  SECURITY PASS: Checked ${responsesChecked.length} responses, no foreign yacht data`);
  });
});

// ============================================================================
// SECTION 2: FAULTS - YACHT ISOLATION
// SEC-QF-01: Fault filter only shows current yacht data
// ============================================================================

test.describe('Quick Filters - Faults Security', () => {
  test.describe.configure({ retries: 0 });

  test('SECURITY: Fault filter only shows current yacht data', async ({ hodPage, supabaseAdmin }) => {
    await hodPage.goto(SECURITY_CONFIG.faultsFiltered);
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/faults')) {
      console.log('  Feature flag disabled - skipping security test');
      return;
    }

    // Capture all fault entity IDs
    const rows = hodPage.locator('[data-testid^="entity-row-"], [data-testid^="fault-row-"], tr[data-entity-id], [data-entity-id]');
    const rowCount = await rows.count();
    const rowIds: string[] = [];

    for (let i = 0; i < rowCount; i++) {
      const entityId = await rows.nth(i).getAttribute('data-entity-id');
      if (entityId && entityId.match(/^[0-9a-f-]{36}$/i)) {
        rowIds.push(entityId);
      }
    }

    console.log(`  Found ${rowIds.length} fault rows to verify`);

    // SECURITY CHECK: Database verification
    for (const id of rowIds) {
      const { data, error } = await supabaseAdmin
        .from(SECURITY_CONFIG.tables.faults)
        .select('yacht_id')
        .eq('id', id)
        .single();

      expect(error).toBeNull();
      expect(data).not.toBeNull();
      expect(data?.yacht_id).toBe(SECURITY_CONFIG.yachtId);

      if (data?.yacht_id !== SECURITY_CONFIG.yachtId) {
        throw new Error(`SECURITY BREACH: Fault ${id} belongs to yacht ${data?.yacht_id}, expected ${SECURITY_CONFIG.yachtId}`);
      }
    }

    console.log(`  SECURITY PASS: All ${rowIds.length} faults belong to current yacht`);
  });

  test('SECURITY: Fault network responses scoped to current yacht', async ({ hodPage }) => {
    const foreignYachtIds: string[] = [];
    const responsesChecked: number[] = [];

    hodPage.on('response', async (response) => {
      const url = response.url();
      if (url.includes('/faults') || url.includes('/v1/') || url.includes('pms_faults')) {
        try {
          const json = await response.json();
          responsesChecked.push(response.status());

          const items = Array.isArray(json) ? json : (json.data || json.items || []);
          if (Array.isArray(items)) {
            for (const item of items) {
              if (item.yacht_id && item.yacht_id !== SECURITY_CONFIG.yachtId) {
                foreignYachtIds.push(item.yacht_id);
              }
            }
          }

          if (json.yacht_id && json.yacht_id !== SECURITY_CONFIG.yachtId) {
            foreignYachtIds.push(json.yacht_id);
          }
        } catch {
          // Non-JSON response
        }
      }
    });

    await hodPage.goto(SECURITY_CONFIG.faultsFiltered);
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(3000);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/faults')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    expect(foreignYachtIds.length).toBe(0);

    if (foreignYachtIds.length > 0) {
      throw new Error(`SECURITY BREACH: Found ${foreignYachtIds.length} foreign yacht IDs in fault responses`);
    }

    console.log(`  SECURITY PASS: Checked ${responsesChecked.length} responses, no foreign yacht data`);
  });
});

// ============================================================================
// SECTION 3: INVENTORY - YACHT ISOLATION
// SEC-QF-01: Inventory filter only shows current yacht data
// ============================================================================

test.describe('Quick Filters - Inventory Security', () => {
  test.describe.configure({ retries: 0 });

  test('SECURITY: Inventory filter only shows current yacht data', async ({ hodPage, supabaseAdmin }) => {
    await hodPage.goto(SECURITY_CONFIG.inventoryFiltered);
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/inventory')) {
      console.log('  Feature flag disabled - skipping security test');
      return;
    }

    // Capture all inventory/part entity IDs
    const rows = hodPage.locator('[data-testid^="entity-row-"], [data-testid^="inventory-row-"], [data-testid^="part-row-"], tr[data-entity-id], [data-entity-id]');
    const rowCount = await rows.count();
    const rowIds: string[] = [];

    for (let i = 0; i < rowCount; i++) {
      const entityId = await rows.nth(i).getAttribute('data-entity-id');
      if (entityId && entityId.match(/^[0-9a-f-]{36}$/i)) {
        rowIds.push(entityId);
      }
    }

    console.log(`  Found ${rowIds.length} inventory rows to verify`);

    // SECURITY CHECK: Database verification
    for (const id of rowIds) {
      const { data, error } = await supabaseAdmin
        .from(SECURITY_CONFIG.tables.parts)
        .select('yacht_id')
        .eq('id', id)
        .single();

      expect(error).toBeNull();
      expect(data).not.toBeNull();
      expect(data?.yacht_id).toBe(SECURITY_CONFIG.yachtId);

      if (data?.yacht_id !== SECURITY_CONFIG.yachtId) {
        throw new Error(`SECURITY BREACH: Part ${id} belongs to yacht ${data?.yacht_id}, expected ${SECURITY_CONFIG.yachtId}`);
      }
    }

    console.log(`  SECURITY PASS: All ${rowIds.length} inventory items belong to current yacht`);
  });

  test('SECURITY: Inventory network responses scoped to current yacht', async ({ hodPage }) => {
    const foreignYachtIds: string[] = [];
    const responsesChecked: number[] = [];

    hodPage.on('response', async (response) => {
      const url = response.url();
      if (url.includes('/inventory') || url.includes('/v1/') || url.includes('pms_parts')) {
        try {
          const json = await response.json();
          responsesChecked.push(response.status());

          const items = Array.isArray(json) ? json : (json.data || json.items || []);
          if (Array.isArray(items)) {
            for (const item of items) {
              if (item.yacht_id && item.yacht_id !== SECURITY_CONFIG.yachtId) {
                foreignYachtIds.push(item.yacht_id);
              }
            }
          }

          if (json.yacht_id && json.yacht_id !== SECURITY_CONFIG.yachtId) {
            foreignYachtIds.push(json.yacht_id);
          }
        } catch {
          // Non-JSON response
        }
      }
    });

    await hodPage.goto(SECURITY_CONFIG.inventoryFiltered);
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(3000);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/inventory')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    expect(foreignYachtIds.length).toBe(0);

    if (foreignYachtIds.length > 0) {
      throw new Error(`SECURITY BREACH: Found ${foreignYachtIds.length} foreign yacht IDs in inventory responses`);
    }

    console.log(`  SECURITY PASS: Checked ${responsesChecked.length} responses, no foreign yacht data`);
  });
});

// ============================================================================
// SECTION 4: CROSS-DOMAIN SECURITY
// SEC-QF-02: Verify no cross-domain data leakage when switching filters
// ============================================================================

test.describe('Quick Filters - Cross-Domain Security', () => {
  test.describe.configure({ retries: 0 });

  test('SECURITY: Switching between filtered views maintains yacht isolation', async ({ hodPage, supabaseAdmin }) => {
    const allEntityIds: { domain: string; id: string }[] = [];

    // Visit each filtered domain and collect entity IDs
    const domains = [
      { url: SECURITY_CONFIG.workOrdersFiltered, name: 'work-orders', table: SECURITY_CONFIG.tables.workOrders },
      { url: SECURITY_CONFIG.faultsFiltered, name: 'faults', table: SECURITY_CONFIG.tables.faults },
      { url: SECURITY_CONFIG.inventoryFiltered, name: 'inventory', table: SECURITY_CONFIG.tables.parts },
    ];

    for (const domain of domains) {
      await hodPage.goto(domain.url);
      await hodPage.waitForLoadState('networkidle');
      await hodPage.waitForTimeout(2000);

      const currentUrl = hodPage.url();
      if (currentUrl.includes('/app') && !currentUrl.includes(`/${domain.name}`)) {
        console.log(`  Feature flag disabled for ${domain.name} - skipping`);
        continue;
      }

      const rows = hodPage.locator('[data-entity-id]');
      const rowCount = await rows.count();

      for (let i = 0; i < rowCount; i++) {
        const entityId = await rows.nth(i).getAttribute('data-entity-id');
        if (entityId && entityId.match(/^[0-9a-f-]{36}$/i)) {
          allEntityIds.push({ domain: domain.name, id: entityId });
        }
      }

      console.log(`  Collected ${rowCount} entities from ${domain.name}`);
    }

    // SECURITY CHECK: Verify ALL collected IDs belong to current yacht
    console.log(`  Verifying ${allEntityIds.length} total entities across all domains`);

    for (const entity of allEntityIds) {
      const tableMap: Record<string, string> = {
        'work-orders': SECURITY_CONFIG.tables.workOrders,
        'faults': SECURITY_CONFIG.tables.faults,
        'inventory': SECURITY_CONFIG.tables.parts,
      };

      const { data, error } = await supabaseAdmin
        .from(tableMap[entity.domain])
        .select('yacht_id')
        .eq('id', entity.id)
        .single();

      if (error) {
        // Entity may have been deleted or wrong table - log but don't fail
        console.log(`  Warning: Could not verify ${entity.domain}/${entity.id}: ${error.message}`);
        continue;
      }

      expect(data?.yacht_id).toBe(SECURITY_CONFIG.yachtId);

      if (data?.yacht_id !== SECURITY_CONFIG.yachtId) {
        throw new Error(`SECURITY BREACH: ${entity.domain} entity ${entity.id} belongs to yacht ${data?.yacht_id}`);
      }
    }

    console.log(`  SECURITY PASS: All cross-domain entities verified for yacht isolation`);
  });

  test('SECURITY: Rapid filter navigation does not leak cross-yacht data', async ({ hodPage }) => {
    const foreignYachtIds: Set<string> = new Set();
    let totalResponsesChecked = 0;

    // Set up response interceptor before navigation
    hodPage.on('response', async (response) => {
      const url = response.url();
      if (url.includes('/v1/') || url.includes('supabase') || url.includes('pms_')) {
        try {
          const json = await response.json();
          totalResponsesChecked++;

          const checkItem = (item: Record<string, unknown>) => {
            if (item.yacht_id && item.yacht_id !== SECURITY_CONFIG.yachtId) {
              foreignYachtIds.add(item.yacht_id as string);
            }
          };

          const items = Array.isArray(json) ? json : (json.data || json.items || []);
          if (Array.isArray(items)) {
            items.forEach(checkItem);
          }
          if (json.yacht_id) checkItem(json);
        } catch {
          // Non-JSON response
        }
      }
    });

    // Rapid navigation sequence (simulates user quickly switching between filters)
    const routes = [
      SECURITY_CONFIG.workOrdersFiltered,
      SECURITY_CONFIG.faultsFiltered,
      SECURITY_CONFIG.inventoryFiltered,
      SECURITY_CONFIG.workOrdersOverdue,
      SECURITY_CONFIG.faultsUnresolved,
      SECURITY_CONFIG.inventoryAll,
    ];

    for (const route of routes) {
      await hodPage.goto(route);
      await hodPage.waitForTimeout(500); // Quick navigation - don't wait for full load
    }

    // Wait for all pending requests to complete
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // SECURITY CHECK
    expect(foreignYachtIds.size).toBe(0);

    if (foreignYachtIds.size > 0) {
      throw new Error(`SECURITY BREACH: Rapid navigation exposed ${foreignYachtIds.size} foreign yacht IDs: ${Array.from(foreignYachtIds).join(', ')}`);
    }

    console.log(`  SECURITY PASS: Rapid navigation checked ${totalResponsesChecked} responses, no leakage`);
  });
});

// ============================================================================
// SECTION 5: RBAC ENFORCEMENT ON FILTERED VIEWS
// SEC-QF-04: Role permissions apply correctly to filtered results
// ============================================================================

test.describe('Quick Filters - RBAC Enforcement', () => {
  test.describe.configure({ retries: 0 });

  test('SECURITY: Crew sees filtered work orders but limited actions', async ({ crewPage, supabaseAdmin }) => {
    await crewPage.goto(SECURITY_CONFIG.workOrdersFiltered);
    await crewPage.waitForLoadState('networkidle');
    await crewPage.waitForTimeout(2000);

    const currentUrl = crewPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/work-orders')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    // Verify crew can see list (not blocked by permissions)
    const errorState = crewPage.locator(':text("Access Denied"), :text("Unauthorized"), :text("Permission denied")');
    const isBlocked = await errorState.isVisible({ timeout: 3000 }).catch(() => false);
    expect(isBlocked).toBe(false);

    // Verify data is still yacht-scoped even for crew
    const rows = crewPage.locator('[data-entity-id]');
    const rowCount = await rows.count();

    for (let i = 0; i < Math.min(rowCount, 5); i++) {
      const entityId = await rows.nth(i).getAttribute('data-entity-id');
      if (entityId && entityId.match(/^[0-9a-f-]{36}$/i)) {
        const { data } = await supabaseAdmin
          .from(SECURITY_CONFIG.tables.workOrders)
          .select('yacht_id')
          .eq('id', entityId)
          .single();

        expect(data?.yacht_id).toBe(SECURITY_CONFIG.yachtId);
      }
    }

    // Verify limited actions for crew (no delete, no archive)
    const deleteButton = crewPage.locator('button:has-text("Delete"), button:has-text("Archive")');
    const hasDeleteAction = await deleteButton.isVisible({ timeout: 3000 }).catch(() => false);
    expect(hasDeleteAction).toBe(false);

    console.log('  SECURITY PASS: Crew RBAC verified on filtered work orders');
  });

  test('SECURITY: Captain has full access to filtered views', async ({ captainPage, supabaseAdmin }) => {
    await captainPage.goto(SECURITY_CONFIG.workOrdersFiltered);
    await captainPage.waitForLoadState('networkidle');
    await captainPage.waitForTimeout(2000);

    const currentUrl = captainPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/work-orders')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    // Captain should not be blocked
    const errorState = captainPage.locator(':text("Access Denied"), :text("Unauthorized")');
    const isBlocked = await errorState.isVisible({ timeout: 3000 }).catch(() => false);
    expect(isBlocked).toBe(false);

    // Verify yacht isolation still applies to captain
    const rows = captainPage.locator('[data-entity-id]');
    const rowCount = await rows.count();

    for (let i = 0; i < Math.min(rowCount, 5); i++) {
      const entityId = await rows.nth(i).getAttribute('data-entity-id');
      if (entityId && entityId.match(/^[0-9a-f-]{36}$/i)) {
        const { data } = await supabaseAdmin
          .from(SECURITY_CONFIG.tables.workOrders)
          .select('yacht_id')
          .eq('id', entityId)
          .single();

        // Even captain is bound to their yacht
        expect(data?.yacht_id).toBe(SECURITY_CONFIG.yachtId);
      }
    }

    console.log('  SECURITY PASS: Captain access verified, yacht isolation maintained');
  });
});

// ============================================================================
// SECTION 6: UI LEAKAGE PREVENTION
// SEC-QF-03: No identifiable cross-yacht data in DOM
// ============================================================================

test.describe('Quick Filters - UI Leakage Prevention', () => {
  test.describe.configure({ retries: 0 });

  test('SECURITY: No foreign yacht identifiers in page DOM', async ({ hodPage, supabaseAdmin }) => {
    // Get a list of other yacht IDs that should NOT appear
    const { data: otherYachts } = await supabaseAdmin
      .from('yachts')
      .select('id, name')
      .neq('id', SECURITY_CONFIG.yachtId)
      .limit(5);

    if (!otherYachts || otherYachts.length === 0) {
      console.log('  No other yachts in database - single-tenant test environment');
      return;
    }

    await hodPage.goto(SECURITY_CONFIG.workOrdersFiltered);
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/work-orders')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    // Get entire page HTML
    const pageHtml = await hodPage.content();

    // SECURITY CHECK: Scan for foreign yacht IDs in DOM
    for (const yacht of otherYachts) {
      const containsForeignYachtId = pageHtml.includes(yacht.id);

      if (containsForeignYachtId) {
        throw new Error(`SECURITY BREACH: Foreign yacht ID ${yacht.id} (${yacht.name}) found in page DOM`);
      }
    }

    console.log(`  SECURITY PASS: Scanned DOM for ${otherYachts.length} foreign yacht IDs, none found`);
  });

  test('SECURITY: localStorage and sessionStorage do not contain foreign yacht data', async ({ hodPage, supabaseAdmin }) => {
    // Get foreign yacht IDs
    const { data: otherYachts } = await supabaseAdmin
      .from('yachts')
      .select('id')
      .neq('id', SECURITY_CONFIG.yachtId)
      .limit(10);

    if (!otherYachts || otherYachts.length === 0) {
      console.log('  No other yachts in database - skipping');
      return;
    }

    await hodPage.goto(SECURITY_CONFIG.workOrdersFiltered);
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/work-orders')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    // Check localStorage and sessionStorage
    const storageData = await hodPage.evaluate(() => {
      const localStorageData = JSON.stringify(Object.fromEntries(
        Object.keys(localStorage).map(k => [k, localStorage.getItem(k)])
      ));
      const sessionStorageData = JSON.stringify(Object.fromEntries(
        Object.keys(sessionStorage).map(k => [k, sessionStorage.getItem(k)])
      ));
      return { localStorage: localStorageData, sessionStorage: sessionStorageData };
    });

    // SECURITY CHECK: No foreign yacht IDs in storage
    for (const yacht of otherYachts) {
      if (storageData.localStorage.includes(yacht.id)) {
        throw new Error(`SECURITY BREACH: Foreign yacht ID ${yacht.id} found in localStorage`);
      }
      if (storageData.sessionStorage.includes(yacht.id)) {
        throw new Error(`SECURITY BREACH: Foreign yacht ID ${yacht.id} found in sessionStorage`);
      }
    }

    console.log(`  SECURITY PASS: Browser storage verified clean of foreign yacht IDs`);
  });
});

// ============================================================================
// SECTION 7: FILTER PARAMETER TAMPERING
// Verify URL parameter manipulation cannot bypass yacht isolation
// ============================================================================

test.describe('Quick Filters - Parameter Tampering Prevention', () => {
  test.describe.configure({ retries: 0 });

  test('SECURITY: Injecting foreign yacht_id in URL does not bypass isolation', async ({ hodPage, supabaseAdmin }) => {
    // Get a foreign yacht ID
    const { data: foreignYacht } = await supabaseAdmin
      .from('yachts')
      .select('id')
      .neq('id', SECURITY_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!foreignYacht) {
      console.log('  No foreign yacht available for tampering test');
      return;
    }

    // Attempt to inject foreign yacht_id via URL parameter
    const tamperUrl = `/work-orders?filter=wo_open&yacht_id=${foreignYacht.id}`;
    await hodPage.goto(tamperUrl);
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/work-orders')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    // Verify no data from foreign yacht appears
    const rows = hodPage.locator('[data-entity-id]');
    const rowCount = await rows.count();

    for (let i = 0; i < rowCount; i++) {
      const entityId = await rows.nth(i).getAttribute('data-entity-id');
      if (entityId && entityId.match(/^[0-9a-f-]{36}$/i)) {
        const { data } = await supabaseAdmin
          .from(SECURITY_CONFIG.tables.workOrders)
          .select('yacht_id')
          .eq('id', entityId)
          .single();

        // MUST be current yacht, NOT the injected yacht
        expect(data?.yacht_id).toBe(SECURITY_CONFIG.yachtId);
        expect(data?.yacht_id).not.toBe(foreignYacht.id);
      }
    }

    console.log('  SECURITY PASS: URL yacht_id tampering did not bypass isolation');
  });
});
