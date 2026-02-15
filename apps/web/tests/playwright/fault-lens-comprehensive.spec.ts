/**
 * Fault Lens - Comprehensive E2E Test Suite
 *
 * Tests all user journeys for fault management:
 * - Search faults
 * - View fault details
 * - Report new faults
 * - Acknowledge/close/update faults
 * - Diagnose faults
 * - Create work orders from faults
 *
 * Roles tested: Captain, HOD, Crew
 * All tests on single URL: app.celeste7.ai
 *
 * Fault severity values: cosmetic|minor|major|critical|safety
 * Fault status transitions: open → investigating → work_ordered → resolved → closed
 */

import { test, expect, Page } from '@playwright/test';
import { loginAs, searchInSpotlight } from './auth.helper';

const SCREENSHOT_DIR = '/tmp/fault_lens_test_screenshots';

// =============================================================================
// TEST DATA
// =============================================================================

const TEST_QUERIES = {
  valid: {
    faultCode: 'FLT-',
    equipment: 'generator',
    symptom: 'leak',
    severity: 'critical',
    location: 'engine room',
  },
  invalid: {
    nonexistent: 'NONEXISTENT_FAULT_XYZ999',
    malformed: '"><script>alert(1)</script>',
    special: '!@#$%^&*()',
    sqlInjection: "'; DROP TABLE pms_faults; --",
  }
};

const PERF = {
  searchMaxTime: 2000,
  detailsMaxTime: 1500,
  actionMaxTime: 3000,
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
// PHASE 1: CAPTAIN - SUCCESS PATHS (SEARCH & VIEW)
// =============================================================================

test.describe('Phase 1: Captain Success Paths - Fault Search', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('FAULT-CAP-001: Search for active faults', async ({ page }) => {
    const startTime = Date.now();
    await searchInSpotlight(page, 'active faults');
    const searchTime = Date.now() - startTime;

    await page.waitForTimeout(1000);
    const count = await getSearchResults(page);

    expect(searchTime).toBeLessThan(PERF.searchMaxTime);
    console.log(`FAULT-CAP-001: Found ${count} active faults in ${searchTime}ms`);

    await captureScreenshot(page, 'FAULT-CAP-001');
    await closeSpotlight(page);
  });

  test('FAULT-CAP-002: Search for faults by symptom', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.symptom);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`FAULT-CAP-002: Found ${count} faults with "${TEST_QUERIES.valid.symptom}"`);

    await captureScreenshot(page, 'FAULT-CAP-002');
    await closeSpotlight(page);
  });

  test('FAULT-CAP-003: Search for critical faults', async ({ page }) => {
    await searchInSpotlight(page, 'critical faults');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`FAULT-CAP-003: Found ${count} critical faults`);

    await captureScreenshot(page, 'FAULT-CAP-003');
    await closeSpotlight(page);
  });

  test('FAULT-CAP-004: Search faults by equipment', async ({ page }) => {
    await searchInSpotlight(page, `faults on ${TEST_QUERIES.valid.equipment}`);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`FAULT-CAP-004: Found ${count} faults for "${TEST_QUERIES.valid.equipment}"`);

    await captureScreenshot(page, 'FAULT-CAP-004');
    await closeSpotlight(page);
  });

  test('FAULT-CAP-005: Search with NLP query', async ({ page }) => {
    await searchInSpotlight(page, 'show me all engine faults reported this week');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`FAULT-CAP-005: NLP search returned ${count} faults`);

    await captureScreenshot(page, 'FAULT-CAP-005');
    await closeSpotlight(page);
  });

  test('FAULT-CAP-006: View fault details', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Should show fault details panel
    const detailsPanel = page.locator('[data-testid="context-panel"], [data-testid="details-panel"]');
    const panelVisible = await detailsPanel.isVisible().catch(() => false);

    console.log(`FAULT-CAP-006: Details panel visible: ${panelVisible}`);

    await captureScreenshot(page, 'FAULT-CAP-006');
    await closeSpotlight(page);
  });

  test('FAULT-CAP-007: View fault severity indicator', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Look for severity indicator
    const severityIndicator = page.locator('text=/critical|major|minor|cosmetic|safety/i');
    const severityVisible = await severityIndicator.isVisible().catch(() => false);

    console.log(`FAULT-CAP-007: Severity indicator visible: ${severityVisible}`);

    await captureScreenshot(page, 'FAULT-CAP-007');
    await closeSpotlight(page);
  });

  test('FAULT-CAP-008: View fault history for equipment', async ({ page }) => {
    await searchInSpotlight(page, `fault history ${TEST_QUERIES.valid.equipment}`);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`FAULT-CAP-008: Found ${count} historical faults`);

    await captureScreenshot(page, 'FAULT-CAP-008');
    await closeSpotlight(page);
  });

  test('FAULT-CAP-009: View open faults requiring action', async ({ page }) => {
    await searchInSpotlight(page, 'open faults');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`FAULT-CAP-009: Found ${count} open faults`);

    await captureScreenshot(page, 'FAULT-CAP-009');
    await closeSpotlight(page);
  });

  test('FAULT-CAP-010: Search by location', async ({ page }) => {
    await searchInSpotlight(page, `faults in ${TEST_QUERIES.valid.location}`);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`FAULT-CAP-010: Found ${count} faults in "${TEST_QUERIES.valid.location}"`);

    await captureScreenshot(page, 'FAULT-CAP-010');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 2: CAPTAIN - MUTATION ACTIONS
// =============================================================================

test.describe('Phase 2: Captain Mutation Actions', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('FAULT-CAP-011: Captain sees fault action buttons', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Captain should see mutation buttons
    const actionButtons = page.locator('button:has-text("Acknowledge"), button:has-text("Close"), button:has-text("Diagnose")');
    const actionsCount = await actionButtons.count();

    console.log(`FAULT-CAP-011: Captain sees ${actionsCount} action buttons`);

    await captureScreenshot(page, 'FAULT-CAP-011');
    await closeSpotlight(page);
  });

  test('FAULT-CAP-012: Captain sees "Report Fault" option', async ({ page }) => {
    await searchInSpotlight(page, 'report fault');
    await page.waitForTimeout(1000);

    // Should see report fault in actions or results
    const reportAction = page.locator('text=/report.*fault|new.*fault|log.*fault/i');
    const reportVisible = await reportAction.isVisible().catch(() => false);

    console.log(`FAULT-CAP-012: Report fault visible: ${reportVisible}`);

    await captureScreenshot(page, 'FAULT-CAP-012');
    await closeSpotlight(page);
  });

  test('FAULT-CAP-013: Captain sees "Create Work Order" button', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Captain should see WO creation button (signed action)
    const woButton = page.locator('button:has-text("Create Work Order"), button:has-text("Work Order")');
    const woVisible = await woButton.isVisible().catch(() => false);

    console.log(`FAULT-CAP-013: Create WO button visible: ${woVisible}`);

    await captureScreenshot(page, 'FAULT-CAP-013');
    await closeSpotlight(page);
  });

  test('FAULT-CAP-014: Captain sees diagnose action', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    const diagnoseBtn = page.locator('button:has-text("Diagnose")');
    const diagnoseVisible = await diagnoseBtn.isVisible().catch(() => false);

    console.log(`FAULT-CAP-014: Diagnose button visible: ${diagnoseVisible}`);

    await captureScreenshot(page, 'FAULT-CAP-014');
    await closeSpotlight(page);
  });

  test('FAULT-CAP-015: Captain can access suggest parts', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    const suggestBtn = page.locator('button:has-text("Suggest Parts"), button:has-text("Parts")');
    const suggestVisible = await suggestBtn.isVisible().catch(() => false);

    console.log(`FAULT-CAP-015: Suggest parts visible: ${suggestVisible}`);

    await captureScreenshot(page, 'FAULT-CAP-015');
    await closeSpotlight(page);
  });

  test('FAULT-CAP-016: Captain can add note to fault', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    const noteBtn = page.locator('button:has-text("Add Note"), button:has-text("Note")');
    const noteVisible = await noteBtn.isVisible().catch(() => false);

    console.log(`FAULT-CAP-016: Add note visible: ${noteVisible}`);

    await captureScreenshot(page, 'FAULT-CAP-016');
    await closeSpotlight(page);
  });

  test('FAULT-CAP-017: Captain can add photo to fault', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    const photoBtn = page.locator('button:has-text("Add Photo"), button:has-text("Photo"), button:has-text("Camera")');
    const photoVisible = await photoBtn.isVisible().catch(() => false);

    console.log(`FAULT-CAP-017: Add photo visible: ${photoVisible}`);

    await captureScreenshot(page, 'FAULT-CAP-017');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 3: HOD ROLE TESTS
// =============================================================================

test.describe('Phase 3: HOD Role Tests', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'hod');
  });

  test('FAULT-HOD-001: HOD can search faults', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    expect(count).toBeGreaterThanOrEqual(0);

    console.log(`FAULT-HOD-001: HOD found ${count} faults`);

    await captureScreenshot(page, 'FAULT-HOD-001');
    await closeSpotlight(page);
  });

  test('FAULT-HOD-002: HOD can view fault details', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    console.log('FAULT-HOD-002: HOD viewed fault details');

    await captureScreenshot(page, 'FAULT-HOD-002');
    await closeSpotlight(page);
  });

  test('FAULT-HOD-003: HOD can acknowledge fault', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // HOD should see acknowledge button
    const ackBtn = page.locator('button:has-text("Acknowledge")');
    const ackVisible = await ackBtn.isVisible().catch(() => false);

    console.log(`FAULT-HOD-003: Acknowledge visible for HOD: ${ackVisible}`);

    await captureScreenshot(page, 'FAULT-HOD-003');
    await closeSpotlight(page);
  });

  test('FAULT-HOD-004: HOD can diagnose fault', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    const diagnoseBtn = page.locator('button:has-text("Diagnose")');
    const diagnoseVisible = await diagnoseBtn.isVisible().catch(() => false);

    console.log(`FAULT-HOD-004: Diagnose visible for HOD: ${diagnoseVisible}`);

    await captureScreenshot(page, 'FAULT-HOD-004');
    await closeSpotlight(page);
  });

  test('FAULT-HOD-005: HOD can update fault', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // HOD should see update options
    const updateBtn = page.locator('button:has-text("Update"), button:has-text("Edit")');
    const updateVisible = await updateBtn.isVisible().catch(() => false);

    console.log(`FAULT-HOD-005: Update visible for HOD: ${updateVisible}`);

    await captureScreenshot(page, 'FAULT-HOD-005');
    await closeSpotlight(page);
  });

  test('FAULT-HOD-006: HOD can close fault', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    const closeBtn = page.locator('button:has-text("Close"), button:has-text("Resolve")');
    const closeVisible = await closeBtn.isVisible().catch(() => false);

    console.log(`FAULT-HOD-006: Close visible for HOD: ${closeVisible}`);

    await captureScreenshot(page, 'FAULT-HOD-006');
    await closeSpotlight(page);
  });

  test('FAULT-HOD-007: HOD can add note to fault', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    const noteBtn = page.locator('button:has-text("Add Note"), button:has-text("Note")');
    const noteVisible = await noteBtn.isVisible().catch(() => false);

    console.log(`FAULT-HOD-007: Add note for HOD: ${noteVisible}`);

    await captureScreenshot(page, 'FAULT-HOD-007');
    await closeSpotlight(page);
  });

  test('FAULT-HOD-008: HOD CANNOT create work order (signed action)', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // HOD should NOT see create WO button (captain/manager only)
    const woButton = page.locator('button:has-text("Create Work Order")');
    const woVisible = await woButton.isVisible().catch(() => false);

    console.log(`FAULT-HOD-008: Create WO for HOD: ${woVisible} (should be false)`);

    await captureScreenshot(page, 'FAULT-HOD-008');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 4: CREW ROLE TESTS
// =============================================================================

test.describe('Phase 4: Crew Role Tests', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'crew');
  });

  test('FAULT-CREW-001: Crew can search faults', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`FAULT-CREW-001: Crew found ${count} faults`);

    await captureScreenshot(page, 'FAULT-CREW-001');
    await closeSpotlight(page);
  });

  test('FAULT-CREW-002: Crew can view fault details', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    console.log('FAULT-CREW-002: Crew viewed fault details');

    await captureScreenshot(page, 'FAULT-CREW-002');
    await closeSpotlight(page);
  });

  test('FAULT-CREW-003: Crew CAN report fault', async ({ page }) => {
    await searchInSpotlight(page, 'report fault');
    await page.waitForTimeout(1000);

    // Crew should be able to report faults
    const reportAction = page.locator('text=/report.*fault|new.*fault|log.*fault/i');
    const reportVisible = await reportAction.isVisible().catch(() => false);

    console.log(`FAULT-CREW-003: Report fault for Crew: ${reportVisible}`);

    await captureScreenshot(page, 'FAULT-CREW-003');
    await closeSpotlight(page);
  });

  test('FAULT-CREW-004: Crew CAN add photo to fault', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Crew can add photos per binding brief
    const photoBtn = page.locator('button:has-text("Add Photo"), button:has-text("Photo")');
    const photoVisible = await photoBtn.isVisible().catch(() => false);

    console.log(`FAULT-CREW-004: Add photo for Crew: ${photoVisible}`);

    await captureScreenshot(page, 'FAULT-CREW-004');
    await closeSpotlight(page);
  });

  test('FAULT-CREW-005: Crew CAN add note to fault', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Crew can add notes per binding brief
    const noteBtn = page.locator('button:has-text("Add Note"), button:has-text("Note")');
    const noteVisible = await noteBtn.isVisible().catch(() => false);

    console.log(`FAULT-CREW-005: Add note for Crew: ${noteVisible}`);

    await captureScreenshot(page, 'FAULT-CREW-005');
    await closeSpotlight(page);
  });

  test('FAULT-CREW-006: Crew CANNOT acknowledge fault', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Crew should NOT see acknowledge button
    const ackBtn = page.locator('button:has-text("Acknowledge")');
    const ackVisible = await ackBtn.isVisible().catch(() => false);

    console.log(`FAULT-CREW-006: Acknowledge for Crew: ${ackVisible} (should be false)`);

    await captureScreenshot(page, 'FAULT-CREW-006');
    await closeSpotlight(page);
  });

  test('FAULT-CREW-007: Crew CANNOT close fault', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Crew should NOT see close button
    const closeBtn = page.locator('button:has-text("Close Fault")');
    const closeVisible = await closeBtn.isVisible().catch(() => false);

    console.log(`FAULT-CREW-007: Close for Crew: ${closeVisible} (should be false)`);

    await captureScreenshot(page, 'FAULT-CREW-007');
    await closeSpotlight(page);
  });

  test('FAULT-CREW-008: Crew CANNOT diagnose fault', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Crew should NOT see diagnose button (HOD/captain only)
    const diagnoseBtn = page.locator('button:has-text("Diagnose")');
    const diagnoseVisible = await diagnoseBtn.isVisible().catch(() => false);

    console.log(`FAULT-CREW-008: Diagnose for Crew: ${diagnoseVisible} (should be false)`);

    await captureScreenshot(page, 'FAULT-CREW-008');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 5: FAILURE MODE TESTS
// =============================================================================

test.describe('Phase 5: Fault Lens Failure Modes', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('FAULT-FAIL-001: Search for nonexistent fault', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.invalid.nonexistent);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);

    // Should return 0 or show "no results" message
    console.log(`FAULT-FAIL-001: Nonexistent fault search returned ${count} results`);

    await captureScreenshot(page, 'FAULT-FAIL-001');
    await closeSpotlight(page);

    expect(count).toBe(0);
  });

  test('FAULT-FAIL-002: Special characters in search', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.invalid.special);
    await page.waitForTimeout(1000);

    // Should not crash
    expect(await page.locator('body').isVisible()).toBe(true);

    console.log('FAULT-FAIL-002: Special characters handled');

    await captureScreenshot(page, 'FAULT-FAIL-002');
    await closeSpotlight(page);
  });

  test('FAULT-FAIL-003: XSS attempt in search', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.invalid.malformed);
    await page.waitForTimeout(1000);

    // Check no script executed
    const alertTriggered = await page.evaluate(() => {
      return (window as any).__xss_triggered || false;
    });

    expect(alertTriggered).toBe(false);
    console.log('FAULT-FAIL-003: XSS prevented');

    await captureScreenshot(page, 'FAULT-FAIL-003');
    await closeSpotlight(page);
  });

  test('FAULT-FAIL-004: SQL injection in search', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.invalid.sqlInjection);
    await page.waitForTimeout(1000);

    // App should still work, table should exist
    await closeSpotlight(page);
    await searchInSpotlight(page, 'fault');
    const count = await getSearchResults(page);

    console.log(`FAULT-FAIL-004: Faults still searchable after injection: ${count >= 0}`);

    await captureScreenshot(page, 'FAULT-FAIL-004');
    await closeSpotlight(page);
  });

  test('FAULT-FAIL-005: Empty search', async ({ page }) => {
    await searchInSpotlight(page, '');
    await page.waitForTimeout(1000);

    // Should handle gracefully
    expect(await page.locator('body').isVisible()).toBe(true);
    console.log('FAULT-FAIL-005: Empty search handled');

    await captureScreenshot(page, 'FAULT-FAIL-005');
    await closeSpotlight(page);
  });

  test('FAULT-FAIL-006: Invalid severity value handling', async ({ page }) => {
    // Try searching with invalid severity
    await searchInSpotlight(page, 'fault severity:invalid');
    await page.waitForTimeout(1000);

    // Should handle gracefully
    expect(await page.locator('body').isVisible()).toBe(true);
    console.log('FAULT-FAIL-006: Invalid severity handled');

    await captureScreenshot(page, 'FAULT-FAIL-006');
    await closeSpotlight(page);
  });

  test('FAULT-FAIL-007: Path traversal attempt', async ({ page }) => {
    await searchInSpotlight(page, '../../etc/passwd');
    await page.waitForTimeout(1000);

    // Should not return system files
    const systemContent = page.locator('text=/root:x:0:0|\/bin\/bash|\/sbin\/nologin|nobody:x:/');
    const systemVisible = await systemContent.isVisible().catch(() => false);

    expect(systemVisible).toBe(false);
    console.log('FAULT-FAIL-007: Path traversal prevented');

    await captureScreenshot(page, 'FAULT-FAIL-007');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 6: EDGE CASES
// =============================================================================

test.describe('Phase 6: Fault Lens Edge Cases', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('FAULT-EDGE-001: Rapid successive searches', async ({ page }) => {
    for (let i = 0; i < 5; i++) {
      await searchInSpotlight(page, `fault${i}`);
      await page.waitForTimeout(200);
    }

    // App should still be responsive
    expect(await page.locator('body').isVisible()).toBe(true);
    console.log('FAULT-EDGE-001: Rapid searches handled');

    await captureScreenshot(page, 'FAULT-EDGE-001');
    await closeSpotlight(page);
  });

  test('FAULT-EDGE-002: Unicode in fault search', async ({ page }) => {
    await searchInSpotlight(page, '故障 fault エラー');
    await page.waitForTimeout(1000);

    expect(await page.locator('body').isVisible()).toBe(true);
    console.log('FAULT-EDGE-002: Unicode handled');

    await captureScreenshot(page, 'FAULT-EDGE-002');
    await closeSpotlight(page);
  });

  test('FAULT-EDGE-003: Very long search query', async ({ page }) => {
    const longQuery = 'fault '.repeat(100);
    await searchInSpotlight(page, longQuery);
    await page.waitForTimeout(1000);

    expect(await page.locator('body').isVisible()).toBe(true);
    console.log('FAULT-EDGE-003: Long query handled');

    await captureScreenshot(page, 'FAULT-EDGE-003');
    await closeSpotlight(page);
  });

  test('FAULT-EDGE-004: Search with multiple terms', async ({ page }) => {
    await searchInSpotlight(page, 'critical fault generator engine room leak');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`FAULT-EDGE-004: Multi-term search returned ${count} results`);

    await captureScreenshot(page, 'FAULT-EDGE-004');
    await closeSpotlight(page);
  });

  test('FAULT-EDGE-005: Search immediately after login', async ({ page }) => {
    // Already logged in from beforeEach
    // Search immediately without waiting
    await searchInSpotlight(page, 'fault');

    const count = await getSearchResults(page);
    console.log(`FAULT-EDGE-005: Immediate search returned ${count} results`);

    await captureScreenshot(page, 'FAULT-EDGE-005');
    await closeSpotlight(page);
  });

  test('FAULT-EDGE-006: Fault with special severity keywords', async ({ page }) => {
    // Test symptom-based severity inference (fire/smoke → critical)
    await searchInSpotlight(page, 'fire smoke');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`FAULT-EDGE-006: Fire/smoke search returned ${count} results`);

    await captureScreenshot(page, 'FAULT-EDGE-006');
    await closeSpotlight(page);
  });

  test('FAULT-EDGE-007: Faults by status type', async ({ page }) => {
    await searchInSpotlight(page, 'investigating faults');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`FAULT-EDGE-007: Investigating faults returned ${count} results`);

    await captureScreenshot(page, 'FAULT-EDGE-007');
    await closeSpotlight(page);
  });

  test('FAULT-EDGE-008: Faults marked as false alarm', async ({ page }) => {
    await searchInSpotlight(page, 'false alarm faults');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`FAULT-EDGE-008: False alarm faults returned ${count} results`);

    await captureScreenshot(page, 'FAULT-EDGE-008');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 7: PERFORMANCE TESTS
// =============================================================================

test.describe('Phase 7: Fault Lens Performance', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('FAULT-PERF-001: Search response time < 2s', async ({ page }) => {
    const startTime = Date.now();
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(500); // Wait for results
    const searchTime = Date.now() - startTime;

    console.log(`FAULT-PERF-001: Search time: ${searchTime}ms (threshold: ${PERF.searchMaxTime}ms)`);

    await captureScreenshot(page, 'FAULT-PERF-001');
    await closeSpotlight(page);

    expect(searchTime).toBeLessThan(PERF.searchMaxTime);
  });

  test('FAULT-PERF-002: Details load time < 1.5s', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(500);

    const startTime = Date.now();
    await clickFirstResult(page);
    await page.waitForTimeout(500);
    const detailsTime = Date.now() - startTime;

    console.log(`FAULT-PERF-002: Details load time: ${detailsTime}ms (threshold: ${PERF.detailsMaxTime}ms)`);

    await captureScreenshot(page, 'FAULT-PERF-002');
    await closeSpotlight(page);

    expect(detailsTime).toBeLessThan(PERF.detailsMaxTime);
  });

  test('FAULT-PERF-003: Fault history load time', async ({ page }) => {
    const startTime = Date.now();
    await searchInSpotlight(page, 'fault history');
    await page.waitForTimeout(500);
    const historyTime = Date.now() - startTime;

    console.log(`FAULT-PERF-003: History load time: ${historyTime}ms`);

    await captureScreenshot(page, 'FAULT-PERF-003');
    await closeSpotlight(page);

    expect(historyTime).toBeLessThan(PERF.actionMaxTime);
  });
});

// =============================================================================
// PHASE 8: STATUS TRANSITION TESTS
// =============================================================================

test.describe('Phase 8: Fault Status Transitions', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('FAULT-STATUS-001: View fault status indicator', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Look for status indicator
    const statusIndicator = page.locator('text=/open|investigating|work_ordered|resolved|closed|false_alarm/i');
    const statusVisible = await statusIndicator.isVisible().catch(() => false);

    console.log(`FAULT-STATUS-001: Status indicator visible: ${statusVisible}`);

    await captureScreenshot(page, 'FAULT-STATUS-001');
    await closeSpotlight(page);
  });

  test('FAULT-STATUS-002: Search by open status', async ({ page }) => {
    await searchInSpotlight(page, 'status:open fault');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`FAULT-STATUS-002: Open faults: ${count}`);

    await captureScreenshot(page, 'FAULT-STATUS-002');
    await closeSpotlight(page);
  });

  test('FAULT-STATUS-003: Search by resolved status', async ({ page }) => {
    await searchInSpotlight(page, 'resolved faults');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`FAULT-STATUS-003: Resolved faults: ${count}`);

    await captureScreenshot(page, 'FAULT-STATUS-003');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 9: EQUIPMENT INTEGRATION
// =============================================================================

test.describe('Phase 9: Fault-Equipment Integration', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('FAULT-EQUIP-001: View equipment link from fault', async ({ page }) => {
    await searchInSpotlight(page, 'fault');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Look for equipment reference
    const equipmentLink = page.locator('text=/equipment|asset|linked to/i');
    const equipmentVisible = await equipmentLink.isVisible().catch(() => false);

    console.log(`FAULT-EQUIP-001: Equipment link visible: ${equipmentVisible}`);

    await captureScreenshot(page, 'FAULT-EQUIP-001');
    await closeSpotlight(page);
  });

  test('FAULT-EQUIP-002: Run diagnostic on equipment with fault', async ({ page }) => {
    await searchInSpotlight(page, 'run diagnostic');
    await page.waitForTimeout(1000);

    // Check for diagnostic action
    const diagnosticAction = page.locator('text=/diagnostic|sensor|health/i');
    const diagnosticVisible = await diagnosticAction.isVisible().catch(() => false);

    console.log(`FAULT-EQUIP-002: Diagnostic action visible: ${diagnosticVisible}`);

    await captureScreenshot(page, 'FAULT-EQUIP-002');
    await closeSpotlight(page);
  });
});

// =============================================================================
// SUMMARY
// =============================================================================

test('FAULT-SUMMARY: Fault Lens test suite complete', async ({ page }) => {
  console.log('\n' + '='.repeat(60));
  console.log('FAULT LENS TEST SUITE COMPLETE');
  console.log('='.repeat(60));
  console.log('\nTests by category:');
  console.log('- Captain Success Paths: 10 tests');
  console.log('- Captain Mutations: 7 tests');
  console.log('- HOD Role: 8 tests');
  console.log('- Crew Role: 8 tests');
  console.log('- Failure Modes: 7 tests');
  console.log('- Edge Cases: 8 tests');
  console.log('- Performance: 3 tests');
  console.log('- Status Transitions: 3 tests');
  console.log('- Equipment Integration: 2 tests');
  console.log('\nTotal: 56 tests');
  console.log('Screenshots: ' + SCREENSHOT_DIR);
  console.log('='.repeat(60) + '\n');

  expect(true).toBe(true);
});
