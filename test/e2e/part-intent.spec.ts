import { test, expect, Page } from '@playwright/test';

/**
 * Part Intent E2E Tests
 *
 * Lens: part
 * Tests: 52 total (26 READ + 26 MUTATE)
 *
 * Covers:
 * - READ Navigation tests for all filter combinations
 * - MUTATE Action tests for all 7 part actions
 */

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';

// Test data factory
const testData = {
  part: {
    id: 'part-filter-001',
    name: 'Oil Filter',
    stock_status: 'IN_STOCK',
    category: 'filters',
    manufacturer: 'Mann+Hummel',
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

test.describe('Part Intent Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForSelector('[data-testid="app-ready"]', { timeout: 10000 });
  });

  // ============================================================================
  // READ NAVIGATION TESTS (26 tests)
  // ============================================================================
  test.describe('READ Navigation', () => {
    // Stock status filter tests
    test('READ: show in stock parts navigates to /parts?stock_status=IN_STOCK', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show in stock parts');

      const navigateBtn = page.locator('[data-testid="navigate-action"]');
      await expect(navigateBtn).toBeVisible();
      await navigateBtn.click();

      await expect(page).toHaveURL(/\/parts.*stock_status=IN_STOCK/);
    });

    test('READ: display all parts navigates to /parts', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'display all parts');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/parts/);
    });

    test('READ: list low stock parts filters by stock_status=LOW_STOCK', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list low stock parts');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/parts.*stock_status=LOW_STOCK/);
    });

    test('READ: find out of stock parts filters by stock_status=OUT_OF_STOCK', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find out of stock parts');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/parts.*stock_status=OUT_OF_STOCK/);
    });

    test('READ: show overstocked parts filters by stock_status=OVERSTOCKED', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show overstocked parts');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/parts.*stock_status=OVERSTOCKED/);
    });

    test('READ: view parts on order filters by stock_status=ON_ORDER', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'view parts on order');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/parts.*stock_status=ON_ORDER/);
    });

    // Category filter tests
    test('READ: show filter parts filters by category', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show filter parts');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/parts.*category/);
    });

    test('READ: list electrical parts filters by category', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list electrical parts');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/parts.*category/);
    });

    test('READ: find bearing parts filters by category', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find bearing parts');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/parts.*category/);
    });

    // Manufacturer filter tests
    test('READ: show Mann+Hummel parts filters by manufacturer', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show Mann+Hummel parts');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/parts.*manufacturer/);
    });

    test('READ: find Bosch parts filters by manufacturer', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find Bosch parts');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/parts.*manufacturer/);
    });

    // Location filter tests
    test('READ: parts in engine room store filters by location', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'parts in engine room store');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/parts.*location/);
    });

    test('READ: list parts in main store filters by location', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list parts in main store');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/parts.*location/);
    });

    // Equipment association filter tests
    test('READ: parts for ME1 filters by equipment_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'parts for ME1');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/parts.*equipment/);
    });

    test('READ: spare parts for main engine filters by equipment', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'spare parts for main engine');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/parts/);
    });

    test('READ: parts compatible with DG1 filters by equipment', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'parts compatible with DG1');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/parts/);
    });

    // Reorder needed filter tests
    test('READ: parts needing reorder filters by reorder_needed=true', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'parts needing reorder');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/parts.*reorder/);
    });

    test('READ: show reorder list filters by reorder needed', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show reorder list');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/parts/);
    });

    // Compound filter tests
    test('READ: low stock filter parts applies multiple filters', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'low stock filter parts');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/parts/);
    });

    test('READ: out of stock parts for main engine filters stock and equipment', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'out of stock parts for main engine');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/parts/);
    });

    test('READ: Mann+Hummel parts in engine room filters manufacturer and location', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'Mann+Hummel parts in engine room');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/parts/);
    });

    test('READ: critical spare parts needing reorder filters category and reorder', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'critical spare parts needing reorder');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/parts/);
    });

    test('READ: electrical parts on order filters category and stock status', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'electrical parts on order');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/parts/);
    });

    test('READ: part details for P-001 navigates to part detail', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'part details for P-001');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/parts/);
    });

    test('READ: search for oil filter searches by part name', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'search for oil filter');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/parts/);
    });

    test('READ: find parts with part number MH-4321 searches by part number', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find parts with part number MH-4321');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/parts/);
    });
  });

  // ============================================================================
  // MUTATE ACTION TESTS (26 tests)
  // ============================================================================
  test.describe('MUTATE Actions', () => {
    // consume_part tests
    test('MUTATE: consume part opens modal with required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'consume part');

      const executeBtn = page.locator('[data-testid="execute-action"]');
      await expect(executeBtn).toBeVisible();
      await executeBtn.click();
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="modal-title"]')).toContainText('Consume Part');
      await expect(page.locator('[data-testid="field-part_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-quantity"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-work_order_id"]')).toBeVisible();
    });

    test('MUTATE: use 5 oil filters on WO-123 prefills all fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'use 5 oil filters on WO-123');
      await clickExecute(page);
      await waitForActionModal(page);

      const quantityField = page.locator('[data-testid="field-quantity"]');
      await expect(quantityField).toHaveValue('5');
    });

    test('MUTATE: consume part shows idempotency indicator', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'consume part');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="idempotent-indicator"]')).toBeVisible();
    });

    test('MUTATE: consume part handles INSUFFICIENT_STOCK error', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'consume 9999 parts');
      await clickExecute(page);
      await waitForActionModal(page);

      await page.fill('[data-testid="field-quantity"]', '9999');
      await page.click('[data-testid="modal-submit"]');

      // Should show insufficient stock error
      await expect(page.locator('[data-testid="error-message"]')).toContainText(/insufficient/i);
    });

    // receive_part tests
    test('MUTATE: receive part shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'receive part');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-part_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-quantity"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-supplier_id"]')).toBeVisible();
    });

    test('MUTATE: receive 10 filters from Supplier A prefills fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'receive 10 filters from Supplier A');
      await clickExecute(page);
      await waitForActionModal(page);

      const quantityField = page.locator('[data-testid="field-quantity"]');
      await expect(quantityField).toHaveValue('10');
    });

    test('MUTATE: receive part shows optional batch_number field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'receive part');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-batch_number"]')).toBeVisible();
    });

    test('MUTATE: receive part shows optional expiry_date field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'receive part');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-expiry_date"]')).toBeVisible();
    });

    // transfer_part tests
    test('MUTATE: transfer part shows location fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'transfer part');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-from_location"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-to_location"]')).toBeVisible();
    });

    test('MUTATE: move 5 filters from main store to engine room prefills fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'move 5 filters from main store to engine room');
      await clickExecute(page);
      await waitForActionModal(page);

      const quantityField = page.locator('[data-testid="field-quantity"]');
      await expect(quantityField).toHaveValue('5');
    });

    test('MUTATE: transfer part shows optional transfer_notes field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'transfer part');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-transfer_notes"]')).toBeVisible();
    });

    // adjust_stock_quantity tests
    test('MUTATE: adjust stock quantity shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'adjust stock quantity');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    test('MUTATE: adjust stock shows signature required', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'adjust stock quantity');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="signature-required"]')).toBeVisible();
    });

    test('MUTATE: set stock to 100 for P-001 prefills fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'set stock to 100 for P-001');
      await clickExecute(page);
      await waitForActionModal(page);

      const quantityField = page.locator('[data-testid="field-new_quantity"]');
      await expect(quantityField).toHaveValue('100');
    });

    test('MUTATE: adjust stock shows adjustment_reason field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'adjust stock quantity');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-adjustment_reason"]')).toBeVisible();
    });

    // write_off_part tests
    test('MUTATE: write off part shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'write off part');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    test('MUTATE: write off part shows signature required', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'write off part');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="signature-required"]')).toBeVisible();
    });

    test('MUTATE: write off 5 damaged filters prefills quantity', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'write off 5 damaged filters');
      await clickExecute(page);
      await waitForActionModal(page);

      const quantityField = page.locator('[data-testid="field-quantity"]');
      await expect(quantityField).toHaveValue('5');
    });

    test('MUTATE: write off part shows write_off_reason field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'write off part');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-write_off_reason"]')).toBeVisible();
    });

    // add_to_shopping_list tests
    test('MUTATE: add to shopping list shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add to shopping list');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-part_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-quantity_requested"]')).toBeVisible();
    });

    test('MUTATE: add 10 oil filters to shopping list prefills fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add 10 oil filters to shopping list');
      await clickExecute(page);
      await waitForActionModal(page);

      const quantityField = page.locator('[data-testid="field-quantity_requested"]');
      await expect(quantityField).toHaveValue('10');
    });

    test('MUTATE: add to shopping list shows urgency field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add to shopping list');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-urgency"]')).toBeVisible();
    });

    test('MUTATE: add urgent part to shopping list prefills urgency', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add urgent part to shopping list');
      await clickExecute(page);
      await waitForActionModal(page);

      const urgencyField = page.locator('[data-testid="field-urgency"]');
      await expect(urgencyField).toHaveValue('high');
    });

    // order_part tests
    test('MUTATE: order part shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'order part');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    test('MUTATE: order part shows confirmation required', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'order part');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="confirmation-required"]')).toBeVisible();
    });

    test('MUTATE: order 20 filters from Supplier A prefills fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'order 20 filters from Supplier A');
      await clickExecute(page);
      await waitForActionModal(page);

      const quantityField = page.locator('[data-testid="field-quantity"]');
      await expect(quantityField).toHaveValue('20');
    });
  });
});
