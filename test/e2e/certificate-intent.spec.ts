import { test, expect, Page } from '@playwright/test';

/**
 * Certificate Intent E2E Tests
 *
 * Lens: certificate
 * Tests: 52 total (26 READ + 26 MUTATE)
 *
 * Covers:
 * - READ Navigation tests for all filter combinations
 * - MUTATE Action tests for all 8 certificate actions
 */

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';

// Test data factory
const testData = {
  vesselCertificate: {
    type: 'ISM',
    status: 'active',
    issuing_authority: 'Liberian Registry',
  },
  crewCertificate: {
    type: 'STCW',
    crew_member_id: 'crew-001',
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

test.describe('Certificate Intent Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForSelector('[data-testid="app-ready"]', { timeout: 10000 });
  });

  // ============================================================================
  // READ NAVIGATION TESTS (26 tests)
  // ============================================================================
  test.describe('READ Navigation', () => {
    // Status filter tests
    test('READ: show active certificates navigates to /certificates?status=active', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show active certificates');

      const navigateBtn = page.locator('[data-testid="navigate-action"]');
      await expect(navigateBtn).toBeVisible();
      await navigateBtn.click();

      await expect(page).toHaveURL(/\/certificates.*status=active/);
    });

    test('READ: display all certificates navigates to /certificates', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'display all certificates');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/certificates/);
    });

    test('READ: list expired certificates filters by status=expired', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list expired certificates');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/certificates.*status=expired/);
    });

    test('READ: find draft certificates filters by status=draft', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find draft certificates');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/certificates.*status=draft/);
    });

    test('READ: show superseded certificates filters by status=superseded', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show superseded certificates');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/certificates.*status=superseded/);
    });

    test('READ: view revoked certificates filters by status=revoked', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'view revoked certificates');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/certificates.*status=revoked/);
    });

    // Certificate type filter tests (vessel)
    test('READ: show ISM certificates filters by certificate_type', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show ISM certificates');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/certificates.*type=ISM/);
    });

    test('READ: list SOLAS certificates filters by certificate_type', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list SOLAS certificates');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/certificates.*type=SOLAS/);
    });

    test('READ: find CLASS certificates filters by certificate_type', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find CLASS certificates');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/certificates.*type=CLASS/);
    });

    test('READ: show MARPOL certificates filters by certificate_type', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show MARPOL certificates');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/certificates.*type=MARPOL/);
    });

    // Certificate type filter tests (crew)
    test('READ: show STCW certificates filters by certificate_type', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show STCW certificates');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/certificates.*type=STCW/);
    });

    test('READ: list ENG1 certificates filters by certificate_type', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list ENG1 certificates');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/certificates.*type=ENG1/);
    });

    test('READ: find COC certificates filters by certificate_type', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find COC certificates');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/certificates.*type=COC/);
    });

    // Vessel or crew filter tests
    test('READ: show vessel certificates filters by vessel_or_crew=vessel', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show vessel certificates');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/certificates.*vessel_or_crew=vessel/);
    });

    test('READ: list crew certificates filters by vessel_or_crew=crew', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'list crew certificates');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/certificates.*vessel_or_crew=crew/);
    });

    // Expiry filter tests
    test('READ: certificates expiring soon filters by is_expiring_soon', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'certificates expiring soon');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/certificates.*expiring/);
    });

    test('READ: show certificates expiring this month filters by expiry_date', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'show certificates expiring this month');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/certificates/);
    });

    test('READ: find expired certificates filters by is_expired', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'find expired certificates');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/certificates/);
    });

    test('READ: certificates expiring in 90 days filters by expiry window', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'certificates expiring in 90 days');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/certificates/);
    });

    // Compound filter tests
    test('READ: active vessel certificates expiring soon applies multiple filters', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'active vessel certificates expiring soon');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/certificates/);
    });

    test('READ: expired crew STCW certificates filters type and status', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'expired crew STCW certificates');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/certificates/);
    });

    test('READ: ISM and ISPS certificates filters multiple types', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'ISM and ISPS certificates');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/certificates/);
    });

    test('READ: certificates for John Smith filters by crew member', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'certificates for John Smith');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/certificates/);
    });

    test('READ: medical certificates for crew filters type and crew', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'medical certificates for crew');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/certificates/);
    });

    test('READ: certificate compliance summary shows overview', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'certificate compliance summary');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/certificates/);
    });

    test('READ: renewal calendar shows certificate calendar view', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'renewal calendar');
      await clickNavigate(page);
      await expect(page).toHaveURL(/\/certificates/);
    });
  });

  // ============================================================================
  // MUTATE ACTION TESTS (26 tests)
  // ============================================================================
  test.describe('MUTATE Actions', () => {
    // create_vessel_certificate tests
    test('MUTATE: create vessel certificate opens modal with required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create vessel certificate');

      const executeBtn = page.locator('[data-testid="execute-action"]');
      await expect(executeBtn).toBeVisible();
      await executeBtn.click();
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="modal-title"]')).toContainText('Create Vessel Certificate');
      await expect(page.locator('[data-testid="field-certificate_type"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-issue_date"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-expiry_date"]')).toBeVisible();
    });

    test('MUTATE: create ISM certificate prefills certificate_type', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create ISM certificate');
      await clickExecute(page);
      await waitForActionModal(page);

      const typeField = page.locator('[data-testid="field-certificate_type"]');
      await expect(typeField).toHaveValue('ISM');
    });

    test('MUTATE: create vessel certificate shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create vessel certificate');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    test('MUTATE: create vessel certificate shows confirmation required', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create vessel certificate');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="confirmation-required"]')).toBeVisible();
    });

    // create_crew_certificate tests
    test('MUTATE: create crew certificate shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create crew certificate');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-certificate_type"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-crew_member_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-issue_date"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-expiry_date"]')).toBeVisible();
    });

    test('MUTATE: create STCW for John Smith prefills crew and type', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'create STCW for John Smith');
      await clickExecute(page);
      await waitForActionModal(page);

      const typeField = page.locator('[data-testid="field-certificate_type"]');
      await expect(typeField).toHaveValue('STCW');
    });

    test('MUTATE: add crew certificate shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'add crew certificate');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    // update_certificate tests
    test('MUTATE: update certificate shows optional fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'update certificate');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-expiry_date"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-notes"]')).toBeVisible();
    });

    test('MUTATE: edit certificate CERT-001 prefills certificate_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'edit certificate CERT-001');
      await clickExecute(page);
      await waitForActionModal(page);

      const certField = page.locator('[data-testid="field-certificate_id"]');
      await expect(certField).toHaveValue(/CERT-001/);
    });

    test('MUTATE: extend certificate expiry shows expiry_date field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'extend certificate expiry');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-expiry_date"]')).toBeVisible();
    });

    // link_document_to_certificate tests
    test('MUTATE: link document to certificate shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'link document to certificate');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-certificate_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-document_id"]')).toBeVisible();
    });

    test('MUTATE: attach scan to certificate CERT-002 prefills certificate_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'attach scan to certificate CERT-002');
      await clickExecute(page);
      await waitForActionModal(page);

      const certField = page.locator('[data-testid="field-certificate_id"]');
      await expect(certField).toHaveValue(/CERT-002/);
    });

    // supersede_certificate tests
    test('MUTATE: supersede certificate shows required fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'supersede certificate');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-certificate_id"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-new_certificate_id"]')).toBeVisible();
    });

    test('MUTATE: supersede certificate shows signature required', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'supersede certificate');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="signature-required"]')).toBeVisible();
    });

    test('MUTATE: replace certificate CERT-OLD with CERT-NEW prefills both', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'replace certificate CERT-OLD with CERT-NEW');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-certificate_id"]')).not.toHaveValue('');
    });

    // delete_certificate tests
    test('MUTATE: delete certificate shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'delete certificate');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    test('MUTATE: delete certificate shows confirmation required', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'delete certificate');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="confirmation-required"]')).toBeVisible();
    });

    test('MUTATE: remove certificate CERT-123 prefills certificate_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'remove certificate CERT-123');
      await clickExecute(page);
      await waitForActionModal(page);

      const certField = page.locator('[data-testid="field-certificate_id"]');
      await expect(certField).toHaveValue(/CERT-123/);
    });

    test('MUTATE: delete certificate shows delete_reason field', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'delete certificate');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-delete_reason"]')).toBeVisible();
    });

    // upload_certificate_document tests
    test('MUTATE: upload certificate document shows file upload', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'upload certificate document');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-document_storage_path"]')).toBeVisible();
    });

    test('MUTATE: upload scan for CERT-456 prefills certificate_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'upload scan for CERT-456');
      await clickExecute(page);
      await waitForActionModal(page);

      const certField = page.locator('[data-testid="field-certificate_id"]');
      await expect(certField).toHaveValue(/CERT-456/);
    });

    test('MUTATE: upload certificate document shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'upload certificate document');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    // update_certificate_metadata tests
    test('MUTATE: update certificate metadata shows optional fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'update certificate metadata');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="field-issuing_authority"]')).toBeVisible();
      await expect(page.locator('[data-testid="field-certificate_number"]')).toBeVisible();
    });

    test('MUTATE: change issuing authority for CERT-789 prefills certificate_id', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'change issuing authority for CERT-789');
      await clickExecute(page);
      await waitForActionModal(page);

      const certField = page.locator('[data-testid="field-certificate_id"]');
      await expect(certField).toHaveValue(/CERT-789/);
    });

    test('MUTATE: update certificate metadata shows role restriction', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'update certificate metadata');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="role-restricted"]')).toBeVisible();
    });

    test('MUTATE: update certificate metadata shows confirmation required', async ({ page }) => {
      await openSpotlight(page);
      await typeQuery(page, 'update certificate metadata');
      await clickExecute(page);
      await waitForActionModal(page);

      await expect(page.locator('[data-testid="confirmation-required"]')).toBeVisible();
    });
  });
});
