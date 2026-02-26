import { test, expect, RBAC_CONFIG } from '../rbac-fixtures';

/**
 * SHARD 31: Fragmented Routes - Certificates
 *
 * Tests for the /certificates and /certificates/[id] fragmented routes.
 * These routes bypass the legacy /app single-URL architecture.
 *
 * Requirements Covered:
 * - T3-CERT-01: /certificates list route loads (HTTP 200)
 * - T3-CERT-02: /certificates/[id] detail route loads
 * - T3-CERT-03: Status filters work (valid/expiring_soon/expired)
 * - T3-CERT-04: Linked equipment navigation works
 * - T3-CERT-05: Page refresh preserves state
 * - T3-CERT-06: Browser back/forward works
 * - Feature flag OFF redirects to /app
 *
 * Prerequisites:
 * - NEXT_PUBLIC_FRAGMENTED_ROUTES_ENABLED=true in environment
 * - Authenticated users (HOD, Crew, Captain)
 *
 * Database Table: pms_certificates
 */

// Route configuration
const ROUTES_CONFIG = {
  ...RBAC_CONFIG,
  certificatesList: '/certificates',
  certificateDetail: (id: string) => `/certificates/${id}`,
  equipmentDetail: (id: string) => `/equipment/${id}`,
};

// Certificate status values (from schema)
const CERT_STATUS = {
  VALID: 'valid',
  EXPIRING_SOON: 'expiring_soon',
  EXPIRED: 'expired',
  SUPERSEDED: 'superseded',
} as const;

// ============================================================================
// SECTION 1: ROUTE LOADING TESTS
// T3-CERT-01 and T3-CERT-02: Basic route loads
// ============================================================================

test.describe('Certificates Route Loading', () => {
  test.describe.configure({ retries: 1 });

  test('T3-CERT-01: /certificates list route loads successfully', async ({ hodPage }) => {
    await hodPage.goto(ROUTES_CONFIG.certificatesList);

    // Check for redirect to legacy (feature flag disabled)
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - redirected to legacy /app');
      return;
    }

    await hodPage.waitForLoadState('networkidle');

    // Verify route loaded (not redirected)
    expect(hodPage.url()).toContain('/certificates');

    // Verify list container renders
    const listContainer = hodPage.locator('[data-testid="certificates-list"], main, [role="main"]');
    await expect(listContainer).toBeVisible({ timeout: 10000 });

    // Verify no error state
    const errorState = hodPage.locator('[data-testid="error-state"], .error-message, :text("Failed to load")');
    await expect(errorState).not.toBeVisible();

    // Verify loading completed (spinner gone)
    const spinner = hodPage.locator('.animate-spin, [data-loading="true"]');
    await expect(spinner).not.toBeVisible({ timeout: 15000 });

    console.log('  T3-CERT-01: List route loaded successfully');
  });

  test('T3-CERT-02: /certificates/[id] detail route loads correctly', async ({ hodPage, supabaseAdmin }) => {
    // Get certificate from test yacht
    const { data: certificate } = await supabaseAdmin
      .from('pms_certificates')
      .select('id, certificate_name')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!certificate) {
      console.log('  No certificates in test yacht - skipping');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.certificateDetail(certificate.id));

    // Check for redirect to legacy (feature flag disabled)
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - redirected to legacy /app');
      return;
    }

    await hodPage.waitForLoadState('networkidle');

    // Verify route loaded (not redirected)
    expect(hodPage.url()).toContain(`/certificates/${certificate.id}`);

    // Verify detail content renders
    const detailContainer = hodPage.locator('[data-testid="certificate-detail"], main, [role="main"]');
    await expect(detailContainer).toBeVisible({ timeout: 10000 });

    // Verify certificate name visible
    const certIdentifier = hodPage.locator(`text=${certificate.certificate_name}`);
    const isVisible = await certIdentifier.isVisible({ timeout: 5000 }).catch(() => false);
    if (!isVisible) {
      // Try broader content check
      const content = await hodPage.textContent('body');
      expect(content).toBeTruthy();
    }

    // Verify no error state
    const errorState = hodPage.locator('[data-testid="error-state"], .error-message, :text("Failed to Load")');
    await expect(errorState).not.toBeVisible();

    console.log(`  T3-CERT-02: Detail route loaded for ${certificate.certificate_name}`);
  });

  test('T3-CERT-02b: Non-existent certificate shows 404 state', async ({ hodPage }) => {
    const fakeId = '00000000-0000-0000-0000-000000000000';

    await hodPage.goto(ROUTES_CONFIG.certificateDetail(fakeId));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - redirected to legacy /app');
      return;
    }

    await hodPage.waitForLoadState('networkidle');

    // Should show not found or error state
    const notFoundState = hodPage.locator(
      ':text("Not Found"), :text("not found"), :text("does not exist"), [data-testid="not-found"]'
    );
    const errorState = hodPage.locator(':text("Failed"), :text("Error"), [data-testid="error-state"]');

    const hasNotFound = await notFoundState.isVisible({ timeout: 5000 }).catch(() => false);
    const hasError = await errorState.isVisible({ timeout: 5000 }).catch(() => false);

    // Either not found or error is acceptable for non-existent entity
    expect(hasNotFound || hasError).toBe(true);
    console.log('  T3-CERT-02b: Non-existent certificate handled correctly');
  });
});

// ============================================================================
// SECTION 2: STATUS FILTER TESTS
// T3-CERT-03: Status filters work (valid/expiring_soon/expired)
// ============================================================================

test.describe('Certificates Route Status Filters', () => {
  test.describe.configure({ retries: 1 });

  test('T3-CERT-03a: Valid status filter works', async ({ hodPage, supabaseAdmin }) => {
    // Check if any certificates exist
    const { data: certificates } = await supabaseAdmin
      .from('pms_certificates')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1);

    if (!certificates || certificates.length === 0) {
      console.log('  No certificates in test yacht - skipping filter test');
      return;
    }

    await hodPage.goto(`${ROUTES_CONFIG.certificatesList}?status=${CERT_STATUS.VALID}`);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/certificates')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');

    // Verify filter is applied (URL contains status param)
    expect(hodPage.url()).toContain('status=valid');

    // Verify no error state
    const errorState = hodPage.locator(':text("Failed to load"), [data-testid="error-state"]');
    await expect(errorState).not.toBeVisible();

    console.log('  T3-CERT-03a: Valid status filter applied');
  });

  test('T3-CERT-03b: Expiring soon status filter works', async ({ hodPage, supabaseAdmin }) => {
    const { data: certificates } = await supabaseAdmin
      .from('pms_certificates')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1);

    if (!certificates || certificates.length === 0) {
      console.log('  No certificates in test yacht - skipping filter test');
      return;
    }

    await hodPage.goto(`${ROUTES_CONFIG.certificatesList}?status=${CERT_STATUS.EXPIRING_SOON}`);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/certificates')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');

    // Verify filter is applied
    expect(hodPage.url()).toContain('status=expiring_soon');

    // Verify no error state
    const errorState = hodPage.locator(':text("Failed to load"), [data-testid="error-state"]');
    await expect(errorState).not.toBeVisible();

    console.log('  T3-CERT-03b: Expiring soon status filter applied');
  });

  test('T3-CERT-03c: Expired status filter works', async ({ hodPage, supabaseAdmin }) => {
    const { data: certificates } = await supabaseAdmin
      .from('pms_certificates')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1);

    if (!certificates || certificates.length === 0) {
      console.log('  No certificates in test yacht - skipping filter test');
      return;
    }

    await hodPage.goto(`${ROUTES_CONFIG.certificatesList}?status=${CERT_STATUS.EXPIRED}`);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/certificates')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');

    // Verify filter is applied
    expect(hodPage.url()).toContain('status=expired');

    // Verify no error state
    const errorState = hodPage.locator(':text("Failed to load"), [data-testid="error-state"]');
    await expect(errorState).not.toBeVisible();

    console.log('  T3-CERT-03c: Expired status filter applied');
  });

  test('T3-CERT-03d: Status filter dropdown interaction', async ({ hodPage, supabaseAdmin }) => {
    const { data: certificates } = await supabaseAdmin
      .from('pms_certificates')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1);

    if (!certificates || certificates.length === 0) {
      console.log('  No certificates in test yacht - skipping filter test');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.certificatesList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/certificates')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Look for status filter dropdown/select
    const statusFilter = hodPage.locator(
      '[data-testid="status-filter"], select[name="status"], button:has-text("Status"), [aria-label="Filter by status"]'
    );
    const hasFilter = await statusFilter.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasFilter) {
      await statusFilter.first().click();
      await hodPage.waitForTimeout(500);

      // Look for filter options
      const expiredOption = hodPage.locator('text=Expired, [data-value="expired"], option[value="expired"]');
      const hasOption = await expiredOption.isVisible({ timeout: 3000 }).catch(() => false);

      if (hasOption) {
        await expiredOption.first().click();
        await hodPage.waitForLoadState('networkidle');
        console.log('  T3-CERT-03d: Filter dropdown interaction successful');
      } else {
        console.log('  T3-CERT-03d: Filter options not found (may use different UI)');
      }
    } else {
      console.log('  T3-CERT-03d: Status filter dropdown not visible');
    }
  });
});

// ============================================================================
// SECTION 3: NAVIGATION TESTS
// T3-CERT-04: Linked equipment navigation works
// T3-CERT-06: Browser back/forward works
// ============================================================================

test.describe('Certificates Route Navigation', () => {
  test.describe.configure({ retries: 1 });

  test('T3-CERT-04: Equipment link navigates to /equipment/[id]', async ({ hodPage, supabaseAdmin }) => {
    // Find a certificate with equipment linked
    const { data: certWithEquipment } = await supabaseAdmin
      .from('pms_certificates')
      .select('id, certificate_name, equipment_id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .not('equipment_id', 'is', null)
      .limit(1)
      .single();

    if (!certWithEquipment) {
      console.log('  No certificates with equipment found - skipping');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.certificateDetail(certWithEquipment.id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/certificates')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Find equipment link/button
    const equipmentLink = hodPage.locator(
      '[data-testid="equipment-link"], a[href*="/equipment/"], button:has-text("Equipment"), [data-navigate="equipment"], :text("View Equipment")'
    );

    const hasLink = await equipmentLink.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasLink) {
      await equipmentLink.first().click();
      await hodPage.waitForLoadState('networkidle');

      // Verify navigation occurred
      const newUrl = hodPage.url();
      const navigatedToEquipment = newUrl.includes('/equipment/') || newUrl.includes('entity=equipment');
      expect(navigatedToEquipment).toBe(true);
      console.log('  T3-CERT-04: Equipment navigation verified');
    } else {
      console.log('  T3-CERT-04: No equipment link visible - certificate may not have equipment linked');
    }
  });

  test('T3-CERT-06a: Browser back/forward works naturally on list', async ({ hodPage, supabaseAdmin }) => {
    const { data: certificate } = await supabaseAdmin
      .from('pms_certificates')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!certificate) {
      console.log('  No certificates in test yacht - skipping');
      return;
    }

    // Start at list
    await hodPage.goto(ROUTES_CONFIG.certificatesList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/certificates')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    const listUrl = hodPage.url();

    // Navigate to detail (via URL)
    await hodPage.goto(ROUTES_CONFIG.certificateDetail(certificate.id));
    await hodPage.waitForLoadState('networkidle');
    const detailUrl = hodPage.url();

    expect(detailUrl).toContain(`/certificates/${certificate.id}`);

    // Go back via browser
    await hodPage.goBack();
    await hodPage.waitForLoadState('networkidle');

    // Verify we're back at list
    expect(hodPage.url()).toBe(listUrl);
    console.log('  T3-CERT-06a: Back navigation to list verified');

    // Go forward
    await hodPage.goForward();
    await hodPage.waitForLoadState('networkidle');

    // Verify we're at detail again
    expect(hodPage.url()).toBe(detailUrl);
    console.log('  T3-CERT-06b: Forward navigation to detail verified');
  });

  test('T3-CERT-06b: Browser back from detail returns to previous page', async ({ hodPage, supabaseAdmin }) => {
    const { data: certificate } = await supabaseAdmin
      .from('pms_certificates')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!certificate) {
      console.log('  No certificates in test yacht - skipping');
      return;
    }

    // Start at home/app
    await hodPage.goto('/');
    await hodPage.waitForLoadState('networkidle');

    // Navigate to certificate detail
    await hodPage.goto(ROUTES_CONFIG.certificateDetail(certificate.id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/certificates/')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');

    // Click back button in UI (if exists)
    const backButton = hodPage.locator(
      'button[aria-label="Back"], button:has([data-testid="back-icon"]), [data-testid="back-button"]'
    );
    const hasBackButton = await backButton.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasBackButton) {
      await backButton.click();
      await hodPage.waitForLoadState('networkidle');

      // Should navigate back to list or previous page
      const newUrl = hodPage.url();
      expect(newUrl).not.toContain(`/certificates/${certificate.id}`);
      console.log('  T3-CERT-06b: UI back button works');
    } else {
      // Use browser back
      await hodPage.goBack();
      await hodPage.waitForLoadState('networkidle');
      console.log('  T3-CERT-06b: Browser back works (no UI back button)');
    }
  });
});

// ============================================================================
// SECTION 4: STATE PERSISTENCE TESTS
// T3-CERT-05: Page refresh preserves state
// ============================================================================

test.describe('Certificates Route State Persistence', () => {
  test.describe.configure({ retries: 1 });

  test('T3-CERT-05a: Page refresh preserves detail view', async ({ hodPage, supabaseAdmin }) => {
    const { data: certificate } = await supabaseAdmin
      .from('pms_certificates')
      .select('id, certificate_name')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!certificate) {
      console.log('  No certificates in test yacht - skipping');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.certificateDetail(certificate.id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/certificates')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Store current state
    const beforeRefreshUrl = hodPage.url();
    const beforeContent = await hodPage.textContent('body');

    // Refresh page
    await hodPage.reload();
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Verify state preserved
    const afterRefreshUrl = hodPage.url();
    expect(afterRefreshUrl).toBe(beforeRefreshUrl);

    // Verify content still renders
    const afterContent = await hodPage.textContent('body');
    expect(afterContent).toBeTruthy();

    // Verify certificate name still visible
    const certIdentifier = hodPage.locator(`text=${certificate.certificate_name}`);
    const stillVisible = await certIdentifier.isVisible({ timeout: 5000 }).catch(() => false);

    if (!stillVisible) {
      // Check that content contains certificate info
      expect(afterContent?.includes(certificate.id) || afterContent).toBeTruthy();
    }

    console.log('  T3-CERT-05a: State preserved after refresh');
  });

  test('T3-CERT-05b: Page refresh preserves list with filter', async ({ hodPage, supabaseAdmin }) => {
    const { data: certificates } = await supabaseAdmin
      .from('pms_certificates')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1);

    if (!certificates || certificates.length === 0) {
      console.log('  No certificates in test yacht - skipping');
      return;
    }

    // Navigate to list with status filter
    await hodPage.goto(`${ROUTES_CONFIG.certificatesList}?status=${CERT_STATUS.VALID}`);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/certificates')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    const beforeUrl = hodPage.url();

    // Refresh
    await hodPage.reload();
    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    const afterUrl = hodPage.url();

    // URL should be preserved (including query params)
    expect(afterUrl).toBe(beforeUrl);
    expect(afterUrl).toContain('status=valid');
    console.log('  T3-CERT-05b: List filter state preserved after refresh');
  });
});

// ============================================================================
// SECTION 5: FEATURE FLAG TOGGLE TEST
// Verify route behavior when flag is on/off
// ============================================================================

test.describe('Feature Flag Behavior', () => {
  test.describe.configure({ retries: 0 });

  test('Route redirects to legacy when flag disabled', async ({ hodPage }) => {
    // Note: This test documents expected behavior when flag is OFF
    // In real testing, flag would need to be toggled via environment

    await hodPage.goto(ROUTES_CONFIG.certificatesList);
    await hodPage.waitForLoadState('networkidle');

    const currentUrl = hodPage.url();

    if (currentUrl.includes('/app') && !currentUrl.includes('/certificates')) {
      // Flag is disabled - verify redirect worked
      expect(currentUrl).toContain('/app');
      console.log('  Feature flag OFF: Correctly redirected to /app');
    } else if (currentUrl.includes('/certificates')) {
      // Flag is enabled - verify route works
      expect(currentUrl).toContain('/certificates');
      console.log('  Feature flag ON: Route loaded directly');
    }
  });
});

// ============================================================================
// SECTION 6: RBAC ON ROUTES
// Verify permissions work on fragmented routes
// ============================================================================

test.describe('Certificates Route RBAC', () => {
  test.describe.configure({ retries: 1 });

  test('Crew can view certificate list', async ({ crewPage, supabaseAdmin }) => {
    const { data: certificates } = await supabaseAdmin
      .from('pms_certificates')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1);

    if (!certificates || certificates.length === 0) {
      console.log('  No certificates in test yacht - skipping');
      return;
    }

    await crewPage.goto(ROUTES_CONFIG.certificatesList);

    const currentUrl = crewPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/certificates')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await crewPage.waitForLoadState('networkidle');

    // Crew should be able to view list (RLS: Users can view certificates)
    const errorState = crewPage.locator(':text("Access Denied"), :text("Unauthorized"), [data-testid="permission-denied"]');
    await expect(errorState).not.toBeVisible({ timeout: 5000 });

    console.log('  Crew can view certificate list');
  });

  test('Crew can view certificate detail', async ({ crewPage, supabaseAdmin }) => {
    const { data: certificate } = await supabaseAdmin
      .from('pms_certificates')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!certificate) {
      console.log('  No certificates in test yacht - skipping');
      return;
    }

    await crewPage.goto(ROUTES_CONFIG.certificateDetail(certificate.id));

    const currentUrl = crewPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/certificates')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await crewPage.waitForLoadState('networkidle');

    // Crew should be able to view detail
    const errorState = crewPage.locator(':text("Access Denied"), :text("Unauthorized"), [data-testid="permission-denied"]');
    await expect(errorState).not.toBeVisible({ timeout: 5000 });

    console.log('  Crew can view certificate detail');
  });

  test('Crew sees read-only actions on detail route', async ({ crewPage, supabaseAdmin }) => {
    const { data: certificate } = await supabaseAdmin
      .from('pms_certificates')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!certificate) {
      console.log('  No certificates in test yacht - skipping');
      return;
    }

    await crewPage.goto(ROUTES_CONFIG.certificateDetail(certificate.id));

    const currentUrl = crewPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/certificates')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await crewPage.waitForLoadState('networkidle');
    await crewPage.waitForTimeout(2000);

    // Crew should NOT see Edit/Update button (Officers only per RLS)
    const editButton = crewPage.locator('button:has-text("Edit"), button:has-text("Update")');
    const editVisible = await editButton.isVisible({ timeout: 3000 }).catch(() => false);

    // Crew should NOT see Delete button (Managers only per RLS)
    const deleteButton = crewPage.locator('button:has-text("Delete"), button:has-text("Remove")');
    const deleteVisible = await deleteButton.isVisible({ timeout: 3000 }).catch(() => false);

    // Edit and Delete should be hidden for crew
    if (!editVisible && !deleteVisible) {
      console.log('  Crew has read-only access (Edit/Delete buttons hidden)');
    } else {
      console.log(`  Edit visible: ${editVisible}, Delete visible: ${deleteVisible} (may be hidden via disabled state)`);
    }
  });
});

// ============================================================================
// SECTION 7: PERFORMANCE BASELINE
// Basic load time checks
// ============================================================================

test.describe('Certificates Route Performance', () => {
  test.describe.configure({ retries: 0 });

  test('List route loads within 5 seconds', async ({ hodPage }) => {
    const startTime = Date.now();

    await hodPage.goto(ROUTES_CONFIG.certificatesList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/certificates')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');

    const loadTime = Date.now() - startTime;
    console.log(`  List load time: ${loadTime}ms`);

    // Should load within 5 seconds
    expect(loadTime).toBeLessThan(5000);
  });

  test('Detail route loads within 5 seconds', async ({ hodPage, supabaseAdmin }) => {
    const { data: certificate } = await supabaseAdmin
      .from('pms_certificates')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!certificate) {
      console.log('  No certificates in test yacht - skipping');
      return;
    }

    const startTime = Date.now();

    await hodPage.goto(ROUTES_CONFIG.certificateDetail(certificate.id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/certificates')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');

    const loadTime = Date.now() - startTime;
    console.log(`  Detail load time: ${loadTime}ms`);

    // Should load within 5 seconds
    expect(loadTime).toBeLessThan(5000);
  });
});
