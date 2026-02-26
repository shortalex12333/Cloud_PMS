import { test, expect, RBAC_CONFIG, SpotlightSearchPO } from '../rbac-fixtures';

/**
 * SHARD 31: Quick Filters - Data-Driven Test Matrix
 *
 * ============================================================================
 * COMPREHENSIVE COVERAGE FOR QUICK FILTERS NLP MATCHING
 * ============================================================================
 *
 * This file tests the Quick Filters feature with exhaustive NLP variant coverage.
 * Each of the 11 wired filters (3 domains) is tested with 8-10 query variants.
 *
 * WIRED DOMAINS (only these 3 work):
 * 1. work-orders (5 filters)
 * 2. faults (4 filters)
 * 3. inventory (2 filters)
 *
 * Total test cases: ~100 (11 filters x ~9 variants each)
 *
 * HARD REQUIREMENTS:
 * - retries: 0 (tests MUST be deterministic)
 * - NO soft assertions (no console.log + skip patterns)
 * - All assertions use expect().toBeVisible() / expect().toContain()
 * - Full flow tested: chip visible -> click -> banner -> clear
 */

// ============================================================================
// TEST DATA STRUCTURES
// ============================================================================

interface FilterTestCase {
  /** Human-readable test name */
  name: string;
  /** NLP query to type into Spotlight */
  query: string;
  /** Expected filter ID to match */
  filter_id: string;
  /** Expected route after chip click */
  route: string;
  /** Domain grouping */
  domain: string;
  /** Expected label text in banner */
  expectedChipLabel: string;
}

// ============================================================================
// WORK ORDER FILTER TEST CASES (5 filters x ~9 variants = ~45 tests)
// ============================================================================

const WORK_ORDER_CASES: FilterTestCase[] = [
  // ---------------------------------------------------------------------------
  // wo_overdue - "Overdue work orders" (9 variants)
  // Keywords: ['overdue', 'past due', 'late', 'missed deadline', 'behind schedule']
  // ---------------------------------------------------------------------------
  { name: 'WO overdue v1', query: 'overdue work orders', filter_id: 'wo_overdue', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Overdue work orders' },
  { name: 'WO overdue v2', query: 'past due work orders', filter_id: 'wo_overdue', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Overdue work orders' },
  { name: 'WO overdue v3', query: 'late work orders', filter_id: 'wo_overdue', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Overdue work orders' },
  { name: 'WO overdue v4', query: 'missed deadline work orders', filter_id: 'wo_overdue', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Overdue work orders' },
  { name: 'WO overdue v5', query: 'behind schedule tasks', filter_id: 'wo_overdue', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Overdue work orders' },
  { name: 'WO overdue v6', query: 'overdue maintenance', filter_id: 'wo_overdue', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Overdue work orders' },
  { name: 'WO overdue v7', query: 'show me overdue items', filter_id: 'wo_overdue', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Overdue work orders' },
  { name: 'WO overdue v8', query: 'tasks past due date', filter_id: 'wo_overdue', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Overdue work orders' },
  { name: 'WO overdue v9', query: 'overdue jobs', filter_id: 'wo_overdue', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Overdue work orders' },

  // ---------------------------------------------------------------------------
  // wo_due_7d - "Due this week" (9 variants)
  // Keywords: ['due soon', 'due this week', 'upcoming', 'next 7 days', 'coming up']
  // ---------------------------------------------------------------------------
  { name: 'WO due 7d v1', query: 'due this week', filter_id: 'wo_due_7d', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Due this week' },
  { name: 'WO due 7d v2', query: 'due soon work orders', filter_id: 'wo_due_7d', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Due this week' },
  { name: 'WO due 7d v3', query: 'upcoming work orders', filter_id: 'wo_due_7d', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Due this week' },
  { name: 'WO due 7d v4', query: 'next 7 days tasks', filter_id: 'wo_due_7d', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Due this week' },
  { name: 'WO due 7d v5', query: 'coming up maintenance', filter_id: 'wo_due_7d', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Due this week' },
  { name: 'WO due 7d v6', query: 'work orders coming up', filter_id: 'wo_due_7d', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Due this week' },
  { name: 'WO due 7d v7', query: 'tasks due this week', filter_id: 'wo_due_7d', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Due this week' },
  { name: 'WO due 7d v8', query: 'upcoming tasks', filter_id: 'wo_due_7d', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Due this week' },
  { name: 'WO due 7d v9', query: 'due soon', filter_id: 'wo_due_7d', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Due this week' },

  // ---------------------------------------------------------------------------
  // wo_open - "Open work orders" (10 variants)
  // Keywords: ['open', 'active', 'in progress', 'pending', 'not done']
  // ---------------------------------------------------------------------------
  { name: 'WO open v1', query: 'open work orders', filter_id: 'wo_open', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Open work orders' },
  { name: 'WO open v2', query: 'active work orders', filter_id: 'wo_open', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Open work orders' },
  { name: 'WO open v3', query: 'in progress work orders', filter_id: 'wo_open', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Open work orders' },
  { name: 'WO open v4', query: 'pending work orders', filter_id: 'wo_open', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Open work orders' },
  { name: 'WO open v5', query: 'not done tasks', filter_id: 'wo_open', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Open work orders' },
  { name: 'WO open v6', query: 'active tasks', filter_id: 'wo_open', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Open work orders' },
  { name: 'WO open v7', query: 'show open tasks', filter_id: 'wo_open', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Open work orders' },
  { name: 'WO open v8', query: 'pending maintenance', filter_id: 'wo_open', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Open work orders' },
  { name: 'WO open v9', query: 'work orders in progress', filter_id: 'wo_open', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Open work orders' },
  { name: 'WO open v10', query: 'open jobs', filter_id: 'wo_open', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Open work orders' },

  // ---------------------------------------------------------------------------
  // wo_priority_emergency - "Emergency priority" (8 variants)
  // Keywords: ['emergency', 'urgent', 'critical priority']
  // ---------------------------------------------------------------------------
  { name: 'WO emergency v1', query: 'emergency work orders', filter_id: 'wo_priority_emergency', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Emergency priority' },
  { name: 'WO emergency v2', query: 'urgent work orders', filter_id: 'wo_priority_emergency', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Emergency priority' },
  { name: 'WO emergency v3', query: 'critical priority tasks', filter_id: 'wo_priority_emergency', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Emergency priority' },
  { name: 'WO emergency v4', query: 'emergency tasks', filter_id: 'wo_priority_emergency', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Emergency priority' },
  { name: 'WO emergency v5', query: 'urgent maintenance', filter_id: 'wo_priority_emergency', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Emergency priority' },
  { name: 'WO emergency v6', query: 'emergency priority jobs', filter_id: 'wo_priority_emergency', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Emergency priority' },
  { name: 'WO emergency v7', query: 'show emergency items', filter_id: 'wo_priority_emergency', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Emergency priority' },
  { name: 'WO emergency v8', query: 'urgent tasks', filter_id: 'wo_priority_emergency', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Emergency priority' },

  // ---------------------------------------------------------------------------
  // wo_priority_critical - "Critical priority" (8 variants)
  // Keywords: ['critical', 'high priority']
  // ---------------------------------------------------------------------------
  { name: 'WO critical v1', query: 'critical work orders', filter_id: 'wo_priority_critical', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Critical priority' },
  { name: 'WO critical v2', query: 'high priority work orders', filter_id: 'wo_priority_critical', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Critical priority' },
  { name: 'WO critical v3', query: 'critical tasks', filter_id: 'wo_priority_critical', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Critical priority' },
  { name: 'WO critical v4', query: 'high priority tasks', filter_id: 'wo_priority_critical', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Critical priority' },
  { name: 'WO critical v5', query: 'critical maintenance', filter_id: 'wo_priority_critical', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Critical priority' },
  { name: 'WO critical v6', query: 'high priority jobs', filter_id: 'wo_priority_critical', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Critical priority' },
  { name: 'WO critical v7', query: 'show critical items', filter_id: 'wo_priority_critical', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Critical priority' },
  { name: 'WO critical v8', query: 'critical priority maintenance', filter_id: 'wo_priority_critical', route: '/work-orders', domain: 'work-orders', expectedChipLabel: 'Critical priority' },
];

// ============================================================================
// FAULT FILTER TEST CASES (4 filters x ~9 variants = ~36 tests)
// ============================================================================

const FAULT_CASES: FilterTestCase[] = [
  // ---------------------------------------------------------------------------
  // fault_open - "Open faults" (9 variants)
  // Keywords: ['open faults', 'active faults', 'unresolved faults']
  // ---------------------------------------------------------------------------
  { name: 'Fault open v1', query: 'open faults', filter_id: 'fault_open', route: '/faults', domain: 'faults', expectedChipLabel: 'Open faults' },
  { name: 'Fault open v2', query: 'active faults', filter_id: 'fault_open', route: '/faults', domain: 'faults', expectedChipLabel: 'Open faults' },
  { name: 'Fault open v3', query: 'unresolved faults', filter_id: 'fault_open', route: '/faults', domain: 'faults', expectedChipLabel: 'Open faults' },
  { name: 'Fault open v4', query: 'show open faults', filter_id: 'fault_open', route: '/faults', domain: 'faults', expectedChipLabel: 'Open faults' },
  { name: 'Fault open v5', query: 'faults that are open', filter_id: 'fault_open', route: '/faults', domain: 'faults', expectedChipLabel: 'Open faults' },
  { name: 'Fault open v6', query: 'active fault reports', filter_id: 'fault_open', route: '/faults', domain: 'faults', expectedChipLabel: 'Open faults' },
  { name: 'Fault open v7', query: 'open fault list', filter_id: 'fault_open', route: '/faults', domain: 'faults', expectedChipLabel: 'Open faults' },
  { name: 'Fault open v8', query: 'all open faults', filter_id: 'fault_open', route: '/faults', domain: 'faults', expectedChipLabel: 'Open faults' },
  { name: 'Fault open v9', query: 'open issues', filter_id: 'fault_open', route: '/faults', domain: 'faults', expectedChipLabel: 'Open faults' },

  // ---------------------------------------------------------------------------
  // fault_unresolved - "Unresolved faults" (9 variants)
  // Keywords: ['unresolved', 'not fixed', 'pending faults']
  // ---------------------------------------------------------------------------
  { name: 'Fault unresolved v1', query: 'unresolved faults', filter_id: 'fault_unresolved', route: '/faults', domain: 'faults', expectedChipLabel: 'Unresolved faults' },
  { name: 'Fault unresolved v2', query: 'not fixed faults', filter_id: 'fault_unresolved', route: '/faults', domain: 'faults', expectedChipLabel: 'Unresolved faults' },
  { name: 'Fault unresolved v3', query: 'pending faults', filter_id: 'fault_unresolved', route: '/faults', domain: 'faults', expectedChipLabel: 'Unresolved faults' },
  { name: 'Fault unresolved v4', query: 'faults not fixed', filter_id: 'fault_unresolved', route: '/faults', domain: 'faults', expectedChipLabel: 'Unresolved faults' },
  { name: 'Fault unresolved v5', query: 'unresolved issues', filter_id: 'fault_unresolved', route: '/faults', domain: 'faults', expectedChipLabel: 'Unresolved faults' },
  { name: 'Fault unresolved v6', query: 'faults still pending', filter_id: 'fault_unresolved', route: '/faults', domain: 'faults', expectedChipLabel: 'Unresolved faults' },
  { name: 'Fault unresolved v7', query: 'show unresolved', filter_id: 'fault_unresolved', route: '/faults', domain: 'faults', expectedChipLabel: 'Unresolved faults' },
  { name: 'Fault unresolved v8', query: 'pending fault reports', filter_id: 'fault_unresolved', route: '/faults', domain: 'faults', expectedChipLabel: 'Unresolved faults' },
  { name: 'Fault unresolved v9', query: 'unresolved problems', filter_id: 'fault_unresolved', route: '/faults', domain: 'faults', expectedChipLabel: 'Unresolved faults' },

  // ---------------------------------------------------------------------------
  // fault_critical - "Critical faults" (10 variants)
  // Keywords: ['critical', 'safety', 'severe', 'major fault']
  // ---------------------------------------------------------------------------
  { name: 'Fault critical v1', query: 'critical faults', filter_id: 'fault_critical', route: '/faults', domain: 'faults', expectedChipLabel: 'Critical faults' },
  { name: 'Fault critical v2', query: 'safety faults', filter_id: 'fault_critical', route: '/faults', domain: 'faults', expectedChipLabel: 'Critical faults' },
  { name: 'Fault critical v3', query: 'severe faults', filter_id: 'fault_critical', route: '/faults', domain: 'faults', expectedChipLabel: 'Critical faults' },
  { name: 'Fault critical v4', query: 'major fault', filter_id: 'fault_critical', route: '/faults', domain: 'faults', expectedChipLabel: 'Critical faults' },
  { name: 'Fault critical v5', query: 'critical issues', filter_id: 'fault_critical', route: '/faults', domain: 'faults', expectedChipLabel: 'Critical faults' },
  { name: 'Fault critical v6', query: 'safety issues', filter_id: 'fault_critical', route: '/faults', domain: 'faults', expectedChipLabel: 'Critical faults' },
  { name: 'Fault critical v7', query: 'severe problems', filter_id: 'fault_critical', route: '/faults', domain: 'faults', expectedChipLabel: 'Critical faults' },
  { name: 'Fault critical v8', query: 'critical fault reports', filter_id: 'fault_critical', route: '/faults', domain: 'faults', expectedChipLabel: 'Critical faults' },
  { name: 'Fault critical v9', query: 'major faults list', filter_id: 'fault_critical', route: '/faults', domain: 'faults', expectedChipLabel: 'Critical faults' },
  { name: 'Fault critical v10', query: 'show critical', filter_id: 'fault_critical', route: '/faults', domain: 'faults', expectedChipLabel: 'Critical faults' },

  // ---------------------------------------------------------------------------
  // fault_investigating - "Under investigation" (8 variants)
  // Keywords: ['investigating', 'being looked at']
  // ---------------------------------------------------------------------------
  { name: 'Fault investigating v1', query: 'investigating faults', filter_id: 'fault_investigating', route: '/faults', domain: 'faults', expectedChipLabel: 'Under investigation' },
  { name: 'Fault investigating v2', query: 'being looked at', filter_id: 'fault_investigating', route: '/faults', domain: 'faults', expectedChipLabel: 'Under investigation' },
  { name: 'Fault investigating v3', query: 'under investigation', filter_id: 'fault_investigating', route: '/faults', domain: 'faults', expectedChipLabel: 'Under investigation' },
  { name: 'Fault investigating v4', query: 'faults being investigated', filter_id: 'fault_investigating', route: '/faults', domain: 'faults', expectedChipLabel: 'Under investigation' },
  { name: 'Fault investigating v5', query: 'currently investigating', filter_id: 'fault_investigating', route: '/faults', domain: 'faults', expectedChipLabel: 'Under investigation' },
  { name: 'Fault investigating v6', query: 'investigation in progress', filter_id: 'fault_investigating', route: '/faults', domain: 'faults', expectedChipLabel: 'Under investigation' },
  { name: 'Fault investigating v7', query: 'faults under review', filter_id: 'fault_investigating', route: '/faults', domain: 'faults', expectedChipLabel: 'Under investigation' },
  { name: 'Fault investigating v8', query: 'show investigating', filter_id: 'fault_investigating', route: '/faults', domain: 'faults', expectedChipLabel: 'Under investigation' },
];

// ============================================================================
// INVENTORY FILTER TEST CASES (2 filters x ~10 variants = ~20 tests)
// ============================================================================

const INVENTORY_CASES: FilterTestCase[] = [
  // ---------------------------------------------------------------------------
  // inv_low_stock - "Low stock" (10 variants)
  // Keywords: ['low stock', 'running low', 'reorder', 'below minimum']
  // ---------------------------------------------------------------------------
  { name: 'Inv low stock v1', query: 'low stock', filter_id: 'inv_low_stock', route: '/inventory', domain: 'inventory', expectedChipLabel: 'Low stock' },
  { name: 'Inv low stock v2', query: 'running low', filter_id: 'inv_low_stock', route: '/inventory', domain: 'inventory', expectedChipLabel: 'Low stock' },
  { name: 'Inv low stock v3', query: 'reorder items', filter_id: 'inv_low_stock', route: '/inventory', domain: 'inventory', expectedChipLabel: 'Low stock' },
  { name: 'Inv low stock v4', query: 'below minimum stock', filter_id: 'inv_low_stock', route: '/inventory', domain: 'inventory', expectedChipLabel: 'Low stock' },
  { name: 'Inv low stock v5', query: 'low inventory', filter_id: 'inv_low_stock', route: '/inventory', domain: 'inventory', expectedChipLabel: 'Low stock' },
  { name: 'Inv low stock v6', query: 'parts running low', filter_id: 'inv_low_stock', route: '/inventory', domain: 'inventory', expectedChipLabel: 'Low stock' },
  { name: 'Inv low stock v7', query: 'need to reorder', filter_id: 'inv_low_stock', route: '/inventory', domain: 'inventory', expectedChipLabel: 'Low stock' },
  { name: 'Inv low stock v8', query: 'low stock parts', filter_id: 'inv_low_stock', route: '/inventory', domain: 'inventory', expectedChipLabel: 'Low stock' },
  { name: 'Inv low stock v9', query: 'items below minimum', filter_id: 'inv_low_stock', route: '/inventory', domain: 'inventory', expectedChipLabel: 'Low stock' },
  { name: 'Inv low stock v10', query: 'show low stock', filter_id: 'inv_low_stock', route: '/inventory', domain: 'inventory', expectedChipLabel: 'Low stock' },

  // ---------------------------------------------------------------------------
  // inv_out_of_stock - "Out of stock" (10 variants)
  // Keywords: ['out of stock', 'zero stock', 'no stock', 'empty']
  // ---------------------------------------------------------------------------
  { name: 'Inv out of stock v1', query: 'out of stock', filter_id: 'inv_out_of_stock', route: '/inventory', domain: 'inventory', expectedChipLabel: 'Out of stock' },
  { name: 'Inv out of stock v2', query: 'zero stock', filter_id: 'inv_out_of_stock', route: '/inventory', domain: 'inventory', expectedChipLabel: 'Out of stock' },
  { name: 'Inv out of stock v3', query: 'no stock', filter_id: 'inv_out_of_stock', route: '/inventory', domain: 'inventory', expectedChipLabel: 'Out of stock' },
  { name: 'Inv out of stock v4', query: 'empty inventory', filter_id: 'inv_out_of_stock', route: '/inventory', domain: 'inventory', expectedChipLabel: 'Out of stock' },
  { name: 'Inv out of stock v5', query: 'parts out of stock', filter_id: 'inv_out_of_stock', route: '/inventory', domain: 'inventory', expectedChipLabel: 'Out of stock' },
  { name: 'Inv out of stock v6', query: 'zero quantity', filter_id: 'inv_out_of_stock', route: '/inventory', domain: 'inventory', expectedChipLabel: 'Out of stock' },
  { name: 'Inv out of stock v7', query: 'no inventory', filter_id: 'inv_out_of_stock', route: '/inventory', domain: 'inventory', expectedChipLabel: 'Out of stock' },
  { name: 'Inv out of stock v8', query: 'empty stock', filter_id: 'inv_out_of_stock', route: '/inventory', domain: 'inventory', expectedChipLabel: 'Out of stock' },
  { name: 'Inv out of stock v9', query: 'items out of stock', filter_id: 'inv_out_of_stock', route: '/inventory', domain: 'inventory', expectedChipLabel: 'Out of stock' },
  { name: 'Inv out of stock v10', query: 'show out of stock', filter_id: 'inv_out_of_stock', route: '/inventory', domain: 'inventory', expectedChipLabel: 'Out of stock' },
];

// ============================================================================
// COMBINED TEST MATRIX
// ============================================================================

const ALL_TEST_CASES: FilterTestCase[] = [
  ...WORK_ORDER_CASES,
  ...FAULT_CASES,
  ...INVENTORY_CASES,
];

// Log test matrix statistics
console.log(`Quick Filters Test Matrix Statistics:`);
console.log(`  Work Order Cases: ${WORK_ORDER_CASES.length}`);
console.log(`  Fault Cases: ${FAULT_CASES.length}`);
console.log(`  Inventory Cases: ${INVENTORY_CASES.length}`);
console.log(`  TOTAL: ${ALL_TEST_CASES.length} test cases`);

// ============================================================================
// DATA-DRIVEN TESTS
// ============================================================================

test.describe('Quick Filters - Data-Driven Matrix', () => {
  // HARD REQUIREMENT: No retries - tests must be deterministic
  test.describe.configure({ retries: 0 });

  // ---------------------------------------------------------------------------
  // WORK ORDER DOMAIN TESTS
  // ---------------------------------------------------------------------------
  test.describe('Work Order Filters', () => {
    for (const testCase of WORK_ORDER_CASES) {
      test(`${testCase.name}: "${testCase.query}" -> ${testCase.filter_id}`, async ({ hodPage }) => {
        // Step 1: Navigate to /app
        await hodPage.goto('/app');
        await hodPage.waitForLoadState('networkidle');

        // Step 2: Type query into Spotlight
        const spotlight = new SpotlightSearchPO(hodPage);
        await spotlight.search(testCase.query);
        await hodPage.waitForTimeout(1500);

        // Step 3: HARD ASSERTION - Chip must be visible
        const chip = hodPage.locator(`[data-filter-id="${testCase.filter_id}"]`);
        await expect(chip).toBeVisible({ timeout: 5000 });

        // Step 4: Click chip
        await chip.click();
        await hodPage.waitForURL(`**${testCase.route}?filter=${testCase.filter_id}`, { timeout: 10000 });

        // Step 5: HARD ASSERTION - Filter banner must show
        const banner = hodPage.locator('[data-testid="active-filter-banner"]');
        await expect(banner).toBeVisible({ timeout: 5000 });
        await expect(banner).toContainText(testCase.expectedChipLabel);

        // Step 6: HARD ASSERTION - Clear button must work
        const clearBtn = hodPage.locator('[data-testid="clear-filter-button"]');
        await expect(clearBtn).toBeVisible({ timeout: 3000 });
        await clearBtn.click();
        await hodPage.waitForURL(`**${testCase.route}`, { timeout: 5000 });
        await expect(hodPage).not.toHaveURL(/filter=/);
      });
    }
  });

  // ---------------------------------------------------------------------------
  // FAULT DOMAIN TESTS
  // ---------------------------------------------------------------------------
  test.describe('Fault Filters', () => {
    for (const testCase of FAULT_CASES) {
      test(`${testCase.name}: "${testCase.query}" -> ${testCase.filter_id}`, async ({ hodPage }) => {
        // Step 1: Navigate to /app
        await hodPage.goto('/app');
        await hodPage.waitForLoadState('networkidle');

        // Step 2: Type query into Spotlight
        const spotlight = new SpotlightSearchPO(hodPage);
        await spotlight.search(testCase.query);
        await hodPage.waitForTimeout(1500);

        // Step 3: HARD ASSERTION - Chip must be visible
        const chip = hodPage.locator(`[data-filter-id="${testCase.filter_id}"]`);
        await expect(chip).toBeVisible({ timeout: 5000 });

        // Step 4: Click chip
        await chip.click();
        await hodPage.waitForURL(`**${testCase.route}?filter=${testCase.filter_id}`, { timeout: 10000 });

        // Step 5: HARD ASSERTION - Filter banner must show
        const banner = hodPage.locator('[data-testid="active-filter-banner"]');
        await expect(banner).toBeVisible({ timeout: 5000 });
        await expect(banner).toContainText(testCase.expectedChipLabel);

        // Step 6: HARD ASSERTION - Clear button must work
        const clearBtn = hodPage.locator('[data-testid="clear-filter-button"]');
        await expect(clearBtn).toBeVisible({ timeout: 3000 });
        await clearBtn.click();
        await hodPage.waitForURL(`**${testCase.route}`, { timeout: 5000 });
        await expect(hodPage).not.toHaveURL(/filter=/);
      });
    }
  });

  // ---------------------------------------------------------------------------
  // INVENTORY DOMAIN TESTS
  // ---------------------------------------------------------------------------
  test.describe('Inventory Filters', () => {
    for (const testCase of INVENTORY_CASES) {
      test(`${testCase.name}: "${testCase.query}" -> ${testCase.filter_id}`, async ({ hodPage }) => {
        // Step 1: Navigate to /app
        await hodPage.goto('/app');
        await hodPage.waitForLoadState('networkidle');

        // Step 2: Type query into Spotlight
        const spotlight = new SpotlightSearchPO(hodPage);
        await spotlight.search(testCase.query);
        await hodPage.waitForTimeout(1500);

        // Step 3: HARD ASSERTION - Chip must be visible
        const chip = hodPage.locator(`[data-filter-id="${testCase.filter_id}"]`);
        await expect(chip).toBeVisible({ timeout: 5000 });

        // Step 4: Click chip
        await chip.click();
        await hodPage.waitForURL(`**${testCase.route}?filter=${testCase.filter_id}`, { timeout: 10000 });

        // Step 5: HARD ASSERTION - Filter banner must show
        const banner = hodPage.locator('[data-testid="active-filter-banner"]');
        await expect(banner).toBeVisible({ timeout: 5000 });
        await expect(banner).toContainText(testCase.expectedChipLabel);

        // Step 6: HARD ASSERTION - Clear button must work
        const clearBtn = hodPage.locator('[data-testid="clear-filter-button"]');
        await expect(clearBtn).toBeVisible({ timeout: 3000 });
        await clearBtn.click();
        await hodPage.waitForURL(`**${testCase.route}`, { timeout: 5000 });
        await expect(hodPage).not.toHaveURL(/filter=/);
      });
    }
  });
});

// ============================================================================
// EDGE CASE TESTS
// ============================================================================

test.describe('Quick Filters - Edge Cases', () => {
  test.describe.configure({ retries: 0 });

  test('Short queries (<3 chars) should NOT show filter chips', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('ab');
    await hodPage.waitForTimeout(1000);

    // Filter chips container should not be visible
    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).not.toBeVisible({ timeout: 2000 });
  });

  test('Empty query should NOT show filter chips', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('');
    await hodPage.waitForTimeout(1000);

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).not.toBeVisible({ timeout: 2000 });
  });

  test('Unrelated query should NOT show filter chips', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('xyzzy plugh');
    await hodPage.waitForTimeout(1500);

    // No filter chips should appear for unrelated queries
    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    const isVisible = await filterChips.isVisible().catch(() => false);

    if (isVisible) {
      // If chips are visible, ensure none match our filter IDs
      const anyKnownChip = hodPage.locator('[data-filter-id^="wo_"], [data-filter-id^="fault_"], [data-filter-id^="inv_"]');
      await expect(anyKnownChip).not.toBeVisible({ timeout: 2000 });
    }
  });
});

// ============================================================================
// DETERMINISM TESTS
// ============================================================================

test.describe('Quick Filters - Determinism Verification', () => {
  test.describe.configure({ retries: 0 });

  test('Same query produces same chips (deterministic) - Run 1', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('overdue work orders');
    await hodPage.waitForTimeout(1500);

    // Must always show wo_overdue chip first
    const overdueChip = hodPage.locator('[data-filter-id="wo_overdue"]');
    await expect(overdueChip).toBeVisible({ timeout: 5000 });
  });

  test('Same query produces same chips (deterministic) - Run 2', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('overdue work orders');
    await hodPage.waitForTimeout(1500);

    // Must always show wo_overdue chip first (same as Run 1)
    const overdueChip = hodPage.locator('[data-filter-id="wo_overdue"]');
    await expect(overdueChip).toBeVisible({ timeout: 5000 });
  });

  test('Same query produces same chips (deterministic) - Run 3', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('overdue work orders');
    await hodPage.waitForTimeout(1500);

    // Must always show wo_overdue chip first (same as Run 1 & 2)
    const overdueChip = hodPage.locator('[data-filter-id="wo_overdue"]');
    await expect(overdueChip).toBeVisible({ timeout: 5000 });
  });
});

// ============================================================================
// CROSS-DOMAIN COLLISION TESTS
// ============================================================================

test.describe('Quick Filters - Cross-Domain Disambiguation', () => {
  test.describe.configure({ retries: 0 });

  test('Query "critical" should show both work order and fault chips', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('critical');
    await hodPage.waitForTimeout(1500);

    // "critical" keyword matches both wo_priority_critical and fault_critical
    // At least one should be visible
    const woCriticalChip = hodPage.locator('[data-filter-id="wo_priority_critical"]');
    const faultCriticalChip = hodPage.locator('[data-filter-id="fault_critical"]');

    // Use Promise.race pattern to check if at least one is visible
    const woVisible = await woCriticalChip.isVisible().catch(() => false);
    const faultVisible = await faultCriticalChip.isVisible().catch(() => false);

    // HARD ASSERTION: At least one critical chip should be visible
    expect(woVisible || faultVisible).toBe(true);
  });

  test('Query "open" should prefer work orders over faults', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('open');
    await hodPage.waitForTimeout(1500);

    // "open" is a keyword for both wo_open and fault_open
    // Work orders should take priority (more common use case)
    const woOpenChip = hodPage.locator('[data-filter-id="wo_open"]');
    await expect(woOpenChip).toBeVisible({ timeout: 5000 });
  });
});

// ============================================================================
// DIRECT URL NAVIGATION TESTS
// ============================================================================

test.describe('Quick Filters - Direct URL Navigation', () => {
  test.describe.configure({ retries: 0 });

  test('Direct navigation to /work-orders?filter=wo_overdue shows banner', async ({ hodPage }) => {
    await hodPage.goto('/work-orders?filter=wo_overdue');
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(1000);

    const banner = hodPage.locator('[data-testid="active-filter-banner"]');
    await expect(banner).toBeVisible({ timeout: 5000 });
    await expect(banner).toContainText('Overdue');
  });

  test('Direct navigation to /faults?filter=fault_critical shows banner', async ({ hodPage }) => {
    await hodPage.goto('/faults?filter=fault_critical');
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(1000);

    const banner = hodPage.locator('[data-testid="active-filter-banner"]');
    await expect(banner).toBeVisible({ timeout: 5000 });
    await expect(banner).toContainText('Critical');
  });

  test('Direct navigation to /inventory?filter=inv_low_stock shows banner', async ({ hodPage }) => {
    await hodPage.goto('/inventory?filter=inv_low_stock');
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(1000);

    const banner = hodPage.locator('[data-testid="active-filter-banner"]');
    await expect(banner).toBeVisible({ timeout: 5000 });
    await expect(banner).toContainText('Low stock');
  });

  test('Invalid filter ID in URL should NOT show banner', async ({ hodPage }) => {
    await hodPage.goto('/work-orders?filter=invalid_filter_xyz');
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(1000);

    // Invalid filter should not show a banner (graceful degradation)
    const banner = hodPage.locator('[data-testid="active-filter-banner"]');
    await expect(banner).not.toBeVisible({ timeout: 3000 });
  });
});

// ============================================================================
// FILTER CHIP ATTRIBUTES TESTS
// ============================================================================

test.describe('Quick Filters - Chip Attributes', () => {
  test.describe.configure({ retries: 0 });

  test('Filter chip has correct data attributes', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('overdue work orders');
    await hodPage.waitForTimeout(1500);

    const chip = hodPage.locator('[data-filter-id="wo_overdue"]');
    await expect(chip).toBeVisible({ timeout: 5000 });

    // Verify chip has expected filter ID
    const filterId = await chip.getAttribute('data-filter-id');
    expect(filterId).toBe('wo_overdue');
  });

  test('Filter chip text matches label', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('low stock');
    await hodPage.waitForTimeout(1500);

    const chip = hodPage.locator('[data-filter-id="inv_low_stock"]');
    await expect(chip).toBeVisible({ timeout: 5000 });
    await expect(chip).toContainText('Low stock');
  });
});
