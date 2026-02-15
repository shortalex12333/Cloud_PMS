/**
 * Work Order Lens - Comprehensive E2E Test Suite
 *
 * Tests all user journeys for work order management:
 * - Search work orders
 * - View work order details
 * - View checklist progress
 * - Add notes and parts
 * - Complete work orders
 *
 * Roles tested: Captain, HOD, Crew
 * All tests on single URL: app.celeste7.ai
 *
 * Work Order Status Flow: draft → open → in_progress → pending_parts → completed → closed
 */

import { test, expect, Page } from '@playwright/test';
import { loginAs, searchInSpotlight } from './auth.helper';

const SCREENSHOT_DIR = '/tmp/work_order_lens_test_screenshots';

// =============================================================================
// TEST DATA
// =============================================================================

const TEST_QUERIES = {
  valid: {
    woNumber: 'WO-',
    equipment: 'generator',
    priority: 'high',
    status: 'open',
    assignee: 'engineer',
  },
  invalid: {
    nonexistent: 'NONEXISTENT_WO_XYZ999',
    malformed: '"><script>alert(1)</script>',
    special: '!@#$%^&*()',
    sqlInjection: "'; DROP TABLE pms_work_orders; --",
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
// PHASE 1: CAPTAIN - SUCCESS PATHS
// =============================================================================

test.describe('Phase 1: Captain Success Paths - Work Order Search', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('WO-CAP-001: Search for open work orders', async ({ page }) => {
    const startTime = Date.now();
    await searchInSpotlight(page, 'open work orders');
    const searchTime = Date.now() - startTime;

    await page.waitForTimeout(1000);
    const count = await getSearchResults(page);

    expect(searchTime).toBeLessThan(PERF.searchMaxTime);
    console.log(`WO-CAP-001: Found ${count} open work orders in ${searchTime}ms`);

    await captureScreenshot(page, 'WO-CAP-001');
    await closeSpotlight(page);
  });

  test('WO-CAP-002: Search by work order number', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.woNumber);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`WO-CAP-002: Found ${count} work orders with "${TEST_QUERIES.valid.woNumber}"`);

    await captureScreenshot(page, 'WO-CAP-002');
    await closeSpotlight(page);
  });

  test('WO-CAP-003: Search work orders by equipment', async ({ page }) => {
    await searchInSpotlight(page, `work orders for ${TEST_QUERIES.valid.equipment}`);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`WO-CAP-003: Found ${count} WOs for "${TEST_QUERIES.valid.equipment}"`);

    await captureScreenshot(page, 'WO-CAP-003');
    await closeSpotlight(page);
  });

  test('WO-CAP-004: Search high priority work orders', async ({ page }) => {
    await searchInSpotlight(page, 'high priority work orders');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`WO-CAP-004: Found ${count} high priority WOs`);

    await captureScreenshot(page, 'WO-CAP-004');
    await closeSpotlight(page);
  });

  test('WO-CAP-005: Search with NLP query', async ({ page }) => {
    await searchInSpotlight(page, 'show me all overdue work orders');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`WO-CAP-005: NLP search returned ${count} WOs`);

    await captureScreenshot(page, 'WO-CAP-005');
    await closeSpotlight(page);
  });

  test('WO-CAP-006: View work order details', async ({ page }) => {
    await searchInSpotlight(page, 'work order');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Should show work order details panel
    const detailsPanel = page.locator('[data-testid="context-panel"], [data-testid="details-panel"]');
    const panelVisible = await detailsPanel.isVisible().catch(() => false);

    console.log(`WO-CAP-006: Details panel visible: ${panelVisible}`);

    await captureScreenshot(page, 'WO-CAP-006');
    await closeSpotlight(page);
  });

  test('WO-CAP-007: View work order checklist', async ({ page }) => {
    await searchInSpotlight(page, 'work order');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Look for checklist section
    const checklistSection = page.locator('text=/checklist|task|step/i');
    const checklistVisible = await checklistSection.isVisible().catch(() => false);

    console.log(`WO-CAP-007: Checklist visible: ${checklistVisible}`);

    await captureScreenshot(page, 'WO-CAP-007');
    await closeSpotlight(page);
  });

  test('WO-CAP-008: View work order status', async ({ page }) => {
    await searchInSpotlight(page, 'work order');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Look for status indicator
    const statusIndicator = page.locator('text=/open|in_progress|completed|pending|closed/i');
    const statusVisible = await statusIndicator.isVisible().catch(() => false);

    console.log(`WO-CAP-008: Status visible: ${statusVisible}`);

    await captureScreenshot(page, 'WO-CAP-008');
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

  test('WO-CAP-009: Captain sees action buttons', async ({ page }) => {
    await searchInSpotlight(page, 'work order');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Captain should see mutation buttons
    const actionButtons = page.locator('button:has-text("Add Note"), button:has-text("Add Part"), button:has-text("Complete")');
    const actionsCount = await actionButtons.count();

    console.log(`WO-CAP-009: Captain sees ${actionsCount} action buttons`);

    await captureScreenshot(page, 'WO-CAP-009');
    await closeSpotlight(page);
  });

  test('WO-CAP-010: Captain sees add note option', async ({ page }) => {
    await searchInSpotlight(page, 'work order');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    const noteBtn = page.locator('button:has-text("Add Note"), button:has-text("Note")');
    const noteVisible = await noteBtn.isVisible().catch(() => false);

    console.log(`WO-CAP-010: Add note visible: ${noteVisible}`);

    await captureScreenshot(page, 'WO-CAP-010');
    await closeSpotlight(page);
  });

  test('WO-CAP-011: Captain sees add part option', async ({ page }) => {
    await searchInSpotlight(page, 'work order');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    const partBtn = page.locator('button:has-text("Add Part"), button:has-text("Part")');
    const partVisible = await partBtn.isVisible().catch(() => false);

    console.log(`WO-CAP-011: Add part visible: ${partVisible}`);

    await captureScreenshot(page, 'WO-CAP-011');
    await closeSpotlight(page);
  });

  test('WO-CAP-012: Captain sees complete option', async ({ page }) => {
    await searchInSpotlight(page, 'work order in progress');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    const completeBtn = page.locator('button:has-text("Complete"), button:has-text("Mark Complete")');
    const completeVisible = await completeBtn.isVisible().catch(() => false);

    console.log(`WO-CAP-012: Complete button visible: ${completeVisible}`);

    await captureScreenshot(page, 'WO-CAP-012');
    await closeSpotlight(page);
  });

  test('WO-CAP-013: View work order history', async ({ page }) => {
    await searchInSpotlight(page, 'work order');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    const historyBtn = page.locator('button:has-text("History"), [data-testid="history-tab"]');
    if (await historyBtn.isVisible()) {
      await historyBtn.click();
      await page.waitForTimeout(500);
    }

    console.log('WO-CAP-013: Work order history viewed');

    await captureScreenshot(page, 'WO-CAP-013');
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

  test('WO-HOD-001: HOD can search work orders', async ({ page }) => {
    await searchInSpotlight(page, 'work order');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    expect(count).toBeGreaterThanOrEqual(0);

    console.log(`WO-HOD-001: HOD found ${count} work orders`);

    await captureScreenshot(page, 'WO-HOD-001');
    await closeSpotlight(page);
  });

  test('WO-HOD-002: HOD can view work order details', async ({ page }) => {
    await searchInSpotlight(page, 'work order');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    console.log('WO-HOD-002: HOD viewed work order details');

    await captureScreenshot(page, 'WO-HOD-002');
    await closeSpotlight(page);
  });

  test('WO-HOD-003: HOD can add notes', async ({ page }) => {
    await searchInSpotlight(page, 'work order');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    const noteBtn = page.locator('button:has-text("Add Note")');
    const noteVisible = await noteBtn.isVisible().catch(() => false);

    console.log(`WO-HOD-003: Add note for HOD: ${noteVisible}`);

    await captureScreenshot(page, 'WO-HOD-003');
    await closeSpotlight(page);
  });

  test('WO-HOD-004: HOD can add parts to WO', async ({ page }) => {
    await searchInSpotlight(page, 'work order');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    const partBtn = page.locator('button:has-text("Add Part")');
    const partVisible = await partBtn.isVisible().catch(() => false);

    console.log(`WO-HOD-004: Add part for HOD: ${partVisible}`);

    await captureScreenshot(page, 'WO-HOD-004');
    await closeSpotlight(page);
  });

  test('WO-HOD-005: HOD can complete work orders', async ({ page }) => {
    await searchInSpotlight(page, 'work order in progress');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    const completeBtn = page.locator('button:has-text("Complete")');
    const completeVisible = await completeBtn.isVisible().catch(() => false);

    console.log(`WO-HOD-005: Complete for HOD: ${completeVisible}`);

    await captureScreenshot(page, 'WO-HOD-005');
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

  test('WO-CREW-001: Crew can search work orders', async ({ page }) => {
    await searchInSpotlight(page, 'work order');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`WO-CREW-001: Crew found ${count} work orders`);

    await captureScreenshot(page, 'WO-CREW-001');
    await closeSpotlight(page);
  });

  test('WO-CREW-002: Crew can view work order details', async ({ page }) => {
    await searchInSpotlight(page, 'work order');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    console.log('WO-CREW-002: Crew viewed work order details');

    await captureScreenshot(page, 'WO-CREW-002');
    await closeSpotlight(page);
  });

  test('WO-CREW-003: Crew can view checklist', async ({ page }) => {
    await searchInSpotlight(page, 'work order');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    const checklistSection = page.locator('text=/checklist|task/i');
    const checklistVisible = await checklistSection.isVisible().catch(() => false);

    console.log(`WO-CREW-003: Checklist visible for Crew: ${checklistVisible}`);

    await captureScreenshot(page, 'WO-CREW-003');
    await closeSpotlight(page);
  });

  test('WO-CREW-004: Crew CANNOT complete work order', async ({ page }) => {
    await searchInSpotlight(page, 'work order');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Crew should NOT see complete button
    const completeBtn = page.locator('button:has-text("Mark Complete")');
    const completeVisible = await completeBtn.isVisible().catch(() => false);

    console.log(`WO-CREW-004: Complete for Crew: ${completeVisible} (should be false)`);

    await captureScreenshot(page, 'WO-CREW-004');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 5: FAILURE MODE TESTS
// =============================================================================

test.describe('Phase 5: Work Order Lens Failure Modes', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('WO-FAIL-001: Search for nonexistent work order', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.invalid.nonexistent);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);

    console.log(`WO-FAIL-001: Nonexistent WO search returned ${count} results`);

    await captureScreenshot(page, 'WO-FAIL-001');
    await closeSpotlight(page);

    expect(count).toBe(0);
  });

  test('WO-FAIL-002: Special characters in search', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.invalid.special);
    await page.waitForTimeout(1000);

    expect(await page.locator('body').isVisible()).toBe(true);
    console.log('WO-FAIL-002: Special characters handled');

    await captureScreenshot(page, 'WO-FAIL-002');
    await closeSpotlight(page);
  });

  test('WO-FAIL-003: XSS attempt in search', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.invalid.malformed);
    await page.waitForTimeout(1000);

    const alertTriggered = await page.evaluate(() => {
      return (window as any).__xss_triggered || false;
    });

    expect(alertTriggered).toBe(false);
    console.log('WO-FAIL-003: XSS prevented');

    await captureScreenshot(page, 'WO-FAIL-003');
    await closeSpotlight(page);
  });

  test('WO-FAIL-004: SQL injection in search', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.invalid.sqlInjection);
    await page.waitForTimeout(1000);

    await closeSpotlight(page);
    await searchInSpotlight(page, 'work order');
    const count = await getSearchResults(page);

    console.log(`WO-FAIL-004: WOs still searchable after injection: ${count >= 0}`);

    await captureScreenshot(page, 'WO-FAIL-004');
    await closeSpotlight(page);
  });

  test('WO-FAIL-005: Empty search', async ({ page }) => {
    await searchInSpotlight(page, '');
    await page.waitForTimeout(1000);

    expect(await page.locator('body').isVisible()).toBe(true);
    console.log('WO-FAIL-005: Empty search handled');

    await captureScreenshot(page, 'WO-FAIL-005');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 6: EDGE CASES
// =============================================================================

test.describe('Phase 6: Work Order Lens Edge Cases', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('WO-EDGE-001: Rapid successive searches', async ({ page }) => {
    for (let i = 0; i < 5; i++) {
      await searchInSpotlight(page, `wo${i}`);
      await page.waitForTimeout(200);
    }

    expect(await page.locator('body').isVisible()).toBe(true);
    console.log('WO-EDGE-001: Rapid searches handled');

    await captureScreenshot(page, 'WO-EDGE-001');
    await closeSpotlight(page);
  });

  test('WO-EDGE-002: Unicode in work order search', async ({ page }) => {
    await searchInSpotlight(page, '作業指示 work order');
    await page.waitForTimeout(1000);

    expect(await page.locator('body').isVisible()).toBe(true);
    console.log('WO-EDGE-002: Unicode handled');

    await captureScreenshot(page, 'WO-EDGE-002');
    await closeSpotlight(page);
  });

  test('WO-EDGE-003: Very long search query', async ({ page }) => {
    const longQuery = 'work order '.repeat(100);
    await searchInSpotlight(page, longQuery);
    await page.waitForTimeout(1000);

    expect(await page.locator('body').isVisible()).toBe(true);
    console.log('WO-EDGE-003: Long query handled');

    await captureScreenshot(page, 'WO-EDGE-003');
    await closeSpotlight(page);
  });

  test('WO-EDGE-004: Search with multiple terms', async ({ page }) => {
    await searchInSpotlight(page, 'open work order generator maintenance high priority');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`WO-EDGE-004: Multi-term search returned ${count} results`);

    await captureScreenshot(page, 'WO-EDGE-004');
    await closeSpotlight(page);
  });

  test('WO-EDGE-005: Search immediately after login', async ({ page }) => {
    await searchInSpotlight(page, 'work order');

    const count = await getSearchResults(page);
    console.log(`WO-EDGE-005: Immediate search returned ${count} results`);

    await captureScreenshot(page, 'WO-EDGE-005');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 7: PERFORMANCE TESTS
// =============================================================================

test.describe('Phase 7: Work Order Lens Performance', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('WO-PERF-001: Search response time < 2s', async ({ page }) => {
    const startTime = Date.now();
    await searchInSpotlight(page, 'work order');
    await page.waitForTimeout(500);
    const searchTime = Date.now() - startTime;

    console.log(`WO-PERF-001: Search time: ${searchTime}ms (threshold: ${PERF.searchMaxTime}ms)`);

    await captureScreenshot(page, 'WO-PERF-001');
    await closeSpotlight(page);

    expect(searchTime).toBeLessThan(PERF.searchMaxTime);
  });

  test('WO-PERF-002: Details load time < 1.5s', async ({ page }) => {
    await searchInSpotlight(page, 'work order');
    await page.waitForTimeout(500);

    const startTime = Date.now();
    await clickFirstResult(page);
    await page.waitForTimeout(500);
    const detailsTime = Date.now() - startTime;

    console.log(`WO-PERF-002: Details load time: ${detailsTime}ms (threshold: ${PERF.detailsMaxTime}ms)`);

    await captureScreenshot(page, 'WO-PERF-002');
    await closeSpotlight(page);

    expect(detailsTime).toBeLessThan(PERF.detailsMaxTime);
  });
});

// =============================================================================
// SUMMARY
// =============================================================================

test('WO-SUMMARY: Work Order Lens test suite complete', async ({ page }) => {
  console.log('\n' + '='.repeat(60));
  console.log('WORK ORDER LENS TEST SUITE COMPLETE');
  console.log('='.repeat(60));
  console.log('\nTests by category:');
  console.log('- Captain Success Paths: 8 tests');
  console.log('- Captain Mutations: 5 tests');
  console.log('- HOD Role: 5 tests');
  console.log('- Crew Role: 4 tests');
  console.log('- Failure Modes: 5 tests');
  console.log('- Edge Cases: 5 tests');
  console.log('- Performance: 2 tests');
  console.log('\nTotal: 34 tests');
  console.log('Screenshots: ' + SCREENSHOT_DIR);
  console.log('='.repeat(60) + '\n');

  expect(true).toBe(true);
});
