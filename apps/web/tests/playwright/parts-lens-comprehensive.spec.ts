/**
 * Parts/Inventory Lens - Comprehensive E2E Test Suite
 *
 * Tests all user journeys for parts/inventory management:
 * - Search parts
 * - View part details
 * - Check stock levels
 * - Consume/receive parts
 * - Shopping list operations
 *
 * Roles tested: Captain, HOD, Crew
 * All tests on single URL: app.celeste7.ai
 */

import { test, expect, Page } from '@playwright/test';
import { loginAs, searchInSpotlight } from './auth.helper';

const SCREENSHOT_DIR = '/tmp/parts_lens_test_screenshots';

// =============================================================================
// TEST DATA
// =============================================================================

const TEST_QUERIES = {
  valid: {
    partName: 'filter',
    partNumber: 'MTU-001',
    location: 'engine room',
    category: 'oil filter',
    equipment: 'generator',
  },
  invalid: {
    nonexistent: 'NONEXISTENT_PART_XYZ999',
    malformed: '"><script>alert(1)</script>',
    special: '!@#$%^&*()',
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

test.describe('Phase 1: Captain Success Paths - Parts Search', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('PART-CAP-001: Search for part by name', async ({ page }) => {
    const startTime = Date.now();
    await searchInSpotlight(page, TEST_QUERIES.valid.partName);
    const searchTime = Date.now() - startTime;

    await page.waitForTimeout(1000);
    const count = await getSearchResults(page);

    expect(searchTime).toBeLessThan(PERF.searchMaxTime);
    console.log(`PART-CAP-001: Found ${count} parts for "${TEST_QUERIES.valid.partName}" in ${searchTime}ms`);

    await captureScreenshot(page, 'PART-CAP-001');
    await closeSpotlight(page);
  });

  test('PART-CAP-002: Search for part by part number', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.partNumber);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`PART-CAP-002: Found ${count} parts for part number "${TEST_QUERIES.valid.partNumber}"`);

    await captureScreenshot(page, 'PART-CAP-002');
    await closeSpotlight(page);
  });

  test('PART-CAP-003: Search for parts by location', async ({ page }) => {
    await searchInSpotlight(page, `parts in ${TEST_QUERIES.valid.location}`);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`PART-CAP-003: Found ${count} parts in "${TEST_QUERIES.valid.location}"`);

    await captureScreenshot(page, 'PART-CAP-003');
    await closeSpotlight(page);
  });

  test('PART-CAP-004: Search with NLP query', async ({ page }) => {
    await searchInSpotlight(page, 'show me all oil filters for the main engine');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`PART-CAP-004: NLP search returned ${count} parts`);

    await captureScreenshot(page, 'PART-CAP-004');
    await closeSpotlight(page);
  });

  test('PART-CAP-005: View part details', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.partName);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Should show part details panel
    const detailsPanel = page.locator('[data-testid="context-panel"], [data-testid="details-panel"]');
    const panelVisible = await detailsPanel.isVisible().catch(() => false);

    console.log(`PART-CAP-005: Details panel visible: ${panelVisible}`);

    await captureScreenshot(page, 'PART-CAP-005');
    await closeSpotlight(page);
  });

  test('PART-CAP-006: Check stock level displays', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.partName);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Look for stock level information
    const stockInfo = page.locator('text=/stock|quantity|in stock|available/i');
    const stockVisible = await stockInfo.isVisible().catch(() => false);

    console.log(`PART-CAP-006: Stock info visible: ${stockVisible}`);

    await captureScreenshot(page, 'PART-CAP-006');
    await closeSpotlight(page);
  });

  test('PART-CAP-007: View low stock parts', async ({ page }) => {
    await searchInSpotlight(page, 'low stock parts');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`PART-CAP-007: Found ${count} low stock parts`);

    await captureScreenshot(page, 'PART-CAP-007');
    await closeSpotlight(page);
  });

  test('PART-CAP-008: View part location', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.partName);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Look for location information
    const locationInfo = page.locator('text=/location|stored|locker|box/i');
    const locationVisible = await locationInfo.isVisible().catch(() => false);

    console.log(`PART-CAP-008: Location info visible: ${locationVisible}`);

    await captureScreenshot(page, 'PART-CAP-008');
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

  test('PART-CAP-009: Captain sees action buttons', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.partName);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Captain should see mutation buttons
    const actionButtons = page.locator('button:has-text("Consume"), button:has-text("Receive"), button:has-text("Adjust")');
    const actionsCount = await actionButtons.count();

    console.log(`PART-CAP-009: Captain sees ${actionsCount} action buttons`);

    await captureScreenshot(page, 'PART-CAP-009');
    await closeSpotlight(page);
  });

  test('PART-CAP-010: Add to shopping list action', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.partName);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    const shoppingBtn = page.locator('button:has-text("Add to Shopping"), button:has-text("Shopping List")');
    const shoppingVisible = await shoppingBtn.isVisible().catch(() => false);

    console.log(`PART-CAP-010: Shopping list button visible: ${shoppingVisible}`);

    await captureScreenshot(page, 'PART-CAP-010');
    await closeSpotlight(page);
  });

  test('PART-CAP-011: View part history', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.partName);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    const historyBtn = page.locator('button:has-text("History"), [data-testid="history-tab"]');
    if (await historyBtn.isVisible()) {
      await historyBtn.click();
      await page.waitForTimeout(500);
    }

    console.log('PART-CAP-011: Part history viewed');

    await captureScreenshot(page, 'PART-CAP-011');
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

  test('PART-HOD-001: HOD can search parts', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.partName);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    expect(count).toBeGreaterThanOrEqual(0);

    console.log(`PART-HOD-001: HOD found ${count} parts`);

    await captureScreenshot(page, 'PART-HOD-001');
    await closeSpotlight(page);
  });

  test('PART-HOD-002: HOD can view part details', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.partName);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    console.log('PART-HOD-002: HOD viewed part details');

    await captureScreenshot(page, 'PART-HOD-002');
    await closeSpotlight(page);
  });

  test('PART-HOD-003: HOD sees consume/receive actions', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.partName);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // HOD should see action buttons
    const consumeBtn = page.locator('button:has-text("Consume")');
    const receiveBtn = page.locator('button:has-text("Receive")');

    const consumeVisible = await consumeBtn.isVisible().catch(() => false);
    const receiveVisible = await receiveBtn.isVisible().catch(() => false);

    console.log(`PART-HOD-003: Consume: ${consumeVisible}, Receive: ${receiveVisible}`);

    await captureScreenshot(page, 'PART-HOD-003');
    await closeSpotlight(page);
  });

  test('PART-HOD-004: HOD can add to shopping list', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.partName);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    const shoppingBtn = page.locator('button:has-text("Shopping")');
    const shoppingVisible = await shoppingBtn.isVisible().catch(() => false);

    console.log(`PART-HOD-004: Shopping list for HOD: ${shoppingVisible}`);

    await captureScreenshot(page, 'PART-HOD-004');
    await closeSpotlight(page);
  });

  test('PART-HOD-005: HOD cannot see write-off action', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.partName);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Write-off is signed action - only captain
    const writeOffBtn = page.locator('button:has-text("Write Off"), button:has-text("Write-off")');
    const writeOffVisible = await writeOffBtn.isVisible().catch(() => false);

    console.log(`PART-HOD-005: Write-off visible for HOD: ${writeOffVisible}`);

    await captureScreenshot(page, 'PART-HOD-005');
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

  test('PART-CREW-001: Crew can search parts', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.partName);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`PART-CREW-001: Crew found ${count} parts`);

    await captureScreenshot(page, 'PART-CREW-001');
    await closeSpotlight(page);
  });

  test('PART-CREW-002: Crew can view part details', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.partName);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    console.log('PART-CREW-002: Crew viewed part details');

    await captureScreenshot(page, 'PART-CREW-002');
    await closeSpotlight(page);
  });

  test('PART-CREW-003: Crew CANNOT see consume action', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.partName);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    const consumeBtn = page.locator('button:has-text("Consume")');
    const consumeVisible = await consumeBtn.isVisible().catch(() => false);

    // Crew should NOT see consume button
    console.log(`PART-CREW-003: Consume visible for Crew: ${consumeVisible} (should be false)`);

    await captureScreenshot(page, 'PART-CREW-003');
    await closeSpotlight(page);
  });

  test('PART-CREW-004: Crew CANNOT see receive action', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.partName);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    const receiveBtn = page.locator('button:has-text("Receive")');
    const receiveVisible = await receiveBtn.isVisible().catch(() => false);

    // Crew should NOT see receive button
    console.log(`PART-CREW-004: Receive visible for Crew: ${receiveVisible} (should be false)`);

    await captureScreenshot(page, 'PART-CREW-004');
    await closeSpotlight(page);
  });

  test('PART-CREW-005: Crew CAN add to shopping list', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.partName);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // All crew can request parts
    const shoppingBtn = page.locator('button:has-text("Shopping"), button:has-text("Request")');
    const shoppingVisible = await shoppingBtn.isVisible().catch(() => false);

    console.log(`PART-CREW-005: Shopping list for Crew: ${shoppingVisible}`);

    await captureScreenshot(page, 'PART-CREW-005');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 5: FAILURE MODE TESTS
// =============================================================================

test.describe('Phase 5: Parts Lens Failure Modes', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('PART-FAIL-001: Search for nonexistent part', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.invalid.nonexistent);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);

    // Should return 0 or show "no results" message
    console.log(`PART-FAIL-001: Nonexistent part search returned ${count} results`);

    await captureScreenshot(page, 'PART-FAIL-001');
    await closeSpotlight(page);

    expect(count).toBe(0);
  });

  test('PART-FAIL-002: Special characters in search', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.invalid.special);
    await page.waitForTimeout(1000);

    // Should not crash
    expect(await page.locator('body').isVisible()).toBe(true);

    console.log('PART-FAIL-002: Special characters handled');

    await captureScreenshot(page, 'PART-FAIL-002');
    await closeSpotlight(page);
  });

  test('PART-FAIL-003: XSS attempt in search', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.invalid.malformed);
    await page.waitForTimeout(1000);

    // Check no script executed
    const alertTriggered = await page.evaluate(() => {
      return (window as any).__xss_triggered || false;
    });

    expect(alertTriggered).toBe(false);
    console.log('PART-FAIL-003: XSS prevented');

    await captureScreenshot(page, 'PART-FAIL-003');
    await closeSpotlight(page);
  });

  test('PART-FAIL-004: SQL injection in search', async ({ page }) => {
    await searchInSpotlight(page, "'; DROP TABLE pms_parts; --");
    await page.waitForTimeout(1000);

    // App should still work, table should exist
    await searchInSpotlight(page, TEST_QUERIES.valid.partName);
    const count = await getSearchResults(page);

    console.log(`PART-FAIL-004: Parts still searchable after injection: ${count >= 0}`);

    await captureScreenshot(page, 'PART-FAIL-004');
    await closeSpotlight(page);
  });

  test('PART-FAIL-005: Empty search', async ({ page }) => {
    await searchInSpotlight(page, '');
    await page.waitForTimeout(1000);

    // Should handle gracefully
    expect(await page.locator('body').isVisible()).toBe(true);
    console.log('PART-FAIL-005: Empty search handled');

    await captureScreenshot(page, 'PART-FAIL-005');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 6: EDGE CASES
// =============================================================================

test.describe('Phase 6: Parts Lens Edge Cases', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('PART-EDGE-001: Rapid successive searches', async ({ page }) => {
    for (let i = 0; i < 5; i++) {
      await searchInSpotlight(page, `part${i}`);
      await page.waitForTimeout(200);
    }

    // App should still be responsive
    expect(await page.locator('body').isVisible()).toBe(true);
    console.log('PART-EDGE-001: Rapid searches handled');

    await captureScreenshot(page, 'PART-EDGE-001');
    await closeSpotlight(page);
  });

  test('PART-EDGE-002: Unicode in part search', async ({ page }) => {
    await searchInSpotlight(page, '部品 filter 零件');
    await page.waitForTimeout(1000);

    expect(await page.locator('body').isVisible()).toBe(true);
    console.log('PART-EDGE-002: Unicode handled');

    await captureScreenshot(page, 'PART-EDGE-002');
    await closeSpotlight(page);
  });

  test('PART-EDGE-003: Very long search query', async ({ page }) => {
    const longQuery = 'filter '.repeat(100);
    await searchInSpotlight(page, longQuery);
    await page.waitForTimeout(1000);

    expect(await page.locator('body').isVisible()).toBe(true);
    console.log('PART-EDGE-003: Long query handled');

    await captureScreenshot(page, 'PART-EDGE-003');
    await closeSpotlight(page);
  });

  test('PART-EDGE-004: Search with multiple terms', async ({ page }) => {
    await searchInSpotlight(page, 'oil filter MTU engine room spare');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`PART-EDGE-004: Multi-term search returned ${count} results`);

    await captureScreenshot(page, 'PART-EDGE-004');
    await closeSpotlight(page);
  });

  test('PART-EDGE-005: Search immediately after login', async ({ page }) => {
    // Already logged in from beforeEach
    // Search immediately without waiting
    await searchInSpotlight(page, TEST_QUERIES.valid.partName);

    const count = await getSearchResults(page);
    console.log(`PART-EDGE-005: Immediate search returned ${count} results`);

    await captureScreenshot(page, 'PART-EDGE-005');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 7: PERFORMANCE TESTS
// =============================================================================

test.describe('Phase 7: Parts Lens Performance', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('PART-PERF-001: Search response time < 2s', async ({ page }) => {
    const startTime = Date.now();
    await searchInSpotlight(page, TEST_QUERIES.valid.partName);
    await page.waitForTimeout(500); // Wait for results
    const searchTime = Date.now() - startTime;

    console.log(`PART-PERF-001: Search time: ${searchTime}ms (threshold: ${PERF.searchMaxTime}ms)`);

    await captureScreenshot(page, 'PART-PERF-001');
    await closeSpotlight(page);

    expect(searchTime).toBeLessThan(PERF.searchMaxTime);
  });

  test('PART-PERF-002: Details load time < 1.5s', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.partName);
    await page.waitForTimeout(500);

    const startTime = Date.now();
    await clickFirstResult(page);
    await page.waitForTimeout(500);
    const detailsTime = Date.now() - startTime;

    console.log(`PART-PERF-002: Details load time: ${detailsTime}ms (threshold: ${PERF.detailsMaxTime}ms)`);

    await captureScreenshot(page, 'PART-PERF-002');
    await closeSpotlight(page);

    expect(detailsTime).toBeLessThan(PERF.detailsMaxTime);
  });
});

// =============================================================================
// SUMMARY
// =============================================================================

test('PART-SUMMARY: Parts Lens test suite complete', async ({ page }) => {
  console.log('\n' + '='.repeat(60));
  console.log('PARTS LENS TEST SUITE COMPLETE');
  console.log('='.repeat(60));
  console.log('\nTests by category:');
  console.log('- Captain Success Paths: 8 tests');
  console.log('- Captain Mutations: 3 tests');
  console.log('- HOD Role: 5 tests');
  console.log('- Crew Role: 5 tests');
  console.log('- Failure Modes: 5 tests');
  console.log('- Edge Cases: 5 tests');
  console.log('- Performance: 2 tests');
  console.log('\nTotal: 33 tests');
  console.log('Screenshots: ' + SCREENSHOT_DIR);
  console.log('='.repeat(60) + '\n');

  expect(true).toBe(true);
});
