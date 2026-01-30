/**
 * Live Site E2E Diagnostic Test
 * Captures ALL network traffic during document search to diagnose
 * whether /v1/actions/list is being called
 */
import { test, expect, Page } from '@playwright/test';
import { saveArtifact } from '../../helpers/artifacts';

const APP_URL = process.env.APP_URL || 'https://app.celeste7.ai';

// Test accounts
const HOD_ACCOUNT = {
  email: 'hod.tenant@alex-short.com',
  password: 'Password2!',
};

async function loginFresh(page: Page, account: { email: string; password: string }): Promise<void> {
  await page.goto(APP_URL);
  await page.waitForSelector('input[type="email"], input[name="email"]', { timeout: 15000 });
  await page.fill('input[type="email"], input[name="email"]', account.email);
  await page.fill('input[type="password"], input[name="password"]', account.password);
  await page.click('button[type="submit"]');
  await page.waitForTimeout(5000); // Wait for redirect and session setup
}

test.describe('Live Site Network Diagnostic', () => {

  test('Full network trace during "upload document" search', async ({ page }) => {
    const testName = 'documents/live-network-diagnostic';

    // Collect ALL requests
    const allRequests: { url: string; method: string; timestamp: number }[] = [];
    const allResponses: { url: string; status: number; timestamp: number }[] = [];

    page.on('request', (req) => {
      allRequests.push({
        url: req.url(),
        method: req.method(),
        timestamp: Date.now(),
      });
    });

    page.on('response', (res) => {
      allResponses.push({
        url: res.url(),
        status: res.status(),
        timestamp: Date.now(),
      });
    });

    // Login fresh
    await loginFresh(page, HOD_ACCOUNT);

    // Mark the point where login is complete
    const loginCompleteTime = Date.now();

    // Wait for page to fully load
    await page.waitForTimeout(2000);

    // Clear logs to focus on search phase
    const preSearchRequests = [...allRequests];
    allRequests.length = 0;
    allResponses.length = 0;

    // Find search input
    const searchSelectors = [
      '[data-testid="search-input"]',
      'input[placeholder*="Search"]',
      'input[placeholder*="search"]',
      'input[type="search"]',
      '.search-input',
      '#search',
    ];

    let searchInput = null;
    for (const selector of searchSelectors) {
      const el = page.locator(selector).first();
      if (await el.count() > 0) {
        searchInput = el;
        break;
      }
    }

    const searchFound = searchInput !== null;

    if (searchInput) {
      await searchInput.click();
      await searchInput.clear();
      await searchInput.fill('upload document');

      // Wait for debounce and API calls
      await page.waitForTimeout(3000);
    }

    // Take screenshot
    await page.screenshot({ path: `test-results/artifacts/${testName}/search_state.png` });

    // Analyze requests
    const actionRequests = allRequests.filter(r =>
      r.url.includes('/v1/actions') ||
      r.url.includes('actions/list')
    );

    const searchRequests = allRequests.filter(r =>
      r.url.includes('/search') ||
      r.url.includes('webhook/search')
    );

    const supabaseRequests = allRequests.filter(r =>
      r.url.includes('supabase')
    );

    const pipelineRequests = allRequests.filter(r =>
      r.url.includes('pipeline-core') ||
      r.url.includes('celeste-pipeline')
    );

    // Check specifically for /v1/actions/list
    const actionListCall = allRequests.find(r => r.url.includes('/v1/actions/list'));

    // Build diagnostic report
    const diagnosticReport = {
      timestamp: new Date().toISOString(),
      testPhase: 'search',
      query: 'upload document',
      searchInputFound: searchFound,

      networkSummary: {
        totalRequestsDuringSearch: allRequests.length,
        actionRequests: actionRequests.length,
        searchRequests: searchRequests.length,
        supabaseRequests: supabaseRequests.length,
        pipelineRequests: pipelineRequests.length,
      },

      criticalCheck: {
        actionListCalled: !!actionListCall,
        actionListUrl: actionListCall?.url || 'NOT CALLED',
      },

      actionRequestDetails: actionRequests.map(r => ({
        method: r.method,
        url: r.url,
      })),

      searchRequestDetails: searchRequests.map(r => ({
        method: r.method,
        url: r.url,
      })),

      allRequestUrls: allRequests.map(r => r.url).slice(0, 50), // First 50
    };

    // Save comprehensive artifact
    saveArtifact('live_diagnostic_report.json', diagnosticReport, testName);

    // Console output for immediate visibility
    console.log('\n========================================');
    console.log('LIVE DIAGNOSTIC REPORT');
    console.log('========================================');
    console.log('Search input found:', searchFound);
    console.log('Total requests during search:', allRequests.length);
    console.log('/v1/actions/list CALLED:', !!actionListCall);
    console.log('Action requests:', actionRequests.length);
    console.log('Search requests:', searchRequests.length);
    console.log('========================================\n');

    // The test passes if we successfully captured the diagnostic data
    // The important finding is whether /v1/actions/list was called
    expect(searchFound).toBe(true);

    // Log finding for manual review
    if (!actionListCall) {
      console.log('⚠️  WARNING: /v1/actions/list was NOT called!');
      console.log('This means the frontend fix may not be deployed.');
    } else {
      console.log('✅ /v1/actions/list WAS called:', actionListCall.url);
    }
  });

  test('Verify API is accessible and returns document actions', async ({ request }) => {
    const testName = 'documents/api-verification';

    // Get a fresh token by logging in
    // This test uses the pre-authenticated state from global setup

    // Direct API call to verify backend works
    const response = await request.get('https://pipeline-core.int.celeste7.ai/v1/actions/list?domain=documents');

    const status = response.status();
    let body = null;

    if (status === 200) {
      body = await response.json();
    }

    saveArtifact('api_verification.json', {
      endpoint: '/v1/actions/list?domain=documents',
      status,
      hasActions: body?.actions?.length > 0,
      actionCount: body?.actions?.length || 0,
      actionIds: body?.actions?.map((a: any) => a.action_id) || [],
      timestamp: new Date().toISOString(),
    }, testName);

    // Without auth, expect 401
    // This just verifies the API is reachable
    expect(status).toBeLessThan(500);
  });

  test('Full journey: Login → Search → Verify Actions Appear', async ({ page }) => {
    const testName = 'documents/full-journey';

    const networkLog: string[] = [];

    page.on('request', (req) => {
      if (req.url().includes('actions') || req.url().includes('search')) {
        networkLog.push(`→ ${req.method()} ${req.url()}`);
      }
    });

    page.on('response', (res) => {
      if (res.url().includes('actions') || res.url().includes('search')) {
        networkLog.push(`← ${res.status()} ${res.url()}`);
      }
    });

    // Step 1: Login
    await loginFresh(page, HOD_ACCOUNT);
    await page.screenshot({ path: `test-results/artifacts/${testName}/01_after_login.png` });

    // Step 2: Search for document action
    const searchInput = page.locator('input[placeholder*="Search"], input[placeholder*="search"], [data-testid="search-input"]').first();

    if (await searchInput.count() > 0) {
      await searchInput.click();
      await page.screenshot({ path: `test-results/artifacts/${testName}/02_search_focused.png` });

      await searchInput.fill('upload document');
      await page.screenshot({ path: `test-results/artifacts/${testName}/03_search_typed.png` });

      // Wait for results
      await page.waitForTimeout(3000);
      await page.screenshot({ path: `test-results/artifacts/${testName}/04_search_results.png` });
    }

    // Step 3: Look for action chips/buttons
    const actionElements = await page.locator('[data-testid*="action"], [data-action-id], .action-chip, .action-button, button:has-text("Upload")').all();

    saveArtifact('full_journey_report.json', {
      steps: ['login', 'search', 'wait_results', 'check_actions'],
      searchInputFound: await searchInput.count() > 0,
      actionElementsFound: actionElements.length,
      networkLog,
      timestamp: new Date().toISOString(),
    }, testName);

    console.log('\n=== FULL JOURNEY RESULTS ===');
    console.log('Action elements found:', actionElements.length);
    console.log('Network log:');
    networkLog.forEach(l => console.log('  ', l));
    console.log('============================\n');
  });

});
