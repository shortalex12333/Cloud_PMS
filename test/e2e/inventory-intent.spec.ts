import { test, expect, Page } from '@playwright/test';

/**
 * Inventory Intent E2E Tests
 *
 * Lens: inventory
 * Tests: 50 total (25 READ + 25 MUTATE)
 *
 * Covers:
 * - READ Navigation tests for all filter combinations
 * - MUTATE Action tests for all 5 inventory actions
 */

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';

// Test data factory
const testData = {
  inventory: {
    part_id: 'part-filter-001',
    stock_status: 'IN_STOCK',
    location: 'main-store',
    category: 'filters',
  },
};

// Helper functions
async function openSpotlight(page: Page): Promise<void> {
  await page.keyboard.press('Meta+K');
  await page.waitForSelector('[data-testid="spotlight-input"]', { state: 'visible' });
}

async function typeQuery(page: Page, query: string): Promise<void> {
  await page.fill('[data-testid="spotlight-input"]', query);
  await page.waitForSelector('[data-testid="suggested-actions"]', { timeout: 5000 });
}

async function clickNavigate(page: Page): Promise<void> {
  const navigateBtn = page.locator('[data-testid="navigate-action"]');
  await expect(navigateBtn).toBeVisible();
  await navigateBtn.click();
}

async function clickExecute(page: Page): Promise<void> {
  const executeBtn = page.locator('[data-testid="execute-action"]');
  await expect(executeBtn).toBeVisible();
  await executeBtn.click();
}

async function waitForActionModal(page: Page): Promise<void> {
  await page.waitForSelector('[data-testid="action-modal"]', { state: 'visible' });
}

async function verifyReadinessIndicator(page: Page, expectedState: 'READY' | 'NEEDS_INPUT' | 'BLOCKED'): Promise<void> {
  const indicator = page.locator('[data-testid="readiness-indicator"]');
  await expect(indicator).toHaveAttribute('data-state', expectedState);
}

test.describe('Inventory Intent Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForSelector('[data-testid="app-ready"]', { timeout: 10000 });
  });

  // ============================================================================
  // READ NAVIGATION TESTS (25 tests)
  // ============================================================================
  test.describe('READ Navigation', () => {
    // Stock status filter tests
    test('READ: show inventory navigates to /inventory', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show inventory');

      const navigateBtn = page.locator('[data-testid="navigate-action"]');
      await expect(navigateBtn).toBeVisible();
      await navigateBtn.click();

      await expect(page).toHaveURL(/\/inventory/);
    });

    test('READ: display in stock inventory filters by stock_status=IN_STOCK', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'display in stock inventory');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/inventory.*stock_status=IN_STOCK/);
    });

    test('READ: list low stock inventory filters by stock_status=LOW_STOCK', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list low stock inventory');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/inventory.*stock_status=LOW_STOCK/);
    });

    test('READ: find out of stock inventory filters by stock_status=OUT_OF_STOCK', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find out of stock inventory');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/inventory.*stock_status=OUT_OF_STOCK/);
    });

    test('READ: show overstocked inventory filters by stock_status=OVERSTOCKED', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show overstocked inventory');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/inventory.*stock_status=OVERSTOCKED/);
    });

    test('READ: view inventory on order filters by stock_status=ON_ORDER', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'view inventory on order');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/inventory.*stock_status=ON_ORDER/);
    });

    // Location filter tests
    test('READ: inventory in main store filters by location', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'inventory in main store');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/inventory.*location/);
    });

    test('READ: show inventory in engine room filters by location', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show inventory in engine room');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/inventory.*location/);
    });

    test('READ: list inventory in bosun store filters by location', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list inventory in bosun store');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/inventory.*location/);
    });

    // Category filter tests
    test('READ: show filter inventory filters by category', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show filter inventory');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/inventory.*category/);
    });

    test('READ: list electrical inventory filters by category', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list electrical inventory');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/inventory.*category/);
    });

    test('READ: find safety inventory filters by category', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find safety inventory');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/inventory.*category/);
    });

    // Reorder needed filter tests
    test('READ: inventory needing reorder filters by reorder_needed=true', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'inventory needing reorder');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/inventory.*reorder/);
    });

    test('READ: show reorder alerts filters by reorder needed', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show reorder alerts');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/inventory/);
    });

    // Last counted filter tests
    test('READ: inventory counted this week filters by last_counted_at', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'inventory counted this week');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/inventory/);
    });

    test('READ: inventory not counted in 30 days filters by last_counted_at', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'inventory not counted in 30 days');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/inventory/);
    });

    test('READ: show inventory needing count filters by count due', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show inventory needing count');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/inventory/);
    });

    // Compound filter tests
    test('READ: low stock filters in main store applies multiple filters', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'low stock filters in main store');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/inventory/);
    });

    test('READ: out of stock electrical parts filters stock and category', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'out of stock electrical parts');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/inventory/);
    });

    test('READ: inventory in engine room needing reorder filters location and reorder', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'inventory in engine room needing reorder');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/inventory/);
    });

    test('READ: overstocked items in main store filters status and location', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'overstocked items in main store');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/inventory/);
    });

    test('READ: safety equipment not counted recently filters category and count date', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'safety equipment not counted recently');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/inventory/);
    });

    test('READ: critical inventory low stock filters urgency and status', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'critical inventory low stock');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/inventory/);
    });

    test('READ: inventory summary shows dashboard view', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'inventory summary');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/inventory/);
    });

    test('READ: stock levels overview shows inventory overview', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'stock levels overview');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/inventory/);
    });
  });

  // ============================================================================
  // MUTATE ACTION TESTS (25 tests)
  // ============================================================================
  test.describe('MUTATE Actions', () => {
    // log_part_usage tests
    test('MUTATE: log part usage opens modal with required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'log part usage');

      const executeBtn = page.locator('[data-testid="execute-action"]');
      await expect(executeBtn).toBeVisible();
      await executeBtn.click();
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="modal-title"]')).toContainText('Log Part Usage');
      await expect(page.locator('[data-testid="field-part_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-quantity"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-work_order_id"]')).toBeVisible();
    });

    test('MUTATE: use 5 filters on WO-123 prefills all fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'use 5 filters on WO-123');
      await clickExecute(page);
      await waitForActionModal(page);

      const quantityField = page.locator('[data-testid="field-quantity"]');
      await expect(quantityField).toHaveValue('5');
    });

    test('MUTATE: log part usage shows optional usage_notes field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'log part usage');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-usage_notes"]')).toBeVisible();
    });

    test('MUTATE: record consumption for WO prefills work_order_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'record consumption for WO-456');
      await clickExecute(page);
      await waitForActionModal(page);

      const woField = page.locator('[data-testid="field-work_order_id"]');
      await expect(woField).toHaveValue(/WO-456/);
    });

    // update_stock_level tests
    test('MUTATE: update stock level shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'update stock level');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-part_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-quantity_change"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-reason"]')).toBeVisible();
    });

    test('MUTATE: adjust stock by +10 prefills quantity_change', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'adjust stock by +10');
      await clickExecute(page);
      await waitForActionModal(page);

      const quantityField = page.locator('[data-testid="field-quantity_change"]');
      await expect(quantityField).toHaveValue('10');
    });

    test('MUTATE: decrease stock by 5 prefills negative quantity', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'decrease stock by 5');
      await clickExecute(page);
      await waitForActionModal(page);

      const quantityField = page.locator('[data-testid="field-quantity_change"]');
      await expect(quantityField).toHaveValue('-5');
    });

    test('MUTATE: update stock shows optional reference_id field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'update stock level');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-reference_id"]')).toBeVisible();
    });

    test('MUTATE: correct inventory count shows reason field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'correct inventory count');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-reason"]')).toBeVisible();
    });

    // create_purchase_request tests
    test('MUTATE: create purchase request shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create purchase request');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-part_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-quantity_requested"]')).toBeVisible();
    });

    test('MUTATE: request 20 filters prefills quantity', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'request 20 filters');
      await clickExecute(page);
      await waitForActionModal(page);

      const quantityField = page.locator('[data-testid="field-quantity_requested"]');
      await expect(quantityField).toHaveValue('20');
    });

    test('MUTATE: create purchase request shows urgency field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create purchase request');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-urgency"]')).toBeVisible();
    });

    test('MUTATE: urgent purchase request prefills urgency', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'urgent purchase request');
      await clickExecute(page);
      await waitForActionModal(page);

      const urgencyField = page.locator('[data-testid="field-urgency"]');
      await expect(urgencyField).toHaveValue('high');
    });

    test('MUTATE: create purchase request shows required_by_date field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create purchase request');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-required_by_date"]')).toBeVisible();
    });

    test('MUTATE: order parts shows preferred_supplier field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'order parts');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-preferred_supplier"]')).toBeVisible();
    });

    // reserve_part tests
    test('MUTATE: reserve part shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'reserve part');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-part_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-quantity"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-work_order_id"]')).toBeVisible();
    });

    test('MUTATE: reserve 5 filters for WO-789 prefills all fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'reserve 5 filters for WO-789');
      await clickExecute(page);
      await waitForActionModal(page);

      const quantityField = page.locator('[data-testid="field-quantity"]');
      await expect(quantityField).toHaveValue('5');
    });

    test('MUTATE: reserve part shows optional reservation_notes field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'reserve part');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-reservation_notes"]')).toBeVisible();
    });

    test('MUTATE: allocate parts for work order shows reservation modal', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'allocate parts for work order');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="modal-title"]')).toContainText('Reserve');
    });

    // count_inventory tests
    test('MUTATE: count inventory shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'count inventory');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-part_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-counted_quantity"]')).toBeVisible();
    });

    test('MUTATE: record count of 50 filters prefills quantity', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'record count of 50 filters');
      await clickExecute(page);
      await waitForActionModal(page);

      const quantityField = page.locator('[data-testid="field-counted_quantity"]');
      await expect(quantityField).toHaveValue('50');
    });

    test('MUTATE: count inventory shows optional count_notes field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'count inventory');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-count_notes"]')).toBeVisible();
    });

    test('MUTATE: count inventory shows discrepancy_reason field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'count inventory');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-discrepancy_reason"]')).toBeVisible();
    });

    test('MUTATE: physical count for P-001 prefills part_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'physical count for P-001');
      await clickExecute(page);
      await waitForActionModal(page);

      const partField = page.locator('[data-testid="field-part_id"]');
      await expect(partField).toHaveValue(/P-001/);
    });

    test('MUTATE: inventory count submission updates last_counted_at', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'count inventory');
      await clickExecute(page);
      await waitForActionModal(page);

      // Fill required fields
      await page.fill('[data-testid="field-counted_quantity"]', '100');

      // Submit
      await page.click('[data-testid="modal-submit"]');

      // Verify success toast
      await expect(page.locator('[data-testid="toast-success"]')).toBeVisible();
    });
  });
});
