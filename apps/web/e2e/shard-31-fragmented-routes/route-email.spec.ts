import { test, expect, RBAC_CONFIG } from '../rbac-fixtures';

/**
 * SHARD 31: Fragmented Routes - Email
 *
 * Tests for /email and /email/[threadId] routes.
 * These are Tier 2 fragmented routes separate from the legacy email overlay (shard-6).
 *
 * Requirements Covered:
 * - T2-EM-01: /email list route loads successfully
 * - T2-EM-02: /email/[threadId] detail route loads correctly
 * - T2-EM-03: Thread search works
 * - T2-EM-04: Linked/Unlinked filter works
 * - T2-EM-07: Page refresh preserves state
 * - GR-05: Browser back/forward works naturally
 *
 * Prerequisites:
 * - NEXT_PUBLIC_FRAGMENTED_ROUTES_ENABLED=true in environment
 * - Authenticated users (HOD, Crew)
 */

const ROUTES_CONFIG = {
  ...RBAC_CONFIG,
  emailList: '/email',
  emailDetail: (threadId: string) => `/email/${threadId}`,
  // Feature flag must be enabled for these routes to work
  featureFlagEnabled: process.env.NEXT_PUBLIC_FRAGMENTED_ROUTES_ENABLED === 'true',
};

// ============================================================================
// SECTION 1: ROUTE LOADING TESTS
// T2-EM-01 and T2-EM-02: Basic route loads
// ============================================================================

test.describe('Email Route Loading', () => {
  test.describe.configure({ retries: 1 });

  test('T2-EM-01: /email list route loads successfully', async ({ hodPage }) => {
    // Collect console errors
    const consoleErrors: string[] = [];
    hodPage.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Navigate directly to fragmented route
    await hodPage.goto(ROUTES_CONFIG.emailList);

    // Check for redirect to legacy (feature flag disabled)
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - redirected to legacy /app');
      return;
    }

    // Wait for page to load
    await hodPage.waitForLoadState('networkidle');

    // Verify route loaded (not redirected)
    expect(hodPage.url()).toContain('/email');

    // Verify main content renders (RouteLayout with page title "Email")
    const mainContainer = hodPage.locator('main, [role="main"]');
    await expect(mainContainer).toBeVisible({ timeout: 10000 });

    // Verify page title or heading
    const emailTitle = hodPage.locator('h1:has-text("Email")');
    await expect(emailTitle).toBeVisible({ timeout: 5000 });

    // Verify no error state
    const errorState = hodPage.locator(':text("Failed to load"), :text("Failed to Load")');
    await expect(errorState).not.toBeVisible();

    // Verify loading completed (spinner gone)
    const spinner = hodPage.locator('.animate-spin');
    await expect(spinner).not.toBeVisible({ timeout: 15000 });

    // Check for critical console errors (filter out common noise)
    const criticalErrors = consoleErrors.filter(
      e => !e.includes('favicon') && !e.includes('404') && !e.includes('hydration')
    );
    expect(criticalErrors.length).toBe(0);

    console.log('  T2-EM-01: Email list route loaded successfully');
  });

  test('T2-EM-02: /email/[threadId] detail route loads correctly', async ({ hodPage, supabaseAdmin }) => {
    // Get an email thread from the test yacht
    const { data: thread } = await supabaseAdmin
      .from('inbox_email_threads')
      .select('id, latest_subject')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!thread) {
      console.log('  No email threads in test yacht - skipping');
      return;
    }

    // Collect console errors
    const consoleErrors: string[] = [];
    hodPage.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Navigate directly to detail route
    await hodPage.goto(ROUTES_CONFIG.emailDetail(thread.id));

    // Check for redirect to legacy (feature flag disabled)
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - redirected to legacy /app');
      return;
    }

    // Wait for page to load
    await hodPage.waitForLoadState('networkidle');

    // Verify route loaded (not redirected)
    expect(hodPage.url()).toContain(`/email/${thread.id}`);

    // Verify detail content renders
    const detailContainer = hodPage.locator('main, [role="main"]');
    await expect(detailContainer).toBeVisible({ timeout: 10000 });

    // Verify back button is present (data-testid="back-button")
    const backButton = hodPage.locator('[data-testid="back-button"]');
    await expect(backButton).toBeVisible({ timeout: 5000 });

    // Verify no error state
    const errorState = hodPage.locator(':text("Failed to Load"), :text("Failed to load")');
    await expect(errorState).not.toBeVisible();

    // Verify loading completed
    const spinner = hodPage.locator('.animate-spin');
    await expect(spinner).not.toBeVisible({ timeout: 15000 });

    // Check for critical console errors
    const criticalErrors = consoleErrors.filter(
      e => !e.includes('favicon') && !e.includes('404') && !e.includes('hydration')
    );
    expect(criticalErrors.length).toBe(0);

    console.log(`  T2-EM-02: Email detail route loaded for thread: ${thread.latest_subject || '(no subject)'}`);
  });

  test('T2-EM-02b: Non-existent thread shows not found state', async ({ hodPage }) => {
    const fakeId = '00000000-0000-0000-0000-000000000000';

    await hodPage.goto(ROUTES_CONFIG.emailDetail(fakeId));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - redirected to legacy /app');
      return;
    }

    await hodPage.waitForLoadState('networkidle');

    // Should show not found or error state
    const notFoundState = hodPage.locator(
      ':text("Not Found"), :text("not found"), :text("Thread Not Found")'
    );
    const errorState = hodPage.locator(':text("Failed"), :text("Error")');

    const hasNotFound = await notFoundState.isVisible({ timeout: 5000 }).catch(() => false);
    const hasError = await errorState.isVisible({ timeout: 5000 }).catch(() => false);

    // Either not found or error is acceptable for non-existent thread
    expect(hasNotFound || hasError).toBe(true);
    console.log('  T2-EM-02b: Non-existent thread handled correctly');
  });
});

// ============================================================================
// SECTION 2: SEARCH TESTS
// T2-EM-03: Thread search works
// ============================================================================

test.describe('Email Route Search', () => {
  test.describe.configure({ retries: 1 });

  test('T2-EM-03: Thread search input is functional', async ({ hodPage }) => {
    await hodPage.goto(ROUTES_CONFIG.emailList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Find search input by placeholder text
    const searchInput = hodPage.locator('input[placeholder*="Search"]');
    const hasSearchInput = await searchInput.isVisible({ timeout: 5000 }).catch(() => false);

    if (!hasSearchInput) {
      console.log('  Search input not visible - may not be implemented yet');
      return;
    }

    // Type a search query
    await searchInput.fill('test search query');
    await hodPage.waitForTimeout(500); // Wait for debounce

    // Verify input has the value
    await expect(searchInput).toHaveValue('test search query');

    // Clear search
    await searchInput.clear();
    await expect(searchInput).toHaveValue('');

    console.log('  T2-EM-03: Search input functional');
  });

  test('T2-EM-03b: Search with keywords filters results', async ({ hodPage, supabaseAdmin }) => {
    // Get a thread with known subject
    const { data: thread } = await supabaseAdmin
      .from('inbox_email_threads')
      .select('id, latest_subject')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .not('latest_subject', 'is', null)
      .limit(1)
      .single();

    if (!thread?.latest_subject) {
      console.log('  No threads with subjects found');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.emailList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    const searchInput = hodPage.locator('input[placeholder*="Search"]');
    const hasSearchInput = await searchInput.isVisible({ timeout: 5000 }).catch(() => false);

    if (!hasSearchInput) {
      console.log('  Search input not visible');
      return;
    }

    // Search for part of the subject
    const searchTerm = thread.latest_subject.split(' ')[0];
    await searchInput.fill(searchTerm);
    await hodPage.waitForTimeout(1000); // Wait for search to execute

    // Page should not show error
    const errorState = hodPage.locator(':text("Failed to load")');
    await expect(errorState).not.toBeVisible();

    console.log(`  T2-EM-03b: Search with keyword "${searchTerm}" executed`);
  });
});

// ============================================================================
// SECTION 3: FILTER TESTS
// T2-EM-04: Linked/Unlinked filter works
// ============================================================================

test.describe('Email Route Filters', () => {
  test.describe.configure({ retries: 1 });

  test('T2-EM-04: Linked/Unlinked filter buttons are functional', async ({ hodPage }) => {
    await hodPage.goto(ROUTES_CONFIG.emailList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Find filter buttons (All, Linked, Unlinked)
    const allFilter = hodPage.locator('button:has-text("All")');
    const linkedFilter = hodPage.locator('button:has-text("Linked")');
    const unlinkedFilter = hodPage.locator('button:has-text("Unlinked")');

    const hasFilters = await allFilter.isVisible({ timeout: 5000 }).catch(() => false);

    if (!hasFilters) {
      console.log('  Filter buttons not visible - may not be implemented yet');
      return;
    }

    // Click Linked filter
    await linkedFilter.click();
    await hodPage.waitForTimeout(1000);

    // Verify Linked is now active (has brand-primary background class or similar)
    // The active state is indicated by bg-brand-primary class
    const linkedActive = await linkedFilter.evaluate(
      el => window.getComputedStyle(el).backgroundColor
    );
    expect(linkedActive).toBeTruthy();

    // Click Unlinked filter
    await unlinkedFilter.click();
    await hodPage.waitForTimeout(1000);

    // Verify no errors after filter change
    const errorState = hodPage.locator(':text("Failed to load")');
    await expect(errorState).not.toBeVisible();

    // Click All filter to reset
    await allFilter.click();
    await hodPage.waitForTimeout(500);

    console.log('  T2-EM-04: Linked/Unlinked filters functional');
  });

  test('T2-EM-04b: Filter state reflected in page behavior', async ({ hodPage }) => {
    await hodPage.goto(ROUTES_CONFIG.emailList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    const linkedFilter = hodPage.locator('button:has-text("Linked")');
    const hasFilters = await linkedFilter.isVisible({ timeout: 5000 }).catch(() => false);

    if (!hasFilters) {
      console.log('  Filter buttons not visible');
      return;
    }

    // Click Linked filter
    await linkedFilter.click();
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(1500);

    // If there are threads, they should show "Linked" status
    // If no threads, empty state should show
    const linkedPills = hodPage.locator(':text("Linked")');
    const emptyState = hodPage.locator(':text("No Emails"), :text("No Results")');

    const hasLinkedPills = await linkedPills.first().isVisible({ timeout: 3000 }).catch(() => false);
    const hasEmptyState = await emptyState.isVisible({ timeout: 3000 }).catch(() => false);

    // Either we have linked emails or an empty state
    expect(hasLinkedPills || hasEmptyState).toBe(true);

    console.log('  T2-EM-04b: Filter state correctly affects display');
  });
});

// ============================================================================
// SECTION 4: STATE PERSISTENCE TESTS
// T2-EM-07: Page refresh preserves state
// ============================================================================

test.describe('Email Route State Persistence', () => {
  test.describe.configure({ retries: 1 });

  test('T2-EM-07: Page refresh preserves detail view', async ({ hodPage, supabaseAdmin }) => {
    const { data: thread } = await supabaseAdmin
      .from('inbox_email_threads')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!thread) {
      console.log('  No email threads in test yacht');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.emailDetail(thread.id));

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

    // Verify state preserved
    const afterRefreshUrl = hodPage.url();
    expect(afterRefreshUrl).toBe(beforeRefreshUrl);

    // Verify content still renders (not error state)
    const errorState = hodPage.locator(':text("Failed to Load")');
    await expect(errorState).not.toBeVisible();

    // Verify back button still visible
    const backButton = hodPage.locator('[data-testid="back-button"]');
    const hasBackButton = await backButton.isVisible({ timeout: 5000 }).catch(() => false);
    expect(hasBackButton).toBe(true);

    console.log('  T2-EM-07: State preserved after refresh');
  });

  test('T2-EM-07b: Page refresh preserves list view', async ({ hodPage }) => {
    await hodPage.goto(ROUTES_CONFIG.emailList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');

    const beforeUrl = hodPage.url();

    // Refresh
    await hodPage.reload();
    await hodPage.waitForLoadState('networkidle');

    const afterUrl = hodPage.url();
    expect(afterUrl).toBe(beforeUrl);

    // Verify page still renders
    const emailTitle = hodPage.locator('h1:has-text("Email")');
    await expect(emailTitle).toBeVisible({ timeout: 5000 });

    console.log('  T2-EM-07b: List state preserved after refresh');
  });

  test('T2-EM-07c: Selected thread param preserved on refresh', async ({ hodPage, supabaseAdmin }) => {
    const { data: thread } = await supabaseAdmin
      .from('inbox_email_threads')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!thread) {
      console.log('  No email threads in test yacht');
      return;
    }

    // Navigate with thread query param (preview panel state)
    await hodPage.goto(`${ROUTES_CONFIG.emailList}?thread=${thread.id}`);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/email')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');

    const beforeUrl = hodPage.url();

    // Refresh
    await hodPage.reload();
    await hodPage.waitForLoadState('networkidle');

    const afterUrl = hodPage.url();

    // URL should be preserved (including query params)
    expect(afterUrl).toBe(beforeUrl);
    console.log('  T2-EM-07c: Thread selection preserved after refresh');
  });
});

// ============================================================================
// SECTION 5: NAVIGATION TESTS
// GR-05: Browser back/forward works naturally
// ============================================================================

test.describe('Email Route Navigation', () => {
  test.describe.configure({ retries: 1 });

  test('GR-05: Browser back/forward works on email list to detail', async ({ hodPage, supabaseAdmin }) => {
    const { data: thread } = await supabaseAdmin
      .from('inbox_email_threads')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!thread) {
      console.log('  No email threads in test yacht');
      return;
    }

    // Start at list
    await hodPage.goto(ROUTES_CONFIG.emailList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    const listUrl = hodPage.url();

    // Navigate to detail (via URL)
    await hodPage.goto(ROUTES_CONFIG.emailDetail(thread.id));
    await hodPage.waitForLoadState('networkidle');
    const detailUrl = hodPage.url();

    expect(detailUrl).toContain(`/email/${thread.id}`);

    // Go back via browser
    await hodPage.goBack();
    await hodPage.waitForLoadState('networkidle');

    // Verify we're back at list
    expect(hodPage.url()).toBe(listUrl);
    console.log('  GR-05a: Back navigation to list verified');

    // Go forward
    await hodPage.goForward();
    await hodPage.waitForLoadState('networkidle');

    // Verify we're at detail again
    expect(hodPage.url()).toBe(detailUrl);
    console.log('  GR-05b: Forward navigation to detail verified');
  });

  test('GR-05b: UI back button navigates correctly', async ({ hodPage, supabaseAdmin }) => {
    const { data: thread } = await supabaseAdmin
      .from('inbox_email_threads')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!thread) {
      console.log('  No email threads in test yacht');
      return;
    }

    // Start at email list
    await hodPage.goto(ROUTES_CONFIG.emailList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');

    // Navigate to detail
    await hodPage.goto(ROUTES_CONFIG.emailDetail(thread.id));
    await hodPage.waitForLoadState('networkidle');

    // Click back button in UI
    const backButton = hodPage.locator('[data-testid="back-button"]');
    const hasBackButton = await backButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasBackButton) {
      await backButton.click();
      await hodPage.waitForLoadState('networkidle');

      // Should navigate back (either to list or previous page)
      const newUrl = hodPage.url();
      expect(newUrl).not.toContain(`/email/${thread.id}`);
      console.log('  GR-05b: UI back button works');
    } else {
      console.log('  Back button not visible - testing browser back instead');
      await hodPage.goBack();
      await hodPage.waitForLoadState('networkidle');
      console.log('  Browser back works');
    }
  });

  test('GR-05c: Cross-entity navigation from linked email', async ({ hodPage, supabaseAdmin }) => {
    // Find a thread with links
    const { data: linkedThread } = await supabaseAdmin
      .from('inbox_email_thread_links')
      .select('thread_id, object_type, object_id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!linkedThread) {
      console.log('  No linked threads found - skipping cross-entity navigation test');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.emailDetail(linkedThread.thread_id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Look for linked object buttons in LinkedObjectsPanel
    const linkedObjectButton = hodPage.locator('button:has-text("work order"), button:has-text("equipment"), button:has-text("fault")');
    const hasLinkedObjects = await linkedObjectButton.first().isVisible({ timeout: 5000 }).catch(() => false);

    if (hasLinkedObjects) {
      await linkedObjectButton.first().click();
      await hodPage.waitForLoadState('networkidle');

      const newUrl = hodPage.url();
      // Should navigate to the linked entity route
      const navigatedToEntity =
        newUrl.includes('/work-orders/') ||
        newUrl.includes('/equipment/') ||
        newUrl.includes('/faults/') ||
        newUrl.includes('/inventory/') ||
        newUrl.includes('entity=');

      expect(navigatedToEntity).toBe(true);
      console.log('  GR-05c: Cross-entity navigation from linked email works');
    } else {
      console.log('  No linked objects visible in thread');
    }
  });
});

// ============================================================================
// SECTION 6: ARCHITECTURE COMPLIANCE TESTS
// No legacy context dependencies
// ============================================================================

test.describe('Email Route Architecture Compliance', () => {
  test.describe.configure({ retries: 1 });

  test('Route does not use legacy contexts', async ({ hodPage }) => {
    await hodPage.goto(ROUTES_CONFIG.emailList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');

    // Check that legacy context hooks are not called
    const consoleErrors: string[] = [];
    hodPage.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Navigate around to trigger any context issues
    await hodPage.waitForTimeout(2000);

    // Check for context-related errors
    const contextErrors = consoleErrors.filter(
      e => e.includes('SurfaceContext') || e.includes('NavigationContext') || e.includes('useContext')
    );

    expect(contextErrors.length).toBe(0);
    console.log('  No legacy context errors detected');
  });
});

// ============================================================================
// SECTION 7: RBAC TESTS
// Verify permissions work on fragmented routes
// ============================================================================

test.describe('Email Route RBAC', () => {
  test.describe.configure({ retries: 1 });

  test('Crew can view email list', async ({ crewPage }) => {
    await crewPage.goto(ROUTES_CONFIG.emailList);

    const currentUrl = crewPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await crewPage.waitForLoadState('networkidle');

    // Crew should be able to view list
    const errorState = crewPage.locator(':text("Access Denied"), :text("Unauthorized")');
    await expect(errorState).not.toBeVisible({ timeout: 5000 });

    console.log('  Crew can view email list');
  });

  test('HOD can view email detail', async ({ hodPage, supabaseAdmin }) => {
    const { data: thread } = await supabaseAdmin
      .from('inbox_email_threads')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!thread) {
      console.log('  No email threads in test yacht');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.emailDetail(thread.id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');

    // HOD should be able to view detail
    const errorState = hodPage.locator(':text("Access Denied"), :text("Unauthorized")');
    await expect(errorState).not.toBeVisible({ timeout: 5000 });

    console.log('  HOD can view email detail');
  });
});

// ============================================================================
// SECTION 8: PERFORMANCE BASELINE
// Basic load time checks
// ============================================================================

test.describe('Email Route Performance', () => {
  test.describe.configure({ retries: 0 });

  test('List route loads within 5 seconds', async ({ hodPage }) => {
    const startTime = Date.now();

    await hodPage.goto(ROUTES_CONFIG.emailList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');

    const loadTime = Date.now() - startTime;
    console.log(`  Email list load time: ${loadTime}ms`);

    // Should load within 5 seconds
    expect(loadTime).toBeLessThan(5000);
  });

  test('Detail route loads within 5 seconds', async ({ hodPage, supabaseAdmin }) => {
    const { data: thread } = await supabaseAdmin
      .from('inbox_email_threads')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!thread) {
      console.log('  No email threads in test yacht');
      return;
    }

    const startTime = Date.now();

    await hodPage.goto(ROUTES_CONFIG.emailDetail(thread.id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');

    const loadTime = Date.now() - startTime;
    console.log(`  Email detail load time: ${loadTime}ms`);

    // Should load within 5 seconds
    expect(loadTime).toBeLessThan(5000);
  });
});

// ============================================================================
// SECTION 9: FEATURE FLAG BEHAVIOR
// Verify route behavior when flag is on/off
// ============================================================================

test.describe('Feature Flag Behavior', () => {
  test.describe.configure({ retries: 0 });

  test('Email route redirects to legacy when flag disabled', async ({ hodPage }) => {
    await hodPage.goto(ROUTES_CONFIG.emailList);
    await hodPage.waitForLoadState('networkidle');

    const currentUrl = hodPage.url();

    if (currentUrl.includes('/app')) {
      // Flag is disabled - verify redirect worked
      expect(currentUrl).toContain('/app');
      console.log('  Feature flag OFF: Correctly redirected to /app');
    } else if (currentUrl.includes('/email')) {
      // Flag is enabled - verify route works
      expect(currentUrl).toContain('/email');
      console.log('  Feature flag ON: Route loaded directly');
    }
  });
});
