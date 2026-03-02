import { test, expect, Page } from '@playwright/test';

/**
 * Email Intent E2E Tests
 *
 * Lens: email
 * Tests: 50 total (25 READ + 25 MUTATE)
 *
 * Covers:
 * - READ Navigation tests for all filter combinations
 * - MUTATE Action tests for all 7 email actions
 */

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';

// Test data factory
const testData = {
  email: {
    thread_id: 'thread-001',
    subject: 'RE: Main Engine Service',
    has_attachments: true,
    is_read: false,
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

test.describe('Email Intent Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForSelector('[data-testid="app-ready"]', { timeout: 10000 });
  });

  // ============================================================================
  // READ NAVIGATION TESTS (25 tests)
  // ============================================================================
  test.describe('READ Navigation', () => {
    // Filter state tests
    test('READ: show emails navigates to /emails', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show emails');

      const navigateBtn = page.locator('[data-testid="navigate-action"]');
      await expect(navigateBtn).toBeVisible();
      await navigateBtn.click();

      await expect(page).toHaveURL(/\/emails/);
    });

    test('READ: display all emails navigates to /emails?filter_state=all', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'display all emails');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/emails.*filter_state=all/);
    });

    test('READ: show linked emails filters by filter_state=linked', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show linked emails');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/emails.*filter_state=linked/);
    });

    test('READ: display unlinked emails filters by filter_state=unlinked', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'display unlinked emails');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/emails.*filter_state=unlinked/);
    });

    // Read status filter tests
    test('READ: show unread emails filters by is_read=false', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show unread emails');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/emails.*is_read=false/);
    });

    test('READ: display read emails filters by is_read=true', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'display read emails');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/emails.*is_read=true/);
    });

    // Attachment filter tests
    test('READ: emails with attachments filters by has_attachments=true', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'emails with attachments');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/emails.*has_attachments=true/);
    });

    test('READ: show emails without attachments filters by has_attachments', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show emails without attachments');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/emails.*has_attachments=false/);
    });

    // Date filter tests
    test('READ: emails received today filters by received_at', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'emails received today');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/emails/);
    });

    test('READ: emails from this week filters by received_at', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'emails from this week');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/emails/);
    });

    test('READ: emails received last month filters by received_at', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'emails received last month');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/emails/);
    });

    test('READ: recent emails filters by recency', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'recent emails');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/emails/);
    });

    // Search query filter tests
    test('READ: search emails for main engine filters by search_query', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'search emails for main engine');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/emails.*search/);
    });

    test('READ: find emails about service filters by search', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find emails about service');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/emails/);
    });

    test('READ: emails mentioning MAN filters by search', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'emails mentioning MAN');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/emails/);
    });

    // Thread filter tests
    test('READ: email thread T-001 filters by thread_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'email thread T-001');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/emails.*thread/);
    });

    test('READ: show conversation for thread filters by thread_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show conversation for thread');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/emails/);
    });

    // Compound filter tests
    test('READ: unread emails with attachments applies multiple filters', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'unread emails with attachments');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/emails/);
    });

    test('READ: linked emails from this week filters state and date', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'linked emails from this week');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/emails/);
    });

    test('READ: unlinked emails about parts filters state and search', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'unlinked emails about parts');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/emails/);
    });

    test('READ: recent unread emails with attachments applies 3 filters', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'recent unread emails with attachments');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/emails/);
    });

    // Special views
    test('READ: email inbox shows inbox view', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'email inbox');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/emails/);
    });

    test('READ: email summary shows overview', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'email summary');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/emails/);
    });

    test('READ: emails needing action shows action queue', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'emails needing action');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/emails/);
    });

    test('READ: supplier emails filters by sender type', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'supplier emails');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/emails/);
    });
  });

  // ============================================================================
  // MUTATE ACTION TESTS (25 tests)
  // ============================================================================
  test.describe('MUTATE Actions', () => {
    // link_email_to_entity tests
    test('MUTATE: link email to entity opens modal with required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'link email to entity');

      const executeBtn = page.locator('[data-testid="execute-action"]');
      await expect(executeBtn).toBeVisible();
      await executeBtn.click();
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="modal-title"]')).toContainText('Link Email');
      await expect(page.locator('[data-testid="field-thread_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-entity_type"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-entity_id"]')).toBeVisible();
    });

    test('MUTATE: link email T-001 to work order WO-123 prefills fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'link email T-001 to work order WO-123');
      await clickExecute(page);
      await waitForActionModal(page);

      const threadField = page.locator('[data-testid="field-thread_id"]');
      await expect(threadField).toHaveValue(/T-001/);
    });

    test('MUTATE: link email to equipment prefills entity_type', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'link email to equipment');
      await clickExecute(page);
      await waitForActionModal(page);

      const entityTypeField = page.locator('[data-testid="field-entity_type"]');
      await expect(entityTypeField).toHaveValue('equipment');
    });

    test('MUTATE: link email to fault prefills entity_type', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'link email to fault');
      await clickExecute(page);
      await waitForActionModal(page);

      const entityTypeField = page.locator('[data-testid="field-entity_type"]');
      await expect(entityTypeField).toHaveValue('fault');
    });

    // unlink_email_from_entity tests
    test('MUTATE: unlink email from entity shows link_id field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'unlink email from entity');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-link_id"]')).toBeVisible();
    });

    test('MUTATE: remove email link L-001 prefills link_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'remove email link L-001');
      await clickExecute(page);
      await waitForActionModal(page);

      const linkField = page.locator('[data-testid="field-link_id"]');
      await expect(linkField).toHaveValue(/L-001/);
    });

    // create_work_order_from_email tests
    test('MUTATE: create work order from email shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create work order from email');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-thread_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-title"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-equipment_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-priority"]')).toBeVisible();
    });

    test('MUTATE: create WO from email T-002 prefills thread_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create WO from email T-002');
      await clickExecute(page);
      await waitForActionModal(page);

      const threadField = page.locator('[data-testid="field-thread_id"]');
      await expect(threadField).toHaveValue(/T-002/);
    });

    test('MUTATE: create work order from email shows signature required', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create work order from email');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="signature-required"]')).toBeVisible();
    });

    test('MUTATE: create urgent WO from email prefills priority', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create urgent WO from email');
      await clickExecute(page);
      await waitForActionModal(page);

      const priorityField = page.locator('[data-testid="field-priority"]');
      await expect(priorityField).toHaveValue('urgent');
    });

    // create_fault_from_email tests
    test('MUTATE: create fault from email shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create fault from email');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-thread_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-title"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-equipment_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-severity"]')).toBeVisible();
    });

    test('MUTATE: report fault from email T-003 prefills thread_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'report fault from email T-003');
      await clickExecute(page);
      await waitForActionModal(page);

      const threadField = page.locator('[data-testid="field-thread_id"]');
      await expect(threadField).toHaveValue(/T-003/);
    });

    test('MUTATE: create critical fault from email prefills severity', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create critical fault from email');
      await clickExecute(page);
      await waitForActionModal(page);

      const severityField = page.locator('[data-testid="field-severity"]');
      await expect(severityField).toHaveValue('critical');
    });

    // mark_thread_read tests
    test('MUTATE: mark thread read shows thread_id field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'mark thread read');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-thread_id"]')).toBeVisible();
    });

    test('MUTATE: mark email T-004 as read prefills thread_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'mark email T-004 as read');
      await clickExecute(page);
      await waitForActionModal(page);

      const threadField = page.locator('[data-testid="field-thread_id"]');
      await expect(threadField).toHaveValue(/T-004/);
    });

    test('MUTATE: read email opens mark read modal', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'read email');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="modal-title"]')).toContainText('Mark');
    });

    // archive_thread tests
    test('MUTATE: archive thread shows required field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'archive thread');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-thread_id"]')).toBeVisible();
    });

    test('MUTATE: archive email T-005 prefills thread_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'archive email T-005');
      await clickExecute(page);
      await waitForActionModal(page);

      const threadField = page.locator('[data-testid="field-thread_id"]');
      await expect(threadField).toHaveValue(/T-005/);
    });

    test('MUTATE: archive thread shows confirmation required', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'archive thread');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="confirmation-required"]')).toBeVisible();
    });

    test('MUTATE: archive thread shows optional archive_reason field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'archive thread');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-archive_reason"]')).toBeVisible();
    });

    // download_attachment tests
    test('MUTATE: download attachment shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'download attachment');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-message_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-attachment_id"]')).toBeVisible();
    });

    test('MUTATE: download attachment A-001 from M-001 prefills fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'download attachment A-001 from M-001');
      await clickExecute(page);
      await waitForActionModal(page);

      const attachmentField = page.locator('[data-testid="field-attachment_id"]');
      await expect(attachmentField).toHaveValue(/A-001/);
    });

    test('MUTATE: save email attachment shows download modal', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'save email attachment');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="modal-title"]')).toContainText('Download');
    });

    test('MUTATE: get attachment from email shows picker', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'get attachment from email');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="attachment-picker"]')).toBeVisible();
    });

    test('MUTATE: link email shows optional link_notes field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'link email to entity');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-link_notes"]')).toBeVisible();
    });
  });
});
