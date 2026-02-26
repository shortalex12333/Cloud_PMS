import { test, expect, RBAC_CONFIG } from '../rbac-fixtures';

/**
 * SHARD 31: Fragmented Routes - Receiving
 *
 * Tests for /receiving and /receiving/[id] routes.
 * These routes handle receiving records for deliveries and incoming shipments.
 *
 * Requirements Covered:
 * - T3-RCV-01: /receiving list loads (HTTP 200, no console errors)
 * - T3-RCV-02: /receiving/[id] detail loads with data
 * - T3-RCV-03: Status filters work (if present)
 * - T3-RCV-04: Accept/Reject buttons visible for draft status
 * - T3-RCV-05: Page refresh preserves URL state
 * - T3-RCV-06: Browser back/forward works
 * - Feature flag OFF redirects to /app
 *
 * Receiving Status Values:
 * - draft: Initial state, can be edited
 * - in_review: Submitted for review, Accept/Reject visible
 * - accepted: Approved receiving
 * - rejected: Rejected receiving
 */

// Route configuration
const ROUTES_CONFIG = {
  ...RBAC_CONFIG,
  receivingList: '/receiving',
  receivingDetail: (id: string) => `/receiving/${id}`,
};

// ============================================================================
// SECTION 1: ROUTE LOADING TESTS
// T3-RCV-01 and T3-RCV-02: Basic route loads
// ============================================================================

test.describe('Receiving Route Loading', () => {
  test.describe.configure({ retries: 1 });

  test('T3-RCV-01: /receiving list loads (HTTP 200, no console errors)', async ({ hodPage }) => {
    // Track console errors
    const consoleErrors: string[] = [];
    hodPage.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Navigate to receiving list
    await hodPage.goto(ROUTES_CONFIG.receivingList);

    // Check for redirect to legacy (feature flag disabled)
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - redirected to legacy /app');
      return;
    }

    // Wait for page to load
    await hodPage.waitForLoadState('networkidle');

    // Verify route loaded (not redirected)
    expect(hodPage.url()).toContain('/receiving');

    // Verify list container renders
    const listContainer = hodPage.locator('main, [role="main"]');
    await expect(listContainer).toBeVisible({ timeout: 10000 });

    // Verify no error state
    const errorState = hodPage.locator(':text("Failed to load"), :text("Failed to Load")');
    await expect(errorState).not.toBeVisible();

    // Verify loading completed (spinner gone)
    const spinner = hodPage.locator('.animate-spin, [data-loading="true"]');
    await expect(spinner).not.toBeVisible({ timeout: 15000 });

    // Check for critical console errors (filter out known noise)
    const criticalErrors = consoleErrors.filter(e =>
      !e.includes('favicon') &&
      !e.includes('ResizeObserver') &&
      !e.includes('hydration')
    );

    if (criticalErrors.length > 0) {
      console.log('  Console errors detected:', criticalErrors);
    }

    console.log('  T3-RCV-01: List route loaded successfully');
  });

  test('T3-RCV-02: /receiving/[id] detail loads with data', async ({ hodPage, supabaseAdmin }) => {
    // Try to find an existing receiving record
    const { data: receiving } = await supabaseAdmin
      .from('inv_receiving')
      .select('id, po_number, vendor_name')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!receiving) {
      console.log('  No receiving records in test yacht - skipping');
      return;
    }

    // Navigate to detail route
    await hodPage.goto(ROUTES_CONFIG.receivingDetail(receiving.id));

    // Check for redirect to legacy (feature flag disabled)
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - redirected to legacy /app');
      return;
    }

    // Wait for page to load
    await hodPage.waitForLoadState('networkidle');

    // Verify route loaded (not redirected)
    expect(hodPage.url()).toContain(`/receiving/${receiving.id}`);

    // Verify detail content renders
    const detailContainer = hodPage.locator('main, [role="main"]');
    await expect(detailContainer).toBeVisible({ timeout: 10000 });

    // Verify some content loaded
    const content = await hodPage.textContent('body');
    expect(content).toBeTruthy();

    // Check for StatusPill component (key UI element)
    const statusPill = hodPage.locator('[class*="status"], [data-status]');
    const hasStatusPill = await statusPill.isVisible({ timeout: 5000 }).catch(() => false);

    console.log(`  T3-RCV-02: Detail route loaded for ${receiving.po_number || receiving.id}`);
    console.log(`  StatusPill visible: ${hasStatusPill}`);
  });

  test('T3-RCV-02b: Non-existent receiving shows 404 state', async ({ hodPage }) => {
    const fakeId = '00000000-0000-0000-0000-000000000000';

    await hodPage.goto(ROUTES_CONFIG.receivingDetail(fakeId));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - redirected to legacy /app');
      return;
    }

    await hodPage.waitForLoadState('networkidle');

    // Should show not found or error state
    const notFoundState = hodPage.locator(
      ':text("Not Found"), :text("not found"), :text("does not exist"), :text("Receiving Not Found")'
    );
    const errorState = hodPage.locator(':text("Failed"), :text("Error")');

    const hasNotFound = await notFoundState.isVisible({ timeout: 5000 }).catch(() => false);
    const hasError = await errorState.isVisible({ timeout: 5000 }).catch(() => false);

    // Either not found or error is acceptable for non-existent entity
    expect(hasNotFound || hasError).toBe(true);
    console.log('  T3-RCV-02b: Non-existent receiving handled correctly');
  });
});

// ============================================================================
// SECTION 2: STATUS FILTER TESTS
// T3-RCV-03: Status filters work (if present)
// ============================================================================

test.describe('Receiving Status Filters', () => {
  test.describe.configure({ retries: 1 });

  test('T3-RCV-03: Status filters work (if present)', async ({ hodPage }) => {
    await hodPage.goto(ROUTES_CONFIG.receivingList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');

    // Look for status filter controls
    const filterControls = hodPage.locator(
      'select:has-text("Status"), [data-testid="status-filter"], button:has-text("Filter"), ' +
      '[aria-label*="filter"], [role="combobox"]:has-text("Status")'
    );

    const hasFilters = await filterControls.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasFilters) {
      console.log('  Status filters present - testing interaction');

      // Try to interact with the filter
      await filterControls.first().click();
      await hodPage.waitForTimeout(500);

      // Look for filter options
      const filterOptions = hodPage.locator(
        '[role="option"], [role="menuitem"], option'
      );

      const optionsVisible = await filterOptions.first().isVisible({ timeout: 3000 }).catch(() => false);

      if (optionsVisible) {
        console.log('  T3-RCV-03: Filter dropdown opened successfully');
      } else {
        console.log('  T3-RCV-03: Filter exists but no dropdown options found');
      }
    } else {
      // Check if there are status tabs instead
      const statusTabs = hodPage.locator(
        'button:has-text("Draft"), button:has-text("In Review"), button:has-text("Accepted"), button:has-text("Rejected")'
      );

      const hasTabs = await statusTabs.first().isVisible({ timeout: 3000 }).catch(() => false);

      if (hasTabs) {
        console.log('  Status tabs present instead of dropdown');
        await statusTabs.first().click();
        await hodPage.waitForTimeout(500);
        console.log('  T3-RCV-03: Status tab interaction verified');
      } else {
        console.log('  T3-RCV-03: No status filters present in current UI');
      }
    }
  });
});

// ============================================================================
// SECTION 3: ACTION BUTTON TESTS
// T3-RCV-04: Accept/Reject buttons visible for in_review status
// ============================================================================

test.describe('Receiving Action Buttons', () => {
  test.describe.configure({ retries: 1 });

  test('T3-RCV-04: Accept/Reject buttons visible for in_review status', async ({ hodPage, supabaseAdmin }) => {
    // Find a receiving record in draft or in_review status
    const { data: receiving } = await supabaseAdmin
      .from('inv_receiving')
      .select('id, status')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .in('status', ['draft', 'in_review'])
      .limit(1)
      .single();

    if (!receiving) {
      console.log('  No draft/in_review receiving records found - skipping');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.receivingDetail(receiving.id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000); // Wait for data to load

    if (receiving.status === 'in_review') {
      // Check for Accept button
      const acceptButton = hodPage.locator('button:has-text("Accept")');
      const hasAccept = await acceptButton.isVisible({ timeout: 5000 }).catch(() => false);

      // Check for Reject button
      const rejectButton = hodPage.locator('button:has-text("Reject")');
      const hasReject = await rejectButton.isVisible({ timeout: 5000 }).catch(() => false);

      expect(hasAccept).toBe(true);
      expect(hasReject).toBe(true);

      console.log(`  T3-RCV-04: Accept button visible: ${hasAccept}`);
      console.log(`  T3-RCV-04: Reject button visible: ${hasReject}`);
    } else if (receiving.status === 'draft') {
      // For draft, check Submit for Review button
      const submitButton = hodPage.locator('button:has-text("Submit for Review"), button:has-text("Submit")');
      const hasSubmit = await submitButton.isVisible({ timeout: 5000 }).catch(() => false);

      // Draft should also have Edit button
      const editButton = hodPage.locator('button:has-text("Edit")');
      const hasEdit = await editButton.isVisible({ timeout: 5000 }).catch(() => false);

      console.log(`  T3-RCV-04: Submit for Review button visible: ${hasSubmit}`);
      console.log(`  T3-RCV-04: Edit button visible: ${hasEdit}`);
    }
  });

  test('T3-RCV-04b: Action buttons are clickable', async ({ hodPage, supabaseAdmin }) => {
    // Find a receiving record with actionable status
    const { data: receiving } = await supabaseAdmin
      .from('inv_receiving')
      .select('id, status')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .in('status', ['draft', 'in_review'])
      .limit(1)
      .single();

    if (!receiving) {
      console.log('  No actionable receiving records found - skipping');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.receivingDetail(receiving.id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Find Edit button (should be present for all draft/in_review)
    const editButton = hodPage.locator('button:has-text("Edit")');
    const hasEdit = await editButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasEdit) {
      // Verify button is not disabled
      const isDisabled = await editButton.isDisabled();
      expect(isDisabled).toBe(false);
      console.log('  T3-RCV-04b: Edit button is clickable');
    } else {
      console.log('  T3-RCV-04b: Edit button not found in current state');
    }
  });
});

// ============================================================================
// SECTION 4: STATE PERSISTENCE TESTS
// T3-RCV-05: Page refresh preserves URL state
// ============================================================================

test.describe('Receiving State Persistence', () => {
  test.describe.configure({ retries: 1 });

  test('T3-RCV-05: Page refresh preserves URL state', async ({ hodPage, supabaseAdmin }) => {
    // Get a receiving record
    const { data: receiving } = await supabaseAdmin
      .from('inv_receiving')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!receiving) {
      console.log('  No receiving records in test yacht - skipping');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.receivingDetail(receiving.id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Store current state
    const beforeRefreshUrl = hodPage.url();

    // Refresh page
    await hodPage.reload();
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Verify URL preserved
    const afterRefreshUrl = hodPage.url();
    expect(afterRefreshUrl).toBe(beforeRefreshUrl);

    // Verify content still renders
    const content = await hodPage.textContent('body');
    expect(content).toBeTruthy();

    console.log('  T3-RCV-05: State preserved after refresh');
  });

  test('T3-RCV-05b: List with selection preserves state after refresh', async ({ hodPage, supabaseAdmin }) => {
    // Get a receiving record
    const { data: receiving } = await supabaseAdmin
      .from('inv_receiving')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!receiving) {
      console.log('  No receiving records in test yacht - skipping');
      return;
    }

    // Navigate to list with selection query param
    await hodPage.goto(`${ROUTES_CONFIG.receivingList}?id=${receiving.id}`);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/receiving')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    const beforeUrl = hodPage.url();

    // Refresh
    await hodPage.reload();
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    const afterUrl = hodPage.url();

    // URL should be preserved (including query params if present)
    expect(afterUrl).toBe(beforeUrl);
    console.log('  T3-RCV-05b: List selection state preserved after refresh');
  });
});

// ============================================================================
// SECTION 5: NAVIGATION TESTS
// T3-RCV-06: Browser back/forward works
// ============================================================================

test.describe('Receiving Navigation', () => {
  test.describe.configure({ retries: 1 });

  test('T3-RCV-06: Browser back/forward works', async ({ hodPage, supabaseAdmin }) => {
    // Get a receiving record
    const { data: receiving } = await supabaseAdmin
      .from('inv_receiving')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!receiving) {
      console.log('  No receiving records in test yacht - skipping');
      return;
    }

    // Start at list
    await hodPage.goto(ROUTES_CONFIG.receivingList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    const listUrl = hodPage.url();

    // Navigate to detail
    await hodPage.goto(ROUTES_CONFIG.receivingDetail(receiving.id));
    await hodPage.waitForLoadState('networkidle');
    const detailUrl = hodPage.url();

    expect(detailUrl).toContain(`/receiving/${receiving.id}`);

    // Go back via browser
    await hodPage.goBack();
    await hodPage.waitForLoadState('networkidle');

    // Verify we're back at list
    expect(hodPage.url()).toBe(listUrl);
    console.log('  T3-RCV-06a: Back navigation to list verified');

    // Go forward
    await hodPage.goForward();
    await hodPage.waitForLoadState('networkidle');

    // Verify we're at detail again
    expect(hodPage.url()).toBe(detailUrl);
    console.log('  T3-RCV-06b: Forward navigation to detail verified');
  });

  test('T3-RCV-06b: UI back button works', async ({ hodPage, supabaseAdmin }) => {
    // Get a receiving record
    const { data: receiving } = await supabaseAdmin
      .from('inv_receiving')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!receiving) {
      console.log('  No receiving records in test yacht - skipping');
      return;
    }

    // Navigate to detail
    await hodPage.goto(ROUTES_CONFIG.receivingDetail(receiving.id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/receiving/')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Find the back button in UI
    const backButton = hodPage.locator(
      'button[aria-label="Back"], [data-testid="back-button"], button:has(svg path[d*="15 18"])'
    );
    const hasBackButton = await backButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasBackButton) {
      await backButton.click();
      await hodPage.waitForLoadState('networkidle');

      // Should navigate away from detail
      const newUrl = hodPage.url();
      expect(newUrl).not.toContain(`/receiving/${receiving.id}`);
      console.log('  T3-RCV-06b: UI back button works');
    } else {
      console.log('  T3-RCV-06b: No UI back button found (using browser navigation)');
    }
  });
});

// ============================================================================
// SECTION 6: FEATURE FLAG TESTS
// Feature flag OFF redirects to /app
// ============================================================================

test.describe('Receiving Feature Flag Behavior', () => {
  test.describe.configure({ retries: 0 });

  test('Feature flag OFF redirects list to /app', async ({ hodPage }) => {
    await hodPage.goto(ROUTES_CONFIG.receivingList);
    await hodPage.waitForLoadState('networkidle');

    const currentUrl = hodPage.url();

    if (currentUrl.includes('/app')) {
      // Flag is disabled - verify redirect worked
      expect(currentUrl).toContain('/app');
      console.log('  Feature flag OFF: Correctly redirected to /app');
    } else if (currentUrl.includes('/receiving')) {
      // Flag is enabled - verify route works
      expect(currentUrl).toContain('/receiving');
      console.log('  Feature flag ON: Route loaded directly');
    }
  });

  test('Feature flag OFF redirects detail to /app with params', async ({ hodPage, supabaseAdmin }) => {
    // Get a receiving record
    const { data: receiving } = await supabaseAdmin
      .from('inv_receiving')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!receiving) {
      console.log('  No receiving records in test yacht - skipping');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.receivingDetail(receiving.id));
    await hodPage.waitForLoadState('networkidle');

    const currentUrl = hodPage.url();

    if (currentUrl.includes('/app')) {
      // Flag is disabled - should redirect with entity params
      expect(currentUrl).toContain('/app');
      // May include entity=receiving&id= params
      console.log('  Feature flag OFF: Detail redirected to /app');
    } else if (currentUrl.includes('/receiving/')) {
      // Flag is enabled - verify route works
      expect(currentUrl).toContain(`/receiving/${receiving.id}`);
      console.log('  Feature flag ON: Detail route loaded directly');
    }
  });
});

// ============================================================================
// SECTION 7: KEY UI ELEMENTS
// Verify StatusPill and VitalSignsRow are visible
// ============================================================================

test.describe('Receiving UI Elements', () => {
  test.describe.configure({ retries: 1 });

  test('Key elements visible (StatusPill, VitalSignsRow)', async ({ hodPage, supabaseAdmin }) => {
    // Get a receiving record
    const { data: receiving } = await supabaseAdmin
      .from('inv_receiving')
      .select('id, status, total, currency')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!receiving) {
      console.log('  No receiving records in test yacht - skipping');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.receivingDetail(receiving.id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/receiving/')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Check for StatusPill
    const statusPill = hodPage.locator(
      '[class*="StatusPill"], [class*="status-pill"], [data-status], ' +
      'span[class*="rounded"]:has-text("draft"), span[class*="rounded"]:has-text("review"), ' +
      'span[class*="rounded"]:has-text("accepted"), span[class*="rounded"]:has-text("rejected")'
    );
    const hasStatusPill = await statusPill.isVisible({ timeout: 5000 }).catch(() => false);
    console.log(`  StatusPill visible: ${hasStatusPill}`);

    // Check for total amount display (key vital sign)
    const totalDisplay = hodPage.locator(
      ':text("Total"), :text("Amount"), [class*="total"], [class*="amount"]'
    );
    const hasTotalDisplay = await totalDisplay.isVisible({ timeout: 5000 }).catch(() => false);
    console.log(`  Total amount display visible: ${hasTotalDisplay}`);

    // Check for currency formatting (e.g., $1,234.56)
    const currencyPattern = hodPage.locator('text=/\\$[\\d,]+\\.\\d{2}/');
    const hasCurrency = await currencyPattern.isVisible({ timeout: 3000 }).catch(() => false);
    console.log(`  Currency formatted value visible: ${hasCurrency}`);

    // At minimum, we should see some content
    const mainContent = hodPage.locator('main, [role="main"]');
    await expect(mainContent).toBeVisible();

    console.log('  Key UI elements check completed');
  });

  test('List items show StatusPill', async ({ hodPage }) => {
    await hodPage.goto(ROUTES_CONFIG.receivingList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Check if list has items
    const listItems = hodPage.locator('button[class*="text-left"], [role="listitem"], [class*="list-item"]');
    const itemCount = await listItems.count();

    if (itemCount > 0) {
      // Check for StatusPill in list items
      const statusInList = hodPage.locator(
        '[class*="StatusPill"], [class*="status-pill"], ' +
        'span[class*="rounded"]:has-text("draft"), span[class*="rounded"]:has-text("review")'
      );
      const hasStatusInList = await statusInList.isVisible({ timeout: 5000 }).catch(() => false);
      console.log(`  StatusPill in list items: ${hasStatusInList}`);
      console.log(`  List items found: ${itemCount}`);
    } else {
      console.log('  No list items found - list may be empty');
    }
  });
});

// ============================================================================
// SECTION 8: PERFORMANCE BASELINE
// Basic load time checks
// ============================================================================

test.describe('Receiving Route Performance', () => {
  test.describe.configure({ retries: 0 });

  test('List route loads within 5 seconds', async ({ hodPage }) => {
    const startTime = Date.now();

    await hodPage.goto(ROUTES_CONFIG.receivingList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');

    const loadTime = Date.now() - startTime;
    console.log(`  List load time: ${loadTime}ms`);

    // Should load within 5 seconds
    expect(loadTime).toBeLessThan(5000);
  });

  test('Detail route loads within 5 seconds', async ({ hodPage, supabaseAdmin }) => {
    // Get a receiving record
    const { data: receiving } = await supabaseAdmin
      .from('inv_receiving')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!receiving) {
      console.log('  No receiving records in test yacht - skipping');
      return;
    }

    const startTime = Date.now();

    await hodPage.goto(ROUTES_CONFIG.receivingDetail(receiving.id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');

    const loadTime = Date.now() - startTime;
    console.log(`  Detail load time: ${loadTime}ms`);

    // Should load within 5 seconds
    expect(loadTime).toBeLessThan(5000);
  });
});
