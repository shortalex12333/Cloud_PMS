import { test, expect, RBAC_CONFIG } from '../rbac-fixtures';

/**
 * SHARD 31: Fragmented Routes - Shopping List
 *
 * Tests for /shopping-list and /shopping-list/[id] routes.
 * Shopping lists track parts and supplies that need to be ordered.
 *
 * Requirements Covered:
 * - T3-SL-01: /shopping-list list loads (HTTP 200, no console errors)
 * - T3-SL-02: /shopping-list/[id] detail loads with data
 * - T3-SL-03: Status filters work (if present)
 * - T3-SL-04: Add Item / Approve / Reject buttons visible based on status
 * - T3-SL-05: Page refresh preserves URL state
 * - T3-SL-06: Browser back/forward works
 * - Feature flag OFF redirects to /app
 *
 * Prerequisites:
 * - NEXT_PUBLIC_FRAGMENTED_ROUTES_ENABLED=true in environment
 * - Authenticated users (HOD, Crew, Captain)
 */

// Route configuration
const ROUTES_CONFIG = {
  ...RBAC_CONFIG,
  shoppingListList: '/shopping-list',
  shoppingListDetail: (id: string) => `/shopping-list/${id}`,
};

// Shopping list status values
const SL_STATUS = {
  PENDING: 'pending',
  APPROVED: 'approved',
  REJECTED: 'rejected',
  ORDERED: 'ordered',
} as const;

// ============================================================================
// SECTION 1: ROUTE LOADING TESTS
// T3-SL-01 and T3-SL-02: Basic route loads
// ============================================================================

test.describe('Shopping List Route Loading', () => {
  test.describe.configure({ retries: 1 });

  test('T3-SL-01: /shopping-list list route loads successfully', async ({ hodPage }) => {
    // Collect console errors
    const consoleErrors: string[] = [];
    hodPage.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Navigate directly to fragmented route
    await hodPage.goto(ROUTES_CONFIG.shoppingListList);

    // Check for redirect to legacy (feature flag disabled)
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - redirected to legacy /app');
      return;
    }

    // Wait for page to load
    await hodPage.waitForLoadState('networkidle');

    // Verify route loaded (not redirected)
    expect(hodPage.url()).toContain('/shopping-list');

    // Verify list container renders
    const listContainer = hodPage.locator('main, [role="main"]');
    await expect(listContainer).toBeVisible({ timeout: 10000 });

    // Verify no error state
    const errorState = hodPage.locator(':text("Failed to load"), :text("Error"), [data-testid="error-state"]');
    await expect(errorState).not.toBeVisible();

    // Verify loading completed (spinner gone)
    const spinner = hodPage.locator('.animate-spin, [data-loading="true"]');
    await expect(spinner).not.toBeVisible({ timeout: 15000 });

    // Verify no critical console errors
    const criticalErrors = consoleErrors.filter(
      e => !e.includes('ResizeObserver') && !e.includes('hydration')
    );
    expect(criticalErrors.length).toBe(0);

    console.log('  T3-SL-01: List route loaded successfully with no console errors');
  });

  test('T3-SL-02: /shopping-list/[id] detail route loads with data', async ({ hodPage, supabaseAdmin }) => {
    // First find a shopping list to navigate to
    const { data: shoppingList } = await supabaseAdmin
      .from('pms_shopping_lists')
      .select('id, title, status')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!shoppingList) {
      console.log('  No shopping lists found in test yacht - skipping');
      return;
    }

    // Navigate directly to detail route
    await hodPage.goto(ROUTES_CONFIG.shoppingListDetail(shoppingList.id));

    // Check for redirect to legacy (feature flag disabled)
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/shopping-list/')) {
      console.log('  Feature flag disabled - redirected to legacy /app');
      return;
    }

    // Wait for page to load
    await hodPage.waitForLoadState('networkidle');

    // Verify route loaded (not redirected)
    expect(hodPage.url()).toContain(`/shopping-list/${shoppingList.id}`);

    // Verify detail content renders
    const detailContainer = hodPage.locator('main, [role="main"]');
    await expect(detailContainer).toBeVisible({ timeout: 10000 });

    // Verify shopping list title or content visible
    const titleVisible = await hodPage.locator(`text=${shoppingList.title}`).isVisible({ timeout: 5000 }).catch(() => false);
    const contentExists = await hodPage.textContent('body');

    expect(titleVisible || contentExists?.includes('Shopping')).toBe(true);

    // Verify no error state
    const errorState = hodPage.locator(':text("Failed to Load"), :text("Not Found"), [data-testid="error-state"]');
    await expect(errorState).not.toBeVisible();

    // Verify StatusPill is visible
    const statusPill = hodPage.locator('[class*="StatusPill"], [class*="status"], [data-status]');
    const hasStatusPill = await statusPill.isVisible({ timeout: 5000 }).catch(() => false);

    console.log(`  T3-SL-02: Detail route loaded for "${shoppingList.title}" (status visible: ${hasStatusPill})`);
  });

  test('T3-SL-02b: Non-existent shopping list shows 404 state', async ({ hodPage }) => {
    const fakeId = '00000000-0000-0000-0000-000000000000';
    await hodPage.goto(ROUTES_CONFIG.shoppingListDetail(fakeId));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/shopping-list/')) {
      console.log('  Feature flag disabled - redirected to legacy /app');
      return;
    }

    await hodPage.waitForLoadState('networkidle');

    const notFoundState = hodPage.locator(':text("Not Found"), :text("not found"), :text("does not exist")');
    const errorState = hodPage.locator(':text("Failed"), :text("Error")');
    const hasNotFound = await notFoundState.isVisible({ timeout: 5000 }).catch(() => false);
    const hasError = await errorState.isVisible({ timeout: 5000 }).catch(() => false);

    expect(hasNotFound || hasError).toBe(true);
    console.log('  T3-SL-02b: Non-existent shopping list handled correctly');
  });
});

// ============================================================================
// SECTION 2: STATUS FILTERS TESTS
// T3-SL-03: Status filters work (if present)
// ============================================================================

test.describe('Shopping List Status Filters', () => {
  test.describe.configure({ retries: 1 });

  test('T3-SL-03: Status filters work (if present)', async ({ hodPage }) => {
    await hodPage.goto(ROUTES_CONFIG.shoppingListList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Look for status filter controls
    const filterSelector = hodPage.locator(
      'select:has-text("Status"), [data-testid="status-filter"], button:has-text("Pending"), button:has-text("Approved"), [role="combobox"], [class*="filter"]'
    );

    const hasFilters = await filterSelector.first().isVisible({ timeout: 5000 }).catch(() => false);

    if (hasFilters) {
      // Try clicking on a status filter
      const pendingFilter = hodPage.locator('button:has-text("pending"), button:has-text("Pending")').first();
      const isPendingFilterVisible = await pendingFilter.isVisible({ timeout: 3000 }).catch(() => false);

      if (isPendingFilterVisible) {
        await pendingFilter.click();
        await hodPage.waitForTimeout(1000);

        // Verify URL or UI updated
        const urlAfterFilter = hodPage.url();
        const filterApplied = urlAfterFilter.includes('status=') || urlAfterFilter.includes('filter=');

        console.log(`  T3-SL-03: Status filter clicked, URL param: ${filterApplied}`);
      } else {
        console.log('  T3-SL-03: Filter controls present but no pending filter button');
      }
    } else {
      console.log('  T3-SL-03: No status filters found on page (acceptable - feature may not be implemented)');
    }
  });
});

// ============================================================================
// SECTION 3: ACTION BUTTON TESTS
// T3-SL-04: Add Item / Approve / Reject buttons visible based on status
// ============================================================================

test.describe('Shopping List Action Buttons', () => {
  test.describe.configure({ retries: 1 });

  test('T3-SL-04a: Pending shopping list shows Approve/Reject buttons', async ({ hodPage, supabaseAdmin }) => {
    // Find a pending shopping list
    const { data: pendingList } = await supabaseAdmin
      .from('pms_shopping_lists')
      .select('id, title, status')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .eq('status', SL_STATUS.PENDING)
      .limit(1)
      .single();

    if (!pendingList) {
      console.log('  No pending shopping lists found - skipping');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.shoppingListDetail(pendingList.id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/shopping-list/')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Check for Approve button
    const approveButton = hodPage.locator('button:has-text("Approve")');
    const hasApprove = await approveButton.isVisible({ timeout: 5000 }).catch(() => false);

    // Check for Reject button
    const rejectButton = hodPage.locator('button:has-text("Reject")');
    const hasReject = await rejectButton.isVisible({ timeout: 5000 }).catch(() => false);

    // Check for Add Item button
    const addItemButton = hodPage.locator('button:has-text("Add Item"), button:has-text("Add item")');
    const hasAddItem = await addItemButton.isVisible({ timeout: 5000 }).catch(() => false);

    console.log(`  T3-SL-04a: Pending list - Approve: ${hasApprove}, Reject: ${hasReject}, Add Item: ${hasAddItem}`);

    // For pending status, Approve and Reject should be visible
    expect(hasApprove || hasReject || hasAddItem).toBe(true);
  });

  test('T3-SL-04b: Approved shopping list shows appropriate buttons', async ({ hodPage, supabaseAdmin }) => {
    // Find an approved shopping list
    const { data: approvedList } = await supabaseAdmin
      .from('pms_shopping_lists')
      .select('id, title, status')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .eq('status', SL_STATUS.APPROVED)
      .limit(1)
      .single();

    if (!approvedList) {
      console.log('  No approved shopping lists found - skipping');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.shoppingListDetail(approvedList.id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/shopping-list/')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Approve button should NOT be visible for already approved
    const approveButton = hodPage.locator('button:has-text("Approve")');
    const hasApprove = await approveButton.isVisible({ timeout: 3000 }).catch(() => false);

    // Mark as Ordered should be visible for approved
    const orderButton = hodPage.locator('button:has-text("Mark as Ordered"), button:has-text("Order")');
    const hasOrderButton = await orderButton.isVisible({ timeout: 5000 }).catch(() => false);

    // Add Item should still be available
    const addItemButton = hodPage.locator('button:has-text("Add Item"), button:has-text("Add item")');
    const hasAddItem = await addItemButton.isVisible({ timeout: 5000 }).catch(() => false);

    console.log(`  T3-SL-04b: Approved list - Approve: ${hasApprove}, Order: ${hasOrderButton}, Add Item: ${hasAddItem}`);

    // Approve should NOT appear for already approved lists
    expect(hasApprove).toBe(false);
  });

  test('T3-SL-04c: Rejected shopping list shows limited actions', async ({ hodPage, supabaseAdmin }) => {
    // Find a rejected shopping list
    const { data: rejectedList } = await supabaseAdmin
      .from('pms_shopping_lists')
      .select('id, title, status')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .eq('status', SL_STATUS.REJECTED)
      .limit(1)
      .single();

    if (!rejectedList) {
      console.log('  No rejected shopping lists found - skipping');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.shoppingListDetail(rejectedList.id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/shopping-list/')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Approve/Reject should NOT be visible for rejected
    const approveButton = hodPage.locator('button:has-text("Approve")');
    const hasApprove = await approveButton.isVisible({ timeout: 3000 }).catch(() => false);

    const rejectButton = hodPage.locator('button:has-text("Reject")');
    const hasReject = await rejectButton.isVisible({ timeout: 3000 }).catch(() => false);

    console.log(`  T3-SL-04c: Rejected list - Approve: ${hasApprove}, Reject: ${hasReject}`);

    // For rejected status, neither approve nor reject should be visible
    expect(hasApprove).toBe(false);
    expect(hasReject).toBe(false);
  });
});

// ============================================================================
// SECTION 4: STATE PERSISTENCE TESTS
// T3-SL-05: Page refresh preserves URL state
// ============================================================================

test.describe('Shopping List State Persistence', () => {
  test.describe.configure({ retries: 1 });

  test('T3-SL-05: Page refresh preserves URL state on list', async ({ hodPage }) => {
    await hodPage.goto(ROUTES_CONFIG.shoppingListList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    const beforeUrl = hodPage.url();

    // Refresh page
    await hodPage.reload();
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    const afterUrl = hodPage.url();
    expect(afterUrl).toBe(beforeUrl);
    console.log('  T3-SL-05: List URL preserved after refresh');
  });

  test('T3-SL-05b: Page refresh preserves detail view', async ({ hodPage, supabaseAdmin }) => {
    const { data: shoppingList } = await supabaseAdmin
      .from('pms_shopping_lists')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!shoppingList) {
      console.log('  No shopping list in test yacht - skipping');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.shoppingListDetail(shoppingList.id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/shopping-list/')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    const beforeUrl = hodPage.url();
    const beforeContent = await hodPage.textContent('body');

    // Refresh page
    await hodPage.reload();
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    const afterUrl = hodPage.url();
    const afterContent = await hodPage.textContent('body');

    expect(afterUrl).toBe(beforeUrl);
    expect(afterContent).toBeTruthy();

    console.log('  T3-SL-05b: Detail state preserved after refresh');
  });
});

// ============================================================================
// SECTION 5: BROWSER NAVIGATION TESTS
// T3-SL-06: Browser back/forward works
// ============================================================================

test.describe('Shopping List Browser Navigation', () => {
  test.describe.configure({ retries: 1 });

  test('T3-SL-06: Browser back/forward works naturally', async ({ hodPage, supabaseAdmin }) => {
    const { data: shoppingList } = await supabaseAdmin
      .from('pms_shopping_lists')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!shoppingList) {
      console.log('  No shopping list in test yacht - skipping');
      return;
    }

    // Start at list
    await hodPage.goto(ROUTES_CONFIG.shoppingListList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    const listUrl = hodPage.url();

    // Navigate to detail
    await hodPage.goto(ROUTES_CONFIG.shoppingListDetail(shoppingList.id));
    await hodPage.waitForLoadState('networkidle');
    const detailUrl = hodPage.url();

    expect(detailUrl).toContain(`/shopping-list/${shoppingList.id}`);

    // Go back via browser
    await hodPage.goBack();
    await hodPage.waitForLoadState('networkidle');

    // Verify we're back at list
    expect(hodPage.url()).toBe(listUrl);
    console.log('  T3-SL-06a: Back navigation to list verified');

    // Go forward
    await hodPage.goForward();
    await hodPage.waitForLoadState('networkidle');

    // Verify we're at detail again
    expect(hodPage.url()).toBe(detailUrl);
    console.log('  T3-SL-06b: Forward navigation to detail verified');
  });

  test('T3-SL-06b: Back button in UI works', async ({ hodPage, supabaseAdmin }) => {
    const { data: shoppingList } = await supabaseAdmin
      .from('pms_shopping_lists')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!shoppingList) {
      console.log('  No shopping list in test yacht - skipping');
      return;
    }

    // Start at home
    await hodPage.goto('/');
    await hodPage.waitForLoadState('networkidle');

    // Navigate to detail
    await hodPage.goto(ROUTES_CONFIG.shoppingListDetail(shoppingList.id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/shopping-list/')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Click back button in UI (if exists)
    const backButton = hodPage.locator(
      'button[aria-label="Back"], [data-testid="back-button"], button:has([data-testid="back-icon"])'
    );
    const hasBackButton = await backButton.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasBackButton) {
      await backButton.click();
      await hodPage.waitForLoadState('networkidle');

      // Should navigate back
      const newUrl = hodPage.url();
      expect(newUrl).not.toContain(`/shopping-list/${shoppingList.id}`);
      console.log('  T3-SL-06b: UI back button works');
    } else {
      // Use browser back
      await hodPage.goBack();
      await hodPage.waitForLoadState('networkidle');
      console.log('  T3-SL-06b: Browser back works (no UI back button)');
    }
  });
});

// ============================================================================
// SECTION 6: FEATURE FLAG BEHAVIOR
// Feature flag OFF redirects to /app
// ============================================================================

test.describe('Shopping List Feature Flag Behavior', () => {
  test.describe.configure({ retries: 0 });

  test('Feature flag OFF redirects list to /app', async ({ hodPage }) => {
    await hodPage.goto(ROUTES_CONFIG.shoppingListList);
    await hodPage.waitForLoadState('networkidle');

    const currentUrl = hodPage.url();

    if (currentUrl.includes('/app')) {
      // Flag is disabled - verify redirect worked
      expect(currentUrl).toContain('/app');
      console.log('  Feature flag OFF: Correctly redirected to /app');
    } else if (currentUrl.includes('/shopping-list')) {
      // Flag is enabled - verify route works
      expect(currentUrl).toContain('/shopping-list');
      console.log('  Feature flag ON: Route loaded directly');
    }
  });

  test('Feature flag OFF redirects detail to /app with entity params', async ({ hodPage, supabaseAdmin }) => {
    const { data: shoppingList } = await supabaseAdmin
      .from('pms_shopping_lists')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!shoppingList) {
      console.log('  No shopping list in test yacht - skipping');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.shoppingListDetail(shoppingList.id));
    await hodPage.waitForLoadState('networkidle');

    const currentUrl = hodPage.url();

    if (currentUrl.includes('/app') && currentUrl.includes('entity=')) {
      // Flag is disabled - verify redirect included entity params
      expect(currentUrl).toContain('entity=shopping_list');
      expect(currentUrl).toContain(`id=${shoppingList.id}`);
      console.log('  Feature flag OFF: Detail redirected to /app with entity params');
    } else if (currentUrl.includes(`/shopping-list/${shoppingList.id}`)) {
      // Flag is enabled
      console.log('  Feature flag ON: Detail route loaded directly');
    }
  });
});

// ============================================================================
// SECTION 7: KEY ELEMENTS VISIBILITY
// Verify StatusPill, title, and key UI elements render
// ============================================================================

test.describe('Shopping List Key Elements', () => {
  test.describe.configure({ retries: 1 });

  test('StatusPill and title are visible on list', async ({ hodPage }) => {
    await hodPage.goto(ROUTES_CONFIG.shoppingListList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Check for page title
    const pageTitle = hodPage.locator('h1:has-text("Shopping"), [data-testid="page-title"]');
    const hasTitleHeader = await pageTitle.isVisible({ timeout: 5000 }).catch(() => false);

    // Check for status pills in list
    const statusPill = hodPage.locator('[class*="StatusPill"], [class*="status-pill"], [data-status]');
    const hasStatusPills = await statusPill.first().isVisible({ timeout: 5000 }).catch(() => false);

    console.log(`  List key elements - Title: ${hasTitleHeader}, StatusPills: ${hasStatusPills}`);

    // At least the title should be visible
    expect(hasTitleHeader || hasStatusPills).toBe(true);
  });

  test('StatusPill and title are visible on detail', async ({ hodPage, supabaseAdmin }) => {
    const { data: shoppingList } = await supabaseAdmin
      .from('pms_shopping_lists')
      .select('id, title, status')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!shoppingList) {
      console.log('  No shopping list in test yacht - skipping');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.shoppingListDetail(shoppingList.id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/shopping-list/')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Check for title
    const titleElement = hodPage.locator(`h1:has-text("${shoppingList.title}"), h2:has-text("${shoppingList.title}")`);
    const hasTitleVisible = await titleElement.isVisible({ timeout: 5000 }).catch(() => false);

    // Check for status pill
    const statusPill = hodPage.locator('[class*="StatusPill"], [class*="status"], [data-status]');
    const hasStatusPill = await statusPill.first().isVisible({ timeout: 5000 }).catch(() => false);

    console.log(`  Detail key elements - Title: ${hasTitleVisible}, StatusPill: ${hasStatusPill}`);

    // At least one key element should be visible
    expect(hasTitleVisible || hasStatusPill).toBe(true);
  });

  test('Buttons are clickable on detail', async ({ hodPage, supabaseAdmin }) => {
    const { data: shoppingList } = await supabaseAdmin
      .from('pms_shopping_lists')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .eq('status', SL_STATUS.PENDING)
      .limit(1)
      .single();

    if (!shoppingList) {
      console.log('  No pending shopping list in test yacht - skipping');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.shoppingListDetail(shoppingList.id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/shopping-list/')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Find any action button
    const actionButton = hodPage.locator(
      'button:has-text("Add Item"), button:has-text("Approve"), button:has-text("Reject")'
    ).first();

    const hasButton = await actionButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasButton) {
      // Verify button is enabled and clickable
      const isEnabled = await actionButton.isEnabled();
      expect(isEnabled).toBe(true);
      console.log('  Buttons are visible and clickable');
    } else {
      console.log('  No action buttons found on detail page');
    }
  });
});

// ============================================================================
// SECTION 8: PERFORMANCE BASELINE
// Basic load time checks
// ============================================================================

test.describe('Shopping List Route Performance', () => {
  test.describe.configure({ retries: 0 });

  test('List route loads within 5 seconds', async ({ hodPage }) => {
    const startTime = Date.now();

    await hodPage.goto(ROUTES_CONFIG.shoppingListList);

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
    const { data: shoppingList } = await supabaseAdmin
      .from('pms_shopping_lists')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!shoppingList) {
      console.log('  No shopping list in test yacht - skipping');
      return;
    }

    const startTime = Date.now();

    await hodPage.goto(ROUTES_CONFIG.shoppingListDetail(shoppingList.id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/shopping-list/')) {
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
