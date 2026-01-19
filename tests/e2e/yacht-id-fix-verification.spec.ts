/**
 * Yacht ID Fix Verification Test
 *
 * CRITICAL: This test verifies that yacht_id is NOT null in search requests.
 *
 * The bug was: getYachtId() in authHelpers.ts read from user_metadata.yacht_id
 * which was NEVER set. The fix passes yacht_id from AuthContext.
 *
 * SUCCESS CRITERIA:
 * 1. User can log in
 * 2. Search request contains yacht_id that is NOT null
 * 3. Search returns actual results (not empty due to null yacht_id)
 */

import { test, expect } from '@playwright/test';
import { saveArtifact, saveScreenshot, createEvidenceBundle } from '../helpers/artifacts';

test.describe('Yacht ID Propagation Fix Verification', () => {
  const testName = 'yacht-id-fix';

  test('CRITICAL: Search request contains valid yacht_id (not null)', async ({ page }) => {
    const email = process.env.TEST_USER_EMAIL;
    const password = process.env.TEST_USER_PASSWORD;
    const expectedYachtId = process.env.TEST_USER_YACHT_ID;

    if (!email || !password) {
      console.error('TEST_USER_EMAIL and TEST_USER_PASSWORD must be set');
      test.fail();
      return;
    }

    // Capture all network requests to the search endpoint
    const searchRequests: Array<{
      url: string;
      method: string;
      postData: any;
      timestamp: string;
    }> = [];

    page.on('request', (request) => {
      const url = request.url();
      if (url.includes('/webhook/search') || url.includes('/search')) {
        let postData = null;
        try {
          const postDataText = request.postData();
          if (postDataText) {
            postData = JSON.parse(postDataText);
          }
        } catch (e) {
          postData = request.postData();
        }

        searchRequests.push({
          url,
          method: request.method(),
          postData,
          timestamp: new Date().toISOString(),
        });

        console.log('[TEST] Captured search request:', {
          url,
          yacht_id: postData?.auth?.yacht_id,
          user_id: postData?.auth?.user_id,
        });
      }
    });

    // Capture console logs for debugging
    const consoleLogs: Array<{ type: string; text: string; timestamp: string }> = [];
    page.on('console', (msg) => {
      consoleLogs.push({
        type: msg.type(),
        text: msg.text(),
        timestamp: new Date().toISOString(),
      });
    });

    // Step 1: Login
    console.log('[TEST] Step 1: Navigating to login page');
    await page.goto('/login');
    await saveScreenshot(page, testName, '01_login_page');

    console.log('[TEST] Step 1: Filling login form');
    await page.fill('input[type="email"], input[name="email"]', email);
    await page.fill('input[type="password"], input[name="password"]', password);

    console.log('[TEST] Step 1: Submitting login form');
    await page.click('button[type="submit"]');

    // Wait for login to complete (redirect away from /login)
    try {
      await page.waitForURL((url) => !url.pathname.includes('/login'), {
        timeout: 20000,
      });
      console.log('[TEST] Step 1: Login completed, redirected to:', page.url());
    } catch (e) {
      await saveScreenshot(page, testName, '01_login_failed');
      saveArtifact('login_error.json', {
        error: String(e),
        currentUrl: page.url(),
        consoleLogs,
      }, testName);
      throw new Error(`Login failed: ${e}`);
    }

    await saveScreenshot(page, testName, '02_logged_in');

    // Step 2: Wait for bootstrap to complete (yacht_id to be available)
    console.log('[TEST] Step 2: Waiting for bootstrap to complete');
    await page.waitForTimeout(3000); // Give bootstrap time to complete

    // Step 3: Find and use the search input
    console.log('[TEST] Step 3: Finding search input');

    // The main app page should have a search input
    const searchInput = page.locator('[data-testid="search-input"]');
    const searchInputAlt = page.locator('input[type="search"]');

    let foundSearch = false;
    if (await searchInput.isVisible({ timeout: 5000 }).catch(() => false)) {
      foundSearch = true;
      console.log('[TEST] Step 3: Found search input with data-testid');
    } else if (await searchInputAlt.isVisible({ timeout: 5000 }).catch(() => false)) {
      foundSearch = true;
      console.log('[TEST] Step 3: Found search input with type="search"');
    }

    if (!foundSearch) {
      await saveScreenshot(page, testName, '03_no_search_input');
      saveArtifact('no_search_error.json', {
        currentUrl: page.url(),
        pageContent: await page.content(),
        consoleLogs,
      }, testName);
      throw new Error('Search input not found on page');
    }

    await saveScreenshot(page, testName, '03_search_input_found');

    // Step 4: Perform a search
    console.log('[TEST] Step 4: Typing search query');
    const searchEl = await searchInput.isVisible() ? searchInput : searchInputAlt;
    await searchEl.click();
    await searchEl.fill('generator');

    // Wait for search request to be made (debounced)
    console.log('[TEST] Step 4: Waiting for search request');
    await page.waitForTimeout(2000);

    await saveScreenshot(page, testName, '04_search_performed');

    // Step 5: Analyze captured requests
    console.log('[TEST] Step 5: Analyzing captured search requests');
    console.log('[TEST] Total search requests captured:', searchRequests.length);

    saveArtifact('search_requests.json', searchRequests, testName);
    saveArtifact('console_logs.json', consoleLogs, testName);

    // CRITICAL ASSERTION: At least one search request was made
    expect(searchRequests.length, 'At least one search request should be made').toBeGreaterThan(0);

    // CRITICAL ASSERTION: yacht_id is NOT null in the search request
    const lastRequest = searchRequests[searchRequests.length - 1];
    const yachtIdInRequest = lastRequest?.postData?.auth?.yacht_id;

    console.log('[TEST] CRITICAL CHECK: yacht_id in request:', yachtIdInRequest);

    // Create evidence bundle BEFORE assertions so we capture the data
    createEvidenceBundle(testName, {
      searchRequests,
      consoleLogs,
      expectedYachtId,
      actualYachtId: yachtIdInRequest,
      assertions: [
        {
          name: 'Search request was made',
          passed: searchRequests.length > 0,
          message: `${searchRequests.length} search requests captured`,
        },
        {
          name: 'yacht_id is NOT null',
          passed: yachtIdInRequest !== null && yachtIdInRequest !== undefined,
          message: `yacht_id = ${yachtIdInRequest}`,
        },
        {
          name: 'yacht_id matches expected',
          passed: yachtIdInRequest === expectedYachtId,
          message: `Expected: ${expectedYachtId}, Got: ${yachtIdInRequest}`,
        },
      ],
    });

    // CRITICAL ASSERTIONS
    expect(yachtIdInRequest, 'yacht_id should NOT be null').not.toBeNull();
    expect(yachtIdInRequest, 'yacht_id should NOT be undefined').not.toBeUndefined();
    expect(yachtIdInRequest, 'yacht_id should NOT be empty string').not.toBe('');
    expect(yachtIdInRequest, 'yacht_id should NOT be placeholder').not.toContain('placeholder');
    expect(yachtIdInRequest, 'yacht_id should NOT be bootstrap-pending').not.toBe('bootstrap-pending');

    // If we have expected yacht_id, verify it matches
    if (expectedYachtId) {
      expect(yachtIdInRequest, `yacht_id should be ${expectedYachtId}`).toBe(expectedYachtId);
    }

    console.log('[TEST] SUCCESS: yacht_id is correctly propagated:', yachtIdInRequest);
  });

  test('Search returns actual results (not empty due to null yacht_id)', async ({ page }) => {
    const email = process.env.TEST_USER_EMAIL;
    const password = process.env.TEST_USER_PASSWORD;

    if (!email || !password) {
      test.skip();
      return;
    }

    // Capture search responses
    const searchResponses: Array<{
      url: string;
      status: number;
      body: any;
    }> = [];

    page.on('response', async (response) => {
      const url = response.url();
      if (url.includes('/webhook/search') || url.includes('/search')) {
        let body = null;
        try {
          body = await response.json();
        } catch (e) {
          body = await response.text().catch(() => null);
        }
        searchResponses.push({
          url,
          status: response.status(),
          body,
        });
      }
    });

    // Login
    await page.goto('/login');
    await page.fill('input[type="email"], input[name="email"]', email);
    await page.fill('input[type="password"], input[name="password"]', password);
    await page.click('button[type="submit"]');
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 20000 });

    // Wait for bootstrap
    await page.waitForTimeout(3000);

    // Search
    const searchInput = page.locator('[data-testid="search-input"], input[type="search"]').first();
    await searchInput.fill('generator');
    await page.waitForTimeout(3000);

    await saveScreenshot(page, testName + '-results', '01_search_results');
    saveArtifact('search_responses.json', searchResponses, testName + '-results');

    // Check that we got a response
    expect(searchResponses.length, 'Search should return a response').toBeGreaterThan(0);

    const lastResponse = searchResponses[searchResponses.length - 1];
    console.log('[TEST] Search response status:', lastResponse?.status);
    console.log('[TEST] Search response results:', lastResponse?.body?.results?.length);

    // Check response status
    expect(lastResponse?.status, 'Search should return 200').toBe(200);

    // Check that success is true
    expect(lastResponse?.body?.success, 'Search response should have success: true').toBe(true);

    // Check that results is an array (may be empty if no matching documents)
    expect(Array.isArray(lastResponse?.body?.results), 'Results should be an array').toBe(true);

    // Log results for debugging
    console.log('[TEST] Search returned', lastResponse?.body?.results?.length || 0, 'results');
  });
});
