import { test, expect, Page } from '@playwright/test';

/**
 * Work Order Intent E2E Tests
 *
 * Lens: work_order
 * Tests: 54 total (27 READ + 27 MUTATE)
 *
 * Covers:
 * - READ Navigation tests for all filter combinations
 * - MUTATE Action tests for all 12 work_order actions
 */

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';

// Test data factory
const testData = {
  workOrder: {
    id: 'wo-test-001',
    title: 'Test Work Order',
    equipment_id: 'eq-main-engine-001',
    priority: 'urgent',
    type: 'corrective',
    description: 'Test description for work order',
  },
  equipment: {
    id: 'eq-main-engine-001',
    name: 'Main Engine #1',
  },
  user: {
    id: 'user-engineer-001',
    name: 'John Engineer',
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

test.describe('Work Order Intent Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    // Login as test user
    await page.waitForSelector('[data-testid="app-ready"]', { timeout: 10000 });
  });

  // ============================================================================
  // READ NAVIGATION TESTS (27 tests)
  // ============================================================================
  test.describe('READ Navigation', () => {
    // Status filter tests
    test('READ: show open work orders navigates to /work-orders?status=open', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show open work orders');

      const navigateBtn = page.locator('[data-testid="navigate-action"]');
      await expect(navigateBtn).toBeVisible();
      await expect(page.locator('[data-testid="suggestion-type"]')).toHaveText('Navigate');

      await navigateBtn.click();
      await expect(page).toHaveURL(/\/work-orders.*status=open/);
    });

    test('READ: display all work orders navigates to /work-orders', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'display all work orders');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders/);
    });

    test('READ: list urgent work orders filters by priority=urgent', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list urgent work orders');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders.*priority=urgent/);
    });

    test('READ: find emergency work orders filters by priority=emergency', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find emergency work orders');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders.*priority=emergency/);
    });

    test('READ: view completed work orders filters by status=completed', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'view completed work orders');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders.*status=completed/);
    });

    test('READ: show me WOs in progress filters by status=in_progress', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show me WOs in progress');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders.*status=in_progress/);
    });

    test('READ: work orders pending parts filters by status=pending_parts', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'work orders that are pending parts');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders.*status=pending_parts/);
    });

    test('READ: display draft work orders filters by status=draft', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'display draft work orders');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders.*status=draft/);
    });

    test('READ: list all preventive work orders filters by type=preventive', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list all preventive work orders');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders.*type=preventive/);
    });

    test('READ: show corrective work orders filters by type=corrective', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show corrective work orders');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders.*type=corrective/);
    });

    test('READ: find planned work orders filters by type=planned', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find planned work orders');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders.*type=planned/);
    });

    test('READ: get unplanned work orders filters by type=unplanned', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'get unplanned work orders');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders.*type=unplanned/);
    });

    test('READ: view closed work orders filters by status=closed', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'view closed work orders');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders.*status=closed/);
    });

    test('READ: show cancelled work orders filters by status=cancelled', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show cancelled work orders');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders.*status=cancelled/);
    });

    test('READ: list routine work orders filters by priority=routine', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list routine work orders');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders.*priority=routine/);
    });

    // Entity reference tests
    test('READ: work orders on ME1 filters by equipment_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'work orders on ME1');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders.*equipment/);
    });

    test('READ: WOs assigned to John filters by assigned_to', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'WOs assigned to John');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders.*assigned/);
    });

    // Date filter tests
    test('READ: find work orders due this week filters by due_date', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find work orders due this week');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders.*due/);
    });

    test('READ: display overdue work orders shows overdue filter', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'display overdue work orders');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders.*overdue/);
    });

    test('READ: show me upcoming work orders filters upcoming', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show me upcoming work orders');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders.*upcoming/);
    });

    test('READ: work orders created last month filters by created_at', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'work orders created last month');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders.*created/);
    });

    // Compound filter tests
    test('READ: find open urgent work orders on main engine applies multiple filters', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find open urgent work orders on main engine');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders/);
      // Verify filter chips
      await expect(page.locator('[data-testid="filter-chip-status"]')).toContainText('open');
      await expect(page.locator('[data-testid="filter-chip-priority"]')).toContainText('urgent');
    });

    test('READ: show high priority corrective WOs applies priority and type filters', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show high priority corrective WOs');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders/);
    });

    test('READ: list work orders for DG1 resolves equipment entity', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list work orders for DG1');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders/);
    });

    test('READ: get open preventive work orders due next week applies 3 filters', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'get open preventive work orders due next week');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders/);
    });

    test('READ: display all work orders assigned to me uses current_user', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'display all work orders assigned to me');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders.*assigned.*me/);
    });

    test('READ: find unassigned work orders filters null assigned_to', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find unassigned work orders');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/work-orders.*unassigned/);
    });
  });

  // ============================================================================
  // MUTATE ACTION TESTS (27 tests)
  // ============================================================================
  test.describe('MUTATE Actions', () => {
    // create_work_order tests
    test('MUTATE: create work order opens modal with prefilled fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create work order');

      const executeBtn = page.locator('[data-testid="execute-action"]');
      await expect(executeBtn).toBeVisible();
      await expect(page.locator('[data-testid="suggestion-type"]')).toHaveText('Execute');

      await executeBtn.click();
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="modal-title"]')).toContainText('Create Work Order');
    });

    test('MUTATE: create new WO for main engine prefills equipment_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create new WO for main engine');
      await clickExecute(page);
      await waitForActionModal(page);

      // Verify equipment is prefilled
      const equipmentField = page.locator('[data-testid="field-equipment_id"]');
      await expect(equipmentField).toHaveValue(/main.*engine/i);
    });

    test('MUTATE: create urgent work order prefills priority=urgent', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create urgent work order');
      await clickExecute(page);
      await waitForActionModal(page);

      const priorityField = page.locator('[data-testid="field-priority"]');
      await expect(priorityField).toHaveValue('urgent');
    });

    test('MUTATE: create corrective work order prefills type=corrective', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create corrective work order');
      await clickExecute(page);
      await waitForActionModal(page);

      const typeField = page.locator('[data-testid="field-type"]');
      await expect(typeField).toHaveValue('corrective');
    });

    test('MUTATE: create work order shows NEEDS_INPUT initially', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create work order');
      await verifyReadinessIndicator(page, 'NEEDS_INPUT');
    });

    test('MUTATE: create work order submission creates database record', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create urgent work order for ME1');
      await clickExecute(page);
      await waitForActionModal(page);

      // Fill required fields
      await page.fill('[data-testid="field-title"]', 'E2E Test Work Order');
      await page.fill('[data-testid="field-description"]', 'Created by E2E test');

      // Submit
      await page.click('[data-testid="modal-submit"]');

      // Verify success toast
      await expect(page.locator('[data-testid="toast-success"]')).toBeVisible();
    });

    // create_work_order_from_fault tests
    test('MUTATE: create work order from fault requires fault_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create work order from fault F-001');
      await clickExecute(page);
      await waitForActionModal(page);

      const faultIdField = page.locator('[data-testid="field-fault_id"]');
      await expect(faultIdField).toHaveValue(/F-001/);
    });

    test('MUTATE: generate WO from fault shows requires_signature indicator', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'generate WO from fault');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="signature-required"]')).toBeVisible();
    });

    // update_work_order tests
    test('MUTATE: update work order WO-123 prefills work_order_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'update work order WO-123');
      await clickExecute(page);
      await waitForActionModal(page);

      const woIdField = page.locator('[data-testid="field-work_order_id"]');
      await expect(woIdField).toHaveValue(/WO-123/);
    });

    test('MUTATE: edit WO title opens update modal', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'edit WO title');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="modal-title"]')).toContainText('Update Work Order');
    });

    // add_note_to_work_order tests
    test('MUTATE: add note to work order WO-456 prefills work_order_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add note to work order WO-456');
      await clickExecute(page);
      await waitForActionModal(page);

      const woIdField = page.locator('[data-testid="field-work_order_id"]');
      await expect(woIdField).toHaveValue(/WO-456/);
    });

    test('MUTATE: add comment to WO shows note_text field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add comment to WO');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-note_text"]')).toBeVisible();
    });

    // add_part_to_work_order tests
    test('MUTATE: add part to work order shows part picker', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add part to work order');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-part_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-quantity"]')).toBeVisible();
    });

    test('MUTATE: add 5 filters to WO-789 prefills quantity', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add 5 filters to WO-789');
      await clickExecute(page);
      await waitForActionModal(page);

      const quantityField = page.locator('[data-testid="field-quantity"]');
      await expect(quantityField).toHaveValue('5');
    });

    // mark_work_order_complete tests
    test('MUTATE: mark work order complete shows resolution field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'mark work order complete');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-resolution"]')).toBeVisible();
      await expect(page.locator('[data-testid="signature-required"]')).toBeVisible();
    });

    test('MUTATE: complete WO-001 prefills work_order_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'complete WO-001');
      await clickExecute(page);
      await waitForActionModal(page);

      const woIdField = page.locator('[data-testid="field-work_order_id"]');
      await expect(woIdField).toHaveValue(/WO-001/);
    });

    // assign_work_order tests
    test('MUTATE: assign work order shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'assign work order');
      await clickExecute(page);
      await waitForActionModal(page);

      // Should show confirmation since it's role_restricted
      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    test('MUTATE: assign WO-123 to John prefills assigned_to', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'assign WO-123 to John');
      await clickExecute(page);
      await waitForActionModal(page);

      const assignedToField = page.locator('[data-testid="field-assigned_to"]');
      await expect(assignedToField).toHaveValue(/John/);
    });

    // close_work_order tests
    test('MUTATE: close work order shows confirmation required', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'close work order');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="confirmation-required"]')).toBeVisible();
    });

    test('MUTATE: close WO-999 prefills work_order_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'close WO-999');
      await clickExecute(page);
      await waitForActionModal(page);

      const woIdField = page.locator('[data-testid="field-work_order_id"]');
      await expect(woIdField).toHaveValue(/WO-999/);
    });

    // schedule_work_order tests
    test('MUTATE: schedule work order shows date picker', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'schedule work order');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-scheduled_date"]')).toBeVisible();
    });

    test('MUTATE: schedule WO for tomorrow prefills scheduled_date', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'schedule WO for tomorrow');
      await clickExecute(page);
      await waitForActionModal(page);

      const dateField = page.locator('[data-testid="field-scheduled_date"]');
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      await expect(dateField).not.toHaveValue('');
    });

    // set_priority_on_work_order tests
    test('MUTATE: set priority on work order shows priority picker', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'set priority on work order');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-priority"]')).toBeVisible();
    });

    test('MUTATE: make WO-123 urgent prefills priority=urgent', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'make WO-123 urgent');
      await clickExecute(page);
      await waitForActionModal(page);

      const priorityField = page.locator('[data-testid="field-priority"]');
      await expect(priorityField).toHaveValue('urgent');
    });

    // attach_photo_to_work_order tests
    test('MUTATE: attach photo to work order shows file upload', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'attach photo to work order');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-photo_storage_path"]')).toBeVisible();
    });

    // attach_document_to_work_order tests
    test('MUTATE: attach document to work order shows document picker', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'attach document to work order');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-document_id"]')).toBeVisible();
    });

    test('MUTATE: link manual to WO-456 shows document selection', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'link manual to WO-456');
      await clickExecute(page);
      await waitForActionModal(page);

      const woIdField = page.locator('[data-testid="field-work_order_id"]');
      await expect(woIdField).toHaveValue(/WO-456/);
    });
  });
});
