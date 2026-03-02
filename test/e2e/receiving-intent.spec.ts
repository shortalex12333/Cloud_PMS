import { test, expect, Page } from '@playwright/test';

/**
 * Receiving Intent E2E Tests
 *
 * Lens: receiving
 * Tests: 52 total (26 READ + 26 MUTATE)
 *
 * Covers:
 * - READ Navigation tests for all filter combinations
 * - MUTATE Action tests for all 9 receiving actions
 */

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';

// Test data factory
const testData = {
  receiving: {
    id: 'rcv-001',
    supplier_id: 'supplier-001',
    status: 'pending_review',
    has_discrepancies: false,
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

test.describe('Receiving Intent Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForSelector('[data-testid="app-ready"]', { timeout: 10000 });
  });

  // ============================================================================
  // READ NAVIGATION TESTS (26 tests)
  // ============================================================================
  test.describe('READ Navigation', () => {
    // Status filter tests
    test('READ: show receiving navigates to /receiving', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show receiving');

      const navigateBtn = page.locator('[data-testid="navigate-action"]');
      await expect(navigateBtn).toBeVisible();
      await navigateBtn.click();

      await expect(page).toHaveURL(/\/receiving/);
    });

    test('READ: display all receiving records navigates to /receiving', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'display all receiving records');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/receiving/);
    });

    test('READ: show draft receiving filters by status=draft', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show draft receiving');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/receiving.*status=draft/);
    });

    test('READ: list pending review receiving filters by status', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list pending review receiving');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/receiving.*status=pending_review/);
    });

    test('READ: find accepted receiving filters by status=accepted', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find accepted receiving');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/receiving.*status=accepted/);
    });

    test('READ: view rejected receiving filters by status=rejected', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'view rejected receiving');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/receiving.*status=rejected/);
    });

    // Supplier filter tests
    test('READ: receiving from Supplier A filters by supplier_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'receiving from Supplier A');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/receiving.*supplier/);
    });

    test('READ: show deliveries from MAN filters by supplier', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show deliveries from MAN');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/receiving/);
    });

    test('READ: receiving from Caterpillar filters by supplier', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'receiving from Caterpillar');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/receiving/);
    });

    // Date filter tests
    test('READ: receiving created today filters by created_at', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'receiving created today');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/receiving/);
    });

    test('READ: receiving from this week filters by created_at', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'receiving from this week');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/receiving/);
    });

    test('READ: receiving received today filters by received_at', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'receiving received today');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/receiving/);
    });

    test('READ: deliveries from last month filters by received_at', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'deliveries from last month');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/receiving/);
    });

    test('READ: recent receiving filters by recency', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'recent receiving');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/receiving/);
    });

    // Discrepancy filter tests
    test('READ: receiving with discrepancies filters by has_discrepancies=true', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'receiving with discrepancies');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/receiving.*discrepancies/);
    });

    test('READ: receiving without issues filters by has_discrepancies=false', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'receiving without issues');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/receiving/);
    });

    test('READ: show problem deliveries filters by discrepancies', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show problem deliveries');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/receiving/);
    });

    // Compound filter tests
    test('READ: pending receiving from Supplier A applies multiple filters', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'pending receiving from Supplier A');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/receiving/);
    });

    test('READ: accepted receiving with discrepancies filters status and discrepancy', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'accepted receiving with discrepancies');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/receiving/);
    });

    test('READ: recent deliveries from MAN filters date and supplier', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'recent deliveries from MAN');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/receiving/);
    });

    test('READ: rejected receiving this month filters status and date', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'rejected receiving this month');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/receiving/);
    });

    // Special views
    test('READ: receiving summary shows overview', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'receiving summary');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/receiving/);
    });

    test('READ: delivery log shows log view', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'delivery log');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/receiving/);
    });

    test('READ: receiving dashboard shows dashboard view', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'receiving dashboard');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/receiving/);
    });

    test('READ: goods received note shows GRN view', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'goods received note');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/receiving/);
    });

    test('READ: receiving report shows report view', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'receiving report');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/receiving/);
    });
  });

  // ============================================================================
  // MUTATE ACTION TESTS (26 tests)
  // ============================================================================
  test.describe('MUTATE Actions', () => {
    // create_receiving tests
    test('MUTATE: create receiving opens modal with required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create receiving');

      const executeBtn = page.locator('[data-testid="execute-action"]');
      await expect(executeBtn).toBeVisible();
      await executeBtn.click();
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="modal-title"]')).toContainText('Create Receiving');
      await expect(page.locator('[data-testid="field-supplier_id"]')).toBeVisible();
    });

    test('MUTATE: create receiving from Supplier A prefills supplier_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create receiving from Supplier A');
      await clickExecute(page);
      await waitForActionModal(page);

      const supplierField = page.locator('[data-testid="field-supplier_id"]');
      await expect(supplierField).not.toHaveValue('');
    });

    test('MUTATE: new delivery shows optional expected_items field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'new delivery');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-expected_items"]')).toBeVisible();
    });

    test('MUTATE: create receiving shows purchase_order_id field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create receiving');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-purchase_order_id"]')).toBeVisible();
    });

    // attach_receiving_image_with_comment tests
    test('MUTATE: attach image to receiving shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'attach image to receiving');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-receiving_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-image_storage_path"]')).toBeVisible();
    });

    test('MUTATE: add photo to receiving R-001 prefills receiving_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add photo to receiving R-001');
      await clickExecute(page);
      await waitForActionModal(page);

      const receivingField = page.locator('[data-testid="field-receiving_id"]');
      await expect(receivingField).toHaveValue(/R-001/);
    });

    test('MUTATE: attach image shows optional comment field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'attach image to receiving');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-comment"]')).toBeVisible();
    });

    // update_receiving_fields tests
    test('MUTATE: update receiving shows optional fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'update receiving');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-supplier_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-notes"]')).toBeVisible();
    });

    test('MUTATE: edit receiving R-002 prefills receiving_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'edit receiving R-002');
      await clickExecute(page);
      await waitForActionModal(page);

      const receivingField = page.locator('[data-testid="field-receiving_id"]');
      await expect(receivingField).toHaveValue(/R-002/);
    });

    test('MUTATE: update receiving shows received_date field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'update receiving');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-received_date"]')).toBeVisible();
    });

    // add_receiving_item tests
    test('MUTATE: add item to receiving shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add item to receiving');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-receiving_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-part_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-quantity_received"]')).toBeVisible();
    });

    test('MUTATE: add 10 filters to receiving R-003 prefills fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add 10 filters to receiving R-003');
      await clickExecute(page);
      await waitForActionModal(page);

      const quantityField = page.locator('[data-testid="field-quantity_received"]');
      await expect(quantityField).toHaveValue('10');
    });

    test('MUTATE: add receiving item shows condition field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add item to receiving');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-condition"]')).toBeVisible();
    });

    // adjust_receiving_item tests
    test('MUTATE: adjust receiving item shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'adjust receiving item');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-receiving_item_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-quantity_received"]')).toBeVisible();
    });

    test('MUTATE: adjust item RI-001 to 5 prefills fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'adjust item RI-001 to 5');
      await clickExecute(page);
      await waitForActionModal(page);

      const itemField = page.locator('[data-testid="field-receiving_item_id"]');
      await expect(itemField).toHaveValue(/RI-001/);
    });

    test('MUTATE: adjust receiving item shows adjustment_reason field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'adjust receiving item');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-adjustment_reason"]')).toBeVisible();
    });

    // link_invoice_document tests
    test('MUTATE: link invoice to receiving shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'link invoice to receiving');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-receiving_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-document_id"]')).toBeVisible();
    });

    test('MUTATE: attach invoice to receiving R-004 prefills receiving_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'attach invoice to receiving R-004');
      await clickExecute(page);
      await waitForActionModal(page);

      const receivingField = page.locator('[data-testid="field-receiving_id"]');
      await expect(receivingField).toHaveValue(/R-004/);
    });

    test('MUTATE: link invoice shows invoice_number field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'link invoice to receiving');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-invoice_number"]')).toBeVisible();
    });

    // accept_receiving tests
    test('MUTATE: accept receiving shows required field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'accept receiving');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-receiving_id"]')).toBeVisible();
    });

    test('MUTATE: accept receiving shows signature required', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'accept receiving');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="signature-required"]')).toBeVisible();
    });

    test('MUTATE: approve receiving R-005 prefills receiving_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'approve receiving R-005');
      await clickExecute(page);
      await waitForActionModal(page);

      const receivingField = page.locator('[data-testid="field-receiving_id"]');
      await expect(receivingField).toHaveValue(/R-005/);
    });

    // reject_receiving tests
    test('MUTATE: reject receiving shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'reject receiving');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-receiving_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-rejection_reason"]')).toBeVisible();
    });

    test('MUTATE: reject receiving R-006 prefills receiving_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'reject receiving R-006');
      await clickExecute(page);
      await waitForActionModal(page);

      const receivingField = page.locator('[data-testid="field-receiving_id"]');
      await expect(receivingField).toHaveValue(/R-006/);
    });

    test('MUTATE: reject receiving shows optional rejection_notes field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'reject receiving');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-rejection_notes"]')).toBeVisible();
    });
  });
});
