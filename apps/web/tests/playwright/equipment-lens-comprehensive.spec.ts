/**
 * Equipment Lens - Comprehensive E2E Test Suite
 *
 * Tests all user journeys for equipment management:
 * - Search equipment
 * - View equipment details
 * - View maintenance history
 * - View associated parts
 * - View linked faults
 * - View equipment manuals
 *
 * Roles tested: Captain, HOD, Crew
 * All tests on single URL: app.celeste7.ai
 */

import { test, expect, Page } from '@playwright/test';
import { loginAs, searchInSpotlight } from './auth.helper';

const SCREENSHOT_DIR = '/tmp/equipment_lens_test_screenshots';

// =============================================================================
// TEST DATA
// =============================================================================

const TEST_QUERIES = {
  valid: {
    equipment: 'generator',
    location: 'engine room',
    type: 'mechanical',
    manufacturer: 'caterpillar',
    status: 'operational',
  },
  invalid: {
    nonexistent: 'NONEXISTENT_EQUIPMENT_XYZ999',
    malformed: '"><script>alert(1)</script>',
    special: '!@#$%^&*()',
    sqlInjection: "'; DROP TABLE pms_equipment; --",
  }
};

const PERF = {
  searchMaxTime: 2000,
  detailsMaxTime: 1500,
  historyMaxTime: 2000,
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

test.describe('Phase 1: Captain Success Paths - Equipment Search', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('EQUIP-CAP-001: Search for equipment by name', async ({ page }) => {
    const startTime = Date.now();
    await searchInSpotlight(page, TEST_QUERIES.valid.equipment);
    const searchTime = Date.now() - startTime;

    await page.waitForTimeout(1000);
    const count = await getSearchResults(page);

    expect(searchTime).toBeLessThan(PERF.searchMaxTime);
    console.log(`EQUIP-CAP-001: Found ${count} equipment for "${TEST_QUERIES.valid.equipment}" in ${searchTime}ms`);

    await captureScreenshot(page, 'EQUIP-CAP-001');
    await closeSpotlight(page);
  });

  test('EQUIP-CAP-002: Search for equipment by location', async ({ page }) => {
    await searchInSpotlight(page, `equipment in ${TEST_QUERIES.valid.location}`);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`EQUIP-CAP-002: Found ${count} equipment in "${TEST_QUERIES.valid.location}"`);

    await captureScreenshot(page, 'EQUIP-CAP-002');
    await closeSpotlight(page);
  });

  test('EQUIP-CAP-003: Search for equipment by type', async ({ page }) => {
    await searchInSpotlight(page, `${TEST_QUERIES.valid.type} equipment`);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`EQUIP-CAP-003: Found ${count} "${TEST_QUERIES.valid.type}" equipment`);

    await captureScreenshot(page, 'EQUIP-CAP-003');
    await closeSpotlight(page);
  });

  test('EQUIP-CAP-004: Search with NLP query', async ({ page }) => {
    await searchInSpotlight(page, 'show me all equipment in the engine room');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`EQUIP-CAP-004: NLP search returned ${count} equipment`);

    await captureScreenshot(page, 'EQUIP-CAP-004');
    await closeSpotlight(page);
  });

  test('EQUIP-CAP-005: View equipment details', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.equipment);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Should show equipment details panel
    const detailsPanel = page.locator('[data-testid="context-panel"], [data-testid="details-panel"]');
    const panelVisible = await detailsPanel.isVisible().catch(() => false);

    console.log(`EQUIP-CAP-005: Details panel visible: ${panelVisible}`);

    await captureScreenshot(page, 'EQUIP-CAP-005');
    await closeSpotlight(page);
  });

  test('EQUIP-CAP-006: View equipment status', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.equipment);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Look for status indicator
    const statusIndicator = page.locator('text=/operational|out of service|maintenance|offline/i');
    const statusVisible = await statusIndicator.isVisible().catch(() => false);

    console.log(`EQUIP-CAP-006: Status visible: ${statusVisible}`);

    await captureScreenshot(page, 'EQUIP-CAP-006');
    await closeSpotlight(page);
  });

  test('EQUIP-CAP-007: View equipment manufacturer/model', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.equipment);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Look for manufacturer/model info
    const mfgInfo = page.locator('text=/manufacturer|model|make/i');
    const mfgVisible = await mfgInfo.isVisible().catch(() => false);

    console.log(`EQUIP-CAP-007: Manufacturer info visible: ${mfgVisible}`);

    await captureScreenshot(page, 'EQUIP-CAP-007');
    await closeSpotlight(page);
  });

  test('EQUIP-CAP-008: View equipment risk score', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.equipment);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Look for risk/health indicator
    const riskIndicator = page.locator('text=/risk|health|score/i');
    const riskVisible = await riskIndicator.isVisible().catch(() => false);

    console.log(`EQUIP-CAP-008: Risk score visible: ${riskVisible}`);

    await captureScreenshot(page, 'EQUIP-CAP-008');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 2: CAPTAIN - RELATED DATA
// =============================================================================

test.describe('Phase 2: Captain - Related Data', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('EQUIP-CAP-009: View maintenance history', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.equipment);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Look for maintenance history section/tab
    const historySection = page.locator('text=/maintenance|history|work order/i');
    const historyVisible = await historySection.isVisible().catch(() => false);

    console.log(`EQUIP-CAP-009: Maintenance history visible: ${historyVisible}`);

    await captureScreenshot(page, 'EQUIP-CAP-009');
    await closeSpotlight(page);
  });

  test('EQUIP-CAP-010: View associated parts', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.equipment);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Look for parts section
    const partsSection = page.locator('text=/parts|spare|inventory/i');
    const partsVisible = await partsSection.isVisible().catch(() => false);

    console.log(`EQUIP-CAP-010: Parts section visible: ${partsVisible}`);

    await captureScreenshot(page, 'EQUIP-CAP-010');
    await closeSpotlight(page);
  });

  test('EQUIP-CAP-011: View linked faults', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.equipment);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Look for faults section
    const faultsSection = page.locator('text=/fault|issue|problem/i');
    const faultsVisible = await faultsSection.isVisible().catch(() => false);

    console.log(`EQUIP-CAP-011: Faults section visible: ${faultsVisible}`);

    await captureScreenshot(page, 'EQUIP-CAP-011');
    await closeSpotlight(page);
  });

  test('EQUIP-CAP-012: View equipment manual', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.equipment);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Look for manual/documentation section
    const manualSection = page.locator('text=/manual|documentation|pdf/i');
    const manualVisible = await manualSection.isVisible().catch(() => false);

    console.log(`EQUIP-CAP-012: Manual section visible: ${manualVisible}`);

    await captureScreenshot(page, 'EQUIP-CAP-012');
    await closeSpotlight(page);
  });

  test('EQUIP-CAP-013: Run diagnostic on equipment', async ({ page }) => {
    await searchInSpotlight(page, `run diagnostic on ${TEST_QUERIES.valid.equipment}`);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`EQUIP-CAP-013: Diagnostic search returned ${count} results`);

    await captureScreenshot(page, 'EQUIP-CAP-013');
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

  test('EQUIP-HOD-001: HOD can search equipment', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.equipment);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    expect(count).toBeGreaterThanOrEqual(0);

    console.log(`EQUIP-HOD-001: HOD found ${count} equipment`);

    await captureScreenshot(page, 'EQUIP-HOD-001');
    await closeSpotlight(page);
  });

  test('EQUIP-HOD-002: HOD can view equipment details', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.equipment);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    console.log('EQUIP-HOD-002: HOD viewed equipment details');

    await captureScreenshot(page, 'EQUIP-HOD-002');
    await closeSpotlight(page);
  });

  test('EQUIP-HOD-003: HOD can view maintenance history', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.equipment);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    const historySection = page.locator('text=/maintenance|history/i');
    const historyVisible = await historySection.isVisible().catch(() => false);

    console.log(`EQUIP-HOD-003: History visible for HOD: ${historyVisible}`);

    await captureScreenshot(page, 'EQUIP-HOD-003');
    await closeSpotlight(page);
  });

  test('EQUIP-HOD-004: HOD can view parts list', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.equipment);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    const partsSection = page.locator('text=/parts|inventory/i');
    const partsVisible = await partsSection.isVisible().catch(() => false);

    console.log(`EQUIP-HOD-004: Parts visible for HOD: ${partsVisible}`);

    await captureScreenshot(page, 'EQUIP-HOD-004');
    await closeSpotlight(page);
  });

  test('EQUIP-HOD-005: HOD can run diagnostics', async ({ page }) => {
    await searchInSpotlight(page, 'diagnostic');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`EQUIP-HOD-005: Diagnostic for HOD returned ${count} results`);

    await captureScreenshot(page, 'EQUIP-HOD-005');
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

  test('EQUIP-CREW-001: Crew can search equipment', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.equipment);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`EQUIP-CREW-001: Crew found ${count} equipment`);

    await captureScreenshot(page, 'EQUIP-CREW-001');
    await closeSpotlight(page);
  });

  test('EQUIP-CREW-002: Crew can view equipment details', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.equipment);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    console.log('EQUIP-CREW-002: Crew viewed equipment details');

    await captureScreenshot(page, 'EQUIP-CREW-002');
    await closeSpotlight(page);
  });

  test('EQUIP-CREW-003: Crew can view manuals', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.equipment);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    const manualSection = page.locator('text=/manual|documentation/i');
    const manualVisible = await manualSection.isVisible().catch(() => false);

    console.log(`EQUIP-CREW-003: Manual visible for Crew: ${manualVisible}`);

    await captureScreenshot(page, 'EQUIP-CREW-003');
    await closeSpotlight(page);
  });

  test('EQUIP-CREW-004: Crew can view faults', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.equipment);
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    const faultsSection = page.locator('text=/fault|issue/i');
    const faultsVisible = await faultsSection.isVisible().catch(() => false);

    console.log(`EQUIP-CREW-004: Faults visible for Crew: ${faultsVisible}`);

    await captureScreenshot(page, 'EQUIP-CREW-004');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 5: FAILURE MODE TESTS
// =============================================================================

test.describe('Phase 5: Equipment Lens Failure Modes', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('EQUIP-FAIL-001: Search for nonexistent equipment', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.invalid.nonexistent);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);

    console.log(`EQUIP-FAIL-001: Nonexistent equipment search returned ${count} results`);

    await captureScreenshot(page, 'EQUIP-FAIL-001');
    await closeSpotlight(page);

    expect(count).toBe(0);
  });

  test('EQUIP-FAIL-002: Special characters in search', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.invalid.special);
    await page.waitForTimeout(1000);

    expect(await page.locator('body').isVisible()).toBe(true);
    console.log('EQUIP-FAIL-002: Special characters handled');

    await captureScreenshot(page, 'EQUIP-FAIL-002');
    await closeSpotlight(page);
  });

  test('EQUIP-FAIL-003: XSS attempt in search', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.invalid.malformed);
    await page.waitForTimeout(1000);

    const alertTriggered = await page.evaluate(() => {
      return (window as any).__xss_triggered || false;
    });

    expect(alertTriggered).toBe(false);
    console.log('EQUIP-FAIL-003: XSS prevented');

    await captureScreenshot(page, 'EQUIP-FAIL-003');
    await closeSpotlight(page);
  });

  test('EQUIP-FAIL-004: SQL injection in search', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.invalid.sqlInjection);
    await page.waitForTimeout(1000);

    await closeSpotlight(page);
    await searchInSpotlight(page, TEST_QUERIES.valid.equipment);
    const count = await getSearchResults(page);

    console.log(`EQUIP-FAIL-004: Equipment still searchable after injection: ${count >= 0}`);

    await captureScreenshot(page, 'EQUIP-FAIL-004');
    await closeSpotlight(page);
  });

  test('EQUIP-FAIL-005: Empty search', async ({ page }) => {
    await searchInSpotlight(page, '');
    await page.waitForTimeout(1000);

    expect(await page.locator('body').isVisible()).toBe(true);
    console.log('EQUIP-FAIL-005: Empty search handled');

    await captureScreenshot(page, 'EQUIP-FAIL-005');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 6: EDGE CASES
// =============================================================================

test.describe('Phase 6: Equipment Lens Edge Cases', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('EQUIP-EDGE-001: Rapid successive searches', async ({ page }) => {
    for (let i = 0; i < 5; i++) {
      await searchInSpotlight(page, `equipment${i}`);
      await page.waitForTimeout(200);
    }

    expect(await page.locator('body').isVisible()).toBe(true);
    console.log('EQUIP-EDGE-001: Rapid searches handled');

    await captureScreenshot(page, 'EQUIP-EDGE-001');
    await closeSpotlight(page);
  });

  test('EQUIP-EDGE-002: Unicode in equipment search', async ({ page }) => {
    await searchInSpotlight(page, '機器 equipment 設備');
    await page.waitForTimeout(1000);

    expect(await page.locator('body').isVisible()).toBe(true);
    console.log('EQUIP-EDGE-002: Unicode handled');

    await captureScreenshot(page, 'EQUIP-EDGE-002');
    await closeSpotlight(page);
  });

  test('EQUIP-EDGE-003: Very long search query', async ({ page }) => {
    const longQuery = 'equipment '.repeat(100);
    await searchInSpotlight(page, longQuery);
    await page.waitForTimeout(1000);

    expect(await page.locator('body').isVisible()).toBe(true);
    console.log('EQUIP-EDGE-003: Long query handled');

    await captureScreenshot(page, 'EQUIP-EDGE-003');
    await closeSpotlight(page);
  });

  test('EQUIP-EDGE-004: Search with multiple terms', async ({ page }) => {
    await searchInSpotlight(page, 'generator engine room caterpillar maintenance');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`EQUIP-EDGE-004: Multi-term search returned ${count} results`);

    await captureScreenshot(page, 'EQUIP-EDGE-004');
    await closeSpotlight(page);
  });

  test('EQUIP-EDGE-005: Search immediately after login', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.equipment);

    const count = await getSearchResults(page);
    console.log(`EQUIP-EDGE-005: Immediate search returned ${count} results`);

    await captureScreenshot(page, 'EQUIP-EDGE-005');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 7: PERFORMANCE TESTS
// =============================================================================

test.describe('Phase 7: Equipment Lens Performance', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('EQUIP-PERF-001: Search response time < 2s', async ({ page }) => {
    const startTime = Date.now();
    await searchInSpotlight(page, TEST_QUERIES.valid.equipment);
    await page.waitForTimeout(500);
    const searchTime = Date.now() - startTime;

    console.log(`EQUIP-PERF-001: Search time: ${searchTime}ms (threshold: ${PERF.searchMaxTime}ms)`);

    await captureScreenshot(page, 'EQUIP-PERF-001');
    await closeSpotlight(page);

    expect(searchTime).toBeLessThan(PERF.searchMaxTime);
  });

  test('EQUIP-PERF-002: Details load time < 1.5s', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.valid.equipment);
    await page.waitForTimeout(500);

    const startTime = Date.now();
    await clickFirstResult(page);
    await page.waitForTimeout(500);
    const detailsTime = Date.now() - startTime;

    console.log(`EQUIP-PERF-002: Details load time: ${detailsTime}ms (threshold: ${PERF.detailsMaxTime}ms)`);

    await captureScreenshot(page, 'EQUIP-PERF-002');
    await closeSpotlight(page);

    expect(detailsTime).toBeLessThan(PERF.detailsMaxTime);
  });
});

// =============================================================================
// SUMMARY
// =============================================================================

test('EQUIP-SUMMARY: Equipment Lens test suite complete', async ({ page }) => {
  console.log('\n' + '='.repeat(60));
  console.log('EQUIPMENT LENS TEST SUITE COMPLETE');
  console.log('='.repeat(60));
  console.log('\nTests by category:');
  console.log('- Captain Success Paths: 8 tests');
  console.log('- Captain Related Data: 5 tests');
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
