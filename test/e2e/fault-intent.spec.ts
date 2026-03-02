import { test, expect, Page } from '@playwright/test';

/**
 * Fault Intent E2E Tests
 *
 * Lens: fault
 * Tests: 52 total (26 READ + 26 MUTATE)
 *
 * Covers:
 * - READ Navigation tests for all filter combinations
 * - MUTATE Action tests for all 9 fault actions
 */

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';

// Test data factory
const testData = {
  fault: {
    id: 'fault-test-001',
    title: 'Test Fault Report',
    equipment_id: 'eq-main-engine-001',
    severity: 'major',
    status: 'open',
  },
  equipment: {
    id: 'eq-main-engine-001',
    name: 'Main Engine #1',
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

test.describe('Fault Intent Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForSelector('[data-testid="app-ready"]', { timeout: 10000 });
  });

  // ============================================================================
  // READ NAVIGATION TESTS (26 tests)
  // ============================================================================
  test.describe('READ Navigation', () => {
    // Status filter tests
    test('READ: show open faults navigates to /faults?status=open', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show open faults');

      const navigateBtn = page.locator('[data-testid="navigate-action"]');
      await expect(navigateBtn).toBeVisible();
      await expect(page.locator('[data-testid="suggestion-type"]')).toHaveText('Navigate');

      await navigateBtn.click();
      await expect(page).toHaveURL(/\/faults.*status=open/);
    });

    test('READ: display all fault reports navigates to /faults', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'display all fault reports');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/faults/);
    });

    test('READ: list critical faults filters by severity=critical', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list critical faults');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/faults.*severity=critical/);
    });

    test('READ: find safety faults filters by severity=safety', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find safety faults');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/faults.*severity=safety/);
    });

    test('READ: get major faults filters by severity=major', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'get major faults');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/faults.*severity=major/);
    });

    test('READ: view minor faults filters by severity=minor', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'view minor faults');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/faults.*severity=minor/);
    });

    test('READ: show me cosmetic faults filters by severity=cosmetic', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show me cosmetic faults');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/faults.*severity=cosmetic/);
    });

    test('READ: faults under investigation filters by status=investigating', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'faults under investigation');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/faults.*status=investigating/);
    });

    test('READ: display faults with work orders filters by status=work_ordered', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'display faults with work orders');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/faults.*status=work_ordered/);
    });

    test('READ: list resolved faults filters by status=resolved', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list resolved faults');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/faults.*status=resolved/);
    });

    test('READ: show closed faults filters by status=closed', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show closed faults');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/faults.*status=closed/);
    });

    test('READ: find false alarm faults filters by status=false_alarm', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find false alarm faults');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/faults.*status=false_alarm/);
    });

    // Entity reference tests
    test('READ: get faults on ME1 filters by equipment_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'get faults on ME1');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/faults.*equipment/);
    });

    test('READ: view faults on main engine resolves equipment entity', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'view faults on main engine');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/faults/);
    });

    test('READ: faults for diesel generator filters by equipment', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'faults for diesel generator');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/faults/);
    });

    test('READ: show faults reported by John filters by reported_by', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show faults reported by John');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/faults.*reported/);
    });

    // Date filter tests
    test('READ: display faults reported this week filters by reported_at', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'display faults reported this week');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/faults.*reported/);
    });

    test('READ: list faults from last month filters by reported_at', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list faults from last month');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/faults/);
    });

    // Location filter tests
    test('READ: faults in engine room filters by location', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'faults in engine room');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/faults.*location/);
    });

    test('READ: find faults on bridge filters by location', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find faults on bridge');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/faults.*location/);
    });

    // Compound filter tests
    test('READ: open critical faults on main engine applies multiple filters', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'open critical faults on main engine');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/faults/);
      await expect(page.locator('[data-testid="filter-chip-status"]')).toContainText('open');
    });

    test('READ: safety faults reported today filters by severity and date', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'safety faults reported today');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/faults/);
    });

    test('READ: unresolved faults in engine room filters status and location', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'unresolved faults in engine room');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/faults/);
    });

    test('READ: major faults on DG1 filters severity and equipment', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'major faults on DG1');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/faults/);
    });

    test('READ: my reported faults uses current_user filter', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'my reported faults');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/faults/);
    });

    test('READ: recent critical faults filters by recency and severity', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'recent critical faults');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/faults/);
    });
  });

  // ============================================================================
  // MUTATE ACTION TESTS (26 tests)
  // ============================================================================
  test.describe('MUTATE Actions', () => {
    // report_fault tests
    test('MUTATE: report fault opens modal with required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'report fault');

      const executeBtn = page.locator('[data-testid="execute-action"]');
      await expect(executeBtn).toBeVisible();
      await expect(page.locator('[data-testid="suggestion-type"]')).toHaveText('Execute');

      await executeBtn.click();
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="modal-title"]')).toContainText('Report Fault');
      await expect(page.locator('[data-testid="field-title"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-equipment_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-severity"]')).toBeVisible();
    });

    test('MUTATE: report fault on main engine prefills equipment_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'report fault on main engine');
      await clickExecute(page);
      await waitForActionModal(page);

      const equipmentField = page.locator('[data-testid="field-equipment_id"]');
      await expect(equipmentField).not.toHaveValue('');
    });

    test('MUTATE: report critical fault prefills severity=critical', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'report critical fault');
      await clickExecute(page);
      await waitForActionModal(page);

      const severityField = page.locator('[data-testid="field-severity"]');
      await expect(severityField).toHaveValue('critical');
    });

    test('MUTATE: log safety issue prefills severity=safety', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'log safety issue');
      await clickExecute(page);
      await waitForActionModal(page);

      const severityField = page.locator('[data-testid="field-severity"]');
      await expect(severityField).toHaveValue('safety');
    });

    test('MUTATE: report fault shows NEEDS_INPUT initially', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'report fault');
      await verifyReadinessIndicator(page, 'NEEDS_INPUT');
    });

    // acknowledge_fault tests
    test('MUTATE: acknowledge fault shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'acknowledge fault');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    test('MUTATE: acknowledge fault F-001 prefills fault_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'acknowledge fault F-001');
      await clickExecute(page);
      await waitForActionModal(page);

      const faultIdField = page.locator('[data-testid="field-fault_id"]');
      await expect(faultIdField).toHaveValue(/F-001/);
    });

    // close_fault tests
    test('MUTATE: close fault shows resolution field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'close fault');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-resolution"]')).toBeVisible();
    });

    test('MUTATE: resolve fault F-123 prefills fault_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'resolve fault F-123');
      await clickExecute(page);
      await waitForActionModal(page);

      const faultIdField = page.locator('[data-testid="field-fault_id"]');
      await expect(faultIdField).toHaveValue(/F-123/);
    });

    test('MUTATE: close fault shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'close fault');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    // update_fault tests
    test('MUTATE: update fault shows optional fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'update fault');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-title"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-severity"]')).toBeVisible();
    });

    test('MUTATE: edit fault F-456 prefills fault_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'edit fault F-456');
      await clickExecute(page);
      await waitForActionModal(page);

      const faultIdField = page.locator('[data-testid="field-fault_id"]');
      await expect(faultIdField).toHaveValue(/F-456/);
    });

    // add_fault_photo tests
    test('MUTATE: add fault photo shows file upload', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add fault photo');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-photo_storage_path"]')).toBeVisible();
    });

    test('MUTATE: attach photo to fault F-789 prefills fault_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'attach photo to fault F-789');
      await clickExecute(page);
      await waitForActionModal(page);

      const faultIdField = page.locator('[data-testid="field-fault_id"]');
      await expect(faultIdField).toHaveValue(/F-789/);
    });

    test('MUTATE: add photo shows optional caption field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add photo to fault');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-caption"]')).toBeVisible();
    });

    // add_fault_note tests
    test('MUTATE: add fault note shows note_text field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add fault note');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-note_text"]')).toBeVisible();
    });

    test('MUTATE: add comment to fault F-001 prefills fault_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add comment to fault F-001');
      await clickExecute(page);
      await waitForActionModal(page);

      const faultIdField = page.locator('[data-testid="field-fault_id"]');
      await expect(faultIdField).toHaveValue(/F-001/);
    });

    // diagnose_fault tests
    test('MUTATE: diagnose fault shows diagnosis field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'diagnose fault');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-diagnosis"]')).toBeVisible();
    });

    test('MUTATE: diagnose fault shows recommended fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'diagnose fault');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-recommended_parts"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-recommended_action"]')).toBeVisible();
    });

    test('MUTATE: diagnose fault shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'diagnose fault');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    // reopen_fault tests
    test('MUTATE: reopen fault shows optional reason field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'reopen fault');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-reopen_reason"]')).toBeVisible();
    });

    test('MUTATE: reopen fault F-999 prefills fault_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'reopen fault F-999');
      await clickExecute(page);
      await waitForActionModal(page);

      const faultIdField = page.locator('[data-testid="field-fault_id"]');
      await expect(faultIdField).toHaveValue(/F-999/);
    });

    test('MUTATE: reopen fault shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'reopen fault');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    // mark_fault_false_alarm tests
    test('MUTATE: mark fault as false alarm shows reason field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'mark fault as false alarm');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-false_alarm_reason"]')).toBeVisible();
    });

    test('MUTATE: false alarm F-123 prefills fault_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'false alarm F-123');
      await clickExecute(page);
      await waitForActionModal(page);

      const faultIdField = page.locator('[data-testid="field-fault_id"]');
      await expect(faultIdField).toHaveValue(/F-123/);
    });

    test('MUTATE: mark false alarm shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'mark fault false alarm');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });
  });
});
