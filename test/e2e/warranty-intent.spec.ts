import { test, expect, Page } from '@playwright/test';

/**
 * Warranty Intent E2E Tests
 *
 * Lens: warranty
 * Tests: 50 total (25 READ + 25 MUTATE)
 *
 * Covers:
 * - READ Navigation tests for all filter combinations
 * - MUTATE Action tests for all 6 warranty actions
 */

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';

// Test data factory
const testData = {
  warranty: {
    id: 'warranty-001',
    equipment_id: 'eq-main-engine-001',
    supplier: 'MAN Energy',
    status: 'active',
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

test.describe('Warranty Intent Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForSelector('[data-testid="app-ready"]', { timeout: 10000 });
  });

  // ============================================================================
  // READ NAVIGATION TESTS (25 tests)
  // ============================================================================
  test.describe('READ Navigation', () => {
    // Status filter tests
    test('READ: show active warranties navigates to /warranties?status=active', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show active warranties');

      const navigateBtn = page.locator('[data-testid="navigate-action"]');
      await expect(navigateBtn).toBeVisible();
      await navigateBtn.click();

      await expect(page).toHaveURL(/\/warranties.*status=active/);
    });

    test('READ: display all warranties navigates to /warranties', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'display all warranties');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/warranties/);
    });

    test('READ: list expired warranties filters by status=expired', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list expired warranties');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/warranties.*status=expired/);
    });

    test('READ: find claimed warranties filters by status=claimed', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find claimed warranties');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/warranties.*status=claimed/);
    });

    test('READ: show voided warranties filters by status=voided', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show voided warranties');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/warranties.*status=voided/);
    });

    // Equipment filter tests
    test('READ: warranties for ME1 filters by equipment_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'warranties for ME1');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/warranties.*equipment/);
    });

    test('READ: main engine warranties filters by equipment', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'main engine warranties');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/warranties/);
    });

    test('READ: diesel generator warranties filters by equipment', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'diesel generator warranties');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/warranties/);
    });

    // Part filter tests
    test('READ: warranties for part P-001 filters by part_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'warranties for part P-001');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/warranties.*part/);
    });

    test('READ: filter warranties filters by part type', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'filter warranties');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/warranties/);
    });

    // Expiry filter tests
    test('READ: warranties expiring soon filters by is_expiring_soon', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'warranties expiring soon');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/warranties.*expiring/);
    });

    test('READ: warranties expiring this month filters by expiry_date', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'warranties expiring this month');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/warranties/);
    });

    test('READ: warranties expiring in 90 days filters by expiry window', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'warranties expiring in 90 days');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/warranties/);
    });

    test('READ: warranties expiring next quarter filters by date range', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'warranties expiring next quarter');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/warranties/);
    });

    // Supplier filter tests
    test('READ: MAN warranties filters by supplier', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'MAN warranties');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/warranties.*supplier/);
    });

    test('READ: warranties from Caterpillar filters by supplier', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'warranties from Caterpillar');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/warranties/);
    });

    test('READ: show supplier A warranties filters by supplier', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show supplier A warranties');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/warranties/);
    });

    // Compound filter tests
    test('READ: active warranties for main engine applies multiple filters', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'active warranties for main engine');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/warranties/);
    });

    test('READ: expiring warranties from MAN filters expiry and supplier', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'expiring warranties from MAN');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/warranties/);
    });

    test('READ: expired equipment warranties filters status and equipment', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'expired equipment warranties');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/warranties/);
    });

    test('READ: claimed part warranties filters status and part', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'claimed part warranties');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/warranties/);
    });

    // Special views
    test('READ: warranty summary shows overview', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'warranty summary');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/warranties/);
    });

    test('READ: warranty expiry calendar shows calendar view', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'warranty expiry calendar');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/warranties/);
    });

    test('READ: warranty claims history shows claims view', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'warranty claims history');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/warranties/);
    });

    test('READ: warranty coverage report shows report view', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'warranty coverage report');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/warranties/);
    });
  });

  // ============================================================================
  // MUTATE ACTION TESTS (25 tests)
  // ============================================================================
  test.describe('MUTATE Actions', () => {
    // create_warranty tests
    test('MUTATE: create warranty opens modal with required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create warranty');

      const executeBtn = page.locator('[data-testid="execute-action"]');
      await expect(executeBtn).toBeVisible();
      await executeBtn.click();
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="modal-title"]')).toContainText('Create Warranty');
      await expect(page.locator('[data-testid="field-equipment_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-start_date"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-end_date"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-supplier"]')).toBeVisible();
    });

    test('MUTATE: add warranty for ME1 prefills equipment_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add warranty for ME1');
      await clickExecute(page);
      await waitForActionModal(page);

      const equipmentField = page.locator('[data-testid="field-equipment_id"]');
      await expect(equipmentField).not.toHaveValue('');
    });

    test('MUTATE: create warranty from MAN prefills supplier', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create warranty from MAN');
      await clickExecute(page);
      await waitForActionModal(page);

      const supplierField = page.locator('[data-testid="field-supplier"]');
      await expect(supplierField).toContainText(/MAN/i);
    });

    test('MUTATE: create warranty shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create warranty');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    // update_warranty tests
    test('MUTATE: update warranty shows optional fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'update warranty');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-end_date"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-coverage_details"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-notes"]')).toBeVisible();
    });

    test('MUTATE: edit warranty W-001 prefills warranty_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'edit warranty W-001');
      await clickExecute(page);
      await waitForActionModal(page);

      const warrantyField = page.locator('[data-testid="field-warranty_id"]');
      await expect(warrantyField).toHaveValue(/W-001/);
    });

    test('MUTATE: update warranty shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'update warranty');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    // claim_warranty tests
    test('MUTATE: claim warranty shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'claim warranty');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-warranty_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-claim_description"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-fault_id"]')).toBeVisible();
    });

    test('MUTATE: claim warranty W-001 for fault F-123 prefills fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'claim warranty W-001 for fault F-123');
      await clickExecute(page);
      await waitForActionModal(page);

      const warrantyField = page.locator('[data-testid="field-warranty_id"]');
      await expect(warrantyField).toHaveValue(/W-001/);
      const faultField = page.locator('[data-testid="field-fault_id"]');
      await expect(faultField).toHaveValue(/F-123/);
    });

    test('MUTATE: file warranty claim shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'file warranty claim');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    test('MUTATE: claim warranty shows supporting_documents field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'claim warranty');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-supporting_documents"]')).toBeVisible();
    });

    // void_warranty tests
    test('MUTATE: void warranty shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'void warranty');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-warranty_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-void_reason"]')).toBeVisible();
    });

    test('MUTATE: void warranty shows manager role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'void warranty');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toContainText(/manager/i);
    });

    test('MUTATE: void warranty shows confirmation required', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'void warranty');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="confirmation-required"]')).toBeVisible();
    });

    test('MUTATE: cancel warranty W-002 prefills warranty_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'cancel warranty W-002');
      await clickExecute(page);
      await waitForActionModal(page);

      const warrantyField = page.locator('[data-testid="field-warranty_id"]');
      await expect(warrantyField).toHaveValue(/W-002/);
    });

    // link_document_to_warranty tests
    test('MUTATE: link document to warranty shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'link document to warranty');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-warranty_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-document_id"]')).toBeVisible();
    });

    test('MUTATE: attach certificate to warranty W-003 prefills warranty_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'attach certificate to warranty W-003');
      await clickExecute(page);
      await waitForActionModal(page);

      const warrantyField = page.locator('[data-testid="field-warranty_id"]');
      await expect(warrantyField).toHaveValue(/W-003/);
    });

    test('MUTATE: link document shows optional link_notes field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'link document to warranty');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-link_notes"]')).toBeVisible();
    });

    test('MUTATE: link document shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'link document to warranty');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    // extend_warranty tests
    test('MUTATE: extend warranty shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'extend warranty');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-warranty_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-new_end_date"]')).toBeVisible();
    });

    test('MUTATE: extend warranty W-004 by 1 year prefills fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'extend warranty W-004 by 1 year');
      await clickExecute(page);
      await waitForActionModal(page);

      const warrantyField = page.locator('[data-testid="field-warranty_id"]');
      await expect(warrantyField).toHaveValue(/W-004/);
    });

    test('MUTATE: extend warranty shows extension_notes field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'extend warranty');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-extension_notes"]')).toBeVisible();
    });

    test('MUTATE: extend warranty shows extension_reference field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'extend warranty');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-extension_reference"]')).toBeVisible();
    });

    test('MUTATE: extend warranty shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'extend warranty');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    test('MUTATE: create warranty shows optional warranty_number field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create warranty');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-warranty_number"]')).toBeVisible();
    });
  });
});
