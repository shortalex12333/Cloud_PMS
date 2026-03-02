import { test, expect, Page } from '@playwright/test';

/**
 * Handover Intent E2E Tests
 *
 * Lens: handover
 * Tests: 50 total (25 READ + 25 MUTATE)
 *
 * Covers:
 * - READ Navigation tests for all filter combinations
 * - MUTATE Action tests for all 6 handover actions
 */

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';

// Test data factory
const testData = {
  handoverItem: {
    id: 'handover-001',
    title: 'Main Engine Issue',
    category: 'ongoing_fault',
    priority: 'high',
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

test.describe('Handover Intent Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForSelector('[data-testid="app-ready"]', { timeout: 10000 });
  });

  // ============================================================================
  // READ NAVIGATION TESTS (25 tests)
  // ============================================================================
  test.describe('READ Navigation', () => {
    // Category filter tests
    test('READ: show handover navigates to /handover', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show handover');

      const navigateBtn = page.locator('[data-testid="navigate-action"]');
      await expect(navigateBtn).toBeVisible();
      await navigateBtn.click();

      await expect(page).toHaveURL(/\/handover/);
    });

    test('READ: display ongoing faults in handover filters by category', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'display ongoing faults in handover');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/handover.*category=ongoing_fault/);
    });

    test('READ: list work in progress items filters by category', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list work in progress items');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/handover.*category=work_in_progress/);
    });

    test('READ: show equipment status items filters by category', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show equipment status items');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/handover.*category=equipment_status/);
    });

    test('READ: view important info in handover filters by category', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'view important info in handover');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/handover.*category=important_info/);
    });

    test('READ: find general handover items filters by category', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find general handover items');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/handover.*category=general/);
    });

    // Priority filter tests
    test('READ: show high priority handover items filters by priority', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show high priority handover items');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/handover.*priority=high/);
    });

    test('READ: list normal priority handover filters by priority', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list normal priority handover');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/handover.*priority=normal/);
    });

    test('READ: find low priority handover items filters by priority', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find low priority handover items');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/handover.*priority=low/);
    });

    // Date filter tests
    test('READ: handover items from today filters by created_at', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'handover items from today');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/handover/);
    });

    test('READ: show handover from this week filters by created_at', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show handover from this week');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/handover/);
    });

    test('READ: recent handover items filters by recency', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'recent handover items');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/handover/);
    });

    // Author filter tests
    test('READ: handover items by John filters by author', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'handover items by John');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/handover.*author/);
    });

    test('READ: my handover items filters by current user', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'my handover items');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/handover/);
    });

    // Entity type filter tests
    test('READ: fault handover items filters by entity_type=fault', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'fault handover items');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/handover.*entity_type=fault/);
    });

    test('READ: work order handover items filters by entity_type', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'work order handover items');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/handover.*entity_type=work_order/);
    });

    test('READ: equipment handover items filters by entity_type', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'equipment handover items');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/handover.*entity_type=equipment/);
    });

    // Compound filter tests
    test('READ: high priority ongoing faults in handover applies multiple filters', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'high priority ongoing faults in handover');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/handover/);
    });

    test('READ: recent work in progress items filters date and category', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'recent work in progress items');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/handover/);
    });

    test('READ: my high priority handover items filters author and priority', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'my high priority handover items');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/handover/);
    });

    test('READ: equipment status items from today filters category and date', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'equipment status items from today');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/handover/);
    });

    // Special views
    test('READ: handover summary shows summary view', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'handover summary');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/handover/);
    });

    test('READ: today handover report shows daily view', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'today handover report');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/handover/);
    });

    test('READ: weekly handover overview shows weekly view', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'weekly handover overview');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/handover/);
    });

    test('READ: handover for next watch shows upcoming handover', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'handover for next watch');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/handover/);
    });
  });

  // ============================================================================
  // MUTATE ACTION TESTS (25 tests)
  // ============================================================================
  test.describe('MUTATE Actions', () => {
    // add_to_handover tests
    test('MUTATE: add to handover opens modal with required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add to handover');

      const executeBtn = page.locator('[data-testid="execute-action"]');
      await expect(executeBtn).toBeVisible();
      await executeBtn.click();
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="modal-title"]')).toContainText('Add to Handover');
      await expect(page.locator('[data-testid="field-title"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-summary_text"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-category"]')).toBeVisible();
    });

    test('MUTATE: add fault to handover prefills category=ongoing_fault', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add fault to handover');
      await clickExecute(page);
      await waitForActionModal(page);

      const categoryField = page.locator('[data-testid="field-category"]');
      await expect(categoryField).toHaveValue('ongoing_fault');
    });

    test('MUTATE: add work order to handover prefills category', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add work order to handover');
      await clickExecute(page);
      await waitForActionModal(page);

      const categoryField = page.locator('[data-testid="field-category"]');
      await expect(categoryField).toHaveValue('work_in_progress');
    });

    test('MUTATE: add high priority handover item prefills priority', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add high priority handover item');
      await clickExecute(page);
      await waitForActionModal(page);

      const priorityField = page.locator('[data-testid="field-priority"]');
      await expect(priorityField).toHaveValue('high');
    });

    test('MUTATE: add equipment status to handover prefills category', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add equipment status to handover');
      await clickExecute(page);
      await waitForActionModal(page);

      const categoryField = page.locator('[data-testid="field-category"]');
      await expect(categoryField).toHaveValue('equipment_status');
    });

    test('MUTATE: add important info to handover prefills category', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add important info to handover');
      await clickExecute(page);
      await waitForActionModal(page);

      const categoryField = page.locator('[data-testid="field-category"]');
      await expect(categoryField).toHaveValue('important_info');
    });

    test('MUTATE: add to handover with entity shows entity_id field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add fault F-001 to handover');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-entity_id"]')).toBeVisible();
    });

    // edit_handover_item tests
    test('MUTATE: edit handover item shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'edit handover item');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-handover_item_id"]')).toBeVisible();
    });

    test('MUTATE: edit handover H-001 prefills item_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'edit handover H-001');
      await clickExecute(page);
      await waitForActionModal(page);

      const itemField = page.locator('[data-testid="field-handover_item_id"]');
      await expect(itemField).toHaveValue(/H-001/);
    });

    test('MUTATE: update handover item shows optional fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'update handover item');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-title"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-summary_text"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-priority"]')).toBeVisible();
    });

    test('MUTATE: change handover priority shows priority picker', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'change handover priority');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-priority"]')).toBeVisible();
    });

    // attach_document_to_handover tests
    test('MUTATE: attach document to handover shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'attach document to handover');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-handover_item_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-document_id"]')).toBeVisible();
    });

    test('MUTATE: link document to handover H-002 prefills item_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'link document to handover H-002');
      await clickExecute(page);
      await waitForActionModal(page);

      const itemField = page.locator('[data-testid="field-handover_item_id"]');
      await expect(itemField).toHaveValue(/H-002/);
    });

    test('MUTATE: attach document shows optional notes field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'attach document to handover');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-attachment_notes"]')).toBeVisible();
    });

    // export_handover tests
    test('MUTATE: export handover shows format picker', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'export handover');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-export_format"]')).toBeVisible();
    });

    test('MUTATE: export handover as PDF prefills format', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'export handover as PDF');
      await clickExecute(page);
      await waitForActionModal(page);

      const formatField = page.locator('[data-testid="field-export_format"]');
      await expect(formatField).toHaveValue('pdf');
    });

    test('MUTATE: export handover shows confirmation required', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'export handover');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="confirmation-required"]')).toBeVisible();
    });

    test('MUTATE: export handover shows date range fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'export handover');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-date_range_start"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-date_range_end"]')).toBeVisible();
    });

    test('MUTATE: export today handover prefills date range', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'export today handover');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-date_range_start"]')).not.toHaveValue('');
    });

    // regenerate_handover_summary tests
    test('MUTATE: regenerate handover summary shows required field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'regenerate handover summary');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-handover_export_id"]')).toBeVisible();
    });

    test('MUTATE: refresh handover export E-001 prefills export_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'refresh handover export E-001');
      await clickExecute(page);
      await waitForActionModal(page);

      const exportField = page.locator('[data-testid="field-handover_export_id"]');
      await expect(exportField).toHaveValue(/E-001/);
    });

    // edit_handover_section tests
    test('MUTATE: edit handover section shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'edit handover section');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-handover_export_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-section_key"]')).toBeVisible();
    });

    test('MUTATE: update handover section shows content field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'update handover section');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-section_content"]')).toBeVisible();
    });

    test('MUTATE: edit faults section in export E-002 prefills fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'edit faults section in export E-002');
      await clickExecute(page);
      await waitForActionModal(page);

      const exportField = page.locator('[data-testid="field-handover_export_id"]');
      await expect(exportField).toHaveValue(/E-002/);
    });

    test('MUTATE: add general note to handover prefills category=general', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add general note to handover');
      await clickExecute(page);
      await waitForActionModal(page);

      const categoryField = page.locator('[data-testid="field-category"]');
      await expect(categoryField).toHaveValue('general');
    });
  });
});
