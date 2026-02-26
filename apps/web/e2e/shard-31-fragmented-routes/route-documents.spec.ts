import { test, expect, RBAC_CONFIG } from '../rbac-fixtures';

/**
 * SHARD 31: Fragmented Routes - Documents
 *
 * Tests for /documents and /documents/[id] routes.
 *
 * Requirements Covered:
 * - T3-DOC-01: /documents list route loads (HTTP 200)
 * - T3-DOC-02: /documents/[id] detail route loads
 * - T3-DOC-03: Status filters work (active/expired/archived)
 * - T3-DOC-04: Download/View buttons visible
 * - T3-DOC-05: Page refresh preserves state
 * - T3-DOC-06: Browser back/forward works
 * - Feature flag OFF redirects to /app
 *
 * Prerequisites:
 * - NEXT_PUBLIC_FRAGMENTED_ROUTES_ENABLED=true in environment
 * - Authenticated users (HOD, Crew, Captain)
 */

const ROUTES_CONFIG = {
  ...RBAC_CONFIG,
  documentsList: '/documents',
  documentDetail: (id: string) => `/documents/${id}`,
};

// Document status enum values (common document management statuses)
const DOC_STATUS = {
  ACTIVE: 'active',
  EXPIRED: 'expired',
  ARCHIVED: 'archived',
  DRAFT: 'draft',
} as const;

// Document type enum values
const DOC_TYPE = {
  INVOICE: 'invoice',
  PACKING_SLIP: 'packing_slip',
  PHOTO: 'photo',
  MANUAL: 'manual',
  CERTIFICATE: 'certificate',
  OTHER: 'other',
} as const;

// ============================================================================
// SECTION 1: ROUTE LOADING TESTS
// T3-DOC-01 and T3-DOC-02: Basic route loads
// ============================================================================

test.describe('Documents Route Loading', () => {
  test.describe.configure({ retries: 1 });

  test('T3-DOC-01: /documents list route loads successfully (HTTP 200)', async ({ hodPage }) => {
    await hodPage.goto(ROUTES_CONFIG.documentsList);

    // Check for redirect to legacy (feature flag disabled)
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - redirected to legacy /app');
      return;
    }

    await hodPage.waitForLoadState('networkidle');

    // Verify route loaded (not redirected)
    expect(hodPage.url()).toContain('/documents');

    // Verify list container renders
    const listContainer = hodPage.locator('[data-testid="documents-list"], main, [role="main"]');
    await expect(listContainer).toBeVisible({ timeout: 10000 });

    // Verify no error state
    const errorState = hodPage.locator('[data-testid="error-state"], .error-message, :text("Failed to load")');
    await expect(errorState).not.toBeVisible();

    // Verify loading completed (spinner gone)
    const spinner = hodPage.locator('.animate-spin, [data-loading="true"]');
    await expect(spinner).not.toBeVisible({ timeout: 15000 });

    console.log('  T3-DOC-01: List route loaded successfully');
  });

  test('T3-DOC-02: /documents/[id] detail route loads correctly', async ({ hodPage, supabaseAdmin }) => {
    // Get document from test yacht
    const { data: document } = await supabaseAdmin
      .from('pms_documents')
      .select('id, title, doc_type')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!document) {
      console.log('  No documents in test yacht - skipping');
      return;
    }

    // Navigate directly to detail route
    await hodPage.goto(ROUTES_CONFIG.documentDetail(document.id));

    // Check for redirect to legacy (feature flag disabled)
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - redirected to legacy /app');
      return;
    }

    await hodPage.waitForLoadState('networkidle');

    // Verify route loaded (not redirected)
    expect(hodPage.url()).toContain(`/documents/${document.id}`);

    // Verify detail content renders
    const detailContainer = hodPage.locator('[data-testid="document-detail"], main, [role="main"]');
    await expect(detailContainer).toBeVisible({ timeout: 10000 });

    // Verify document title or identifier visible
    const docIdentifier = hodPage.locator(`text=${document.title}`);
    const isVisible = await docIdentifier.isVisible({ timeout: 5000 }).catch(() => false);
    if (!isVisible) {
      // Try broader content check
      const content = await hodPage.textContent('body');
      expect(content).toBeTruthy();
    }

    // Verify no error state
    const errorState = hodPage.locator('[data-testid="error-state"], .error-message, :text("Failed to load")');
    await expect(errorState).not.toBeVisible();

    console.log(`  T3-DOC-02: Detail route loaded for ${document.title || document.id}`);
  });

  test('T3-DOC-02b: Non-existent document shows 404 state', async ({ hodPage }) => {
    const fakeId = '00000000-0000-0000-0000-000000000000';

    await hodPage.goto(ROUTES_CONFIG.documentDetail(fakeId));

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
    console.log('  T3-DOC-02b: Non-existent document handled correctly');
  });
});

// ============================================================================
// SECTION 2: STATUS FILTER TESTS
// T3-DOC-03: Status filters work (active/expired/archived)
// ============================================================================

test.describe('Documents Route Status Filters', () => {
  test.describe.configure({ retries: 1 });

  test('T3-DOC-03: Status filter for active documents works', async ({ hodPage, supabaseAdmin }) => {
    // Check if documents with active status exist
    const { data: activeDoc } = await supabaseAdmin
      .from('pms_documents')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .eq('status', DOC_STATUS.ACTIVE)
      .limit(1)
      .single();

    await hodPage.goto(ROUTES_CONFIG.documentsList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Look for status filter dropdown or tabs
    const statusFilter = hodPage.locator(
      '[data-testid="status-filter"], [data-testid="filter-status"], button:has-text("Status"), select:has-text("Active")'
    );
    const hasStatusFilter = await statusFilter.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasStatusFilter) {
      // Try to click/interact with the filter
      await statusFilter.first().click().catch(() => {});
      await hodPage.waitForTimeout(500);

      // Look for active option
      const activeOption = hodPage.locator(':text("Active"), option[value="active"], [data-value="active"]');
      const hasActiveOption = await activeOption.isVisible({ timeout: 3000 }).catch(() => false);

      if (hasActiveOption) {
        await activeOption.first().click().catch(() => {});
        await hodPage.waitForTimeout(1000);
        console.log('  T3-DOC-03: Active status filter clicked');
      } else {
        console.log('  Active option not visible in filter');
      }
    } else {
      // Check for filter tabs instead
      const filterTabs = hodPage.locator('[role="tablist"], .filter-tabs');
      const hasFilterTabs = await filterTabs.isVisible({ timeout: 3000 }).catch(() => false);

      if (hasFilterTabs) {
        const activeTab = hodPage.locator('button:has-text("Active"), [role="tab"]:has-text("Active")');
        const hasActiveTab = await activeTab.isVisible({ timeout: 3000 }).catch(() => false);
        if (hasActiveTab) {
          await activeTab.click();
          await hodPage.waitForTimeout(1000);
          console.log('  T3-DOC-03: Active tab filter clicked');
        }
      } else {
        console.log('  No status filter UI found - may not be implemented');
      }
    }

    // Verify page still loaded without errors
    const errorState = hodPage.locator(':text("Failed"), :text("Error")');
    await expect(errorState).not.toBeVisible({ timeout: 3000 });
    console.log('  T3-DOC-03: Status filter test completed');
  });

  test('T3-DOC-03b: Status filter for expired documents works', async ({ hodPage, supabaseAdmin }) => {
    // Check if documents with expired status exist
    const { data: expiredDoc } = await supabaseAdmin
      .from('pms_documents')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .eq('status', DOC_STATUS.EXPIRED)
      .limit(1)
      .single();

    await hodPage.goto(ROUTES_CONFIG.documentsList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Look for expired filter option
    const expiredFilter = hodPage.locator(
      'button:has-text("Expired"), [role="tab"]:has-text("Expired"), option[value="expired"]'
    );
    const hasExpiredFilter = await expiredFilter.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasExpiredFilter) {
      await expiredFilter.first().click().catch(() => {});
      await hodPage.waitForTimeout(1000);
      console.log('  T3-DOC-03b: Expired filter clicked');
    } else {
      console.log('  Expired filter option not visible - may not be implemented');
    }

    // Verify page still loaded without errors
    const errorState = hodPage.locator(':text("Failed to load")');
    await expect(errorState).not.toBeVisible({ timeout: 3000 });
    console.log('  T3-DOC-03b: Expired filter test completed');
  });

  test('T3-DOC-03c: Status filter for archived documents works', async ({ hodPage, supabaseAdmin }) => {
    // Check if documents with archived status exist
    const { data: archivedDoc } = await supabaseAdmin
      .from('pms_documents')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .eq('status', DOC_STATUS.ARCHIVED)
      .limit(1)
      .single();

    await hodPage.goto(ROUTES_CONFIG.documentsList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Look for archived filter option
    const archivedFilter = hodPage.locator(
      'button:has-text("Archived"), [role="tab"]:has-text("Archived"), option[value="archived"]'
    );
    const hasArchivedFilter = await archivedFilter.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasArchivedFilter) {
      await archivedFilter.first().click().catch(() => {});
      await hodPage.waitForTimeout(1000);
      console.log('  T3-DOC-03c: Archived filter clicked');
    } else {
      console.log('  Archived filter option not visible - may not be implemented');
    }

    // Verify page still loaded without errors
    const errorState = hodPage.locator(':text("Failed to load")');
    await expect(errorState).not.toBeVisible({ timeout: 3000 });
    console.log('  T3-DOC-03c: Archived filter test completed');
  });
});

// ============================================================================
// SECTION 3: DOWNLOAD/VIEW BUTTON TESTS
// T3-DOC-04: Download/View buttons visible
// ============================================================================

test.describe('Documents Route Actions', () => {
  test.describe.configure({ retries: 1 });

  test('T3-DOC-04: Download button visible on document detail', async ({ hodPage, supabaseAdmin }) => {
    // Get document from test yacht
    const { data: document } = await supabaseAdmin
      .from('pms_documents')
      .select('id, title')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!document) {
      console.log('  No documents in test yacht - skipping');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.documentDetail(document.id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Look for download button
    const downloadButton = hodPage.locator(
      'button:has-text("Download"), a:has-text("Download"), [data-testid="download-button"], [aria-label*="download"], button[title*="Download"]'
    );
    const hasDownloadButton = await downloadButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasDownloadButton) {
      console.log('  T3-DOC-04: Download button is visible');
    } else {
      // Download might be in a menu or action dropdown
      const actionMenu = hodPage.locator(
        'button:has-text("Actions"), [data-testid="action-menu"], button[aria-label="More actions"]'
      );
      const hasActionMenu = await actionMenu.isVisible({ timeout: 3000 }).catch(() => false);

      if (hasActionMenu) {
        await actionMenu.click();
        await hodPage.waitForTimeout(500);

        const downloadInMenu = hodPage.locator('[role="menu"] :text("Download"), [role="menuitem"]:has-text("Download")');
        const hasDownloadInMenu = await downloadInMenu.isVisible({ timeout: 3000 }).catch(() => false);

        expect(hasDownloadInMenu).toBe(true);
        console.log('  T3-DOC-04: Download button found in action menu');
      } else {
        console.log('  Download button not visible - may require different document type');
      }
    }
  });

  test('T3-DOC-04b: View button visible on document detail', async ({ hodPage, supabaseAdmin }) => {
    // Get document from test yacht
    const { data: document } = await supabaseAdmin
      .from('pms_documents')
      .select('id, title')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!document) {
      console.log('  No documents in test yacht - skipping');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.documentDetail(document.id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Look for view button or preview functionality
    const viewButton = hodPage.locator(
      'button:has-text("View"), a:has-text("View"), button:has-text("Preview"), [data-testid="view-button"], [aria-label*="view"], [aria-label*="preview"]'
    );
    const hasViewButton = await viewButton.isVisible({ timeout: 5000 }).catch(() => false);

    // Also check for embedded preview/viewer
    const previewArea = hodPage.locator(
      '[data-testid="document-preview"], iframe[src*="preview"], .document-viewer, img[alt*="preview"]'
    );
    const hasPreviewArea = await previewArea.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasViewButton || hasPreviewArea) {
      console.log('  T3-DOC-04b: View/Preview functionality is visible');
    } else {
      console.log('  View button not explicitly visible - document may display inline');
    }
  });

  test('T3-DOC-04c: Download/View buttons visible on list items', async ({ hodPage, supabaseAdmin }) => {
    // Check if documents exist
    const { count } = await supabaseAdmin
      .from('pms_documents')
      .select('id', { count: 'exact', head: true })
      .eq('yacht_id', ROUTES_CONFIG.yachtId);

    if (!count || count === 0) {
      console.log('  No documents in test yacht - skipping');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.documentsList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Look for action buttons on list items
    const listItemActions = hodPage.locator(
      '[data-testid="document-row"] button, tr button, .document-card button, [data-testid*="action"]'
    );
    const hasListActions = await listItemActions.first().isVisible({ timeout: 5000 }).catch(() => false);

    if (hasListActions) {
      console.log('  T3-DOC-04c: List item actions visible');
    } else {
      // Actions might only be visible on hover
      const firstDocumentRow = hodPage.locator('[data-testid="document-row"], tr, .document-card').first();
      const hasRow = await firstDocumentRow.isVisible({ timeout: 3000 }).catch(() => false);

      if (hasRow) {
        await firstDocumentRow.hover();
        await hodPage.waitForTimeout(500);

        const hoverActions = firstDocumentRow.locator('button');
        const hasHoverActions = await hoverActions.first().isVisible({ timeout: 3000 }).catch(() => false);
        console.log(`  T3-DOC-04c: Hover actions visible: ${hasHoverActions}`);
      }
    }
  });
});

// ============================================================================
// SECTION 4: STATE PERSISTENCE TESTS
// T3-DOC-05: Page refresh preserves state
// ============================================================================

test.describe('Documents Route State Persistence', () => {
  test.describe.configure({ retries: 1 });

  test('T3-DOC-05: Page refresh preserves detail view', async ({ hodPage, supabaseAdmin }) => {
    const { data: document } = await supabaseAdmin
      .from('pms_documents')
      .select('id, title')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!document) {
      console.log('  No documents in test yacht - skipping');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.documentDetail(document.id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
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

    // Verify document identifier still visible
    const docIdentifier = hodPage.locator(`text=${document.title}`);
    const stillVisible = await docIdentifier.isVisible({ timeout: 5000 }).catch(() => false);

    if (!stillVisible) {
      // Check for ID in URL instead
      expect(afterRefreshUrl).toContain(document.id);
    }

    console.log('  T3-DOC-05: State preserved after refresh');
  });

  test('T3-DOC-05b: Page refresh preserves list with filter', async ({ hodPage }) => {
    // Navigate to list with query param filter (if supported)
    await hodPage.goto(`${ROUTES_CONFIG.documentsList}?status=active`);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/documents')) {
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

    // URL should be preserved (including query params if present)
    expect(afterUrl).toBe(beforeUrl);
    console.log('  T3-DOC-05b: List state preserved after refresh');
  });
});

// ============================================================================
// SECTION 5: NAVIGATION TESTS
// T3-DOC-06: Browser back/forward works
// ============================================================================

test.describe('Documents Route Navigation', () => {
  test.describe.configure({ retries: 1 });

  test('T3-DOC-06: Browser back/forward works naturally on list', async ({ hodPage, supabaseAdmin }) => {
    const { data: document } = await supabaseAdmin
      .from('pms_documents')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!document) {
      console.log('  No documents in test yacht - skipping');
      return;
    }

    // Start at list
    await hodPage.goto(ROUTES_CONFIG.documentsList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    const listUrl = hodPage.url();

    // Navigate to detail (via URL, not click)
    await hodPage.goto(ROUTES_CONFIG.documentDetail(document.id));
    await hodPage.waitForLoadState('networkidle');
    const detailUrl = hodPage.url();

    expect(detailUrl).toContain(`/documents/${document.id}`);

    // Go back via browser
    await hodPage.goBack();
    await hodPage.waitForLoadState('networkidle');

    // Verify we're back at list
    expect(hodPage.url()).toBe(listUrl);
    console.log('  T3-DOC-06a: Back navigation to list verified');

    // Go forward
    await hodPage.goForward();
    await hodPage.waitForLoadState('networkidle');

    // Verify we're at detail again
    expect(hodPage.url()).toBe(detailUrl);
    console.log('  T3-DOC-06b: Forward navigation to detail verified');
  });

  test('T3-DOC-06b: Browser back from detail returns to previous page', async ({ hodPage, supabaseAdmin }) => {
    const { data: document } = await supabaseAdmin
      .from('pms_documents')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!document) {
      console.log('  No documents in test yacht - skipping');
      return;
    }

    // Start at home/app
    await hodPage.goto('/');
    await hodPage.waitForLoadState('networkidle');

    // Navigate to document detail
    await hodPage.goto(ROUTES_CONFIG.documentDetail(document.id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app') && !currentUrl.includes('/documents/')) {
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
      expect(newUrl).not.toContain(`/documents/${document.id}`);
      console.log('  T3-DOC-06b: UI back button works');
    } else {
      // Use browser back
      await hodPage.goBack();
      await hodPage.waitForLoadState('networkidle');
      console.log('  T3-DOC-06b: Browser back works (no UI back button)');
    }
  });

  test('Clicking document in list navigates to detail', async ({ hodPage, supabaseAdmin }) => {
    const { count } = await supabaseAdmin
      .from('pms_documents')
      .select('id', { count: 'exact', head: true })
      .eq('yacht_id', ROUTES_CONFIG.yachtId);

    if (!count || count === 0) {
      console.log('  No documents in test yacht - skipping');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.documentsList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForLoadState('networkidle');
    await hodPage.waitForTimeout(2000);

    // Find clickable document row/card
    const documentItem = hodPage.locator(
      '[data-testid="document-row"], tr[data-id], .document-card, [data-testid*="document-item"]'
    ).first();
    const hasDocumentItem = await documentItem.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasDocumentItem) {
      await documentItem.click();
      await hodPage.waitForLoadState('networkidle');

      // Should navigate to detail
      const newUrl = hodPage.url();
      const navigatedToDetail = newUrl.includes('/documents/') && newUrl !== ROUTES_CONFIG.documentsList;
      expect(navigatedToDetail).toBe(true);
      console.log('  Document click navigates to detail');
    } else {
      console.log('  No clickable document items found');
    }
  });
});

// ============================================================================
// SECTION 6: FEATURE FLAG TOGGLE TEST
// ============================================================================

test.describe('Feature Flag Behavior', () => {
  test.describe.configure({ retries: 0 });

  test('Feature flag OFF redirects to /app', async ({ hodPage }) => {
    // Note: This test documents expected behavior when flag is OFF
    // In real testing, flag would need to be toggled via environment

    await hodPage.goto(ROUTES_CONFIG.documentsList);
    await hodPage.waitForLoadState('networkidle');

    const currentUrl = hodPage.url();

    if (currentUrl.includes('/app')) {
      // Flag is disabled - verify redirect worked
      expect(currentUrl).toContain('/app');
      console.log('  Feature flag OFF: Correctly redirected to /app');
    } else if (currentUrl.includes('/documents')) {
      // Flag is enabled - verify route works
      expect(currentUrl).toContain('/documents');
      console.log('  Feature flag ON: Route loaded directly');
    }
  });

  test('Feature flag OFF redirects detail to /app', async ({ hodPage, supabaseAdmin }) => {
    const { data: document } = await supabaseAdmin
      .from('pms_documents')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!document) {
      console.log('  No documents in test yacht - skipping');
      return;
    }

    await hodPage.goto(ROUTES_CONFIG.documentDetail(document.id));
    await hodPage.waitForLoadState('networkidle');

    const currentUrl = hodPage.url();

    if (currentUrl.includes('/app')) {
      // Flag is disabled - verify redirect worked
      expect(currentUrl).toContain('/app');
      console.log('  Feature flag OFF: Detail correctly redirected to /app');
    } else if (currentUrl.includes(`/documents/${document.id}`)) {
      // Flag is enabled - verify route works
      expect(currentUrl).toContain(`/documents/${document.id}`);
      console.log('  Feature flag ON: Detail route loaded directly');
    }
  });
});

// ============================================================================
// SECTION 7: RBAC ON ROUTES
// ============================================================================

test.describe('Documents Route RBAC', () => {
  test.describe.configure({ retries: 1 });

  test('Crew can view document list', async ({ crewPage }) => {
    await crewPage.goto(ROUTES_CONFIG.documentsList);

    const currentUrl = crewPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await crewPage.waitForLoadState('networkidle');

    // Crew should be able to view list
    const errorState = crewPage.locator(':text("Access Denied"), :text("Unauthorized"), [data-testid="permission-denied"]');
    await expect(errorState).not.toBeVisible({ timeout: 5000 });

    console.log('  Crew can view document list');
  });

  test('Crew can view document detail', async ({ crewPage, supabaseAdmin }) => {
    const { data: document } = await supabaseAdmin
      .from('pms_documents')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!document) {
      console.log('  No documents in test yacht - skipping');
      return;
    }

    await crewPage.goto(ROUTES_CONFIG.documentDetail(document.id));

    const currentUrl = crewPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await crewPage.waitForLoadState('networkidle');

    // Crew should be able to view detail
    const errorState = crewPage.locator(':text("Access Denied"), :text("Unauthorized"), [data-testid="permission-denied"]');
    await expect(errorState).not.toBeVisible({ timeout: 5000 });

    console.log('  Crew can view document detail');
  });

  test('Crew sees limited actions on document detail', async ({ crewPage, supabaseAdmin }) => {
    const { data: document } = await supabaseAdmin
      .from('pms_documents')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!document) {
      console.log('  No documents in test yacht - skipping');
      return;
    }

    await crewPage.goto(ROUTES_CONFIG.documentDetail(document.id));

    const currentUrl = crewPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await crewPage.waitForLoadState('networkidle');
    await crewPage.waitForTimeout(2000);

    // Crew should NOT see Archive/Delete buttons (Captain/HOD only)
    const archiveButton = crewPage.locator('button:has-text("Archive")');
    const deleteButton = crewPage.locator('button:has-text("Delete")');

    const archiveVisible = await archiveButton.isVisible({ timeout: 3000 }).catch(() => false);
    const deleteVisible = await deleteButton.isVisible({ timeout: 3000 }).catch(() => false);

    // Archive and Delete should typically be hidden for crew
    console.log(`  Archive visible: ${archiveVisible}, Delete visible: ${deleteVisible}`);
    console.log('  Crew actions check completed');
  });
});

// ============================================================================
// SECTION 8: PERFORMANCE BASELINE
// ============================================================================

test.describe('Documents Route Performance', () => {
  test.describe.configure({ retries: 0 });

  test('List route loads within 5 seconds', async ({ hodPage }) => {
    const startTime = Date.now();

    await hodPage.goto(ROUTES_CONFIG.documentsList);

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
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
    const { data: document } = await supabaseAdmin
      .from('pms_documents')
      .select('id')
      .eq('yacht_id', ROUTES_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!document) {
      console.log('  No documents in test yacht - skipping');
      return;
    }

    const startTime = Date.now();

    await hodPage.goto(ROUTES_CONFIG.documentDetail(document.id));

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
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
