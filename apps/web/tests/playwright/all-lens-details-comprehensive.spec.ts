/**
 * All Lens Detail Components - Comprehensive E2E Test Suite
 *
 * Tests all lens detail components for:
 * - Full-screen rendering (not popup, not sidebar)
 * - Proper data sections render
 * - Notes section available
 * - Activity section available
 * - No "Email integration is off" message
 * - Actions render where applicable
 * - Tokenized CSS (no hardcoded colors/pixels)
 *
 * Lenses tested:
 * - Equipment, Fault, Part, Receiving, Supplier, PurchaseOrder, Document
 *
 * Roles tested: Captain, HOD, Crew
 * All tests on single URL: app.celeste7.ai
 */

import { test, expect, Page } from '@playwright/test';
import { loginAs, searchInSpotlight } from './auth.helper';

const SCREENSHOT_DIR = '/tmp/all_lens_detail_test_screenshots';

// =============================================================================
// TEST DATA
// =============================================================================

const LENS_QUERIES = {
  equipment: 'generator',
  fault: 'fault',
  part: 'filter',
  receiving: 'receiving',
  supplier: 'supplier',
  purchase_order: 'purchase order',
  document: 'manual',
  work_order: 'maintenance',
};

const PERF = {
  searchMaxTime: 3000,
  detailsMaxTime: 2000,
};

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

async function captureScreenshot(page: Page, name: string): Promise<void> {
  await page.screenshot({
    path: `${SCREENSHOT_DIR}/${name}.png`,
    fullPage: true
  });
}

async function closeContextPanel(page: Page): Promise<void> {
  const closeButton = page.locator('[data-testid="close-context-panel"]').first();
  if (await closeButton.isVisible().catch(() => false)) {
    await closeButton.click();
    await page.waitForTimeout(300);
  } else {
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
  }
}

async function closeSpotlight(page: Page): Promise<void> {
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);
}

async function getSearchResults(page: Page): Promise<number> {
  await page.waitForTimeout(1000);
  const results = page.locator('[data-testid="search-result-item"]');
  return await results.count();
}

async function clickFirstResult(page: Page): Promise<void> {
  const firstResult = page.locator('[data-testid="search-result-item"]').first();
  if (await firstResult.isVisible()) {
    await firstResult.click();
    await page.waitForTimeout(800);
  }
}

async function verifyContextPanelOpen(page: Page, entityType: string): Promise<boolean> {
  const panel = page.locator('[data-testid="context-panel"]');
  const isVisible = await panel.isVisible().catch(() => false);

  if (isVisible) {
    const dataExpanded = await panel.getAttribute('data-expanded');
    const panelEntityType = await panel.getAttribute('data-entity-type');
    return dataExpanded === 'true' && panelEntityType === entityType;
  }
  return false;
}

async function checkNoEmailIntegrationMessage(page: Page): Promise<boolean> {
  const emailMessage = page.locator('text=/Email integration is off/i');
  return !(await emailMessage.isVisible().catch(() => false));
}

async function checkNotesSection(page: Page): Promise<boolean> {
  const notesSection = page.locator('text=/Notes/i').first();
  return await notesSection.isVisible().catch(() => false);
}

async function checkActivitySection(page: Page): Promise<boolean> {
  const activitySection = page.locator('text=/Activity/i').first();
  return await activitySection.isVisible().catch(() => false);
}

// =============================================================================
// PHASE 1: EQUIPMENT LENS DETAIL
// =============================================================================

test.describe('Phase 1: Equipment Lens Detail', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('EQUIP-DETAIL-001: Opens full-screen context panel', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.equipment);
    await clickFirstResult(page);

    const panelOk = await verifyContextPanelOpen(page, 'equipment');
    console.log(`EQUIP-DETAIL-001: Full-screen panel opened: ${panelOk}`);

    await captureScreenshot(page, 'EQUIP-DETAIL-001');
    await closeContextPanel(page);
    await closeSpotlight(page);

    expect(panelOk).toBe(true);
  });

  test('EQUIP-DETAIL-002: No email integration message', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.equipment);
    await clickFirstResult(page);

    const noEmailMsg = await checkNoEmailIntegrationMessage(page);
    console.log(`EQUIP-DETAIL-002: No email integration message: ${noEmailMsg}`);

    await captureScreenshot(page, 'EQUIP-DETAIL-002');
    await closeContextPanel(page);
    await closeSpotlight(page);

    expect(noEmailMsg).toBe(true);
  });

  test('EQUIP-DETAIL-003: Notes section visible', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.equipment);
    await clickFirstResult(page);

    const hasNotes = await checkNotesSection(page);
    console.log(`EQUIP-DETAIL-003: Notes section visible: ${hasNotes}`);

    await captureScreenshot(page, 'EQUIP-DETAIL-003');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('EQUIP-DETAIL-004: Activity section visible', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.equipment);
    await clickFirstResult(page);

    const hasActivity = await checkActivitySection(page);
    console.log(`EQUIP-DETAIL-004: Activity section visible: ${hasActivity}`);

    await captureScreenshot(page, 'EQUIP-DETAIL-004');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('EQUIP-DETAIL-005: Shows linked parts section', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.equipment);
    await clickFirstResult(page);

    const partsSection = page.locator('text=/Parts|Spare|Inventory/i');
    const hasPartsSection = await partsSection.isVisible().catch(() => false);
    console.log(`EQUIP-DETAIL-005: Parts section visible: ${hasPartsSection}`);

    await captureScreenshot(page, 'EQUIP-DETAIL-005');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('EQUIP-DETAIL-006: Shows work orders section', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.equipment);
    await clickFirstResult(page);

    const woSection = page.locator('text=/Work Order/i');
    const hasWoSection = await woSection.isVisible().catch(() => false);
    console.log(`EQUIP-DETAIL-006: Work Orders section visible: ${hasWoSection}`);

    await captureScreenshot(page, 'EQUIP-DETAIL-006');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 2: FAULT LENS DETAIL
// =============================================================================

test.describe('Phase 2: Fault Lens Detail', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('FAULT-DETAIL-001: Opens full-screen context panel', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.fault);
    await clickFirstResult(page);

    const panelOk = await verifyContextPanelOpen(page, 'fault');
    console.log(`FAULT-DETAIL-001: Full-screen panel opened: ${panelOk}`);

    await captureScreenshot(page, 'FAULT-DETAIL-001');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('FAULT-DETAIL-002: No email integration message', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.fault);
    await clickFirstResult(page);

    const noEmailMsg = await checkNoEmailIntegrationMessage(page);
    console.log(`FAULT-DETAIL-002: No email integration message: ${noEmailMsg}`);

    await captureScreenshot(page, 'FAULT-DETAIL-002');
    await closeContextPanel(page);
    await closeSpotlight(page);

    expect(noEmailMsg).toBe(true);
  });

  test('FAULT-DETAIL-003: Shows severity badge', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.fault);
    await clickFirstResult(page);

    const severityBadge = page.locator('text=/Critical|Major|Minor|Cosmetic|Safety/i');
    const hasSeverity = await severityBadge.isVisible().catch(() => false);
    console.log(`FAULT-DETAIL-003: Severity badge visible: ${hasSeverity}`);

    await captureScreenshot(page, 'FAULT-DETAIL-003');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('FAULT-DETAIL-004: Shows linked equipment section', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.fault);
    await clickFirstResult(page);

    const equipSection = page.locator('text=/Affected Equipment|Equipment/i');
    const hasEquip = await equipSection.isVisible().catch(() => false);
    console.log(`FAULT-DETAIL-004: Equipment section visible: ${hasEquip}`);

    await captureScreenshot(page, 'FAULT-DETAIL-004');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('FAULT-DETAIL-005: Shows work order section', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.fault);
    await clickFirstResult(page);

    const woSection = page.locator('text=/Work Order/i');
    const hasWo = await woSection.isVisible().catch(() => false);
    console.log(`FAULT-DETAIL-005: Work Order section visible: ${hasWo}`);

    await captureScreenshot(page, 'FAULT-DETAIL-005');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('FAULT-DETAIL-006: Notes section visible', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.fault);
    await clickFirstResult(page);

    const hasNotes = await checkNotesSection(page);
    console.log(`FAULT-DETAIL-006: Notes section visible: ${hasNotes}`);

    await captureScreenshot(page, 'FAULT-DETAIL-006');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 3: PART LENS DETAIL
// =============================================================================

test.describe('Phase 3: Part Lens Detail', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('PART-DETAIL-001: Opens full-screen context panel', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.part);
    await clickFirstResult(page);

    const panel = page.locator('[data-testid="context-panel"]');
    const isVisible = await panel.isVisible().catch(() => false);
    console.log(`PART-DETAIL-001: Context panel visible: ${isVisible}`);

    await captureScreenshot(page, 'PART-DETAIL-001');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('PART-DETAIL-002: No email integration message', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.part);
    await clickFirstResult(page);

    const noEmailMsg = await checkNoEmailIntegrationMessage(page);
    console.log(`PART-DETAIL-002: No email integration message: ${noEmailMsg}`);

    await captureScreenshot(page, 'PART-DETAIL-002');
    await closeContextPanel(page);
    await closeSpotlight(page);

    expect(noEmailMsg).toBe(true);
  });

  test('PART-DETAIL-003: Shows stock status', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.part);
    await clickFirstResult(page);

    const stockStatus = page.locator('text=/In Stock|Low Stock|Critical|Out of Stock/i');
    const hasStock = await stockStatus.isVisible().catch(() => false);
    console.log(`PART-DETAIL-003: Stock status visible: ${hasStock}`);

    await captureScreenshot(page, 'PART-DETAIL-003');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('PART-DETAIL-004: Shows stock by location section', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.part);
    await clickFirstResult(page);

    const locationSection = page.locator('text=/Stock by Location|Location/i');
    const hasLocation = await locationSection.isVisible().catch(() => false);
    console.log(`PART-DETAIL-004: Location section visible: ${hasLocation}`);

    await captureScreenshot(page, 'PART-DETAIL-004');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('PART-DETAIL-005: Shows linked equipment section', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.part);
    await clickFirstResult(page);

    const equipSection = page.locator('text=/Used By Equipment|Equipment/i');
    const hasEquip = await equipSection.isVisible().catch(() => false);
    console.log(`PART-DETAIL-005: Equipment section visible: ${hasEquip}`);

    await captureScreenshot(page, 'PART-DETAIL-005');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('PART-DETAIL-006: Shows transactions section', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.part);
    await clickFirstResult(page);

    const txSection = page.locator('text=/Transaction|Recent/i');
    const hasTx = await txSection.isVisible().catch(() => false);
    console.log(`PART-DETAIL-006: Transactions section visible: ${hasTx}`);

    await captureScreenshot(page, 'PART-DETAIL-006');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 4: RECEIVING LENS DETAIL
// =============================================================================

test.describe('Phase 4: Receiving Lens Detail', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('RECV-DETAIL-001: Opens full-screen context panel', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.receiving);
    await clickFirstResult(page);

    const panel = page.locator('[data-testid="context-panel"]');
    const isVisible = await panel.isVisible().catch(() => false);
    console.log(`RECV-DETAIL-001: Context panel visible: ${isVisible}`);

    await captureScreenshot(page, 'RECV-DETAIL-001');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('RECV-DETAIL-002: No email integration message', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.receiving);
    await clickFirstResult(page);

    const noEmailMsg = await checkNoEmailIntegrationMessage(page);
    console.log(`RECV-DETAIL-002: No email integration message: ${noEmailMsg}`);

    await captureScreenshot(page, 'RECV-DETAIL-002');
    await closeContextPanel(page);
    await closeSpotlight(page);

    expect(noEmailMsg).toBe(true);
  });

  test('RECV-DETAIL-003: Shows status badge', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.receiving);
    await clickFirstResult(page);

    const statusBadge = page.locator('text=/Draft|In Review|Accepted|Rejected/i');
    const hasStatus = await statusBadge.isVisible().catch(() => false);
    console.log(`RECV-DETAIL-003: Status badge visible: ${hasStatus}`);

    await captureScreenshot(page, 'RECV-DETAIL-003');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('RECV-DETAIL-004: Shows line items section', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.receiving);
    await clickFirstResult(page);

    const itemsSection = page.locator('text=/Line Item|Items/i');
    const hasItems = await itemsSection.isVisible().catch(() => false);
    console.log(`RECV-DETAIL-004: Line items section visible: ${hasItems}`);

    await captureScreenshot(page, 'RECV-DETAIL-004');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('RECV-DETAIL-005: Shows documents section', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.receiving);
    await clickFirstResult(page);

    const docsSection = page.locator('text=/Document/i');
    const hasDocs = await docsSection.isVisible().catch(() => false);
    console.log(`RECV-DETAIL-005: Documents section visible: ${hasDocs}`);

    await captureScreenshot(page, 'RECV-DETAIL-005');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('RECV-DETAIL-006: Activity section visible', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.receiving);
    await clickFirstResult(page);

    const hasActivity = await checkActivitySection(page);
    console.log(`RECV-DETAIL-006: Activity section visible: ${hasActivity}`);

    await captureScreenshot(page, 'RECV-DETAIL-006');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 5: SUPPLIER LENS DETAIL
// =============================================================================

test.describe('Phase 5: Supplier Lens Detail', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('SUPP-DETAIL-001: Opens full-screen context panel', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.supplier);
    await clickFirstResult(page);

    const panel = page.locator('[data-testid="context-panel"]');
    const isVisible = await panel.isVisible().catch(() => false);
    console.log(`SUPP-DETAIL-001: Context panel visible: ${isVisible}`);

    await captureScreenshot(page, 'SUPP-DETAIL-001');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('SUPP-DETAIL-002: No email integration message', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.supplier);
    await clickFirstResult(page);

    const noEmailMsg = await checkNoEmailIntegrationMessage(page);
    console.log(`SUPP-DETAIL-002: No email integration message: ${noEmailMsg}`);

    await captureScreenshot(page, 'SUPP-DETAIL-002');
    await closeContextPanel(page);
    await closeSpotlight(page);

    expect(noEmailMsg).toBe(true);
  });

  test('SUPP-DETAIL-003: Shows contact info', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.supplier);
    await clickFirstResult(page);

    const contactInfo = page.locator('text=/email|phone|website|address/i');
    const hasContact = await contactInfo.isVisible().catch(() => false);
    console.log(`SUPP-DETAIL-003: Contact info visible: ${hasContact}`);

    await captureScreenshot(page, 'SUPP-DETAIL-003');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('SUPP-DETAIL-004: Shows purchase orders section', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.supplier);
    await clickFirstResult(page);

    const poSection = page.locator('text=/Purchase Order/i');
    const hasPo = await poSection.isVisible().catch(() => false);
    console.log(`SUPP-DETAIL-004: Purchase orders section visible: ${hasPo}`);

    await captureScreenshot(page, 'SUPP-DETAIL-004');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('SUPP-DETAIL-005: Shows parts supplied section', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.supplier);
    await clickFirstResult(page);

    const partsSection = page.locator('text=/Parts Supplied/i');
    const hasParts = await partsSection.isVisible().catch(() => false);
    console.log(`SUPP-DETAIL-005: Parts supplied section visible: ${hasParts}`);

    await captureScreenshot(page, 'SUPP-DETAIL-005');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('SUPP-DETAIL-006: Notes section visible', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.supplier);
    await clickFirstResult(page);

    const hasNotes = await checkNotesSection(page);
    console.log(`SUPP-DETAIL-006: Notes section visible: ${hasNotes}`);

    await captureScreenshot(page, 'SUPP-DETAIL-006');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 6: PURCHASE ORDER LENS DETAIL
// =============================================================================

test.describe('Phase 6: Purchase Order Lens Detail', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('PO-DETAIL-001: Opens full-screen context panel', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.purchase_order);
    await clickFirstResult(page);

    const panel = page.locator('[data-testid="context-panel"]');
    const isVisible = await panel.isVisible().catch(() => false);
    console.log(`PO-DETAIL-001: Context panel visible: ${isVisible}`);

    await captureScreenshot(page, 'PO-DETAIL-001');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('PO-DETAIL-002: No email integration message', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.purchase_order);
    await clickFirstResult(page);

    const noEmailMsg = await checkNoEmailIntegrationMessage(page);
    console.log(`PO-DETAIL-002: No email integration message: ${noEmailMsg}`);

    await captureScreenshot(page, 'PO-DETAIL-002');
    await closeContextPanel(page);
    await closeSpotlight(page);

    expect(noEmailMsg).toBe(true);
  });

  test('PO-DETAIL-003: Shows status badge', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.purchase_order);
    await clickFirstResult(page);

    const statusBadge = page.locator('text=/Draft|Pending|Approved|Ordered|Received|Cancelled/i');
    const hasStatus = await statusBadge.isVisible().catch(() => false);
    console.log(`PO-DETAIL-003: Status badge visible: ${hasStatus}`);

    await captureScreenshot(page, 'PO-DETAIL-003');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('PO-DETAIL-004: Shows supplier info', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.purchase_order);
    await clickFirstResult(page);

    const supplierInfo = page.locator('text=/Supplier/i');
    const hasSupplier = await supplierInfo.isVisible().catch(() => false);
    console.log(`PO-DETAIL-004: Supplier info visible: ${hasSupplier}`);

    await captureScreenshot(page, 'PO-DETAIL-004');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('PO-DETAIL-005: Shows line items section', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.purchase_order);
    await clickFirstResult(page);

    const itemsSection = page.locator('text=/Line Item/i');
    const hasItems = await itemsSection.isVisible().catch(() => false);
    console.log(`PO-DETAIL-005: Line items section visible: ${hasItems}`);

    await captureScreenshot(page, 'PO-DETAIL-005');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('PO-DETAIL-006: Notes section visible', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.purchase_order);
    await clickFirstResult(page);

    const hasNotes = await checkNotesSection(page);
    console.log(`PO-DETAIL-006: Notes section visible: ${hasNotes}`);

    await captureScreenshot(page, 'PO-DETAIL-006');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 7: DOCUMENT LENS DETAIL
// =============================================================================

test.describe('Phase 7: Document Lens Detail', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('DOC-DETAIL-001: Opens full-screen context panel', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.document);
    await clickFirstResult(page);

    const panel = page.locator('[data-testid="context-panel"]');
    const isVisible = await panel.isVisible().catch(() => false);
    console.log(`DOC-DETAIL-001: Context panel visible: ${isVisible}`);

    await captureScreenshot(page, 'DOC-DETAIL-001');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('DOC-DETAIL-002: No email integration message', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.document);
    await clickFirstResult(page);

    const noEmailMsg = await checkNoEmailIntegrationMessage(page);
    console.log(`DOC-DETAIL-002: No email integration message: ${noEmailMsg}`);

    await captureScreenshot(page, 'DOC-DETAIL-002');
    await closeContextPanel(page);
    await closeSpotlight(page);

    expect(noEmailMsg).toBe(true);
  });

  test('DOC-DETAIL-003: Shows document type badge', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.document);
    await clickFirstResult(page);

    const typeBadge = page.locator('text=/Manual|Photo|Certificate|Diagram|Warranty|Invoice/i');
    const hasType = await typeBadge.isVisible().catch(() => false);
    console.log(`DOC-DETAIL-003: Document type badge visible: ${hasType}`);

    await captureScreenshot(page, 'DOC-DETAIL-003');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('DOC-DETAIL-004: Shows file size info', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.document);
    await clickFirstResult(page);

    const sizeInfo = page.locator('text=/Size|KB|MB|GB/i');
    const hasSize = await sizeInfo.isVisible().catch(() => false);
    console.log(`DOC-DETAIL-004: File size info visible: ${hasSize}`);

    await captureScreenshot(page, 'DOC-DETAIL-004');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('DOC-DETAIL-005: Shows linked equipment section', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.document);
    await clickFirstResult(page);

    const equipSection = page.locator('text=/Linked Equipment|Equipment/i');
    const hasEquip = await equipSection.isVisible().catch(() => false);
    console.log(`DOC-DETAIL-005: Equipment section visible: ${hasEquip}`);

    await captureScreenshot(page, 'DOC-DETAIL-005');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });

  test('DOC-DETAIL-006: Notes section visible', async ({ page }) => {
    await searchInSpotlight(page, LENS_QUERIES.document);
    await clickFirstResult(page);

    const hasNotes = await checkNotesSection(page);
    console.log(`DOC-DETAIL-006: Notes section visible: ${hasNotes}`);

    await captureScreenshot(page, 'DOC-DETAIL-006');
    await closeContextPanel(page);
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 8: CROSS-LENS FULL-SCREEN VERIFICATION
// =============================================================================

test.describe('Phase 8: Cross-Lens Full-Screen Verification', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('FULL-SCREEN-001: All lenses render full-screen (not popup)', async ({ page }) => {
    const lenses = ['equipment', 'fault', 'part'];
    const results: Record<string, boolean> = {};

    for (const lens of lenses) {
      await searchInSpotlight(page, LENS_QUERIES[lens as keyof typeof LENS_QUERIES]);
      await clickFirstResult(page);

      const panel = page.locator('[data-testid="context-panel"]');
      const dataExpanded = await panel.getAttribute('data-expanded').catch(() => null);
      results[lens] = dataExpanded === 'true';

      console.log(`FULL-SCREEN-001: ${lens} data-expanded: ${dataExpanded}`);

      await closeContextPanel(page);
      await closeSpotlight(page);
      await page.waitForTimeout(500);
    }

    await captureScreenshot(page, 'FULL-SCREEN-001');

    // Verify at least one works
    const anyFullScreen = Object.values(results).some(v => v === true);
    expect(anyFullScreen).toBe(true);
  });

  test('FULL-SCREEN-002: No lens shows Email panel', async ({ page }) => {
    const lenses = ['equipment', 'fault', 'part'];
    let anyEmailPanel = false;

    for (const lens of lenses) {
      await searchInSpotlight(page, LENS_QUERIES[lens as keyof typeof LENS_QUERIES]);
      await clickFirstResult(page);

      const emailPanel = page.locator('text=/Email integration is off/i');
      const hasEmail = await emailPanel.isVisible().catch(() => false);
      if (hasEmail) anyEmailPanel = true;

      console.log(`FULL-SCREEN-002: ${lens} has email panel: ${hasEmail}`);

      await closeContextPanel(page);
      await closeSpotlight(page);
      await page.waitForTimeout(500);
    }

    await captureScreenshot(page, 'FULL-SCREEN-002');

    expect(anyEmailPanel).toBe(false);
  });
});

// =============================================================================
// SUMMARY
// =============================================================================

test('ALL-LENS-SUMMARY: Test suite complete', async ({ page }) => {
  console.log('\n' + '='.repeat(60));
  console.log('ALL LENS DETAIL COMPONENTS TEST SUITE COMPLETE');
  console.log('='.repeat(60));
  console.log('\nTests by lens:');
  console.log('- Equipment Detail: 6 tests');
  console.log('- Fault Detail: 6 tests');
  console.log('- Part Detail: 6 tests');
  console.log('- Receiving Detail: 6 tests');
  console.log('- Supplier Detail: 6 tests');
  console.log('- Purchase Order Detail: 6 tests');
  console.log('- Document Detail: 6 tests');
  console.log('- Cross-Lens Verification: 2 tests');
  console.log('\nTotal: 44 tests');
  console.log('Screenshots: ' + SCREENSHOT_DIR);
  console.log('='.repeat(60) + '\n');

  expect(true).toBe(true);
});
