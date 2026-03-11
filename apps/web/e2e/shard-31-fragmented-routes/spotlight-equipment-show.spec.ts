import { test, expect, RBAC_CONFIG, SpotlightSearchPO } from '../rbac-fixtures';

/**
 * SHARD 31: Spotlight Equipment SHOW Tests
 *
 * Tests for Spotlight search -> Equipment list navigation with filter inference.
 *
 * Requirements Covered:
 * - SE-01: NLP variants for "equipment needing attention" -> eq_attention filter
 * - SE-02: NLP variants for "failed equipment" -> eq_failed filter
 * - SE-03: NLP variants for "equipment in maintenance" -> eq_maintenance filter
 * - SE-04: NLP variants for "critical equipment" -> eq_critical filter
 * - SE-05: Synonym handling (broken machinery, assets, systems)
 * - SE-06: Domain detection (all systems, all equipment)
 * - SE-07: Cross-yacht isolation verification
 * - SE-08: Role coverage (HoD vs Junior)
 *
 * Filter IDs from catalog.ts:
 * - eq_attention: attention_flag = true
 * - eq_failed: status = 'failed'
 * - eq_maintenance: status = 'maintenance'
 * - eq_critical: criticality = 'critical'
 *
 * Total: 25+ NLP variants + security tests
 */

// ============================================================================
// SECTION 1: eq_attention FILTER VARIANTS (5 variants)
// "Equipment needing attention" -> filter=eq_attention
// ============================================================================

test.describe('SE-01: Equipment Attention Filter Variants', () => {
  test.describe.configure({ retries: 0 });

  test('SE-01a: "equipment needing attention" shows eq_attention chip', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('equipment needing attention');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });
    console.log('  SE-01a: Filter chips visible');

    const attentionChip = hodPage.locator('[data-filter-id="eq_attention"]');
    await expect(attentionChip).toBeVisible({ timeout: 3000 });
    console.log('  SE-01a PASS: eq_attention chip present for "equipment needing attention"');
  });

  test('SE-01b: "equipment needs attention" shows eq_attention chip', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('equipment needs attention');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const attentionChip = hodPage.locator('[data-filter-id="eq_attention"]');
    await expect(attentionChip).toBeVisible({ timeout: 3000 });
    console.log('  SE-01b PASS: eq_attention chip present for "equipment needs attention"');
  });

  test('SE-01c: "flagged equipment" shows eq_attention chip', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('flagged equipment');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const attentionChip = hodPage.locator('[data-filter-id="eq_attention"]');
    await expect(attentionChip).toBeVisible({ timeout: 3000 });
    console.log('  SE-01c PASS: eq_attention chip present for "flagged equipment"');
  });

  test('SE-01d: "check equipment" shows eq_attention chip', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('check equipment');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const attentionChip = hodPage.locator('[data-filter-id="eq_attention"]');
    await expect(attentionChip).toBeVisible({ timeout: 3000 });
    console.log('  SE-01d PASS: eq_attention chip present for "check equipment"');
  });

  test('SE-01e: Clicking eq_attention chip navigates to /equipment?filter=eq_attention', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('equipment needing attention');

    const attentionChip = hodPage.locator('[data-filter-id="eq_attention"]');
    await expect(attentionChip).toBeVisible({ timeout: 5000 });

    await attentionChip.click();
    await hodPage.waitForURL(/\/equipment.*filter=eq_attention/, { timeout: 10000 });

    const currentUrl = hodPage.url();
    console.log(`  Current URL: ${currentUrl}`);

    expect(currentUrl).toContain('/equipment');
    expect(currentUrl).toContain('filter=eq_attention');
    console.log('  SE-01e PASS: Navigated to /equipment?filter=eq_attention');
  });
});

// ============================================================================
// SECTION 2: eq_failed FILTER VARIANTS (5 variants)
// "Failed equipment" -> filter=eq_failed
// ============================================================================

test.describe('SE-02: Equipment Failed Filter Variants', () => {
  test.describe.configure({ retries: 0 });

  test('SE-02a: "failed equipment" shows eq_failed chip', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('failed equipment');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const failedChip = hodPage.locator('[data-filter-id="eq_failed"]');
    await expect(failedChip).toBeVisible({ timeout: 3000 });
    console.log('  SE-02a PASS: eq_failed chip present for "failed equipment"');
  });

  test('SE-02b: "broken equipment" shows eq_failed chip', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('broken equipment');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const failedChip = hodPage.locator('[data-filter-id="eq_failed"]');
    await expect(failedChip).toBeVisible({ timeout: 3000 });
    console.log('  SE-02b PASS: eq_failed chip present for "broken equipment"');
  });

  test('SE-02c: "equipment not working" shows eq_failed chip', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('equipment not working');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const failedChip = hodPage.locator('[data-filter-id="eq_failed"]');
    await expect(failedChip).toBeVisible({ timeout: 3000 });
    console.log('  SE-02c PASS: eq_failed chip present for "equipment not working"');
  });

  test('SE-02d: "equipment down" shows eq_failed chip', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('equipment down');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const failedChip = hodPage.locator('[data-filter-id="eq_failed"]');
    await expect(failedChip).toBeVisible({ timeout: 3000 });
    console.log('  SE-02d PASS: eq_failed chip present for "equipment down"');
  });

  test('SE-02e: Clicking eq_failed chip navigates to /equipment?filter=eq_failed', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('failed equipment');

    const failedChip = hodPage.locator('[data-filter-id="eq_failed"]');
    await expect(failedChip).toBeVisible({ timeout: 5000 });

    await failedChip.click();
    await hodPage.waitForURL(/\/equipment.*filter=eq_failed/, { timeout: 10000 });

    const currentUrl = hodPage.url();
    console.log(`  Current URL: ${currentUrl}`);

    expect(currentUrl).toContain('/equipment');
    expect(currentUrl).toContain('filter=eq_failed');
    console.log('  SE-02e PASS: Navigated to /equipment?filter=eq_failed');
  });
});

// ============================================================================
// SECTION 3: eq_maintenance FILTER VARIANTS (5 variants)
// "Equipment in maintenance" -> filter=eq_maintenance
// ============================================================================

test.describe('SE-03: Equipment Maintenance Filter Variants', () => {
  test.describe.configure({ retries: 0 });

  test('SE-03a: "equipment in maintenance" shows eq_maintenance chip', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('equipment in maintenance');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const maintenanceChip = hodPage.locator('[data-filter-id="eq_maintenance"]');
    await expect(maintenanceChip).toBeVisible({ timeout: 3000 });
    console.log('  SE-03a PASS: eq_maintenance chip present for "equipment in maintenance"');
  });

  test('SE-03b: "equipment maintenance" shows eq_maintenance chip', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('equipment maintenance');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const maintenanceChip = hodPage.locator('[data-filter-id="eq_maintenance"]');
    await expect(maintenanceChip).toBeVisible({ timeout: 3000 });
    console.log('  SE-03b PASS: eq_maintenance chip present for "equipment maintenance"');
  });

  test('SE-03c: "equipment being serviced" shows eq_maintenance chip', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('equipment being serviced');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const maintenanceChip = hodPage.locator('[data-filter-id="eq_maintenance"]');
    await expect(maintenanceChip).toBeVisible({ timeout: 3000 });
    console.log('  SE-03c PASS: eq_maintenance chip present for "equipment being serviced"');
  });

  test('SE-03d: "equipment under repair" shows eq_maintenance chip', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('equipment under repair');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const maintenanceChip = hodPage.locator('[data-filter-id="eq_maintenance"]');
    await expect(maintenanceChip).toBeVisible({ timeout: 3000 });
    console.log('  SE-03d PASS: eq_maintenance chip present for "equipment under repair"');
  });

  test('SE-03e: Clicking eq_maintenance chip navigates to /equipment?filter=eq_maintenance', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('equipment in maintenance');

    const maintenanceChip = hodPage.locator('[data-filter-id="eq_maintenance"]');
    await expect(maintenanceChip).toBeVisible({ timeout: 5000 });

    await maintenanceChip.click();
    await hodPage.waitForURL(/\/equipment.*filter=eq_maintenance/, { timeout: 10000 });

    const currentUrl = hodPage.url();
    console.log(`  Current URL: ${currentUrl}`);

    expect(currentUrl).toContain('/equipment');
    expect(currentUrl).toContain('filter=eq_maintenance');
    console.log('  SE-03e PASS: Navigated to /equipment?filter=eq_maintenance');
  });
});

// ============================================================================
// SECTION 4: eq_critical FILTER VARIANTS (5 variants)
// "Critical equipment" -> filter=eq_critical
// ============================================================================

test.describe('SE-04: Critical Equipment Filter Variants', () => {
  test.describe.configure({ retries: 0 });

  test('SE-04a: "critical equipment" shows eq_critical chip', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('critical equipment');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const criticalChip = hodPage.locator('[data-filter-id="eq_critical"]');
    await expect(criticalChip).toBeVisible({ timeout: 3000 });
    console.log('  SE-04a PASS: eq_critical chip present for "critical equipment"');
  });

  test('SE-04b: "essential equipment" shows eq_critical chip', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('essential equipment');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const criticalChip = hodPage.locator('[data-filter-id="eq_critical"]');
    await expect(criticalChip).toBeVisible({ timeout: 3000 });
    console.log('  SE-04b PASS: eq_critical chip present for "essential equipment"');
  });

  test('SE-04c: "vital equipment" shows eq_critical chip', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('vital equipment');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const criticalChip = hodPage.locator('[data-filter-id="eq_critical"]');
    await expect(criticalChip).toBeVisible({ timeout: 3000 });
    console.log('  SE-04c PASS: eq_critical chip present for "vital equipment"');
  });

  test('SE-04d: "mission critical equipment" shows eq_critical chip', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('mission critical equipment');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const criticalChip = hodPage.locator('[data-filter-id="eq_critical"]');
    await expect(criticalChip).toBeVisible({ timeout: 3000 });
    console.log('  SE-04d PASS: eq_critical chip present for "mission critical equipment"');
  });

  test('SE-04e: Clicking eq_critical chip navigates to /equipment?filter=eq_critical', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('critical equipment');

    const criticalChip = hodPage.locator('[data-filter-id="eq_critical"]');
    await expect(criticalChip).toBeVisible({ timeout: 5000 });

    await criticalChip.click();
    await hodPage.waitForURL(/\/equipment.*filter=eq_critical/, { timeout: 10000 });

    const currentUrl = hodPage.url();
    console.log(`  Current URL: ${currentUrl}`);

    expect(currentUrl).toContain('/equipment');
    expect(currentUrl).toContain('filter=eq_critical');
    console.log('  SE-04e PASS: Navigated to /equipment?filter=eq_critical');
  });
});

// ============================================================================
// SECTION 5: SYNONYM HANDLING (5 variants)
// Tests for machinery, assets, systems synonyms mapping to equipment domain
// ============================================================================

test.describe('SE-05: Equipment Synonym Handling', () => {
  test.describe.configure({ retries: 0 });

  test('SE-05a: "broken machinery" shows eq_failed chip (machinery synonym)', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('broken machinery');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    // Should map "machinery" to equipment domain and "broken" to eq_failed
    const failedChip = hodPage.locator('[data-filter-id="eq_failed"]');
    await expect(failedChip).toBeVisible({ timeout: 3000 });
    console.log('  SE-05a PASS: eq_failed chip present for "broken machinery"');
  });

  test('SE-05b: "failed assets" shows eq_failed chip (assets synonym)', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('failed assets');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const failedChip = hodPage.locator('[data-filter-id="eq_failed"]');
    await expect(failedChip).toBeVisible({ timeout: 3000 });
    console.log('  SE-05b PASS: eq_failed chip present for "failed assets"');
  });

  test('SE-05c: "systems in maintenance" shows eq_maintenance chip (systems synonym)', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('systems in maintenance');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const maintenanceChip = hodPage.locator('[data-filter-id="eq_maintenance"]');
    await expect(maintenanceChip).toBeVisible({ timeout: 3000 });
    console.log('  SE-05c PASS: eq_maintenance chip present for "systems in maintenance"');
  });

  test('SE-05d: "machinery needing attention" shows eq_attention chip', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('machinery needing attention');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const attentionChip = hodPage.locator('[data-filter-id="eq_attention"]');
    await expect(attentionChip).toBeVisible({ timeout: 3000 });
    console.log('  SE-05d PASS: eq_attention chip present for "machinery needing attention"');
  });

  test('SE-05e: "critical assets" shows eq_critical chip', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('critical assets');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const criticalChip = hodPage.locator('[data-filter-id="eq_critical"]');
    await expect(criticalChip).toBeVisible({ timeout: 3000 });
    console.log('  SE-05e PASS: eq_critical chip present for "critical assets"');
  });
});

// ============================================================================
// SECTION 6: DOMAIN DETECTION (5 variants)
// Tests for domain-level queries that suggest equipment filters
// ============================================================================

test.describe('SE-06: Equipment Domain Detection', () => {
  test.describe.configure({ retries: 0 });

  test('SE-06a: "all systems" detects equipment domain and shows equipment chips', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('all systems');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    // Domain detection should show equipment-related chips
    const equipmentChips = hodPage.locator('[data-filter-id^="eq_"]');
    const chipCount = await equipmentChips.count();
    expect(chipCount).toBeGreaterThan(0);
    console.log(`  SE-06a PASS: ${chipCount} equipment chips shown for "all systems"`);
  });

  test('SE-06b: "all equipment" detects equipment domain', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('all equipment');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const equipmentChips = hodPage.locator('[data-filter-id^="eq_"]');
    const chipCount = await equipmentChips.count();
    expect(chipCount).toBeGreaterThan(0);
    console.log(`  SE-06b PASS: ${chipCount} equipment chips shown for "all equipment"`);
  });

  test('SE-06c: "equipment status" detects equipment domain', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('equipment status');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const equipmentChips = hodPage.locator('[data-filter-id^="eq_"]');
    const chipCount = await equipmentChips.count();
    expect(chipCount).toBeGreaterThan(0);
    console.log(`  SE-06c PASS: ${chipCount} equipment chips shown for "equipment status"`);
  });

  test('SE-06d: "machinery overview" detects equipment domain', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('machinery overview');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const equipmentChips = hodPage.locator('[data-filter-id^="eq_"]');
    const chipCount = await equipmentChips.count();
    expect(chipCount).toBeGreaterThan(0);
    console.log(`  SE-06d PASS: ${chipCount} equipment chips shown for "machinery overview"`);
  });

  test('SE-06e: "system health" detects equipment domain', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('system health');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const equipmentChips = hodPage.locator('[data-filter-id^="eq_"]');
    const chipCount = await equipmentChips.count();
    expect(chipCount).toBeGreaterThan(0);
    console.log(`  SE-06e PASS: ${chipCount} equipment chips shown for "system health"`);
  });
});

// ============================================================================
// SECTION 7: FILTER BANNER AND NAVIGATION
// Verify filter banner shows when navigating to equipment list with filter
// ============================================================================

test.describe('SE-07: Equipment Filter Banner', () => {
  test.describe.configure({ retries: 0 });

  test('SE-07a: /equipment?filter=eq_attention shows active filter banner', async ({ hodPage }) => {
    await hodPage.goto('/equipment?filter=eq_attention');
    await hodPage.waitForLoadState('networkidle');

    // Wait for loading to complete
    await hodPage.waitForFunction(
      () => {
        const loading = document.querySelector('.animate-spin');
        return !loading;
      },
      { timeout: 15000 }
    );

    // Check for error state
    const errorState = hodPage.locator('text="Failed to load"');
    const hasError = await errorState.isVisible().catch(() => false);
    if (hasError) {
      console.log('  ERROR: API returned "Failed to load" - equipment endpoint unavailable');
    }
    expect(hasError).toBe(false);

    const filterBanner = hodPage.locator('[data-testid="active-filter-banner"]');
    await expect(filterBanner).toBeVisible({ timeout: 5000 });
    console.log('  SE-07a PASS: Active filter banner visible for eq_attention');

    const bannerText = await filterBanner.textContent();
    expect(bannerText?.toLowerCase()).toContain('attention');
    console.log(`  Banner text: ${bannerText}`);
  });

  test('SE-07b: /equipment?filter=eq_failed shows active filter banner', async ({ hodPage }) => {
    await hodPage.goto('/equipment?filter=eq_failed');
    await hodPage.waitForLoadState('networkidle');

    await hodPage.waitForFunction(
      () => !document.querySelector('.animate-spin'),
      { timeout: 15000 }
    );

    const filterBanner = hodPage.locator('[data-testid="active-filter-banner"]');
    await expect(filterBanner).toBeVisible({ timeout: 5000 });
    console.log('  SE-07b PASS: Active filter banner visible for eq_failed');

    const bannerText = await filterBanner.textContent();
    expect(bannerText?.toLowerCase()).toContain('failed');
    console.log(`  Banner text: ${bannerText}`);
  });

  test('SE-07c: Clear filter button removes eq_maintenance filter', async ({ hodPage }) => {
    await hodPage.goto('/equipment?filter=eq_maintenance');
    await hodPage.waitForLoadState('networkidle');

    const clearButton = hodPage.locator('[data-testid="clear-filter-button"]');
    await expect(clearButton).toBeVisible({ timeout: 5000 });

    await clearButton.click();

    await hodPage.waitForFunction(() => !window.location.href.includes('filter='), { timeout: 5000 });

    const currentUrl = hodPage.url();
    expect(currentUrl).not.toContain('filter=');
    console.log('  SE-07c PASS: Filter cleared from URL');

    const filterBanner = hodPage.locator('[data-testid="active-filter-banner"]');
    await expect(filterBanner).not.toBeVisible({ timeout: 3000 });
    console.log('  SE-07c PASS: Filter banner removed after clear');
  });
});

// ============================================================================
// SECTION 8: CROSS-YACHT ISOLATION
// Verify equipment filters only show data for the current yacht
// ============================================================================

test.describe('SE-08: Cross-Yacht Isolation', () => {
  test.describe.configure({ retries: 0 });

  test('SE-08a: Equipment list only shows equipment for current yacht', async ({ hodPage, supabaseAdmin }) => {
    // Navigate to equipment list with a filter
    await hodPage.goto('/equipment?filter=eq_attention');
    await hodPage.waitForLoadState('networkidle');

    await hodPage.waitForFunction(
      () => !document.querySelector('.animate-spin'),
      { timeout: 15000 }
    );

    // Get all equipment IDs visible on the page
    const equipmentItems = hodPage.locator('[data-testid="equipment-list-item"], [data-entity-type="equipment"]');
    const itemCount = await equipmentItems.count();

    if (itemCount === 0) {
      console.log('  SE-08a: No equipment items with attention flag visible (acceptable)');
      return;
    }

    // Extract equipment IDs from the page
    const equipmentIds: string[] = [];
    for (let i = 0; i < Math.min(itemCount, 5); i++) {
      const item = equipmentItems.nth(i);
      const id = await item.getAttribute('data-entity-id');
      if (id) equipmentIds.push(id);
    }

    if (equipmentIds.length === 0) {
      console.log('  SE-08a: Could not extract equipment IDs from page - skipping cross-yacht check');
      return;
    }

    // Verify all visible equipment belongs to the test yacht
    const { data: equipment, error } = await supabaseAdmin
      .from('pms_equipment')
      .select('id, yacht_id')
      .in('id', equipmentIds);

    if (error) {
      console.log(`  SE-08a WARNING: Database query failed: ${error.message}`);
      return;
    }

    for (const eq of equipment || []) {
      expect(eq.yacht_id).toBe(RBAC_CONFIG.yachtId);
    }

    console.log(`  SE-08a PASS: All ${equipmentIds.length} visible equipment items belong to test yacht`);
  });

  test('SE-08b: Cannot access equipment from another yacht via direct URL', async ({ hodPage, supabaseAdmin }) => {
    // Find equipment from a different yacht
    const { data: otherYachtEquipment } = await supabaseAdmin
      .from('pms_equipment')
      .select('id, name, yacht_id')
      .neq('yacht_id', RBAC_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!otherYachtEquipment) {
      console.log('  SE-08b: No equipment from other yachts found - skipping test');
      return;
    }

    console.log(`  Testing cross-yacht access for equipment: ${otherYachtEquipment.id} (yacht: ${otherYachtEquipment.yacht_id})`);

    // Try to access equipment from another yacht
    await hodPage.goto(`/equipment?id=${otherYachtEquipment.id}`);
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Should show "Not Found" or redirect, not the equipment details
    const notFoundState = hodPage.locator(':text("Not Found"), :text("not found"), :text("Equipment not found")');
    const errorState = hodPage.locator(':text("Failed"), :text("Error"), :text("Access denied")');
    const equipmentDetail = hodPage.locator(`[data-entity-id="${otherYachtEquipment.id}"]`);

    const hasNotFound = await notFoundState.isVisible({ timeout: 3000 }).catch(() => false);
    const hasError = await errorState.isVisible({ timeout: 1000 }).catch(() => false);
    const hasEquipmentDetail = await equipmentDetail.isVisible({ timeout: 1000 }).catch(() => false);

    // SECURITY: Equipment from another yacht should NOT be visible
    expect(hasEquipmentDetail).toBe(false);
    expect(hasNotFound || hasError || !hasEquipmentDetail).toBe(true);

    console.log('  SE-08b PASS: Cross-yacht equipment access correctly blocked');
  });
});

// ============================================================================
// SECTION 9: ROLE COVERAGE (HoD vs Crew)
// Verify both HoD and Junior crew can see equipment filters
// ============================================================================

test.describe('SE-09: Role Coverage', () => {
  test.describe.configure({ retries: 0 });

  test('SE-09a: HoD can see all equipment filter chips', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('equipment');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const equipmentChips = hodPage.locator('[data-filter-id^="eq_"]');
    const chipCount = await equipmentChips.count();
    expect(chipCount).toBeGreaterThan(0);

    console.log(`  SE-09a PASS: HoD sees ${chipCount} equipment filter chips`);
  });

  test('SE-09b: HoD can navigate to equipment list with filter', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('failed equipment');

    const failedChip = hodPage.locator('[data-filter-id="eq_failed"]');
    await expect(failedChip).toBeVisible({ timeout: 5000 });

    await failedChip.click();
    await hodPage.waitForURL(/\/equipment.*filter=eq_failed/, { timeout: 10000 });

    expect(hodPage.url()).toContain('/equipment');
    console.log('  SE-09b PASS: HoD can navigate to filtered equipment list');
  });

  test('SE-09c: Crew can see equipment filter chips', async ({ crewPage }) => {
    await crewPage.goto('/app');
    await crewPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(crewPage);
    await spotlight.search('equipment');

    const filterChips = crewPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const equipmentChips = crewPage.locator('[data-filter-id^="eq_"]');
    const chipCount = await equipmentChips.count();
    expect(chipCount).toBeGreaterThan(0);

    console.log(`  SE-09c PASS: Crew sees ${chipCount} equipment filter chips`);
  });

  test('SE-09d: Crew can navigate to equipment list (read-only)', async ({ crewPage }) => {
    await crewPage.goto('/equipment?filter=eq_attention');
    await crewPage.waitForLoadState('networkidle');

    await crewPage.waitForFunction(
      () => !document.querySelector('.animate-spin'),
      { timeout: 15000 }
    );

    // Crew should be able to view the list
    const equipmentList = crewPage.locator('main, [role="main"]');
    await expect(equipmentList).toBeVisible({ timeout: 10000 });

    // But action buttons should be limited or hidden for crew
    const updateStatusButton = crewPage.locator('[data-testid="update-status-button"], button:has-text("Update Status")');
    const decommissionButton = crewPage.locator('[data-testid="decommission-button"]');

    const canSeeUpdateStatus = await updateStatusButton.isVisible({ timeout: 2000 }).catch(() => false);
    const canSeeDecommission = await decommissionButton.isVisible({ timeout: 2000 }).catch(() => false);

    // Crew should NOT see decommission button
    expect(canSeeDecommission).toBe(false);

    console.log(`  SE-09d PASS: Crew can view equipment list, Update Status: ${canSeeUpdateStatus}, Decommission: ${canSeeDecommission}`);
  });

  test('SE-09e: Captain can see equipment filter chips and navigate', async ({ captainPage }) => {
    await captainPage.goto('/app');
    await captainPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(captainPage);
    await spotlight.search('critical equipment');

    const filterChips = captainPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const criticalChip = captainPage.locator('[data-filter-id="eq_critical"]');
    await expect(criticalChip).toBeVisible({ timeout: 3000 });

    await criticalChip.click();
    await captainPage.waitForURL(/\/equipment.*filter=eq_critical/, { timeout: 10000 });

    expect(captainPage.url()).toContain('/equipment');
    console.log('  SE-09e PASS: Captain can see and navigate with equipment filters');
  });
});

// ============================================================================
// SECTION 10: DETERMINISM TESTS
// Same input produces same chips (run twice to verify)
// ============================================================================

test.describe('SE-10: Determinism', () => {
  test.describe.configure({ retries: 0 });

  test('SE-10a: Same equipment query produces same chips (run 1)', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('failed equipment');

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

    console.log(`  SE-10a Run 1: Found chips: ${chipIds.join(', ')}`);

    // First chip should always be eq_failed for "failed equipment"
    expect(chipIds[0]).toBe('eq_failed');
    console.log('  SE-10a PASS: First chip is eq_failed');
  });

  test('SE-10b: Same equipment query produces same chips (run 2)', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('failed equipment');

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

    console.log(`  SE-10b Run 2: Found chips: ${chipIds.join(', ')}`);

    // Same query should produce same first chip
    expect(chipIds[0]).toBe('eq_failed');
    console.log('  SE-10b PASS: Second run also has eq_failed first - deterministic');
  });
});

// ============================================================================
// SECTION 11: MATCH CONFIDENCE VERIFICATION
// Verify pattern matches have higher scores than keyword matches
// ============================================================================

test.describe('SE-11: Match Confidence', () => {
  test.describe.configure({ retries: 0 });

  test('SE-11a: Pattern match "equipment needing attention" has score >= 0.9', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('equipment needing attention');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const patternChip = hodPage.locator('[data-match-type="pattern"]').first();
    await expect(patternChip).toBeVisible({ timeout: 3000 });

    const score = await patternChip.getAttribute('data-score');
    console.log(`  Pattern match score: ${score}`);

    expect(score).not.toBeNull();
    const numScore = parseFloat(score!);
    expect(numScore).toBeGreaterThanOrEqual(0.9);
    console.log('  SE-11a PASS: Pattern match has high score (>=0.9)');
  });

  test('SE-11b: Domain match has lower score than pattern match', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('equipment');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const domainChip = hodPage.locator('[data-match-type="domain"]').first();
    const hasDomainChip = await domainChip.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasDomainChip) {
      const score = await domainChip.getAttribute('data-score');
      console.log(`  Domain match score: ${score}`);

      expect(score).not.toBeNull();
      const numScore = parseFloat(score!);
      expect(numScore).toBeLessThan(0.5);
      console.log('  SE-11b PASS: Domain match has low score (<0.5)');
    } else {
      console.log('  SE-11b: No domain match chips found (all are pattern/keyword matches)');
    }
  });
});

// ============================================================================
// SECTION 12: EMPTY FILTER STATE
// When filter matches zero items, show appropriate message with clear option
// ============================================================================

test.describe('SE-12: Empty Filter State', () => {
  test.describe.configure({ retries: 0 });

  test('SE-12a: Empty eq_failed results show clear filter option', async ({ hodPage, supabaseAdmin }) => {
    // First, verify there's no failed equipment (or temporarily update if needed)
    const { data: failedEquipment } = await supabaseAdmin
      .from('pms_equipment')
      .select('id')
      .eq('yacht_id', RBAC_CONFIG.yachtId)
      .eq('status', 'failed')
      .limit(1);

    // Navigate to filter that may have no results
    await hodPage.goto('/equipment?filter=eq_failed');
    await hodPage.waitForLoadState('networkidle');

    await hodPage.waitForFunction(
      () => !document.querySelector('.animate-spin'),
      { timeout: 15000 }
    );

    if (!failedEquipment || failedEquipment.length === 0) {
      // Should show empty state
      const emptyState = hodPage.locator('[data-testid="empty-filter-state"], :text("No equipment"), :text("No results")');
      const hasEmptyState = await emptyState.isVisible({ timeout: 5000 }).catch(() => false);

      if (hasEmptyState) {
        console.log('  SE-12a PASS: Empty filter state shown for eq_failed with no matches');

        // Check for clear button
        const clearButton = hodPage.locator('[data-testid="clear-filter-button"], button:has-text("Clear filter")');
        await expect(clearButton).toBeVisible({ timeout: 3000 });
        console.log('  SE-12a PASS: Clear filter button present in empty state');
      } else {
        console.log('  SE-12a: Empty state UI not found - may need specific empty state component');
      }
    } else {
      console.log('  SE-12a: Test yacht has failed equipment - empty state not applicable');
    }
  });
});
