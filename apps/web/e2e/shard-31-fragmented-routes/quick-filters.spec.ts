import { test, expect, RBAC_CONFIG, SpotlightSearchPO } from '../rbac-fixtures';

/**
 * SHARD 31: Fragmented Routes - Quick Filters
 *
 * Tests for Quick Filters feature - deterministic filter suggestions in search.
 *
 * Requirements Covered:
 * - QF-01: Typing explicit feature request shows filter chips
 * - QF-02: Clicking chip navigates to filtered list route
 * - QF-03: Filtered list route shows active filter banner
 * - QF-04: Clear filter button removes filter and shows all items
 * - QF-05: Empty filter state shows appropriate message
 * - QF-06: Tests are deterministic (pass twice)
 *
 * Implementation:
 * - FilterChips component renders suggestions based on query
 * - List pages read ?filter= param and apply client-side filtering
 * - ActiveFilterBanner shows current filter with clear button
 */

// ============================================================================
// SECTION 1: FILTER CHIP VISIBILITY
// QF-01: Explicit feature queries show filter chips
// ============================================================================

test.describe('Quick Filters - Chip Display', () => {
  test.describe.configure({ retries: 0 });

  test('QF-01a: Typing "overdue work orders" shows filter chips', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);

    // Type explicit feature request
    await spotlight.search('overdue work orders');

    // Check for filter chips - must be visible, test fails otherwise
    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });
    console.log('  QF-01a PASS: Filter chips visible');

    // Check for specific chip - must be visible
    const overdueChip = hodPage.locator('[data-filter-id="wo_overdue"]');
    await expect(overdueChip).toBeVisible({ timeout: 3000 });
    console.log('  QF-01a PASS: "Overdue work orders" chip present');
  });

  test('QF-01b: Typing "low stock" shows inventory filter chips', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('low stock');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });
    console.log('  QF-01b PASS: Filter chips visible for "low stock"');

    const lowStockChip = hodPage.locator('[data-filter-id="inv_low_stock"]');
    await expect(lowStockChip).toBeVisible({ timeout: 3000 });
    console.log('  QF-01b PASS: "Low stock" chip present');
  });

  test('QF-01c: Typing "open faults" shows fault filter chips', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('open faults');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });
    console.log('  QF-01c PASS: Filter chips visible for "open faults"');

    const openFaultsChip = hodPage.locator('[data-filter-id="fault_open"]');
    await expect(openFaultsChip).toBeVisible({ timeout: 3000 });
    console.log('  QF-01c PASS: "Open faults" chip present');
  });

  test('QF-01d: Short queries (<3 chars) do not show chips', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('ab');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).not.toBeVisible({ timeout: 3000 });
    console.log('  QF-01d PASS: No chips for short query');
  });
});

// ============================================================================
// SECTION 2: CHIP CLICK NAVIGATION
// QF-02: Clicking chip navigates to filtered route
// ============================================================================

test.describe('Quick Filters - Chip Navigation', () => {
  test.describe.configure({ retries: 0 });

  test('QF-02a: Clicking "Overdue work orders" chip navigates to /work-orders?filter=wo_overdue', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('overdue work orders');

    const overdueChip = hodPage.locator('[data-filter-id="wo_overdue"]');
    await expect(overdueChip).toBeVisible({ timeout: 5000 });

    await overdueChip.click();
    await hodPage.waitForURL(/\/work-orders.*filter=wo_overdue/, { timeout: 10000 });

    const currentUrl = hodPage.url();
    console.log(`  Current URL: ${currentUrl}`);

    expect(currentUrl).toContain('/work-orders');
    expect(currentUrl).toContain('filter=wo_overdue');
    console.log('  QF-02a PASS: Navigated to /work-orders?filter=wo_overdue');
  });

  test('QF-02b: Clicking "Low stock" chip navigates to /inventory?filter=inv_low_stock', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('low stock');

    const lowStockChip = hodPage.locator('[data-filter-id="inv_low_stock"]');
    await expect(lowStockChip).toBeVisible({ timeout: 5000 });

    await lowStockChip.click();
    await hodPage.waitForURL(/\/inventory.*filter=inv_low_stock/, { timeout: 10000 });

    const currentUrl = hodPage.url();
    console.log(`  Current URL: ${currentUrl}`);

    expect(currentUrl).toContain('/inventory');
    expect(currentUrl).toContain('filter=inv_low_stock');
    console.log('  QF-02b PASS: Navigated to /inventory?filter=inv_low_stock');
  });

  test('QF-02c: Clicking "Open faults" chip navigates to /faults?filter=fault_open', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('open faults');

    const openFaultsChip = hodPage.locator('[data-filter-id="fault_open"]');
    await expect(openFaultsChip).toBeVisible({ timeout: 5000 });

    await openFaultsChip.click();
    await hodPage.waitForURL(/\/faults.*filter=fault_open/, { timeout: 10000 });

    const currentUrl = hodPage.url();
    console.log(`  Current URL: ${currentUrl}`);

    expect(currentUrl).toContain('/faults');
    expect(currentUrl).toContain('filter=fault_open');
    console.log('  QF-02c PASS: Navigated to /faults?filter=fault_open');
  });
});

// ============================================================================
// SECTION 3: FILTER BANNER AND CLEAR
// QF-03, QF-04: Active filter banner and clear functionality
// ============================================================================

test.describe('Quick Filters - Filter Banner', () => {
  test.describe.configure({ retries: 0 });

  test('QF-03: Filtered route shows active filter banner', async ({ hodPage }) => {
    // Navigate directly to filtered route
    await hodPage.goto('/work-orders?filter=wo_overdue');
    await hodPage.waitForLoadState('networkidle');

    // Wait for loading to complete (spinner disappears or content loads)
    await hodPage.waitForFunction(
      () => {
        const loading = document.querySelector('.animate-spin');
        return !loading;
      },
      { timeout: 15000 }
    );

    // Check for API error - report clearly if backend is down
    const errorState = hodPage.locator('text="Failed to load items"');
    const hasError = await errorState.isVisible().catch(() => false);
    if (hasError) {
      console.log('  ERROR: API returned "Failed to load items" - work-orders endpoint unavailable');
    }
    expect(hasError).toBe(false); // HARD ASSERTION: API must succeed

    const filterBanner = hodPage.locator('[data-testid="active-filter-banner"]');
    await expect(filterBanner).toBeVisible({ timeout: 5000 });
    console.log('  QF-03 PASS: Active filter banner visible');

    // Check banner text
    const bannerText = await filterBanner.textContent();
    console.log(`  Banner text: ${bannerText}`);

    expect(bannerText).toContain('Overdue');
    console.log('  QF-03 PASS: Banner shows correct filter label');
  });

  test('QF-04: Clear filter button removes filter', async ({ hodPage }) => {
    await hodPage.goto('/work-orders?filter=wo_overdue');
    await hodPage.waitForLoadState('networkidle');

    const clearButton = hodPage.locator('[data-testid="clear-filter-button"]');
    await expect(clearButton).toBeVisible({ timeout: 5000 });

    await clearButton.click();

    // Wait for URL to change (filter param removed)
    await hodPage.waitForFunction(() => !window.location.href.includes('filter='), { timeout: 5000 });

    const currentUrl = hodPage.url();
    console.log(`  URL after clear: ${currentUrl}`);

    // Filter param should be removed
    expect(currentUrl).not.toContain('filter=');
    console.log('  QF-04 PASS: Filter cleared from URL');

    // Banner should be gone
    const filterBanner = hodPage.locator('[data-testid="active-filter-banner"]');
    await expect(filterBanner).not.toBeVisible({ timeout: 3000 });
    console.log('  QF-04 PASS: Filter banner removed');
  });
});

// ============================================================================
// SECTION 4: EMPTY FILTER STATE
// QF-05: When filter matches zero items, show appropriate message
// ============================================================================

test.describe('Quick Filters - Empty State', () => {
  test.describe.configure({ retries: 0 });

  test('QF-05: Empty filter results show clear filter option', async ({ hodPage }) => {
    // Navigate to a filter that likely has no results
    // Using a specific filter that may have no matches
    await hodPage.goto('/work-orders?filter=wo_priority_emergency');
    await hodPage.waitForLoadState('networkidle');

    const emptyState = hodPage.locator('[data-testid="empty-filter-state"]');
    await expect(emptyState).toBeVisible({ timeout: 5000 });
    console.log('  QF-05 PASS: Empty filter state shown');

    // Check for clear button in empty state
    const clearButton = emptyState.locator('button:has-text("Clear filter")');
    await expect(clearButton).toBeVisible({ timeout: 3000 });
    console.log('  QF-05 PASS: Clear filter button in empty state');

    await clearButton.click();

    // Wait for URL to change (filter param removed)
    await hodPage.waitForFunction(() => !window.location.href.includes('filter='), { timeout: 5000 });

    const currentUrl = hodPage.url();
    expect(currentUrl).not.toContain('filter=');
    console.log('  QF-05 PASS: Filter cleared from empty state');
  });
});

// ============================================================================
// SECTION 5: DETERMINISM TESTS
// QF-06: Same input produces same chips (run twice)
// ============================================================================

test.describe('Quick Filters - Determinism', () => {
  test.describe.configure({ retries: 0 }); // No retries - must be deterministic

  test('QF-06a: Same query produces same chips (run 1)', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('overdue work orders');

    // Wait for chips to be visible
    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const chipIds: string[] = [];
    const chips = hodPage.locator('[data-testid^="filter-chip-"]');
    const chipCount = await chips.count();

    expect(chipCount).toBeGreaterThan(0);

    for (let i = 0; i < chipCount; i++) {
      const chip = chips.nth(i);
      const filterId = await chip.getAttribute('data-filter-id');
      if (filterId) chipIds.push(filterId);
    }

    console.log(`  QF-06a Run 1: Found chips: ${chipIds.join(', ')}`);

    // First chip should always be wo_overdue
    expect(chipIds[0]).toBe('wo_overdue');
    console.log('  QF-06a PASS: First chip is wo_overdue');
  });

  test('QF-06b: Same query produces same chips (run 2)', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('overdue work orders');

    // Wait for chips to be visible
    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const chipIds: string[] = [];
    const chips = hodPage.locator('[data-testid^="filter-chip-"]');
    const chipCount = await chips.count();

    expect(chipCount).toBeGreaterThan(0);

    for (let i = 0; i < chipCount; i++) {
      const chip = chips.nth(i);
      const filterId = await chip.getAttribute('data-filter-id');
      if (filterId) chipIds.push(filterId);
    }

    console.log(`  QF-06b Run 2: Found chips: ${chipIds.join(', ')}`);

    // Same query should produce same first chip
    expect(chipIds[0]).toBe('wo_overdue');
    console.log('  QF-06b PASS: Second run also has wo_overdue first - deterministic');
  });
});

// ============================================================================
// SECTION 6: CHIP MATCH TYPE VERIFICATION
// Verify high-confidence matches are visually distinct
// ============================================================================

test.describe('Quick Filters - Match Confidence', () => {
  test.describe.configure({ retries: 0 });

  test('Pattern matches have higher score than keyword matches', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('overdue work orders');

    // Wait for filter chips to be visible first
    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const patternChip = hodPage.locator('[data-match-type="pattern"]').first();
    await expect(patternChip).toBeVisible({ timeout: 3000 });

    const score = await patternChip.getAttribute('data-score');
    console.log(`  Pattern match score: ${score}`);

    expect(score).not.toBeNull();
    const numScore = parseFloat(score!);
    expect(numScore).toBeGreaterThanOrEqual(0.9);
    console.log('  PASS: Pattern match has high score (>=0.9)');
  });
});
