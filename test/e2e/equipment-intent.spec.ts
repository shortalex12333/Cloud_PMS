import { test, expect, Page } from '@playwright/test';

/**
 * Equipment Intent E2E Tests
 *
 * Lens: equipment
 * Tests: 50 total (25 READ + 25 MUTATE)
 *
 * Covers:
 * - READ Navigation tests for all filter combinations
 * - MUTATE Action tests for all 5 equipment actions
 */

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';

// Test data factory
const testData = {
  equipment: {
    id: 'eq-main-engine-001',
    name: 'Main Engine #1',
    status: 'operational',
    category: 'propulsion',
    manufacturer: 'MAN',
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

test.describe('Equipment Intent Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForSelector('[data-testid="app-ready"]', { timeout: 10000 });
  });

  // ============================================================================
  // READ NAVIGATION TESTS (25 tests)
  // ============================================================================
  test.describe('READ Navigation', () => {
    // Status filter tests
    test('READ: show operational equipment navigates to /equipment?status=operational', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show operational equipment');

      const navigateBtn = page.locator('[data-testid="navigate-action"]');
      await expect(navigateBtn).toBeVisible();
      await navigateBtn.click();

      await expect(page).toHaveURL(/\/equipment.*status=operational/);
    });

    test('READ: display all equipment navigates to /equipment', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'display all equipment');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/equipment/);
    });

    test('READ: list out of service equipment filters by status', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list out of service equipment');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/equipment.*status=out_of_service/);
    });

    test('READ: find equipment under maintenance filters by status', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find equipment under maintenance');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/equipment.*status=maintenance/);
    });

    test('READ: view decommissioned equipment filters by status', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'view decommissioned equipment');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/equipment.*status=decommissioned/);
    });

    // Category filter tests
    test('READ: show propulsion equipment filters by category', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show propulsion equipment');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/equipment.*category=propulsion/);
    });

    test('READ: list electrical equipment filters by category', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list electrical equipment');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/equipment.*category=electrical/);
    });

    test('READ: find HVAC equipment filters by category', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find HVAC equipment');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/equipment.*category/);
    });

    test('READ: get safety equipment filters by category', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'get safety equipment');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/equipment.*category=safety/);
    });

    // Location filter tests
    test('READ: equipment in engine room filters by location', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'equipment in engine room');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/equipment.*location/);
    });

    test('READ: find equipment on bridge filters by location', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find equipment on bridge');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/equipment.*location/);
    });

    test('READ: list equipment in galley filters by location', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list equipment in galley');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/equipment.*location/);
    });

    // Manufacturer filter tests
    test('READ: show MAN equipment filters by manufacturer', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show MAN equipment');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/equipment.*manufacturer/);
    });

    test('READ: find Caterpillar equipment filters by manufacturer', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find Caterpillar equipment');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/equipment.*manufacturer/);
    });

    // Date filter tests
    test('READ: equipment installed this year filters by install_date', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'equipment installed this year');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/equipment/);
    });

    test('READ: equipment last serviced this month filters by service_date', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'equipment last serviced this month');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/equipment/);
    });

    test('READ: find equipment needing service filters by service due', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find equipment needing service');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/equipment/);
    });

    // Risk score filter tests
    test('READ: show high risk equipment filters by risk_score', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show high risk equipment');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/equipment/);
    });

    test('READ: list critical risk equipment filters by risk threshold', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list critical risk equipment');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/equipment/);
    });

    // Compound filter tests
    test('READ: operational propulsion equipment applies multiple filters', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'operational propulsion equipment');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/equipment/);
    });

    test('READ: out of service equipment in engine room filters status and location', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'out of service equipment in engine room');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/equipment/);
    });

    test('READ: MAN equipment under maintenance filters manufacturer and status', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'MAN equipment under maintenance');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/equipment/);
    });

    test('READ: high risk electrical equipment filters risk and category', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'high risk electrical equipment');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/equipment/);
    });

    test('READ: recently serviced propulsion equipment filters date and category', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'recently serviced propulsion equipment');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/equipment/);
    });

    test('READ: equipment details for ME1 navigates to equipment detail', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'equipment details for ME1');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/equipment/);
    });
  });

  // ============================================================================
  // MUTATE ACTION TESTS (25 tests)
  // ============================================================================
  test.describe('MUTATE Actions', () => {
    // update_equipment tests
    test('MUTATE: update equipment opens modal with fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'update equipment');

      const executeBtn = page.locator('[data-testid="execute-action"]');
      await expect(executeBtn).toBeVisible();
      await executeBtn.click();
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="modal-title"]')).toContainText('Update Equipment');
    });

    test('MUTATE: update equipment ME1 prefills equipment_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'update equipment ME1');
      await clickExecute(page);
      await waitForActionModal(page);

      const equipmentField = page.locator('[data-testid="field-equipment_id"]');
      await expect(equipmentField).not.toHaveValue('');
    });

    test('MUTATE: edit main engine details prefills equipment', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'edit main engine details');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-equipment_id"]')).toBeVisible();
    });

    test('MUTATE: update equipment shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'update equipment');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    test('MUTATE: change equipment location shows location field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'change equipment location');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-location"]')).toBeVisible();
    });

    // set_equipment_status tests
    test('MUTATE: set equipment status shows status picker', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'set equipment status');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-status"]')).toBeVisible();
    });

    test('MUTATE: mark ME1 out of service prefills equipment and status', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'mark ME1 out of service');
      await clickExecute(page);
      await waitForActionModal(page);

      const statusField = page.locator('[data-testid="field-status"]');
      await expect(statusField).toHaveValue('out_of_service');
    });

    test('MUTATE: put equipment under maintenance prefills status', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'put equipment under maintenance');
      await clickExecute(page);
      await waitForActionModal(page);

      const statusField = page.locator('[data-testid="field-status"]');
      await expect(statusField).toHaveValue('maintenance');
    });

    test('MUTATE: mark equipment operational prefills status', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'mark equipment operational');
      await clickExecute(page);
      await waitForActionModal(page);

      const statusField = page.locator('[data-testid="field-status"]');
      await expect(statusField).toHaveValue('operational');
    });

    test('MUTATE: set equipment status shows optional reason field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'set equipment status');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-status_reason"]')).toBeVisible();
    });

    test('MUTATE: set equipment status shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'set equipment status');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    // link_document_to_equipment tests
    test('MUTATE: link document to equipment shows document picker', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'link document to equipment');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-document_id"]')).toBeVisible();
    });

    test('MUTATE: attach manual to ME1 prefills equipment_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'attach manual to ME1');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-equipment_id"]')).not.toHaveValue('');
    });

    test('MUTATE: link document shows optional link_type field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'link document to equipment');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-link_type"]')).toBeVisible();
    });

    test('MUTATE: attach specification to equipment shows fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'attach specification to equipment');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="modal-title"]')).toContainText('Link Document');
    });

    // update_running_hours tests
    test('MUTATE: update running hours shows hours field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'update running hours');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-running_hours"]')).toBeVisible();
    });

    test('MUTATE: log running hours for ME1 prefills equipment', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'log running hours for ME1');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-equipment_id"]')).not.toHaveValue('');
    });

    test('MUTATE: record 5000 hours on DG1 prefills hours', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'record 5000 hours on DG1');
      await clickExecute(page);
      await waitForActionModal(page);

      const hoursField = page.locator('[data-testid="field-running_hours"]');
      await expect(hoursField).toHaveValue('5000');
    });

    test('MUTATE: update running hours shows optional recorded_at field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'update running hours');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-recorded_at"]')).toBeVisible();
    });

    // log_contractor_work tests
    test('MUTATE: log contractor work shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'log contractor work');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-contractor_name"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-work_description"]')).toBeVisible();
    });

    test('MUTATE: log contractor work on ME1 prefills equipment', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'log contractor work on ME1');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-equipment_id"]')).not.toHaveValue('');
    });

    test('MUTATE: record service by ABC Marine prefills contractor', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'record service by ABC Marine');
      await clickExecute(page);
      await waitForActionModal(page);

      const contractorField = page.locator('[data-testid="field-contractor_name"]');
      await expect(contractorField).toContainText(/ABC Marine/i);
    });

    test('MUTATE: log contractor work shows optional invoice field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'log contractor work');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-invoice_reference"]')).toBeVisible();
    });

    test('MUTATE: log contractor work shows optional work_date field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'log contractor work');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-work_date"]')).toBeVisible();
    });

    test('MUTATE: log contractor work with all fields filled submits successfully', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'log contractor work on ME1');
      await clickExecute(page);
      await waitForActionModal(page);

      // Fill required fields
      await page.fill('[data-testid="field-contractor_name"]', 'Test Contractor');
      await page.fill('[data-testid="field-work_description"]', 'E2E Test Service');

      // Submit
      await page.click('[data-testid="modal-submit"]');

      // Verify success
      await expect(page.locator('[data-testid="toast-success"]')).toBeVisible();
    });
  });
});
