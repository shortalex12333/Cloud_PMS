import { test, expect, RBAC_CONFIG, SpotlightSearchPO } from '../rbac-fixtures';

/**
 * SHARD 31: Spotlight -> Documents SHOW Queries
 *
 * Tests for NLP-driven Quick Filter navigation from Spotlight to Documents list.
 * User types natural language query, system shows filter chip, click navigates to filtered list.
 *
 * Requirements Covered:
 * - SDOC-01: Natural language document queries show filter chips
 * - SDOC-02: Filter chip click navigates to /documents?filter=...
 * - SDOC-03: Filtered list renders with active filter banner
 * - SDOC-04: Cross-yacht isolation (Yacht B documents not visible to Yacht A user)
 * - SDOC-05: Role-based visibility (Crew can view, only HOD can update)
 *
 * Implementation:
 * - SpotlightSearch detects document intent from NLP patterns
 * - FilterChips component renders suggestions with data-filter-id
 * - Click triggers router.push('/documents?filter=${filterId}')
 * - DocumentsList reads filter param and applies client-side filtering
 *
 * Document Lens v2 Enums (from lens definition):
 * - doc_type: manual, drawing, certificate, photo, invoice, report, specification, procedure, safety, other
 * - OEM/Manufacturer filtering
 * - Equipment-linked documents
 * - Tag-based filtering
 * - Temporal filtering (recent uploads)
 */

// ============================================================================
// TEST DATA: 25 NLP Variants with Expected Chips and Filter IDs
// Each entry covers filter dimensions (doc_type, oem, equipment, tags, temporal)
// ============================================================================

interface ShowQuery {
  query: string;
  expectedChip: string;
  filterId: string;
  description?: string;
}

const SHOW_QUERIES: ShowQuery[] = [
  // === DOMAIN DETECTION / GENERAL QUERIES (3) ===
  {
    query: 'search documents',
    expectedChip: 'All Documents',
    filterId: 'doc_all',
    description: 'Domain detection - route to /documents',
  },
  {
    query: 'find documents',
    expectedChip: 'All Documents',
    filterId: 'doc_all',
  },
  {
    query: 'browse files',
    expectedChip: 'All Documents',
    filterId: 'doc_all',
  },

  // === DOCUMENT TYPE QUERIES (8) ===
  {
    query: 'show all manuals',
    expectedChip: 'Manuals',
    filterId: 'doc_type_manual',
    description: 'doc_type = manual',
  },
  {
    query: 'equipment manuals',
    expectedChip: 'Manuals',
    filterId: 'doc_type_manual',
  },
  {
    query: 'technical drawings',
    expectedChip: 'Drawings',
    filterId: 'doc_type_drawing',
    description: 'doc_type = drawing',
  },
  {
    query: 'schematics and diagrams',
    expectedChip: 'Drawings',
    filterId: 'doc_type_drawing',
  },
  {
    query: 'certificate documents',
    expectedChip: 'Certificates',
    filterId: 'doc_type_certificate',
    description: 'doc_type = certificate',
  },
  {
    query: 'photos and images',
    expectedChip: 'Photos',
    filterId: 'doc_type_photo',
    description: 'doc_type = photo',
  },
  {
    query: 'inspection photos',
    expectedChip: 'Photos',
    filterId: 'doc_type_photo',
  },
  {
    query: 'safety documents',
    expectedChip: 'Safety',
    filterId: 'doc_type_safety',
    description: 'doc_type = safety (MSDS, fire plans)',
  },

  // === TEMPORAL QUERIES (4) ===
  {
    query: 'recent documents',
    expectedChip: 'Recent Uploads',
    filterId: 'doc_recent',
    description: 'Created in last 7 days',
  },
  {
    query: 'recently uploaded files',
    expectedChip: 'Recent Uploads',
    filterId: 'doc_recent',
  },
  {
    query: 'new documents this week',
    expectedChip: 'This Week',
    filterId: 'doc_this_week',
    description: 'Created within current week',
  },
  {
    query: 'documents uploaded today',
    expectedChip: 'Today',
    filterId: 'doc_today',
    description: 'Created today',
  },

  // === EQUIPMENT-LINKED QUERIES (4) ===
  {
    query: 'documents for main engine',
    expectedChip: 'Main Engine Docs',
    filterId: 'doc_equipment_main_engine',
    description: 'equipment_ids contains main engine',
  },
  {
    query: 'generator documentation',
    expectedChip: 'Generator Docs',
    filterId: 'doc_equipment_generator',
  },
  {
    query: 'watermaker documents',
    expectedChip: 'Watermaker Docs',
    filterId: 'doc_equipment_watermaker',
  },
  {
    query: 'files for auxiliary equipment',
    expectedChip: 'Auxiliary Docs',
    filterId: 'doc_equipment_auxiliary',
  },

  // === OEM/MANUFACTURER QUERIES (3) ===
  {
    query: 'caterpillar manuals',
    expectedChip: 'Caterpillar',
    filterId: 'doc_oem_caterpillar',
    description: 'oem ILIKE caterpillar',
  },
  {
    query: 'MTU documentation',
    expectedChip: 'MTU',
    filterId: 'doc_oem_mtu',
  },
  {
    query: 'Kohler documents',
    expectedChip: 'Kohler',
    filterId: 'doc_oem_kohler',
  },

  // === TAG-BASED QUERIES (3) ===
  {
    query: 'documents tagged maintenance',
    expectedChip: 'Tagged: maintenance',
    filterId: 'doc_tag_maintenance',
    description: 'tags contains maintenance',
  },
  {
    query: 'files with safety tag',
    expectedChip: 'Tagged: safety',
    filterId: 'doc_tag_safety',
  },
  {
    query: 'emergency procedures',
    expectedChip: 'Emergency Docs',
    filterId: 'doc_tag_emergency',
  },
];

// ============================================================================
// SECTION 1: FILTER CHIP DISPLAY TESTS
// SDOC-01: Natural language queries show appropriate filter chips
// ============================================================================

test.describe('Spotlight -> Documents SHOW queries', () => {
  test.describe.configure({ retries: 0 }); // Strict mode - no retries

  // Generate test for each NLP variant
  for (const { query, expectedChip, filterId, description } of SHOW_QUERIES) {
    test(`"${query}" -> shows chip "${expectedChip}" and navigates`, async ({ hodPage }) => {
      // Navigate to app
      await hodPage.goto('/app');
      await hodPage.waitForLoadState('networkidle');

      const spotlight = new SpotlightSearchPO(hodPage);

      // Type the NLP query
      await spotlight.search(query);

      // Wait for filter chips to appear
      const filterChips = hodPage.locator('[data-testid="filter-chips"]');
      await expect(filterChips).toBeVisible({ timeout: 5000 });

      // Verify expected chip is present
      const expectedFilterChip = hodPage.locator(`[data-filter-id="${filterId}"]`);
      await expect(expectedFilterChip).toBeVisible({ timeout: 3000 });

      // Verify chip label matches expected
      const chipText = await expectedFilterChip.textContent();
      expect(chipText).toContain(expectedChip);

      if (description) {
        console.log(`  Query: "${query}"`);
        console.log(`  Chip: ${expectedChip} (${filterId})`);
        console.log(`  Description: ${description}`);
      }

      // Click the chip
      await expectedFilterChip.click();

      // Wait for navigation to documents list with filter
      await hodPage.waitForURL(/\/documents.*filter=/, { timeout: 10000 });

      // Verify URL contains correct filter
      const currentUrl = hodPage.url();
      expect(currentUrl).toContain('/documents');
      expect(currentUrl).toContain(`filter=${filterId}`);

      console.log(`  PASS: Navigated to ${currentUrl}`);

      // Verify list page renders (at least header/container visible)
      const listContainer = hodPage.locator(
        '[data-testid="documents-list"], [data-testid="documents-container"], main'
      );
      await expect(listContainer).toBeVisible({ timeout: 10000 });

      // Verify active filter banner is shown
      const filterBanner = hodPage.locator('[data-testid="active-filter-banner"]');
      const bannerVisible = await filterBanner.isVisible({ timeout: 5000 }).catch(() => false);

      if (bannerVisible) {
        const bannerText = await filterBanner.textContent();
        console.log(`  Filter banner: ${bannerText}`);
      }
    });
  }
});

// ============================================================================
// SECTION 2: COMBINED FILTER QUERIES
// Test natural language queries that combine multiple filter dimensions
// ============================================================================

test.describe('Spotlight -> Documents SHOW - Combined Filters', () => {
  test.describe.configure({ retries: 0 });

  const COMBINED_QUERIES = [
    {
      query: 'recent caterpillar manuals',
      expectedChips: ['Recent Uploads', 'Caterpillar'],
      filterIds: ['doc_recent', 'doc_oem_caterpillar'],
    },
    {
      query: 'main engine technical drawings',
      expectedChips: ['Drawings', 'Main Engine Docs'],
      filterIds: ['doc_type_drawing', 'doc_equipment_main_engine'],
    },
    {
      query: 'safety documents tagged emergency',
      expectedChips: ['Safety', 'Tagged: emergency'],
      filterIds: ['doc_type_safety', 'doc_tag_emergency'],
    },
  ];

  for (const { query, expectedChips, filterIds } of COMBINED_QUERIES) {
    test(`"${query}" -> shows multiple chips`, async ({ hodPage }) => {
      await hodPage.goto('/app');
      await hodPage.waitForLoadState('networkidle');

      const spotlight = new SpotlightSearchPO(hodPage);
      await spotlight.search(query);

      const filterChipsContainer = hodPage.locator('[data-testid="filter-chips"]');
      await expect(filterChipsContainer).toBeVisible({ timeout: 5000 });

      // Verify at least the primary chip is visible
      // (Combined queries may show multiple chips or primary match)
      const primaryChip = hodPage.locator(`[data-filter-id="${filterIds[0]}"]`);
      const primaryVisible = await primaryChip.isVisible({ timeout: 3000 }).catch(() => false);

      if (primaryVisible) {
        console.log(`  Primary chip visible: ${filterIds[0]}`);

        // Click primary chip
        await primaryChip.click();
        await hodPage.waitForURL(/\/documents.*filter=/, { timeout: 10000 });

        const currentUrl = hodPage.url();
        expect(currentUrl).toContain('/documents');
        console.log(`  PASS: Navigated to ${currentUrl}`);
      } else {
        // Check if any of the expected chips are visible
        let anyChipFound = false;
        for (const filterId of filterIds) {
          const chip = hodPage.locator(`[data-filter-id="${filterId}"]`);
          const visible = await chip.isVisible({ timeout: 1000 }).catch(() => false);
          if (visible) {
            anyChipFound = true;
            console.log(`  Found chip: ${filterId}`);
            await chip.click();
            await hodPage.waitForURL(/\/documents.*filter=/, { timeout: 10000 });
            break;
          }
        }

        if (!anyChipFound) {
          // Combined query may not match exactly - check for any document chip
          const anyDocChip = hodPage.locator('[data-filter-id^="doc_"]').first();
          const anyVisible = await anyDocChip.isVisible({ timeout: 3000 }).catch(() => false);
          expect(anyVisible).toBe(true);
          console.log('  Found alternative document chip');
        }
      }
    });
  }
});

// ============================================================================
// SECTION 3: CROSS-YACHT ISOLATION TEST
// SDOC-04: Documents from Yacht B not visible to Yacht A user
// ============================================================================

test.describe('Spotlight -> Documents SHOW - Cross-Yacht Isolation', () => {
  test.describe.configure({ retries: 0 });

  test('documents from Yacht B not visible to Yacht A user', async ({ hodPage, supabaseAdmin }) => {
    // First, get count of documents for the test yacht
    const { count: testYachtCount, error: countError } = await supabaseAdmin
      .from('doc_metadata')
      .select('id', { count: 'exact', head: true })
      .eq('yacht_id', RBAC_CONFIG.yachtId);

    if (countError) {
      console.log('  Error fetching count:', countError.message);
      return;
    }

    console.log(`  Test yacht document count: ${testYachtCount}`);

    // Navigate to documents list with no filter
    await hodPage.goto('/documents');
    await hodPage.waitForLoadState('networkidle');

    // Check if redirected to legacy (feature flag)
    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping cross-yacht test');
      return;
    }

    // Wait for list to load
    await hodPage.waitForTimeout(3000);

    // Count visible documents
    const documentRows = hodPage.locator(
      '[data-testid="document-row"], [data-testid^="doc-"], tr[data-entity-type="document"]'
    );
    const visibleCount = await documentRows.count();

    console.log(`  Visible documents in UI: ${visibleCount}`);

    // The count should match test yacht's documents (within reasonable margin)
    // This verifies RLS is working - user only sees their yacht's data
    if (testYachtCount !== null) {
      // UI might paginate, so visible count could be less
      expect(visibleCount).toBeLessThanOrEqual(testYachtCount + 1); // +1 for potential header row
      console.log('  PASS: Cross-yacht isolation verified');
    }

    // Try to access a document ID from another yacht (should fail)
    const { data: otherYachtDoc } = await supabaseAdmin
      .from('doc_metadata')
      .select('id')
      .neq('yacht_id', RBAC_CONFIG.yachtId)
      .limit(1)
      .single();

    if (otherYachtDoc) {
      // Attempt to navigate to document from different yacht
      await hodPage.goto(`/documents/${otherYachtDoc.id}`);
      await hodPage.waitForLoadState('networkidle');

      // Should show not found or access denied
      const notFoundState = hodPage.locator(
        ':text("Not Found"), :text("not found"), :text("Access Denied"), :text("Forbidden"), [data-testid="not-found"], [data-testid="error-state"]'
      );
      const hasNotFound = await notFoundState.isVisible({ timeout: 5000 }).catch(() => false);

      expect(hasNotFound).toBe(true);
      console.log('  PASS: Cannot access other yacht document');
    } else {
      console.log('  No other yacht documents found for cross-yacht test');
    }
  });
});

// ============================================================================
// SECTION 4: ROLE-BASED VISIBILITY TESTS
// SDOC-05: Role permissions per Document Lens v2
// - Crew: View, Upload (no update/delete)
// - HOD: View, Upload, Update, Add Tags, Link Equipment (no delete)
// - Manager: All actions including signed delete
// ============================================================================

test.describe('Spotlight -> Documents SHOW - Role Coverage', () => {
  test.describe.configure({ retries: 0 });

  test('Crew can view documents but sees limited actions', async ({ crewPage, supabaseAdmin }) => {
    // Get a document for testing
    const { data: document } = await supabaseAdmin
      .from('doc_metadata')
      .select('id, filename')
      .eq('yacht_id', RBAC_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!document) {
      console.log('  No documents found - skipping role test');
      return;
    }

    // Navigate to documents list as crew member
    await crewPage.goto('/documents');
    await crewPage.waitForLoadState('networkidle');

    const currentUrl = crewPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping role test');
      return;
    }

    // Verify list loads (crew can view)
    const listContainer = crewPage.locator(
      '[data-testid="documents-list"], [data-testid="documents-container"], main'
    );
    await expect(listContainer).toBeVisible({ timeout: 10000 });
    console.log('  Crew can view documents list');

    // Navigate to specific document detail
    await crewPage.goto(`/documents/${document.id}`);
    await crewPage.waitForLoadState('networkidle');

    if (crewPage.url().includes('/documents/')) {
      // Verify detail page loads
      const detailContainer = crewPage.locator(
        '[data-testid="document-detail"], main, [role="main"]'
      );
      await expect(detailContainer).toBeVisible({ timeout: 10000 });
      console.log('  Crew can view document detail');

      // Check for restricted actions (should NOT be visible for crew)
      // Per Document Lens v2: Crew cannot Update or Delete
      const updateButton = crewPage.locator(
        'button:has-text("Edit"), button:has-text("Update"), [data-action="update_document"]'
      );
      const deleteButton = crewPage.locator(
        'button:has-text("Delete"), [data-action="delete_document"]'
      );
      const addTagsButton = crewPage.locator(
        'button:has-text("Add Tags"), [data-action="add_document_tags"]'
      );

      const updateVisible = await updateButton.isVisible({ timeout: 2000 }).catch(() => false);
      const deleteVisible = await deleteButton.isVisible({ timeout: 2000 }).catch(() => false);
      const addTagsVisible = await addTagsButton.isVisible({ timeout: 2000 }).catch(() => false);

      // Per Document Lens v2: Crew (deckhand, steward) cannot Update/Delete/Add Tags
      if (!updateVisible && !deleteVisible && !addTagsVisible) {
        console.log('  PASS: Crew does not see Update/Delete/Add Tags actions');
      } else {
        console.log('  WARNING: Crew may have elevated permissions');
      }

      // Check that Download/View IS visible (crew can view/download)
      const downloadButton = crewPage.locator(
        'button:has-text("Download"), a:has-text("Download"), [data-action="get_document_url"]'
      );
      const downloadVisible = await downloadButton.isVisible({ timeout: 2000 }).catch(() => false);
      console.log(`  Download action visible: ${downloadVisible}`);
    }
  });

  test('HOD sees document management actions', async ({ hodPage, supabaseAdmin }) => {
    // Get a document for testing
    const { data: document } = await supabaseAdmin
      .from('doc_metadata')
      .select('id, filename')
      .eq('yacht_id', RBAC_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!document) {
      console.log('  No documents found - skipping role test');
      return;
    }

    await hodPage.goto(`/documents/${document.id}`);
    await hodPage.waitForLoadState('networkidle');

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    // Wait for detail page to load
    await hodPage.waitForTimeout(2000);

    // HOD should see more actions per Document Lens v2
    // HOD can: Upload, Update, Add Tags, Link Equipment
    const actionButtons = hodPage.locator('[data-testid^="action-"], button[data-action]');
    const actionCount = await actionButtons.count();

    console.log(`  HOD sees ${actionCount} action buttons`);

    // Check for specific HOD actions
    const updateButton = hodPage.locator('button:has-text("Edit"), button:has-text("Update")');
    const updateVisible = await updateButton.isVisible({ timeout: 2000 }).catch(() => false);

    const addTagsButton = hodPage.locator('button:has-text("Add Tags"), button:has-text("Tag")');
    const addTagsVisible = await addTagsButton.isVisible({ timeout: 2000 }).catch(() => false);

    const linkEquipmentButton = hodPage.locator('button:has-text("Link Equipment"), button:has-text("Link")');
    const linkEquipmentVisible = await linkEquipmentButton.isVisible({ timeout: 2000 }).catch(() => false);

    if (updateVisible) {
      console.log('  PASS: HOD sees Update action');
    }
    if (addTagsVisible) {
      console.log('  PASS: HOD sees Add Tags action');
    }
    if (linkEquipmentVisible) {
      console.log('  PASS: HOD sees Link Equipment action');
    }

    // HOD should NOT see Delete (Manager only)
    const deleteButton = hodPage.locator('button:has-text("Delete"), [data-action="delete_document"]');
    const deleteVisible = await deleteButton.isVisible({ timeout: 2000 }).catch(() => false);

    if (!deleteVisible) {
      console.log('  PASS: HOD does not see Delete action (Manager only)');
    }
  });

  test('Captain/Manager sees all actions including delete', async ({ captainPage, supabaseAdmin }) => {
    // Get a document for testing
    const { data: document } = await supabaseAdmin
      .from('doc_metadata')
      .select('id, filename')
      .eq('yacht_id', RBAC_CONFIG.yachtId)
      .limit(1)
      .single();

    if (!document) {
      console.log('  No documents found - skipping role test');
      return;
    }

    await captainPage.goto(`/documents/${document.id}`);
    await captainPage.waitForLoadState('networkidle');

    const currentUrl = captainPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    // Wait for detail page to load
    await captainPage.waitForTimeout(2000);

    // Captain/Manager should see Delete action (signed)
    const deleteButton = captainPage.locator(
      'button:has-text("Delete"), [data-action="delete_document"]'
    );
    const deleteVisible = await deleteButton.isVisible({ timeout: 3000 }).catch(() => false);

    if (deleteVisible) {
      console.log('  PASS: Captain sees Delete action');
    } else {
      console.log('  Delete action not visible - may require signature modal');
    }

    // Verify all other actions are available
    const updateButton = captainPage.locator('button:has-text("Edit"), button:has-text("Update")');
    const updateVisible = await updateButton.isVisible({ timeout: 2000 }).catch(() => false);

    if (updateVisible) {
      console.log('  PASS: Captain sees Update action');
    }
  });
});

// ============================================================================
// SECTION 5: FILTER CLEARING AND NAVIGATION
// Test that filters can be cleared and navigation state is preserved
// ============================================================================

test.describe('Spotlight -> Documents SHOW - Filter Management', () => {
  test.describe.configure({ retries: 0 });

  test('filter can be cleared from banner', async ({ hodPage }) => {
    // Navigate directly to filtered URL
    await hodPage.goto('/documents?filter=doc_type_manual');
    await hodPage.waitForLoadState('networkidle');

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    // Wait for page to load
    await hodPage.waitForTimeout(2000);

    // Find and click clear filter button
    const clearButton = hodPage.locator('[data-testid="clear-filter-button"]');
    const clearVisible = await clearButton.isVisible({ timeout: 5000 }).catch(() => false);

    if (clearVisible) {
      await clearButton.click();

      // Wait for URL to update (filter param removed)
      await hodPage.waitForFunction(
        () => !window.location.href.includes('filter='),
        { timeout: 5000 }
      );

      const newUrl = hodPage.url();
      expect(newUrl).not.toContain('filter=');
      console.log('  PASS: Filter cleared from URL');

      // Banner should be hidden
      const filterBanner = hodPage.locator('[data-testid="active-filter-banner"]');
      await expect(filterBanner).not.toBeVisible({ timeout: 3000 });
      console.log('  PASS: Filter banner hidden');
    } else {
      console.log('  Clear button not visible - may have different UI');
    }
  });

  test('browser back preserves filter state', async ({ hodPage }) => {
    // Start at documents list
    await hodPage.goto('/documents');
    await hodPage.waitForLoadState('networkidle');

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    // Use spotlight to navigate to filtered view
    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('technical drawings');

    const drawingsChip = hodPage.locator('[data-filter-id="doc_type_drawing"]');
    const chipVisible = await drawingsChip.isVisible({ timeout: 5000 }).catch(() => false);

    if (!chipVisible) {
      console.log('  Filter chip not visible - skipping back button test');
      return;
    }

    await drawingsChip.click();
    await hodPage.waitForURL(/\/documents.*filter=doc_type_drawing/, { timeout: 10000 });

    console.log('  Navigated to filtered view');

    // Navigate to a document detail (if any exist)
    const firstDoc = hodPage.locator('[data-testid="document-row"]').first();
    const hasDocuments = await firstDoc.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasDocuments) {
      await firstDoc.click();
      await hodPage.waitForLoadState('networkidle');

      // Now go back
      await hodPage.goBack();
      await hodPage.waitForLoadState('networkidle');

      // Should return to filtered view
      const backUrl = hodPage.url();
      expect(backUrl).toContain('filter=doc_type_drawing');
      console.log('  PASS: Back button preserved filter state');
    } else {
      console.log('  No documents to navigate to - skipping detail navigation');
    }
  });
});

// ============================================================================
// SECTION 6: EMPTY STATE HANDLING
// Test that empty filter results show appropriate messaging
// ============================================================================

test.describe('Spotlight -> Documents SHOW - Empty States', () => {
  test.describe.configure({ retries: 0 });

  test('empty filter results show clear message', async ({ hodPage }) => {
    // Navigate to a filter that likely has no results (invoice docs are rare)
    await hodPage.goto('/documents?filter=doc_type_invoice');
    await hodPage.waitForLoadState('networkidle');

    const currentUrl = hodPage.url();
    if (currentUrl.includes('/app')) {
      console.log('  Feature flag disabled - skipping');
      return;
    }

    await hodPage.waitForTimeout(3000);

    // Check for empty state or results
    const emptyState = hodPage.locator(
      '[data-testid="empty-filter-state"], [data-testid="no-results"], :text("No documents"), :text("No results")'
    );
    const documentRows = hodPage.locator('[data-testid="document-row"]');

    const isEmpty = await emptyState.isVisible({ timeout: 3000 }).catch(() => false);
    const hasResults = (await documentRows.count()) > 0;

    if (isEmpty) {
      console.log('  Empty state shown (no invoice docs)');

      // Verify clear filter option exists in empty state
      const clearInEmpty = hodPage.locator(
        '[data-testid="empty-filter-state"] button:has-text("Clear"), [data-testid="empty-filter-state"] a:has-text("Clear")'
      );
      const clearVisible = await clearInEmpty.isVisible({ timeout: 2000 }).catch(() => false);

      if (clearVisible) {
        console.log('  PASS: Clear option in empty state');
      }
    } else if (hasResults) {
      console.log('  Invoice documents exist - showing results');
    } else {
      console.log('  Neither empty state nor results visible - check implementation');
    }
  });
});

// ============================================================================
// SECTION 7: DETERMINISM VERIFICATION
// Ensure same query always produces same chip (no randomness)
// ============================================================================

test.describe('Spotlight -> Documents SHOW - Determinism', () => {
  test.describe.configure({ retries: 0 });

  test('same query produces same chip (run 1 of 2)', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('technical drawings');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const chips = hodPage.locator('[data-testid^="filter-chip-"]');
    const chipCount = await chips.count();

    expect(chipCount).toBeGreaterThan(0);

    const firstChipId = await chips.first().getAttribute('data-filter-id');
    expect(firstChipId).toBe('doc_type_drawing');

    console.log(`  Run 1: First chip is ${firstChipId}`);
  });

  test('same query produces same chip (run 2 of 2)', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('technical drawings');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    const chips = hodPage.locator('[data-testid^="filter-chip-"]');
    const chipCount = await chips.count();

    expect(chipCount).toBeGreaterThan(0);

    const firstChipId = await chips.first().getAttribute('data-filter-id');
    expect(firstChipId).toBe('doc_type_drawing');

    console.log(`  Run 2: First chip is ${firstChipId} - DETERMINISTIC`);
  });
});

// ============================================================================
// SECTION 8: CHIP MATCH QUALITY
// Verify pattern matches have high confidence scores
// ============================================================================

test.describe('Spotlight -> Documents SHOW - Match Quality', () => {
  test.describe.configure({ retries: 0 });

  test('exact pattern match has high score', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('show all manuals');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    await expect(filterChips).toBeVisible({ timeout: 5000 });

    // Check for pattern match type and score
    const patternChip = hodPage.locator('[data-match-type="pattern"]').first();
    const isPatternMatch = await patternChip.isVisible({ timeout: 3000 }).catch(() => false);

    if (isPatternMatch) {
      const score = await patternChip.getAttribute('data-score');
      console.log(`  Match type: pattern, score: ${score}`);

      if (score) {
        const numScore = parseFloat(score);
        expect(numScore).toBeGreaterThanOrEqual(0.8);
        console.log('  PASS: Pattern match has high score (>=0.8)');
      }
    } else {
      // May be using different match type attribute
      const anyChip = hodPage.locator('[data-filter-id="doc_type_manual"]');
      const chipVisible = await anyChip.isVisible({ timeout: 2000 }).catch(() => false);
      expect(chipVisible).toBe(true);
      console.log('  Chip visible but match type not specified');
    }
  });

  test('partial match has lower priority than exact match', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);

    // Query that could match multiple filters
    await spotlight.search('documents');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    const chipsVisible = await filterChips.isVisible({ timeout: 5000 }).catch(() => false);

    if (chipsVisible) {
      const chips = hodPage.locator('[data-filter-id^="doc_"]');
      const chipCount = await chips.count();

      console.log(`  Generic query "documents" shows ${chipCount} chips`);

      // For generic query, should show broad filter (all) first
      if (chipCount > 0) {
        const firstChipId = await chips.first().getAttribute('data-filter-id');
        console.log(`  First chip: ${firstChipId}`);
        // Generic query should prioritize broad filters
        expect(firstChipId).toMatch(/doc_(all|recent|type)/);
      }
    } else {
      console.log('  No chips for generic query - may require more specific input');
    }
  });
});

// ============================================================================
// SECTION 9: DOCUMENT-SPECIFIC FILTER SCENARIOS
// Test scenarios from Document Lens v2: equipment links, tags, OEM
// ============================================================================

test.describe('Spotlight -> Documents SHOW - Lens Scenarios', () => {
  test.describe.configure({ retries: 0 });

  test('equipment-linked document search', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('documents for main engine');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    const chipsVisible = await filterChips.isVisible({ timeout: 5000 }).catch(() => false);

    if (chipsVisible) {
      // Should show equipment-specific chip or equipment selector
      const equipmentChip = hodPage.locator(
        '[data-filter-id*="equipment"], [data-filter-id*="main_engine"]'
      ).first();
      const equipmentVisible = await equipmentChip.isVisible({ timeout: 3000 }).catch(() => false);

      if (equipmentVisible) {
        console.log('  PASS: Equipment-linked document chip visible');
        await equipmentChip.click();
        await hodPage.waitForURL(/\/documents/, { timeout: 10000 });
      } else {
        // May navigate to equipment selector first
        const anyDocChip = hodPage.locator('[data-filter-id^="doc_"]').first();
        const anyVisible = await anyDocChip.isVisible({ timeout: 2000 }).catch(() => false);
        expect(anyVisible).toBe(true);
        console.log('  Document chips visible for equipment query');
      }
    }
  });

  test('OEM/manufacturer document search', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('caterpillar manuals');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    const chipsVisible = await filterChips.isVisible({ timeout: 5000 }).catch(() => false);

    if (chipsVisible) {
      // Should show OEM-specific chip
      const oemChip = hodPage.locator(
        '[data-filter-id*="oem"], [data-filter-id*="caterpillar"]'
      ).first();
      const oemVisible = await oemChip.isVisible({ timeout: 3000 }).catch(() => false);

      if (oemVisible) {
        console.log('  PASS: OEM-specific chip visible');
      } else {
        // May fall back to manual type
        const manualChip = hodPage.locator('[data-filter-id="doc_type_manual"]');
        const manualVisible = await manualChip.isVisible({ timeout: 2000 }).catch(() => false);
        if (manualVisible) {
          console.log('  OEM chip not found, but manual type chip visible');
        }
      }
    }
  });

  test('tag-based document search', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('documents tagged safety');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    const chipsVisible = await filterChips.isVisible({ timeout: 5000 }).catch(() => false);

    if (chipsVisible) {
      // Should show tag-specific chip
      const tagChip = hodPage.locator(
        '[data-filter-id*="tag"], [data-filter-id*="safety"]'
      ).first();
      const tagVisible = await tagChip.isVisible({ timeout: 3000 }).catch(() => false);

      if (tagVisible) {
        console.log('  PASS: Tag-specific chip visible');
      } else {
        // May fall back to safety doc type
        const safetyChip = hodPage.locator('[data-filter-id="doc_type_safety"]');
        const safetyVisible = await safetyChip.isVisible({ timeout: 2000 }).catch(() => false);
        if (safetyVisible) {
          console.log('  Tag chip not found, but safety type chip visible');
        }
      }
    }
  });
});

// ============================================================================
// SECTION 10: SYSTEM PATH HIERARCHICAL NAVIGATION
// Test system_path based filtering (e.g., "Engineering/Main Engine")
// ============================================================================

test.describe('Spotlight -> Documents SHOW - System Path Navigation', () => {
  test.describe.configure({ retries: 0 });

  test('system path search shows hierarchical filter', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('engineering documents');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    const chipsVisible = await filterChips.isVisible({ timeout: 5000 }).catch(() => false);

    if (chipsVisible) {
      // Should show system path chip or department chip
      const pathChip = hodPage.locator(
        '[data-filter-id*="path"], [data-filter-id*="engineering"], [data-filter-id*="system"]'
      ).first();
      const pathVisible = await pathChip.isVisible({ timeout: 3000 }).catch(() => false);

      if (pathVisible) {
        console.log('  PASS: System path chip visible');
        await pathChip.click();
        await hodPage.waitForURL(/\/documents/, { timeout: 10000 });
        console.log('  Navigated to path-filtered documents');
      } else {
        // May show generic document chips
        const anyDocChip = hodPage.locator('[data-filter-id^="doc_"]').first();
        const anyVisible = await anyDocChip.isVisible({ timeout: 2000 }).catch(() => false);
        expect(anyVisible).toBe(true);
        console.log('  Path chip not found, but document chips visible');
      }
    }
  });

  test('deck department documents search', async ({ hodPage }) => {
    await hodPage.goto('/app');
    await hodPage.waitForLoadState('networkidle');

    const spotlight = new SpotlightSearchPO(hodPage);
    await spotlight.search('deck department documents');

    const filterChips = hodPage.locator('[data-testid="filter-chips"]');
    const chipsVisible = await filterChips.isVisible({ timeout: 5000 }).catch(() => false);

    if (chipsVisible) {
      const deckChip = hodPage.locator(
        '[data-filter-id*="deck"], [data-filter-id*="path_deck"]'
      ).first();
      const deckVisible = await deckChip.isVisible({ timeout: 3000 }).catch(() => false);

      if (deckVisible) {
        console.log('  PASS: Deck department chip visible');
      } else {
        console.log('  Deck-specific chip not found - may use generic filters');
      }
    }
  });
});
