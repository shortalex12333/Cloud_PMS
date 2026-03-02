import { test, expect, Page } from '@playwright/test';

/**
 * Hours of Rest Intent E2E Tests
 *
 * Lens: hours_of_rest
 * Tests: 52 total (26 READ + 26 MUTATE)
 *
 * Covers:
 * - READ Navigation tests for all filter combinations
 * - MUTATE Action tests for all 8 hours_of_rest actions
 */

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';

// Test data factory
const testData = {
  hoursOfRest: {
    user_id: 'crew-001',
    record_date: '2024-01-15',
    rest_periods: [
      { start: '00:00', end: '06:00' },
      { start: '12:00', end: '18:00' },
    ],
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

test.describe('Hours of Rest Intent Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForSelector('[data-testid="app-ready"]', { timeout: 10000 });
  });

  // ============================================================================
  // READ NAVIGATION TESTS (26 tests)
  // ============================================================================
  test.describe('READ Navigation', () => {
    // Basic navigation tests
    test('READ: show hours of rest navigates to /hours-of-rest', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show hours of rest');

      const navigateBtn = page.locator('[data-testid="navigate-action"]');
      await expect(navigateBtn).toBeVisible();
      await navigateBtn.click();

      await expect(page).toHaveURL(/\/hours-of-rest/);
    });

    test('READ: display rest records navigates to /hours-of-rest', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'display rest records');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/hours-of-rest/);
    });

    test('READ: view work rest hours navigates to hours list', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'view work rest hours');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/hours-of-rest/);
    });

    // User filter tests
    test('READ: hours of rest for John filters by user', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'hours of rest for John');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/hours-of-rest.*user/);
    });

    test('READ: my hours of rest filters by current_user', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'my hours of rest');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/hours-of-rest/);
    });

    test('READ: rest hours for chief engineer filters by user', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'rest hours for chief engineer');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/hours-of-rest/);
    });

    // Date filter tests
    test('READ: hours of rest for today filters by record_date', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'hours of rest for today');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/hours-of-rest/);
    });

    test('READ: rest records for this week filters by date range', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'rest records for this week');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/hours-of-rest/);
    });

    test('READ: hours of rest last month filters by date range', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'hours of rest last month');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/hours-of-rest/);
    });

    test('READ: rest hours between Jan 1 and Jan 15 filters by date range', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'rest hours between Jan 1 and Jan 15');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/hours-of-rest/);
    });

    // Compliance filter tests
    test('READ: non-compliant daily rest filters by is_daily_compliant=false', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'non-compliant daily rest');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/hours-of-rest.*compliant/);
    });

    test('READ: show daily compliance violations filters by compliance', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show daily compliance violations');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/hours-of-rest/);
    });

    test('READ: non-compliant weekly rest filters by is_weekly_compliant=false', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'non-compliant weekly rest');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/hours-of-rest/);
    });

    test('READ: show weekly compliance violations filters by compliance', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show weekly compliance violations');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/hours-of-rest/);
    });

    test('READ: compliant rest records filters by compliance=true', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'compliant rest records');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/hours-of-rest/);
    });

    // Warning status filter tests
    test('READ: active rest warnings filters by warning_status=active', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'active rest warnings');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/hours-of-rest.*warning/);
    });

    test('READ: acknowledged warnings filters by warning_status', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'acknowledged warnings');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/hours-of-rest/);
    });

    test('READ: dismissed warnings filters by warning_status', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'dismissed warnings');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/hours-of-rest/);
    });

    // Compound filter tests
    test('READ: non-compliant rest for John this week applies multiple filters', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'non-compliant rest for John this week');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/hours-of-rest/);
    });

    test('READ: my active warnings this month filters user and warning', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'my active warnings this month');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/hours-of-rest/);
    });

    test('READ: weekly non-compliance for crew filters compliance and scope', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'weekly non-compliance for crew');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/hours-of-rest/);
    });

    // Special views
    test('READ: hours of rest compliance summary shows overview', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'hours of rest compliance summary');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/hours-of-rest/);
    });

    test('READ: MLC compliance report shows compliance view', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'MLC compliance report');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/hours-of-rest/);
    });

    test('READ: STCW rest hours shows compliance view', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'STCW rest hours');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/hours-of-rest/);
    });

    test('READ: crew rest hours dashboard shows dashboard', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'crew rest hours dashboard');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/hours-of-rest/);
    });

    test('READ: monthly rest hours summary shows monthly view', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'monthly rest hours summary');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/hours-of-rest/);
    });
  });

  // ============================================================================
  // MUTATE ACTION TESTS (26 tests)
  // ============================================================================
  test.describe('MUTATE Actions', () => {
    // log_hours_of_rest tests
    test('MUTATE: log hours of rest opens modal with required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'log hours of rest');

      const executeBtn = page.locator('[data-testid="execute-action"]');
      await expect(executeBtn).toBeVisible();
      await executeBtn.click();
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="modal-title"]')).toContainText('Log Hours');
      await expect(page.locator('[data-testid="field-record_date"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-rest_periods"]')).toBeVisible();
    });

    test('MUTATE: log rest for today prefills record_date', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'log rest for today');
      await clickExecute(page);
      await waitForActionModal(page);

      const dateField = page.locator('[data-testid="field-record_date"]');
      await expect(dateField).not.toHaveValue('');
    });

    test('MUTATE: log hours of rest shows confirmation required', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'log hours of rest');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="confirmation-required"]')).toBeVisible();
    });

    test('MUTATE: record rest periods shows rest period editor', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'record rest periods');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="rest-period-editor"]')).toBeVisible();
    });

    // upsert_hours_of_rest tests
    test('MUTATE: upsert hours of rest shows all fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'update hours of rest');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-user_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-record_date"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-rest_periods"]')).toBeVisible();
    });

    test('MUTATE: update rest hours for John prefills user_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'update rest hours for John');
      await clickExecute(page);
      await waitForActionModal(page);

      const userField = page.locator('[data-testid="field-user_id"]');
      await expect(userField).not.toHaveValue('');
    });

    test('MUTATE: upsert shows optional total_rest_hours field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'update hours of rest');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-total_rest_hours"]')).toBeVisible();
    });

    // create_monthly_signoff tests
    test('MUTATE: create monthly signoff shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create monthly signoff');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-user_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-month"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-year"]')).toBeVisible();
    });

    test('MUTATE: create monthly signoff shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create monthly signoff');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    test('MUTATE: create January signoff for John prefills fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create January signoff for John');
      await clickExecute(page);
      await waitForActionModal(page);

      const monthField = page.locator('[data-testid="field-month"]');
      await expect(monthField).toHaveValue('1');
    });

    // sign_monthly_signoff tests
    test('MUTATE: sign monthly signoff shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'sign monthly signoff');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-signoff_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-signature_type"]')).toBeVisible();
    });

    test('MUTATE: sign monthly signoff shows signature required', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'sign monthly signoff');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="signature-required"]')).toBeVisible();
    });

    test('MUTATE: crew sign signoff S-001 prefills signoff_id and type', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'crew sign signoff S-001');
      await clickExecute(page);
      await waitForActionModal(page);

      const typeField = page.locator('[data-testid="field-signature_type"]');
      await expect(typeField).toHaveValue('crew');
    });

    test('MUTATE: HOD sign signoff prefills signature_type=hod', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'HOD sign signoff');
      await clickExecute(page);
      await waitForActionModal(page);

      const typeField = page.locator('[data-testid="field-signature_type"]');
      await expect(typeField).toHaveValue('hod');
    });

    test('MUTATE: captain sign signoff prefills signature_type=captain', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'captain sign signoff');
      await clickExecute(page);
      await waitForActionModal(page);

      const typeField = page.locator('[data-testid="field-signature_type"]');
      await expect(typeField).toHaveValue('captain');
    });

    // create_crew_template tests
    test('MUTATE: create crew template shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create crew template');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-template_name"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-rest_periods"]')).toBeVisible();
    });

    test('MUTATE: create rest template shows description field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create rest template');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-description"]')).toBeVisible();
    });

    // apply_crew_template tests
    test('MUTATE: apply crew template shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'apply crew template');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-template_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-start_date"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-end_date"]')).toBeVisible();
    });

    test('MUTATE: apply template T-001 for this week prefills fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'apply template T-001 for this week');
      await clickExecute(page);
      await waitForActionModal(page);

      const templateField = page.locator('[data-testid="field-template_id"]');
      await expect(templateField).toHaveValue(/T-001/);
    });

    // acknowledge_warning tests
    test('MUTATE: acknowledge warning shows required field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'acknowledge warning');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-warning_id"]')).toBeVisible();
    });

    test('MUTATE: acknowledge warning W-001 prefills warning_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'acknowledge warning W-001');
      await clickExecute(page);
      await waitForActionModal(page);

      const warningField = page.locator('[data-testid="field-warning_id"]');
      await expect(warningField).toHaveValue(/W-001/);
    });

    test('MUTATE: acknowledge warning shows optional notes field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'acknowledge warning');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-acknowledgment_notes"]')).toBeVisible();
    });

    // dismiss_warning tests
    test('MUTATE: dismiss warning shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'dismiss warning');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-warning_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-dismissal_reason"]')).toBeVisible();
    });

    test('MUTATE: dismiss warning shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'dismiss warning');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    test('MUTATE: dismiss warning W-002 prefills warning_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'dismiss warning W-002');
      await clickExecute(page);
      await waitForActionModal(page);

      const warningField = page.locator('[data-testid="field-warning_id"]');
      await expect(warningField).toHaveValue(/W-002/);
    });
  });
});
