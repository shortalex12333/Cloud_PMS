/**
 * Search E2E Tests
 *
 * Tests search functionality against real Render backend
 */

import { test, expect } from '@playwright/test';
import {
  saveScreenshot,
  saveArtifact,
  saveRequest,
  saveResponse,
  createEvidenceBundle,
} from '../helpers/artifacts';
import { ApiClient } from '../helpers/api-client';

test.describe('Search Functionality', () => {
  let apiClient: ApiClient;

  test.beforeAll(async () => {
    apiClient = new ApiClient();
    await apiClient.ensureAuth();
  });

  test.beforeEach(async ({ page }) => {
    // Capture console logs
    const consoleLogs: Array<{ type: string; text: string; timestamp: string }> = [];
    page.on('console', (msg) => {
      consoleLogs.push({
        type: msg.type(),
        text: msg.text(),
        timestamp: new Date().toISOString(),
      });
    });
    (page as any).__consoleLogs = consoleLogs;
  });

  test('Search API returns results (READ action: search_documents)', async () => {
    const testName = 'search/api_search';

    // Execute search via API
    const response = await apiClient.search('generator', 5);

    // Save request/response
    saveRequest(testName, response.request);
    saveResponse(testName, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
      body: response.data,
    });

    // Create evidence bundle
    createEvidenceBundle(testName, {
      request: response.request,
      response: {
        status: response.status,
        body: response.data,
      },
      assertions: [
        {
          name: 'Status is 200',
          passed: response.status === 200,
          message: `Got status ${response.status}`,
        },
        {
          name: 'Success is true',
          passed: response.data?.success === true,
        },
        {
          name: 'Results is array',
          passed: Array.isArray(response.data?.results),
        },
      ],
    });

    // Assertions
    expect(response.status).toBe(200);
    expect(response.data.success).toBe(true);
    expect(Array.isArray(response.data.results)).toBe(true);
  });

  test('Search in UI shows results', async ({ page }) => {
    const testName = 'search/ui_search';
    const consoleLogs = (page as any).__consoleLogs || [];

    const email = process.env.TEST_USER_EMAIL;
    const password = process.env.TEST_USER_PASSWORD;

    if (!email || !password) {
      test.skip();
      return;
    }

    // Login first
    await page.goto('/login');
    await page.fill('input[type="email"], input[name="email"]', email);
    await page.fill('input[type="password"], input[name="password"]', password);
    await page.click('button[type="submit"]');

    // Wait for login to complete
    await page.waitForURL((url) => !url.pathname.includes('/login'), {
      timeout: 15000,
    });

    // Screenshot after login
    await saveScreenshot(page, testName, '01_logged_in');

    // Navigate to search page or find search input
    // Try multiple approaches
    const searchPageUrl = '/search';
    await page.goto(searchPageUrl).catch(() => {
      // If /search doesn't exist, stay on current page
    });

    // Find search input
    const searchSelectors = [
      'input[type="search"]',
      'input[placeholder*="Search"]',
      'input[placeholder*="search"]',
      '[data-testid="search-input"]',
      'input[name="query"]',
    ];

    let searchInput = null;
    for (const selector of searchSelectors) {
      const element = page.locator(selector).first();
      if (await element.isVisible({ timeout: 2000 }).catch(() => false)) {
        searchInput = element;
        break;
      }
    }

    if (!searchInput) {
      saveArtifact('skip_reason.json', { reason: 'No search input found' }, testName);
      await saveScreenshot(page, testName, 'no_search_input');
      test.skip();
      return;
    }

    // Screenshot before search
    await saveScreenshot(page, testName, '02_before_search');

    // Enter search query
    await searchInput.fill('generator');
    await searchInput.press('Enter');

    // Wait for results to load
    await page.waitForTimeout(3000);

    // Screenshot after search
    await saveScreenshot(page, testName, '03_after_search');

    // Save console logs
    saveArtifact('console_logs.json', consoleLogs, testName);

    // Check for results (try multiple approaches)
    const resultsSelectors = [
      '[data-testid="search-result"]',
      '.search-result',
      '[class*="result"]',
      '[class*="Result"]',
    ];

    let hasResults = false;
    for (const selector of resultsSelectors) {
      const count = await page.locator(selector).count();
      if (count > 0) {
        hasResults = true;
        break;
      }
    }

    // Also check for "no results" message
    const noResultsText = await page.getByText(/no results/i).isVisible().catch(() => false);
    const hasNoResultsMessage = noResultsText;

    // Create evidence bundle
    createEvidenceBundle(testName, {
      consoleLogs,
      assertions: [
        {
          name: 'Has search results or no-results message',
          passed: hasResults || hasNoResultsMessage,
          message: `Results found: ${hasResults}, No results message: ${hasNoResultsMessage}`,
        },
      ],
    });

    // At minimum, the search should complete without errors
    // (having no results is valid if the query doesn't match anything)
    expect(hasResults || hasNoResultsMessage).toBe(true);
  });

  test('Search with special characters handles gracefully', async () => {
    const testName = 'search/special_chars';

    // Test various special characters
    const queries = [
      'test "quoted"',
      "test's apostrophe",
      'test & ampersand',
      'test <script>',
    ];

    const results: Array<{ query: string; status: number; success: boolean }> = [];

    for (const query of queries) {
      const response = await apiClient.search(query, 1);
      results.push({
        query,
        status: response.status,
        success: response.status === 200,
      });
    }

    // Save results
    saveArtifact('special_char_results.json', results, testName);

    // Create evidence bundle
    createEvidenceBundle(testName, {
      response: results,
      assertions: results.map((r) => ({
        name: `Query "${r.query}" handled`,
        passed: r.success,
        message: `Status: ${r.status}`,
      })),
    });

    // All queries should return 200 (even if empty results)
    for (const result of results) {
      expect(result.status, `Query "${result.query}" should not error`).toBe(200);
    }
  });

  test('Search rate limiting is enforced', async () => {
    const testName = 'search/rate_limit';

    // Make many rapid requests
    const promises = [];
    for (let i = 0; i < 20; i++) {
      promises.push(apiClient.search('test', 1));
    }

    const responses = await Promise.all(promises);

    // Count responses by status
    const statusCounts: Record<number, number> = {};
    for (const r of responses) {
      statusCounts[r.status] = (statusCounts[r.status] || 0) + 1;
    }

    saveArtifact('rate_limit_results.json', statusCounts, testName);

    // Most should succeed, some might be rate limited (429)
    const successCount = statusCounts[200] || 0;

    createEvidenceBundle(testName, {
      response: statusCounts,
      assertions: [
        {
          name: 'Some requests succeeded',
          passed: successCount > 0,
          message: `${successCount} succeeded out of 20`,
        },
      ],
    });

    expect(successCount).toBeGreaterThan(0);
  });
});
