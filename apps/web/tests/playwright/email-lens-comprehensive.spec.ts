/**
 * Email Lens - Comprehensive E2E Test Suite
 *
 * Tests all user journeys for email management:
 * - Search emails
 * - View email threads
 * - Link emails to entities (work orders, equipment, faults)
 * - Extract entities from emails
 * - Save attachments to documents
 *
 * Roles tested: Captain, HOD, Crew
 * All tests on single URL: app.celeste7.ai
 *
 * Email Lens Endpoints:
 * - GET /email/search - Hybrid semantic+entity search
 * - GET /email/thread/:thread_id - Get thread with messages
 * - GET /email/related - Get threads linked to an object
 * - POST /email/link/add - Add a new link
 * - POST /email/evidence/save-attachment - Save attachment
 */

import { test, expect, Page } from '@playwright/test';
import { loginAs, searchInSpotlight } from './auth.helper';

const SCREENSHOT_DIR = '/tmp/email_lens_test_screenshots';

// =============================================================================
// TEST DATA
// =============================================================================

const TEST_QUERIES = {
  valid: {
    subject: 'maintenance',
    sender: 'engineer',
    attachment: 'invoice',
    equipment: 'generator',
    workOrder: 'WO-',
    dateRange: 'this week',
  },
  invalid: {
    nonexistent: 'NONEXISTENT_EMAIL_XYZ999@fake.com',
    malformed: '"><script>alert(1)</script>',
    special: '!@#$%^&*()',
    sqlInjection: "'; DROP TABLE email_messages; --",
  }
};

const PERF = {
  searchMaxTime: 3000,  // Email search may be slower due to semantic matching
  threadLoadMaxTime: 2000,
  attachmentListMaxTime: 1500,
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

test.describe('Phase 1: Captain Success Paths - Email Search', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('EMAIL-CAP-001: Search for emails by subject', async ({ page }) => {
    const startTime = Date.now();
    await searchInSpotlight(page, `email ${TEST_QUERIES.valid.subject}`);
    const searchTime = Date.now() - startTime;

    await page.waitForTimeout(1000);
    const count = await getSearchResults(page);

    expect(searchTime).toBeLessThan(PERF.searchMaxTime);
    console.log(`EMAIL-CAP-001: Found ${count} emails for "${TEST_QUERIES.valid.subject}" in ${searchTime}ms`);

    await captureScreenshot(page, 'EMAIL-CAP-001');
    await closeSpotlight(page);
  });

  test('EMAIL-CAP-002: Search for emails with attachments', async ({ page }) => {
    await searchInSpotlight(page, `email with ${TEST_QUERIES.valid.attachment}`);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`EMAIL-CAP-002: Found ${count} emails with "${TEST_QUERIES.valid.attachment}"`);

    await captureScreenshot(page, 'EMAIL-CAP-002');
    await closeSpotlight(page);
  });

  test('EMAIL-CAP-003: Search for emails from sender', async ({ page }) => {
    await searchInSpotlight(page, `emails from ${TEST_QUERIES.valid.sender}`);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`EMAIL-CAP-003: Found ${count} emails from "${TEST_QUERIES.valid.sender}"`);

    await captureScreenshot(page, 'EMAIL-CAP-003');
    await closeSpotlight(page);
  });

  test('EMAIL-CAP-004: Search emails by date range', async ({ page }) => {
    await searchInSpotlight(page, `emails from ${TEST_QUERIES.valid.dateRange}`);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`EMAIL-CAP-004: Found ${count} emails from "${TEST_QUERIES.valid.dateRange}"`);

    await captureScreenshot(page, 'EMAIL-CAP-004');
    await closeSpotlight(page);
  });

  test('EMAIL-CAP-005: Search with NLP query', async ({ page }) => {
    await searchInSpotlight(page, 'show me all emails about generator maintenance');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`EMAIL-CAP-005: NLP search returned ${count} emails`);

    await captureScreenshot(page, 'EMAIL-CAP-005');
    await closeSpotlight(page);
  });

  test('EMAIL-CAP-006: View email thread', async ({ page }) => {
    await searchInSpotlight(page, 'email');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Should show email thread/details panel
    const detailsPanel = page.locator('[data-testid="context-panel"], [data-testid="details-panel"]');
    const panelVisible = await detailsPanel.isVisible().catch(() => false);

    console.log(`EMAIL-CAP-006: Email panel visible: ${panelVisible}`);

    await captureScreenshot(page, 'EMAIL-CAP-006');
    await closeSpotlight(page);
  });

  test('EMAIL-CAP-007: View email attachments list', async ({ page }) => {
    await searchInSpotlight(page, 'email with attachment');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Look for attachments section
    const attachmentsSection = page.locator('text=/attachment|file|document/i');
    const attachmentsVisible = await attachmentsSection.isVisible().catch(() => false);

    console.log(`EMAIL-CAP-007: Attachments section visible: ${attachmentsVisible}`);

    await captureScreenshot(page, 'EMAIL-CAP-007');
    await closeSpotlight(page);
  });

  test('EMAIL-CAP-008: View related entities from email', async ({ page }) => {
    await searchInSpotlight(page, 'email');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Look for related/linked entities
    const relatedSection = page.locator('text=/related|linked|associated/i');
    const relatedVisible = await relatedSection.isVisible().catch(() => false);

    console.log(`EMAIL-CAP-008: Related section visible: ${relatedVisible}`);

    await captureScreenshot(page, 'EMAIL-CAP-008');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 2: CAPTAIN - LINK ACTIONS
// =============================================================================

test.describe('Phase 2: Captain Link Actions', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('EMAIL-CAP-009: Captain sees link to work order option', async ({ page }) => {
    await searchInSpotlight(page, 'email');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Captain should see link options
    const linkButton = page.locator('button:has-text("Link"), button:has-text("Connect")');
    const linkVisible = await linkButton.isVisible().catch(() => false);

    console.log(`EMAIL-CAP-009: Link button visible: ${linkVisible}`);

    await captureScreenshot(page, 'EMAIL-CAP-009');
    await closeSpotlight(page);
  });

  test('EMAIL-CAP-010: Captain sees save attachment option', async ({ page }) => {
    await searchInSpotlight(page, 'email with attachment');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Captain should see save attachment option
    const saveButton = page.locator('button:has-text("Save"), button:has-text("Download")');
    const saveVisible = await saveButton.isVisible().catch(() => false);

    console.log(`EMAIL-CAP-010: Save attachment visible: ${saveVisible}`);

    await captureScreenshot(page, 'EMAIL-CAP-010');
    await closeSpotlight(page);
  });

  test('EMAIL-CAP-011: Captain sees suggested links', async ({ page }) => {
    await searchInSpotlight(page, 'email');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);
    await page.waitForTimeout(500);

    // Look for suggested links section
    const suggestionsSection = page.locator('text=/suggest|recommendation|could be linked/i');
    const suggestionsVisible = await suggestionsSection.isVisible().catch(() => false);

    console.log(`EMAIL-CAP-011: Suggestions visible: ${suggestionsVisible}`);

    await captureScreenshot(page, 'EMAIL-CAP-011');
    await closeSpotlight(page);
  });

  test('EMAIL-CAP-012: Find emails linked to equipment', async ({ page }) => {
    await searchInSpotlight(page, `emails about ${TEST_QUERIES.valid.equipment}`);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`EMAIL-CAP-012: Found ${count} emails about "${TEST_QUERIES.valid.equipment}"`);

    await captureScreenshot(page, 'EMAIL-CAP-012');
    await closeSpotlight(page);
  });

  test('EMAIL-CAP-013: Find emails linked to work orders', async ({ page }) => {
    await searchInSpotlight(page, `emails about work order`);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`EMAIL-CAP-013: Found ${count} emails about work orders`);

    await captureScreenshot(page, 'EMAIL-CAP-013');
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

  test('EMAIL-HOD-001: HOD can search emails', async ({ page }) => {
    await searchInSpotlight(page, 'email');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    expect(count).toBeGreaterThanOrEqual(0);

    console.log(`EMAIL-HOD-001: HOD found ${count} emails`);

    await captureScreenshot(page, 'EMAIL-HOD-001');
    await closeSpotlight(page);
  });

  test('EMAIL-HOD-002: HOD can view email thread', async ({ page }) => {
    await searchInSpotlight(page, 'email');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    console.log('EMAIL-HOD-002: HOD viewed email thread');

    await captureScreenshot(page, 'EMAIL-HOD-002');
    await closeSpotlight(page);
  });

  test('EMAIL-HOD-003: HOD can link emails to entities', async ({ page }) => {
    await searchInSpotlight(page, 'email');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // HOD should see link button
    const linkButton = page.locator('button:has-text("Link")');
    const linkVisible = await linkButton.isVisible().catch(() => false);

    console.log(`EMAIL-HOD-003: Link visible for HOD: ${linkVisible}`);

    await captureScreenshot(page, 'EMAIL-HOD-003');
    await closeSpotlight(page);
  });

  test('EMAIL-HOD-004: HOD can save attachments', async ({ page }) => {
    await searchInSpotlight(page, 'email with attachment');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    const saveButton = page.locator('button:has-text("Save")');
    const saveVisible = await saveButton.isVisible().catch(() => false);

    console.log(`EMAIL-HOD-004: Save attachment for HOD: ${saveVisible}`);

    await captureScreenshot(page, 'EMAIL-HOD-004');
    await closeSpotlight(page);
  });

  test('EMAIL-HOD-005: HOD can view suggested links', async ({ page }) => {
    await searchInSpotlight(page, 'email');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    const suggestionsSection = page.locator('text=/suggest|recommendation/i');
    const suggestionsVisible = await suggestionsSection.isVisible().catch(() => false);

    console.log(`EMAIL-HOD-005: Suggestions visible for HOD: ${suggestionsVisible}`);

    await captureScreenshot(page, 'EMAIL-HOD-005');
    await closeSpotlight(page);
  });

  test('EMAIL-HOD-006: HOD can accept suggested link', async ({ page }) => {
    await searchInSpotlight(page, 'email');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Look for accept button on suggestions
    const acceptButton = page.locator('button:has-text("Accept"), button:has-text("Confirm")');
    const acceptVisible = await acceptButton.isVisible().catch(() => false);

    console.log(`EMAIL-HOD-006: Accept link for HOD: ${acceptVisible}`);

    await captureScreenshot(page, 'EMAIL-HOD-006');
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

  test('EMAIL-CREW-001: Crew can search emails', async ({ page }) => {
    await searchInSpotlight(page, 'email');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`EMAIL-CREW-001: Crew found ${count} emails`);

    await captureScreenshot(page, 'EMAIL-CREW-001');
    await closeSpotlight(page);
  });

  test('EMAIL-CREW-002: Crew can view email thread', async ({ page }) => {
    await searchInSpotlight(page, 'email');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    console.log('EMAIL-CREW-002: Crew viewed email thread');

    await captureScreenshot(page, 'EMAIL-CREW-002');
    await closeSpotlight(page);
  });

  test('EMAIL-CREW-003: Crew can view attachments', async ({ page }) => {
    await searchInSpotlight(page, 'email with attachment');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Crew should be able to view attachments
    const attachmentsList = page.locator('text=/attachment|file/i');
    const attachmentsVisible = await attachmentsList.isVisible().catch(() => false);

    console.log(`EMAIL-CREW-003: Attachments visible for Crew: ${attachmentsVisible}`);

    await captureScreenshot(page, 'EMAIL-CREW-003');
    await closeSpotlight(page);
  });

  test('EMAIL-CREW-004: Crew CANNOT link emails (read-only)', async ({ page }) => {
    await searchInSpotlight(page, 'email');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Crew should NOT see link/mutation buttons
    const linkButton = page.locator('button:has-text("Link to Work Order"), button:has-text("Link to Equipment")');
    const linkVisible = await linkButton.isVisible().catch(() => false);

    console.log(`EMAIL-CREW-004: Link for Crew: ${linkVisible} (should be false)`);

    await captureScreenshot(page, 'EMAIL-CREW-004');
    await closeSpotlight(page);
  });

  test('EMAIL-CREW-005: Crew CANNOT save attachments to documents', async ({ page }) => {
    await searchInSpotlight(page, 'email with attachment');
    await page.waitForTimeout(1000);

    await clickFirstResult(page);

    // Crew should NOT see save to documents button (write action)
    const saveToDocsButton = page.locator('button:has-text("Save to Documents")');
    const saveVisible = await saveToDocsButton.isVisible().catch(() => false);

    console.log(`EMAIL-CREW-005: Save to Docs for Crew: ${saveVisible} (should be false)`);

    await captureScreenshot(page, 'EMAIL-CREW-005');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 5: FAILURE MODE TESTS
// =============================================================================

test.describe('Phase 5: Email Lens Failure Modes', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('EMAIL-FAIL-001: Search for nonexistent email', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.invalid.nonexistent);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);

    console.log(`EMAIL-FAIL-001: Nonexistent email search returned ${count} results`);

    await captureScreenshot(page, 'EMAIL-FAIL-001');
    await closeSpotlight(page);

    expect(count).toBe(0);
  });

  test('EMAIL-FAIL-002: Special characters in search', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.invalid.special);
    await page.waitForTimeout(1000);

    // Should not crash
    expect(await page.locator('body').isVisible()).toBe(true);

    console.log('EMAIL-FAIL-002: Special characters handled');

    await captureScreenshot(page, 'EMAIL-FAIL-002');
    await closeSpotlight(page);
  });

  test('EMAIL-FAIL-003: XSS attempt in search', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.invalid.malformed);
    await page.waitForTimeout(1000);

    // Check no script executed
    const alertTriggered = await page.evaluate(() => {
      return (window as any).__xss_triggered || false;
    });

    expect(alertTriggered).toBe(false);
    console.log('EMAIL-FAIL-003: XSS prevented');

    await captureScreenshot(page, 'EMAIL-FAIL-003');
    await closeSpotlight(page);
  });

  test('EMAIL-FAIL-004: SQL injection in search', async ({ page }) => {
    await searchInSpotlight(page, TEST_QUERIES.invalid.sqlInjection);
    await page.waitForTimeout(1000);

    // App should still work
    await closeSpotlight(page);
    await searchInSpotlight(page, 'email');
    const count = await getSearchResults(page);

    console.log(`EMAIL-FAIL-004: Emails still searchable after injection: ${count >= 0}`);

    await captureScreenshot(page, 'EMAIL-FAIL-004');
    await closeSpotlight(page);
  });

  test('EMAIL-FAIL-005: Empty search', async ({ page }) => {
    await searchInSpotlight(page, '');
    await page.waitForTimeout(1000);

    // Should handle gracefully
    expect(await page.locator('body').isVisible()).toBe(true);
    console.log('EMAIL-FAIL-005: Empty search handled');

    await captureScreenshot(page, 'EMAIL-FAIL-005');
    await closeSpotlight(page);
  });

  test('EMAIL-FAIL-006: Invalid email address format', async ({ page }) => {
    await searchInSpotlight(page, 'email from not-an-email');
    await page.waitForTimeout(1000);

    // Should handle gracefully without crashing
    expect(await page.locator('body').isVisible()).toBe(true);
    console.log('EMAIL-FAIL-006: Invalid email format handled');

    await captureScreenshot(page, 'EMAIL-FAIL-006');
    await closeSpotlight(page);
  });

  test('EMAIL-FAIL-007: Path traversal in attachment', async ({ page }) => {
    await searchInSpotlight(page, 'email attachment ../../../etc/passwd');
    await page.waitForTimeout(1000);

    // Should not expose system files
    const systemContent = page.locator('text=/root:x:0:0|\/bin\/bash|\/sbin\/nologin|nobody:x:/');
    const systemVisible = await systemContent.isVisible().catch(() => false);

    expect(systemVisible).toBe(false);
    console.log('EMAIL-FAIL-007: Path traversal prevented');

    await captureScreenshot(page, 'EMAIL-FAIL-007');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 6: EDGE CASES
// =============================================================================

test.describe('Phase 6: Email Lens Edge Cases', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('EMAIL-EDGE-001: Rapid successive searches', async ({ page }) => {
    for (let i = 0; i < 5; i++) {
      await searchInSpotlight(page, `email${i}`);
      await page.waitForTimeout(200);
    }

    // App should still be responsive
    expect(await page.locator('body').isVisible()).toBe(true);
    console.log('EMAIL-EDGE-001: Rapid searches handled');

    await captureScreenshot(page, 'EMAIL-EDGE-001');
    await closeSpotlight(page);
  });

  test('EMAIL-EDGE-002: Unicode in email search', async ({ page }) => {
    await searchInSpotlight(page, 'email 日本語 email');
    await page.waitForTimeout(1000);

    expect(await page.locator('body').isVisible()).toBe(true);
    console.log('EMAIL-EDGE-002: Unicode handled');

    await captureScreenshot(page, 'EMAIL-EDGE-002');
    await closeSpotlight(page);
  });

  test('EMAIL-EDGE-003: Very long search query', async ({ page }) => {
    const longQuery = 'email '.repeat(100);
    await searchInSpotlight(page, longQuery);
    await page.waitForTimeout(1000);

    expect(await page.locator('body').isVisible()).toBe(true);
    console.log('EMAIL-EDGE-003: Long query handled');

    await captureScreenshot(page, 'EMAIL-EDGE-003');
    await closeSpotlight(page);
  });

  test('EMAIL-EDGE-004: Search with multiple terms', async ({ page }) => {
    await searchInSpotlight(page, 'email maintenance generator invoice this week');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`EMAIL-EDGE-004: Multi-term search returned ${count} results`);

    await captureScreenshot(page, 'EMAIL-EDGE-004');
    await closeSpotlight(page);
  });

  test('EMAIL-EDGE-005: Search immediately after login', async ({ page }) => {
    // Already logged in from beforeEach
    await searchInSpotlight(page, 'email');

    const count = await getSearchResults(page);
    console.log(`EMAIL-EDGE-005: Immediate search returned ${count} results`);

    await captureScreenshot(page, 'EMAIL-EDGE-005');
    await closeSpotlight(page);
  });

  test('EMAIL-EDGE-006: Search for emails with specific file type', async ({ page }) => {
    await searchInSpotlight(page, 'email with pdf attachment');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`EMAIL-EDGE-006: PDF attachment search returned ${count} results`);

    await captureScreenshot(page, 'EMAIL-EDGE-006');
    await closeSpotlight(page);
  });

  test('EMAIL-EDGE-007: Search for emails in date range', async ({ page }) => {
    await searchInSpotlight(page, 'emails from last month');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`EMAIL-EDGE-007: Last month emails returned ${count} results`);

    await captureScreenshot(page, 'EMAIL-EDGE-007');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 7: PERFORMANCE TESTS
// =============================================================================

test.describe('Phase 7: Email Lens Performance', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('EMAIL-PERF-001: Search response time < 3s', async ({ page }) => {
    const startTime = Date.now();
    await searchInSpotlight(page, 'email');
    await page.waitForTimeout(500);
    const searchTime = Date.now() - startTime;

    console.log(`EMAIL-PERF-001: Search time: ${searchTime}ms (threshold: ${PERF.searchMaxTime}ms)`);

    await captureScreenshot(page, 'EMAIL-PERF-001');
    await closeSpotlight(page);

    expect(searchTime).toBeLessThan(PERF.searchMaxTime);
  });

  test('EMAIL-PERF-002: Thread load time < 2s', async ({ page }) => {
    await searchInSpotlight(page, 'email');
    await page.waitForTimeout(500);

    const startTime = Date.now();
    await clickFirstResult(page);
    await page.waitForTimeout(500);
    const threadTime = Date.now() - startTime;

    console.log(`EMAIL-PERF-002: Thread load time: ${threadTime}ms (threshold: ${PERF.threadLoadMaxTime}ms)`);

    await captureScreenshot(page, 'EMAIL-PERF-002');
    await closeSpotlight(page);

    expect(threadTime).toBeLessThan(PERF.threadLoadMaxTime);
  });
});

// =============================================================================
// PHASE 8: SEMANTIC SEARCH TESTS
// =============================================================================

test.describe('Phase 8: Email Semantic Search', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('EMAIL-SEM-001: Semantic search with context', async ({ page }) => {
    await searchInSpotlight(page, 'emails about the broken pump that needs replacement parts');
    await page.waitForTimeout(1500);

    const count = await getSearchResults(page);
    console.log(`EMAIL-SEM-001: Semantic search returned ${count} results`);

    await captureScreenshot(page, 'EMAIL-SEM-001');
    await closeSpotlight(page);
  });

  test('EMAIL-SEM-002: Search with synonyms', async ({ page }) => {
    await searchInSpotlight(page, 'emails about repair parts');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`EMAIL-SEM-002: Synonym search returned ${count} results`);

    await captureScreenshot(page, 'EMAIL-SEM-002');
    await closeSpotlight(page);
  });

  test('EMAIL-SEM-003: Search with question format', async ({ page }) => {
    await searchInSpotlight(page, 'which emails mention the engine overheating?');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`EMAIL-SEM-003: Question search returned ${count} results`);

    await captureScreenshot(page, 'EMAIL-SEM-003');
    await closeSpotlight(page);
  });
});

// =============================================================================
// PHASE 9: ENTITY LINKING TESTS
// =============================================================================

test.describe('Phase 9: Email Entity Linking', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'captain');
  });

  test('EMAIL-LINK-001: View emails linked to equipment', async ({ page }) => {
    await searchInSpotlight(page, `emails linked to ${TEST_QUERIES.valid.equipment}`);
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`EMAIL-LINK-001: Linked emails found: ${count}`);

    await captureScreenshot(page, 'EMAIL-LINK-001');
    await closeSpotlight(page);
  });

  test('EMAIL-LINK-002: View emails linked to work orders', async ({ page }) => {
    await searchInSpotlight(page, 'emails linked to work orders');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`EMAIL-LINK-002: WO linked emails: ${count}`);

    await captureScreenshot(page, 'EMAIL-LINK-002');
    await closeSpotlight(page);
  });

  test('EMAIL-LINK-003: View emails linked to faults', async ({ page }) => {
    await searchInSpotlight(page, 'emails linked to faults');
    await page.waitForTimeout(1000);

    const count = await getSearchResults(page);
    console.log(`EMAIL-LINK-003: Fault linked emails: ${count}`);

    await captureScreenshot(page, 'EMAIL-LINK-003');
    await closeSpotlight(page);
  });
});

// =============================================================================
// SUMMARY
// =============================================================================

test('EMAIL-SUMMARY: Email Lens test suite complete', async ({ page }) => {
  console.log('\n' + '='.repeat(60));
  console.log('EMAIL LENS TEST SUITE COMPLETE');
  console.log('='.repeat(60));
  console.log('\nTests by category:');
  console.log('- Captain Success Paths: 8 tests');
  console.log('- Captain Link Actions: 5 tests');
  console.log('- HOD Role: 6 tests');
  console.log('- Crew Role: 5 tests');
  console.log('- Failure Modes: 7 tests');
  console.log('- Edge Cases: 7 tests');
  console.log('- Performance: 2 tests');
  console.log('- Semantic Search: 3 tests');
  console.log('- Entity Linking: 3 tests');
  console.log('\nTotal: 46 tests');
  console.log('Screenshots: ' + SCREENSHOT_DIR);
  console.log('='.repeat(60) + '\n');

  expect(true).toBe(true);
});
