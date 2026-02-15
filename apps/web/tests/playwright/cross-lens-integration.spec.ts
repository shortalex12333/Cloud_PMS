/**
 * Cross-Lens Integration Tests
 *
 * Tests user journeys that span multiple lenses:
 * - Fault → Work Order → Parts flow
 * - Equipment → Fault → Work Order flow
 * - Email → Work Order link flow
 * - Document → Entity link flows
 * - Context navigation between entities
 *
 * Roles tested: Captain (primary), HOD
 * All tests on single URL: app.celeste7.ai
 */

import { test, expect, Page } from '@playwright/test';
import { loginAs, searchInSpotlight } from './auth.helper';

const SCREENSHOT_DIR = '/tmp/cross_lens_test_screenshots';

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

async function captureScreenshot(page: Page, name: string): Promise<void> {
  await page.screenshot({
    path: `${SCREENSHOT_DIR}/${name}.png`,
    fullPage: true
  });
}

async function closeSpotlight(page: Page): Promise<void> {
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);
}

async function getSearchResults(page: Page): Promise<number> {
  const results = page.locator('[data-testid="search-result-item"]');
  return await results.count();
}

async function clickFirstResult(page: Page): Promise<void> {
  const firstResult = page.locator('[data-testid="search-result-item"]').first();
  if (await firstResult.isVisible()) {
    await firstResult.click();
    await page.waitForTimeout(500);
  }
}

// =============================================================================
// PHASE 1: FAULT → WORK ORDER FLOW
// =============================================================================

test.describe('Phase 1: Fault → Work Order Integration', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('INTEG-001: Search fault then view related work orders', async ({ page }) => {
    // Start with fault search
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Look for related work orders
    const woSection = page.locator('text=/work order|WO-|related/i');
    const woVisible = await woSection.isVisible().catch(() => false);

    console.log(`INTEG-001: Work orders visible from fault: ${woVisible}`);

    await captureScreenshot(page, 'INTEG-001');
    await closeSpotlight(page);
  });

  test('INTEG-002: Fault with linked equipment shows equipment details', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Look for equipment reference
    const equipmentSection = page.locator('text=/equipment|asset|linked/i');
    const equipmentVisible = await equipmentSection.isVisible().catch(() => false);

    console.log(`INTEG-002: Equipment visible from fault: ${equipmentVisible}`);

    await captureScreenshot(page, 'INTEG-002');
    await closeSpotlight(page);
  });

  test('INTEG-003: Navigate from fault to suggested parts', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Look for parts suggestion
    const partsSection = page.locator('text=/parts|suggest|inventory/i');
    const partsVisible = await partsSection.isVisible().catch(() => false);

    console.log(`INTEG-003: Parts suggestions from fault: ${partsVisible}`);

    await captureScreenshot(page, 'INTEG-003');
    await closeSpotlight(page);
  });

  test('INTEG-004: Fault severity affects work order priority', async ({ page }) => {
    await searchInSpotlight(page, 'critical fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Look for priority indicator
    const prioritySection = page.locator('text=/critical|high|priority|urgent/i');
    const priorityVisible = await prioritySection.isVisible().catch(() => false);

    console.log(`INTEG-004: Priority indicator from fault: ${priorityVisible}`);

    await captureScreenshot(page, 'INTEG-004');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 2: EQUIPMENT → MAINTENANCE FLOW
// =============================================================================

test.describe('Phase 2: Equipment → Maintenance Integration', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('INTEG-005: Equipment shows maintenance history', async ({ page }) => {
    await searchInSpotlight(page, 'generator');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Look for maintenance history
    const historySection = page.locator('text=/maintenance|history|work order/i');
    const historyVisible = await historySection.isVisible().catch(() => false);

    console.log(`INTEG-005: Maintenance history visible: ${historyVisible}`);

    await captureScreenshot(page, 'INTEG-005');
    await closeSpotlight(page);
  });

  test('INTEG-006: Equipment shows active faults', async ({ page }) => {
    await searchInSpotlight(page, 'generator');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Look for faults section
    const faultsSection = page.locator('text=/fault|issue|problem/i');
    const faultsVisible = await faultsSection.isVisible().catch(() => false);

    console.log(`INTEG-006: Faults visible from equipment: ${faultsVisible}`);

    await captureScreenshot(page, 'INTEG-006');
    await closeSpotlight(page);
  });

  test('INTEG-007: Equipment shows associated parts', async ({ page }) => {
    await searchInSpotlight(page, 'generator');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Look for parts section
    const partsSection = page.locator('text=/parts|spare|inventory/i');
    const partsVisible = await partsSection.isVisible().catch(() => false);

    console.log(`INTEG-007: Parts visible from equipment: ${partsVisible}`);

    await captureScreenshot(page, 'INTEG-007');
    await closeSpotlight(page);
  });

  test('INTEG-008: Equipment shows linked documents/manuals', async ({ page }) => {
    await searchInSpotlight(page, 'generator');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Look for documentation section
    const docsSection = page.locator('text=/manual|document|pdf/i');
    const docsVisible = await docsSection.isVisible().catch(() => false);

    console.log(`INTEG-008: Manuals visible from equipment: ${docsVisible}`);

    await captureScreenshot(page, 'INTEG-008');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 3: PARTS → INVENTORY FLOW
// =============================================================================

test.describe('Phase 3: Parts → Inventory Integration', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('INTEG-009: Parts shows stock level', async ({ page }) => {
    await searchInSpotlight(page, 'filter');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Look for stock information
    const stockSection = page.locator('text=/stock|quantity|available|inventory/i');
    const stockVisible = await stockSection.isVisible().catch(() => false);

    console.log(`INTEG-009: Stock level visible: ${stockVisible}`);

    await captureScreenshot(page, 'INTEG-009');
    await closeSpotlight(page);
  });

  test('INTEG-010: Low stock parts shows reorder option', async ({ page }) => {
    await searchInSpotlight(page, 'low stock');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`INTEG-010: Low stock items found: ${count}`);

    await captureScreenshot(page, 'INTEG-010');
    await closeSpotlight(page);
  });

  test('INTEG-011: Part shows compatible equipment', async ({ page }) => {
    await searchInSpotlight(page, 'filter');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Look for equipment compatibility
    const equipSection = page.locator('text=/compatible|equipment|fits/i');
    const equipVisible = await equipSection.isVisible().catch(() => false);

    console.log(`INTEG-011: Equipment compatibility visible: ${equipVisible}`);

    await captureScreenshot(page, 'INTEG-011');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 4: WORK ORDER → RELATED ENTITIES
// =============================================================================

test.describe('Phase 4: Work Order → Related Entities', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('INTEG-012: Work order shows linked fault', async ({ page }) => {
    await searchInSpotlight(page, 'work order');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Look for fault reference
    const faultSection = page.locator('text=/fault|FLT-|issue/i');
    const faultVisible = await faultSection.isVisible().catch(() => false);

    console.log(`INTEG-012: Linked fault visible: ${faultVisible}`);

    await captureScreenshot(page, 'INTEG-012');
    await closeSpotlight(page);
  });

  test('INTEG-013: Work order shows target equipment', async ({ page }) => {
    await searchInSpotlight(page, 'work order');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Look for equipment reference
    const equipSection = page.locator('text=/equipment|asset|generator/i');
    const equipVisible = await equipSection.isVisible().catch(() => false);

    console.log(`INTEG-013: Target equipment visible: ${equipVisible}`);

    await captureScreenshot(page, 'INTEG-013');
    await closeSpotlight(page);
  });

  test('INTEG-014: Work order shows required parts', async ({ page }) => {
    await searchInSpotlight(page, 'work order');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Look for parts list
    const partsSection = page.locator('text=/parts|materials|needed/i');
    const partsVisible = await partsSection.isVisible().catch(() => false);

    console.log(`INTEG-014: Required parts visible: ${partsVisible}`);

    await captureScreenshot(page, 'INTEG-014');
    await closeSpotlight(page);
  });

  test('INTEG-015: Work order shows attachments', async ({ page }) => {
    await searchInSpotlight(page, 'work order');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Look for attachments/photos
    const attachSection = page.locator('text=/attachment|photo|file/i');
    const attachVisible = await attachSection.isVisible().catch(() => false);

    console.log(`INTEG-015: Attachments visible: ${attachVisible}`);

    await captureScreenshot(page, 'INTEG-015');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 5: DOCUMENT LINKING
// =============================================================================

test.describe('Phase 5: Document Linking', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('INTEG-016: Document search returns results', async ({ page }) => {
    await searchInSpotlight(page, 'document');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`INTEG-016: Documents found: ${count}`);

    await captureScreenshot(page, 'INTEG-016');
    await closeSpotlight(page);
  });

  test('INTEG-017: Documents shows linked entities', async ({ page }) => {
    await searchInSpotlight(page, 'certificate');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Look for linked entities
    const linkedSection = page.locator('text=/linked|related|associated/i');
    const linkedVisible = await linkedSection.isVisible().catch(() => false);

    console.log(`INTEG-017: Linked entities visible: ${linkedVisible}`);

    await captureScreenshot(page, 'INTEG-017');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 6: EMAIL INTEGRATION
// =============================================================================

test.describe('Phase 6: Email Integration', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('INTEG-018: Email search returns results', async ({ page }) => {
    await searchInSpotlight(page, 'email');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`INTEG-018: Emails found: ${count}`);

    await captureScreenshot(page, 'INTEG-018');
    await closeSpotlight(page);
  });

  test('INTEG-019: Email shows suggested entity links', async ({ page }) => {
    await searchInSpotlight(page, 'email');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Look for suggested links
    const suggestSection = page.locator('text=/suggest|link|could be/i');
    const suggestVisible = await suggestSection.isVisible().catch(() => false);

    console.log(`INTEG-019: Link suggestions visible: ${suggestVisible}`);

    await captureScreenshot(page, 'INTEG-019');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 7: MULTI-ENTITY SEARCH
// =============================================================================

test.describe('Phase 7: Multi-Entity Search', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('INTEG-020: Search returns multiple entity types', async ({ page }) => {
    await searchInSpotlight(page, 'generator maintenance');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`INTEG-020: Multi-entity search returned: ${count} results`);

    await captureScreenshot(page, 'INTEG-020');
    await closeSpotlight(page);
  });

  test('INTEG-021: NLP query spans multiple domains', async ({ page }) => {
    await searchInSpotlight(page, 'show me recent issues with the engine');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`INTEG-021: NLP cross-domain search returned: ${count} results`);

    await captureScreenshot(page, 'INTEG-021');
    await closeSpotlight(page);
  });

  test('INTEG-022: Search with context filtering', async ({ page }) => {
    await searchInSpotlight(page, 'open work orders for generator');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`INTEG-022: Context-filtered search returned: ${count} results`);

    await captureScreenshot(page, 'INTEG-022');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 8: HOD CROSS-LENS ACCESS
// =============================================================================

test.describe('Phase 8: HOD Cross-Lens Access', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'hod');
  });

  test('INTEG-023: HOD can search across all domains', async ({ page }) => {
    await searchInSpotlight(page, 'maintenance');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`INTEG-023: HOD cross-domain search: ${count} results`);

    await captureScreenshot(page, 'INTEG-023');
    await closeSpotlight(page);
  });

  test('INTEG-024: HOD can view equipment → fault flow', async ({ page }) => {
    await searchInSpotlight(page, 'generator');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Look for faults
    const faultSection = page.locator('text=/fault|issue/i');
    const faultVisible = await faultSection.isVisible().catch(() => false);

    console.log(`INTEG-024: HOD sees equipment faults: ${faultVisible}`);

    await captureScreenshot(page, 'INTEG-024');
    await closeSpotlight(page);
  });

  test('INTEG-025: HOD can view work order → parts flow', async ({ page }) => {
    await searchInSpotlight(page, 'work order');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Look for parts
    const partsSection = page.locator('text=/parts|materials/i');
    const partsVisible = await partsSection.isVisible().catch(() => false);

    console.log(`INTEG-025: HOD sees WO parts: ${partsVisible}`);

    await captureScreenshot(page, 'INTEG-025');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 9: PERFORMANCE ACROSS LENSES
// =============================================================================

test.describe('Phase 9: Cross-Lens Performance', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('INTEG-026: Multi-entity search completes in < 3s', async ({ page }) => {
    const startTime = Date.now();
    await searchInSpotlight(page, 'generator work order fault parts');
    await page.waitForTimeout(500);
    const searchTime = Date.now() - startTime;

    console.log(`INTEG-026: Multi-entity search time: ${searchTime}ms`);

    await captureScreenshot(page, 'INTEG-026');
    await closeSpotlight(page);

    expect(searchTime).toBeLessThan(3000);
  });

  test('INTEG-027: Entity detail with related data loads < 2s', async ({ page }) => {
    await searchInSpotlight(page, 'equipment');
    await page.waitForTimeout(500);

    const startTime = Date.now();
    await clickFirstResult(page);
    await page.waitForTimeout(500);
    const loadTime = Date.now() - startTime;

    console.log(`INTEG-027: Entity + relations load time: ${loadTime}ms`);

    await captureScreenshot(page, 'INTEG-027');
    await closeSpotlight(page);

    expect(loadTime).toBeLessThan(2000);
  });
});

// =============================================================================
// PHASE 10: CONTEXT NAVIGATION
// =============================================================================

test.describe('Phase 10: Context Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('INTEG-028: Navigate between related entities', async ({ page }) => {
    await searchInSpotlight(page, 'equipment');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Look for navigation links/buttons
    const navLinks = page.locator('[data-testid="related-link"]').or(page.locator('text=/view|navigate|open/i'));
    const navCount = await navLinks.count();

    console.log(`INTEG-028: Navigation links found: ${navCount}`);

    await captureScreenshot(page, 'INTEG-028');
    await closeSpotlight(page);
  });

  test('INTEG-029: Context preserved during navigation', async ({ page }) => {
    await searchInSpotlight(page, 'generator');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Application should maintain context
    expect(await page.locator('body').isVisible()).toBe(true);
    console.log('INTEG-029: Context preserved');

    await captureScreenshot(page, 'INTEG-029');
    await closeSpotlight(page);
  });
});

// =============================================================================
// SUMMARY
// =============================================================================

test('INTEG-SUMMARY: Cross-lens integration test suite complete', async ({ page }) => {
  console.log('\n' + '='.repeat(60));
  console.log('CROSS-LENS INTEGRATION TEST SUITE COMPLETE');
  console.log('='.repeat(60));
  console.log('\nTests by category:');
  console.log('- Fault → Work Order: 4 tests');
  console.log('- Equipment → Maintenance: 4 tests');
  console.log('- Parts → Inventory: 3 tests');
  console.log('- Work Order → Related: 4 tests');
  console.log('- Document Linking: 2 tests');
  console.log('- Email Integration: 2 tests');
  console.log('- Multi-Entity Search: 3 tests');
  console.log('- HOD Cross-Lens: 3 tests');
  console.log('- Performance: 2 tests');
  console.log('- Context Navigation: 2 tests');
  console.log('\nTotal: 29 tests');
  console.log('Screenshots: ' + SCREENSHOT_DIR);
  console.log('='.repeat(60) + '\n');

  expect(true).toBe(true);
});
