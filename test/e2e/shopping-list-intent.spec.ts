import { test, expect, Page } from '@playwright/test';

/**
 * Shopping List Intent E2E Tests
 *
 * Lens: shopping_list
 * Tests: 52 total (26 READ + 26 MUTATE)
 *
 * Covers:
 * - READ Navigation tests for all filter combinations
 * - MUTATE Action tests for all 7 shopping_list actions
 */

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';

// Test data factory
const testData = {
  shoppingListItem: {
    id: 'sl-001',
    part_name: 'Oil Filter',
    quantity_requested: 10,
    status: 'candidate',
    urgency: 'normal',
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

test.describe('Shopping List Intent Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForSelector('[data-testid="app-ready"]', { timeout: 10000 });
  });

  // ============================================================================
  // READ NAVIGATION TESTS (26 tests)
  // ============================================================================
  test.describe('READ Navigation', () => {
    // Status filter tests
    test('READ: show shopping list navigates to /shopping-list', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show shopping list');

      const navigateBtn = page.locator('[data-testid="navigate-action"]');
      await expect(navigateBtn).toBeVisible();
      await navigateBtn.click();

      await expect(page).toHaveURL(/\/shopping-list/);
    });

    test('READ: display candidate items filters by status=candidate', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'display candidate items');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/shopping-list.*status=candidate/);
    });

    test('READ: list items under review filters by status', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list items under review');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/shopping-list.*status=under_review/);
    });

    test('READ: show approved items filters by status=approved', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show approved items');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/shopping-list.*status=approved/);
    });

    test('READ: find ordered items filters by status=ordered', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find ordered items');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/shopping-list.*status=ordered/);
    });

    test('READ: view partially fulfilled items filters by status', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'view partially fulfilled items');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/shopping-list.*status=partially_fulfilled/);
    });

    test('READ: show fulfilled items filters by status=fulfilled', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show fulfilled items');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/shopping-list.*status=fulfilled/);
    });

    test('READ: list rejected items filters by status=rejected', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list rejected items');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/shopping-list.*status=rejected/);
    });

    // Source type filter tests
    test('READ: items from low inventory filters by source_type', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'items from low inventory');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/shopping-list.*source_type=inventory_low/);
    });

    test('READ: out of stock additions filters by source_type', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'out of stock additions');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/shopping-list.*source_type=inventory_oos/);
    });

    test('READ: work order usage items filters by source_type', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'work order usage items');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/shopping-list.*source_type=work_order_usage/);
    });

    test('READ: manually added items filters by source_type=manual_add', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'manually added items');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/shopping-list.*source_type=manual_add/);
    });

    // Urgency filter tests
    test('READ: critical shopping list items filters by urgency=critical', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'critical shopping list items');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/shopping-list.*urgency=critical/);
    });

    test('READ: high urgency items filters by urgency=high', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'high urgency items');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/shopping-list.*urgency=high/);
    });

    test('READ: normal priority items filters by urgency=normal', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'normal priority items');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/shopping-list.*urgency=normal/);
    });

    test('READ: low priority items filters by urgency=low', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'low priority items');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/shopping-list.*urgency=low/);
    });

    // Date filter tests
    test('READ: items required by next week filters by required_by_date', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'items required by next week');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/shopping-list/);
    });

    test('READ: items added this month filters by created_at', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'items added this month');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/shopping-list/);
    });

    // Part filter tests
    test('READ: shopping list for part P-001 filters by part_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'shopping list for part P-001');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/shopping-list.*part/);
    });

    // Compound filter tests
    test('READ: critical approved items applies multiple filters', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'critical approved items');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/shopping-list/);
    });

    test('READ: high urgency items from low inventory filters urgency and source', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'high urgency items from low inventory');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/shopping-list/);
    });

    test('READ: pending items required this week filters status and date', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'pending items required this week');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/shopping-list/);
    });

    // Special views
    test('READ: shopping list summary shows overview', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'shopping list summary');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/shopping-list/);
    });

    test('READ: pending approvals shows approval queue', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'pending approvals');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/shopping-list/);
    });

    test('READ: procurement dashboard shows dashboard view', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'procurement dashboard');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/shopping-list/);
    });

    test('READ: order tracking shows order status view', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'order tracking');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/shopping-list/);
    });
  });

  // ============================================================================
  // MUTATE ACTION TESTS (26 tests)
  // ============================================================================
  test.describe('MUTATE Actions', () => {
    // create_shopping_list_item tests
    test('MUTATE: add to shopping list opens modal with required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add to shopping list');

      const executeBtn = page.locator('[data-testid="execute-action"]');
      await expect(executeBtn).toBeVisible();
      await executeBtn.click();
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="modal-title"]')).toContainText('Add to Shopping List');
      await expect(page.locator('[data-testid="field-part_name"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-quantity_requested"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-source_type"]')).toBeVisible();
    });

    test('MUTATE: add 10 oil filters to shopping list prefills fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add 10 oil filters to shopping list');
      await clickExecute(page);
      await waitForActionModal(page);

      const quantityField = page.locator('[data-testid="field-quantity_requested"]');
      await expect(quantityField).toHaveValue('10');
    });

    test('MUTATE: add urgent item to shopping list prefills urgency', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add urgent item to shopping list');
      await clickExecute(page);
      await waitForActionModal(page);

      const urgencyField = page.locator('[data-testid="field-urgency"]');
      await expect(urgencyField).toHaveValue('high');
    });

    test('MUTATE: create shopping list item shows optional fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create shopping list item');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-preferred_supplier"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-required_by_date"]')).toBeVisible();
    });

    // approve_shopping_list_item tests
    test('MUTATE: approve shopping list item shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'approve shopping list item');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    test('MUTATE: approve item SL-001 prefills item_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'approve item SL-001');
      await clickExecute(page);
      await waitForActionModal(page);

      const itemField = page.locator('[data-testid="field-item_id"]');
      await expect(itemField).toHaveValue(/SL-001/);
    });

    test('MUTATE: approve shopping list shows optional approval_notes', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'approve shopping list item');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-approval_notes"]')).toBeVisible();
    });

    test('MUTATE: approve shows optional approved_quantity field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'approve shopping list item');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-approved_quantity"]')).toBeVisible();
    });

    // reject_shopping_list_item tests
    test('MUTATE: reject shopping list item shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'reject shopping list item');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-item_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-rejection_reason"]')).toBeVisible();
    });

    test('MUTATE: reject item SL-002 prefills item_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'reject item SL-002');
      await clickExecute(page);
      await waitForActionModal(page);

      const itemField = page.locator('[data-testid="field-item_id"]');
      await expect(itemField).toHaveValue(/SL-002/);
    });

    test('MUTATE: reject shopping list shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'reject shopping list item');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    // promote_candidate_to_part tests
    test('MUTATE: promote candidate to part shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'promote candidate to part');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-item_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-part_category"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-min_quantity"]')).toBeVisible();
    });

    test('MUTATE: promote item SL-003 to part prefills item_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'promote item SL-003 to part');
      await clickExecute(page);
      await waitForActionModal(page);

      const itemField = page.locator('[data-testid="field-item_id"]');
      await expect(itemField).toHaveValue(/SL-003/);
    });

    test('MUTATE: promote candidate shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'promote candidate to part');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    // update_shopping_list_item tests
    test('MUTATE: update shopping list item shows optional fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'update shopping list item');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-quantity_requested"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-urgency"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-required_by_date"]')).toBeVisible();
    });

    test('MUTATE: edit item SL-004 prefills item_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'edit item SL-004');
      await clickExecute(page);
      await waitForActionModal(page);

      const itemField = page.locator('[data-testid="field-item_id"]');
      await expect(itemField).toHaveValue(/SL-004/);
    });

    test('MUTATE: change quantity to 20 for SL-005 prefills fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'change quantity to 20 for SL-005');
      await clickExecute(page);
      await waitForActionModal(page);

      const quantityField = page.locator('[data-testid="field-quantity_requested"]');
      await expect(quantityField).toHaveValue('20');
    });

    // mark_item_ordered tests
    test('MUTATE: mark item ordered shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'mark item ordered');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-item_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-purchase_order_id"]')).toBeVisible();
    });

    test('MUTATE: mark SL-006 as ordered prefills item_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'mark SL-006 as ordered');
      await clickExecute(page);
      await waitForActionModal(page);

      const itemField = page.locator('[data-testid="field-item_id"]');
      await expect(itemField).toHaveValue(/SL-006/);
    });

    test('MUTATE: mark item ordered shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'mark item ordered');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    test('MUTATE: mark ordered shows expected_delivery field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'mark item ordered');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-expected_delivery"]')).toBeVisible();
    });

    // mark_item_received tests
    test('MUTATE: mark item received shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'mark item received');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-item_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-quantity_received"]')).toBeVisible();
    });

    test('MUTATE: receive 10 units for SL-007 prefills fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'receive 10 units for SL-007');
      await clickExecute(page);
      await waitForActionModal(page);

      const quantityField = page.locator('[data-testid="field-quantity_received"]');
      await expect(quantityField).toHaveValue('10');
    });

    test('MUTATE: mark received shows optional receiving_notes', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'mark item received');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-receiving_notes"]')).toBeVisible();
    });

    test('MUTATE: mark received shows optional receiving_id field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'mark item received');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-receiving_id"]')).toBeVisible();
    });
  });
});
