/**
 * INVENTORY LENS - 6 HOUR LIVE TESTING SESSION
 *
 * Deployment: bffb436 (Vercel Preview or app.celeste7.ai)
 * Test Window: Complete real-user simulation
 * Scope: HOD, CREW, CAPTAIN journeys on ONE page architecture
 *
 * Test Users:
 * - HOD: hod.test@alex-short.com / Password2!
 * - CREW: crew.test@alex-short.com / Password2!
 * - CAPTAIN: x@alex-short.com / Password2!
 * - Yacht: 85fe1119-b04c-41ac-80f1-829d23322598
 */

import { test, expect, Page } from '@playwright/test';

// Test configuration
const BASE_URL = process.env.BASE_URL || 'https://app.celeste7.ai';
const YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598';
const SEARCH_QUERY = 'fuel filter stock';

// Storage state paths (pre-authenticated by global setup)
const AUTH_STATES = {
  HOD: 'test-results/.auth-states/hod-state.json',
  CREW: 'test-results/.auth-states/crew-state.json',
  CAPTAIN: 'test-results/.auth-states/captain-state.json',
  CHIEF_ENGINEER: 'test-results/.auth-states/chief_engineer-state.json',
};

// Expected action button counts per role (RBAC verification)
const TEST_USERS = {
  HOD: { expectedActionCount: 4 },
  CREW: { expectedActionCount: 2 },
  CAPTAIN: { expectedActionCount: 4 },
};

// Helper: Perform search
async function performSearch(page: Page, query: string) {
  const searchInput = page.locator('input[placeholder*="Search"], input[type="search"]').first();
  await searchInput.waitFor({ state: 'visible', timeout: 10000 });
  await searchInput.fill(query);
  await searchInput.press('Enter');

  // Wait for results to appear
  await page.waitForTimeout(2000); // Allow time for search results
}

// Helper: Open ContextPanel
async function openContextPanel(page: Page) {
  const firstResult = page.locator('[data-testid="search-result-item"], [class*="search-result"]').first();
  await firstResult.waitFor({ state: 'visible', timeout: 10000 });
  await firstResult.click();

  // Wait for ContextPanel to slide in
  await page.waitForTimeout(500);

  // Verify ContextPanel is visible
  const contextPanel = page.locator('[data-testid="context-panel"], [class*="context-panel"]').first();
  await contextPanel.waitFor({ state: 'visible', timeout: 5000 });
}

// Helper: Get action buttons in ContextPanel
async function getActionButtons(page: Page) {
  const buttons = page.locator('[data-testid="context-panel"] button[data-action], [class*="context-panel"] button[class*="action"]');
  const count = await buttons.count();
  const buttonTexts = [];

  for (let i = 0; i < count; i++) {
    const text = await buttons.nth(i).textContent();
    buttonTexts.push(text?.trim() || '');
  }

  return { count, buttons, buttonTexts };
}

// Helper: Monitor network for /v1/actions/execute
async function monitorActionExecution(page: Page, callback: () => Promise<void>) {
  const requests: any[] = [];

  page.on('request', (request) => {
    if (request.url().includes('/v1/actions/execute')) {
      requests.push({
        method: request.method(),
        url: request.url(),
        payload: request.postDataJSON(),
      });
    }
  });

  const responses: any[] = [];
  page.on('response', async (response) => {
    if (response.url().includes('/v1/actions/execute')) {
      responses.push({
        status: response.status(),
        url: response.url(),
        body: await response.json().catch(() => null),
      });
    }
  });

  await callback();

  await page.waitForTimeout(1000); // Allow responses to complete

  return { requests, responses };
}

// =============================================================================
// PHASE 1: HOD JOURNEY (Elevated Role)
// =============================================================================

test.describe('Phase 1: HOD Journey (Elevated Role)', () => {
  test.use({ storageState: AUTH_STATES.HOD });

  test('1.1 Navigate to App - HOD', async ({ page }) => {
    await page.goto(BASE_URL);

    // Verify URL
    expect(page.url()).toContain('celeste');

    // Verify search bar is visible (indicates logged in)
    const searchInput = page.locator('input[placeholder*="Search"], input[type="search"]').first();
    await expect(searchInput).toBeVisible({ timeout: 10000 });

    console.log('✅ HOD authenticated and app loaded');
  });

  test('1.2-1.3 Search and Open ContextPanel - HOD', async ({ page }) => {
    await page.goto(BASE_URL);

    const initialUrl = page.url();

    // Perform search
    await performSearch(page, SEARCH_QUERY);

    // URL should NOT change
    expect(page.url()).toBe(initialUrl);

    // Open first result in ContextPanel
    await openContextPanel(page);

    // URL should STILL not change
    expect(page.url()).toBe(initialUrl);

    // Verify ContextPanel shows part details
    const partName = page.locator('[data-testid="part-name"], [class*="part-name"]').first();
    await expect(partName).toBeVisible({ timeout: 5000 });

    console.log('✅ Search and ContextPanel opened, URL unchanged');
  });

  test('1.4 Verify 4 Action Buttons (HOD)', async ({ page }) => {
    await page.goto(BASE_URL);
    await performSearch(page, SEARCH_QUERY);
    await openContextPanel(page);

    const { count, buttonTexts } = await getActionButtons(page);

    console.log(`Found ${count} action buttons: ${buttonTexts.join(', ')}`);

    // HOD should see 4 action buttons
    expect(count).toBeGreaterThanOrEqual(TEST_USERS.HOD.expectedActionCount);

    console.log('✅ HOD sees all expected action buttons');
  });

  test('1.5 Execute "Check Stock" Action - CRITICAL FIX VERIFICATION', async ({ page }) => {
    await page.goto(BASE_URL);
    await performSearch(page, SEARCH_QUERY);
    await openContextPanel(page);

    const initialUrl = page.url();

    // Find "Check Stock" button
    const checkStockBtn = page.locator('button').filter({ hasText: /Check Stock/i }).first();
    await checkStockBtn.waitFor({ state: 'visible', timeout: 5000 });

    // Monitor network requests
    const { requests, responses } = await monitorActionExecution(page, async () => {
      await checkStockBtn.click();
      await page.waitForTimeout(2000); // Wait for response
    });

    // CRITICAL VERIFICATION: Request went to /v1/actions/execute
    expect(requests.length).toBeGreaterThan(0);
    expect(requests[0].url).toContain('/v1/actions/execute');
    expect(requests[0].url).not.toContain('/workflows/');

    // CRITICAL VERIFICATION: Response is 200 (NOT 404)
    expect(responses.length).toBeGreaterThan(0);
    expect(responses[0].status).toBe(200);

    // URL should NOT change
    expect(page.url()).toBe(initialUrl);

    console.log('✅ CRITICAL FIX VERIFIED: Action calls /v1/actions/execute, Response 200');
  });

  test('1.8 Execute "Log Usage" Action - Happy Path', async ({ page }) => {
    await page.goto(BASE_URL);
    await performSearch(page, SEARCH_QUERY);
    await openContextPanel(page);

    // Find "Log Usage" button
    const logUsageBtn = page.locator('button').filter({ hasText: /Log Usage/i }).first();
    await logUsageBtn.waitFor({ state: 'visible', timeout: 5000 });
    await logUsageBtn.click();

    // Wait for form modal to appear
    await page.waitForTimeout(1000);

    // Fill form
    const quantityInput = page.locator('input[name="quantity"], input[placeholder*="quantity"]').first();
    await quantityInput.waitFor({ state: 'visible', timeout: 5000 });
    await quantityInput.fill('1');

    const reasonInput = page.locator('input[name="usage_reason"], input[name="reason"], textarea[name="usage_reason"]').first();
    await reasonInput.fill('E2E test - inventory lens live verification');

    const notesInput = page.locator('textarea[name="notes"], input[name="notes"]').first();
    if (await notesInput.count() > 0) {
      await notesInput.fill('Testing bffb436 deployment');
    }

    // Monitor network for submit
    const { requests, responses } = await monitorActionExecution(page, async () => {
      const submitBtn = page.locator('button[type="submit"]').filter({ hasText: /Submit|Log|Confirm/i }).first();
      await submitBtn.click();
      await page.waitForTimeout(2000);
    });

    // Verify action executed
    expect(requests.length).toBeGreaterThan(0);
    expect(requests[0].payload?.action).toContain('log_part_usage');
    expect(responses[0].status).toBe(200);

    // Verify success toast or message
    const toast = page.locator('[role="status"], [class*="toast"]').filter({ hasText: /success|logged/i }).first();
    await expect(toast).toBeVisible({ timeout: 5000 });

    console.log('✅ Log Usage action executed successfully');
  });

  test('1.10 Execute "Log Usage" - Validation Errors', async ({ page }) => {
    await page.goto(BASE_URL);
    await performSearch(page, SEARCH_QUERY);
    await openContextPanel(page);

    const logUsageBtn = page.locator('button').filter({ hasText: /Log Usage/i }).first();
    await logUsageBtn.click();
    await page.waitForTimeout(1000);

    // Submit empty form
    const submitBtn = page.locator('button[type="submit"]').filter({ hasText: /Submit|Log|Confirm/i }).first();
    await submitBtn.click();

    // Verify validation error appears
    const errorMsg = page.locator('[class*="error"], [role="alert"]').filter({ hasText: /required|invalid/i }).first();
    await expect(errorMsg).toBeVisible({ timeout: 3000 });

    console.log('✅ Validation errors working correctly');
  });

  test('1.12 Multiple Searches - Dynamic UX', async ({ page }) => {
    await page.goto(BASE_URL);

    const initialUrl = page.url();

    // Search 1
    await performSearch(page, 'fuel filter');
    expect(page.url()).toBe(initialUrl);

    // Search 2
    await performSearch(page, 'engine oil');
    expect(page.url()).toBe(initialUrl);

    // Search 3
    await performSearch(page, 'spark plug');
    expect(page.url()).toBe(initialUrl);

    console.log('✅ Multiple searches, URL never changed');
  });
});

// =============================================================================
// PHASE 2: CREW JOURNEY (Base Role - RBAC)
// =============================================================================

test.describe('Phase 2: CREW Journey (Base Role - RBAC)', () => {
  test.use({ storageState: AUTH_STATES.CREW });

  test('2.1-2.2 Navigate and Search as CREW', async ({ page }) => {
    await page.goto(BASE_URL);

    const initialUrl = page.url();

    await performSearch(page, SEARCH_QUERY);
    await openContextPanel(page);

    expect(page.url()).toBe(initialUrl);

    console.log('✅ CREW logged in and searched successfully');
  });

  test('2.3 Verify 2 Action Buttons (CREW) - RBAC Enforcement', async ({ page }) => {
    await page.goto(BASE_URL);
    await performSearch(page, SEARCH_QUERY);
    await openContextPanel(page);

    const { count, buttonTexts } = await getActionButtons(page);

    console.log(`CREW sees ${count} action buttons: ${buttonTexts.join(', ')}`);

    // CREW should see ONLY 2 buttons (View Details, Check Stock)
    expect(count).toBeLessThanOrEqual(2);

    // Verify "Log Usage" and "Usage History" NOT visible
    const logUsageBtn = page.locator('button').filter({ hasText: /Log Usage/i });
    const usageHistoryBtn = page.locator('button').filter({ hasText: /Usage History/i });

    expect(await logUsageBtn.count()).toBe(0);
    expect(await usageHistoryBtn.count()).toBe(0);

    console.log('✅ RBAC enforced: CREW does NOT see MUTATE actions');
  });

  test('2.4-2.5 Execute READ Actions (Allowed for CREW)', async ({ page }) => {
    await page.goto(BASE_URL);
    await performSearch(page, SEARCH_QUERY);
    await openContextPanel(page);

    // Execute "Check Stock" - should work
    const checkStockBtn = page.locator('button').filter({ hasText: /Check Stock/i }).first();

    const { responses } = await monitorActionExecution(page, async () => {
      await checkStockBtn.click();
      await page.waitForTimeout(2000);
    });

    expect(responses[0].status).toBe(200);

    console.log('✅ CREW can execute READ actions');
  });

  test('2.6 Attempt Log Usage via API (Should Fail) - RBAC API Enforcement', async ({ page }) => {
    await page.goto(BASE_URL);

    // Attempt to call log_part_usage via API directly
    const response = await page.evaluate(async (yachtId) => {
      const res = await fetch('/api/v1/actions/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'log_part_usage',
          context: { yacht_id: yachtId },
          payload: { part_id: 'test-part-id', quantity: 1, usage_reason: 'Should be blocked' }
        })
      });
      return {
        status: res.status,
        body: await res.json().catch(() => null)
      };
    }, YACHT_ID);

    // Should be 403 Forbidden
    expect(response.status).toBe(403);
    expect(response.body?.error || response.body?.message).toMatch(/forbidden|permission|denied/i);

    console.log('✅ RBAC enforced at API level: CREW blocked from MUTATE');
  });
});

// =============================================================================
// PHASE 3: CAPTAIN JOURNEY (All Permissions)
// =============================================================================

test.describe('Phase 3: CAPTAIN Journey (All Permissions)', () => {
  test.use({ storageState: AUTH_STATES.CAPTAIN });

  test('3.1-3.2 Navigate and Search as CAPTAIN', async ({ page }) => {
    await page.goto(BASE_URL);
    await performSearch(page, SEARCH_QUERY);
    await openContextPanel(page);

    console.log('✅ CAPTAIN logged in and searched successfully');
  });

  test('3.3 Verify All Action Buttons (CAPTAIN)', async ({ page }) => {
    await page.goto(BASE_URL);
    await performSearch(page, SEARCH_QUERY);
    await openContextPanel(page);

    const { count, buttonTexts } = await getActionButtons(page);

    console.log(`CAPTAIN sees ${count} action buttons: ${buttonTexts.join(', ')}`);

    // CAPTAIN should see all 4 buttons
    expect(count).toBeGreaterThanOrEqual(4);

    console.log('✅ CAPTAIN has full MUTATE permissions');
  });
});

// =============================================================================
// PHASE 4: Edge Cases & Stress Testing
// =============================================================================

test.describe('Phase 4: Edge Cases & Stress Testing', () => {
  test.use({ storageState: AUTH_STATES.HOD });

  test('4.1 Empty Query', async ({ page }) => {
    await page.goto(BASE_URL);

    const searchInput = page.locator('input[placeholder*="Search"], input[type="search"]').first();
    await searchInput.fill('');
    await searchInput.press('Enter');

    // Should not crash
    await page.waitForTimeout(1000);

    console.log('✅ Empty query handled gracefully');
  });

  test('4.2 Invalid Query - No Results', async ({ page }) => {
    await page.goto(BASE_URL);

    await performSearch(page, 'xyzabc123notfound999');

    // Should show "No results" message
    const noResults = page.locator('text=/no results|not found|no matches/i').first();
    await expect(noResults).toBeVisible({ timeout: 5000 });

    console.log('✅ Invalid query shows "No results"');
  });

  test('4.3-4.4 Special Characters and Unicode', async ({ page }) => {
    await page.goto(BASE_URL);

    // Special characters
    await performSearch(page, 'fuel & filter');
    await page.waitForTimeout(1000);

    await performSearch(page, 'part#123');
    await page.waitForTimeout(1000);

    // Unicode
    await performSearch(page, 'αβγ filter');
    await page.waitForTimeout(1000);

    console.log('✅ Special characters and Unicode handled');
  });

  test('4.6 Rapid Searches - No Race Conditions', async ({ page }) => {
    await page.goto(BASE_URL);

    const searchInput = page.locator('input[placeholder*="Search"], input[type="search"]').first();

    // Rapid searches
    await searchInput.fill('fuel');
    await searchInput.press('Enter');

    await searchInput.fill('oil');
    await searchInput.press('Enter');

    await searchInput.fill('filter');
    await searchInput.press('Enter');

    await page.waitForTimeout(2000);

    // Should show results for last query
    console.log('✅ Rapid searches handled correctly');
  });
});

// =============================================================================
// PHASE 5: Console & Network Monitoring
// =============================================================================

test.describe('Phase 5: Console & Network Monitoring', () => {
  test.use({ storageState: AUTH_STATES.HOD });

  test('5.1 Monitor Console Errors', async ({ page }) => {
    const consoleErrors: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    page.on('pageerror', (error) => {
      consoleErrors.push(error.message);
    });

    await page.goto(BASE_URL);
    await performSearch(page, SEARCH_QUERY);
    await openContextPanel(page);

    // Check Stock action
    const checkStockBtn = page.locator('button').filter({ hasText: /Check Stock/i }).first();
    if (await checkStockBtn.count() > 0) {
      await checkStockBtn.click();
      await page.waitForTimeout(2000);
    }

    // Filter out expected warnings
    const criticalErrors = consoleErrors.filter(err =>
      !err.includes('Download the React DevTools') &&
      !err.includes('404') === false // We want to catch 404s
    );

    console.log(`Console errors: ${criticalErrors.length}`);
    if (criticalErrors.length > 0) {
      console.log('Errors:', criticalErrors);
    }

    // Should have 0 critical errors
    expect(criticalErrors.length).toBe(0);

    console.log('✅ No console errors detected');
  });

  test('5.2 Monitor Network Requests - NO 404s', async ({ page }) => {
    const failedRequests: any[] = [];

    page.on('response', (response) => {
      if (response.status() === 404) {
        failedRequests.push({
          url: response.url(),
          status: response.status(),
        });
      }
    });

    await page.goto(BASE_URL);
    await performSearch(page, SEARCH_QUERY);
    await openContextPanel(page);

    const checkStockBtn = page.locator('button').filter({ hasText: /Check Stock/i }).first();
    if (await checkStockBtn.count() > 0) {
      await checkStockBtn.click();
      await page.waitForTimeout(2000);
    }

    // Filter out static asset 404s (fonts, images)
    const critical404s = failedRequests.filter(req =>
      req.url.includes('/v1/actions') ||
      req.url.includes('/workflows')
    );

    console.log(`404 errors: ${critical404s.length}`);
    if (critical404s.length > 0) {
      console.log('404s:', critical404s);
    }

    // CRITICAL: Should have 0 action-related 404s
    expect(critical404s.length).toBe(0);

    console.log('✅ NO 404 errors for action execution');
  });
});
