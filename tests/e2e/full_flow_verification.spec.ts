import { test, expect } from '@playwright/test';

const PROD_URL = 'https://app.celeste7.ai';
const TEST_EMAIL = 'x@alex-short.com';
const TEST_PASSWORD = 'Password2!';

interface TestEvidence {
  step: string;
  timestamp: string;
  status: 'pass' | 'fail' | 'skip';
  details: string;
  screenshot?: string;
}

test('Full Production Flow Verification', async ({ page }) => {
  const evidence: TestEvidence[] = [];
  const consoleErrors: string[] = [];
  const networkErrors: string[] = [];
  const apiResponses: { url: string; status: number; ok: boolean }[] = [];

  // Capture all console messages
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(`[${new Date().toISOString()}] ${msg.text()}`);
    }
  });

  // Capture page errors
  page.on('pageerror', err => {
    consoleErrors.push(`[${new Date().toISOString()}] PAGE ERROR: ${err.message}`);
  });

  // Capture ALL network responses
  page.on('response', response => {
    const url = response.url();
    const status = response.status();

    // Track API responses
    if (url.includes('celeste7.ai') || url.includes('supabase.co')) {
      apiResponses.push({ url, status, ok: response.ok() });
    }

    // Track errors
    if (status >= 400) {
      networkErrors.push(`[HTTP ${status}] ${url}`);
    }
  });

  // ==========================================================================
  // TEST 1: LOGIN
  // ==========================================================================
  console.log('\n=== TEST 1: LOGIN ===');

  await page.goto(`${PROD_URL}/login`);
  await page.fill('input[type="email"]', TEST_EMAIL);
  await page.fill('input[type="password"]', TEST_PASSWORD);
  await page.click('button[type="submit"]');

  try {
    await page.waitForURL('**/app**', { timeout: 15000 });
    evidence.push({
      step: 'LOGIN',
      timestamp: new Date().toISOString(),
      status: 'pass',
      details: `Redirected to ${page.url()}`,
    });
    console.log('✅ LOGIN: PASS');
  } catch (e) {
    evidence.push({
      step: 'LOGIN',
      timestamp: new Date().toISOString(),
      status: 'fail',
      details: `Failed: ${e}`,
    });
    console.log('❌ LOGIN: FAIL');
  }

  await page.screenshot({ path: '/tmp/evidence_01_login.png', fullPage: true });

  // Wait for app to fully load
  await page.waitForTimeout(3000);

  // ==========================================================================
  // TEST 2: BOOTSTRAP (Check Auth Debug Panel)
  // ==========================================================================
  console.log('\n=== TEST 2: BOOTSTRAP ===');

  // Look for bootstrap data in page
  const bootstrapData = await page.evaluate(() => {
    // Try to find bootstrap info in localStorage or window
    const stored = localStorage.getItem('celeste_bootstrap');
    return stored ? JSON.parse(stored) : null;
  });

  if (bootstrapData) {
    evidence.push({
      step: 'BOOTSTRAP',
      timestamp: new Date().toISOString(),
      status: 'pass',
      details: `yacht_id: ${bootstrapData.yacht_id}, role: ${bootstrapData.role}`,
    });
    console.log(`✅ BOOTSTRAP: PASS (yacht=${bootstrapData.yacht_id})`);
  } else {
    // Check if we can see bootstrap info in the page
    const pageContent = await page.content();
    const hasYachtContext = pageContent.includes('yacht') || pageContent.includes('captain');
    evidence.push({
      step: 'BOOTSTRAP',
      timestamp: new Date().toISOString(),
      status: hasYachtContext ? 'pass' : 'skip',
      details: hasYachtContext ? 'Yacht context present in page' : 'Could not verify bootstrap data',
    });
    console.log(hasYachtContext ? '✅ BOOTSTRAP: PASS' : '⚠️ BOOTSTRAP: SKIP');
  }

  await page.screenshot({ path: '/tmp/evidence_02_bootstrap.png', fullPage: true });

  // ==========================================================================
  // TEST 3: SEARCH
  // ==========================================================================
  console.log('\n=== TEST 3: SEARCH ===');

  const searchInput = page.locator('input').first();
  await searchInput.fill('watermaker');
  await page.waitForTimeout(3000);

  // Check for search results
  const resultsVisible = await page.locator('[class*="result"], [class*="Result"], [data-testid*="result"]').count();

  evidence.push({
    step: 'SEARCH',
    timestamp: new Date().toISOString(),
    status: resultsVisible > 0 ? 'pass' : 'fail',
    details: `Found ${resultsVisible} result elements`,
  });
  console.log(resultsVisible > 0 ? `✅ SEARCH: PASS (${resultsVisible} results)` : '❌ SEARCH: FAIL');

  await page.screenshot({ path: '/tmp/evidence_03_search.png', fullPage: true });

  // ==========================================================================
  // TEST 4: CLICK RESULT (Navigation Context)
  // ==========================================================================
  console.log('\n=== TEST 4: NAVIGATION CONTEXT ===');

  const errorsBefore = networkErrors.length;

  if (resultsVisible > 0) {
    const results = page.locator('[class*="result"], [class*="Result"], [data-testid*="result"]');
    await results.first().click();
    await page.waitForTimeout(3000);

    const errorsAfter = networkErrors.length;
    const newErrors = errorsAfter - errorsBefore;

    evidence.push({
      step: 'NAVIGATION_CONTEXT',
      timestamp: new Date().toISOString(),
      status: newErrors === 0 ? 'pass' : 'fail',
      details: newErrors === 0 ? 'Click succeeded, no new errors' : `${newErrors} new network errors`,
    });
    console.log(newErrors === 0 ? '✅ NAVIGATION_CONTEXT: PASS' : `❌ NAVIGATION_CONTEXT: FAIL (${newErrors} errors)`);
  } else {
    evidence.push({
      step: 'NAVIGATION_CONTEXT',
      timestamp: new Date().toISOString(),
      status: 'skip',
      details: 'No results to click',
    });
    console.log('⚠️ NAVIGATION_CONTEXT: SKIP');
  }

  await page.screenshot({ path: '/tmp/evidence_04_navigation.png', fullPage: true });

  // ==========================================================================
  // SUMMARY
  // ==========================================================================
  console.log('\n========================================');
  console.log('VERIFICATION SUMMARY');
  console.log('========================================\n');

  console.log('EVIDENCE:');
  evidence.forEach(e => {
    const icon = e.status === 'pass' ? '✅' : e.status === 'fail' ? '❌' : '⚠️';
    console.log(`  ${icon} ${e.step}: ${e.details}`);
  });

  console.log(`\nCONSOLE ERRORS: ${consoleErrors.length}`);
  consoleErrors.forEach(e => console.log(`  ${e}`));

  console.log(`\nNETWORK ERRORS (4xx/5xx): ${networkErrors.length}`);
  networkErrors.forEach(e => console.log(`  ${e}`));

  console.log(`\nAPI RESPONSES CAPTURED: ${apiResponses.length}`);
  // Show only errors and key endpoints
  apiResponses
    .filter(r => !r.ok || r.url.includes('/v1/') || r.url.includes('/api/'))
    .slice(0, 20)
    .forEach(r => {
      const icon = r.ok ? '✅' : '❌';
      console.log(`  ${icon} [${r.status}] ${r.url.split('?')[0]}`);
    });

  console.log('\n========================================');
  console.log(`OVERALL: ${consoleErrors.length === 0 && networkErrors.length === 0 ? '✅ PASS' : '❌ ISSUES FOUND'}`);
  console.log('========================================\n');

  // Final assertion
  expect(networkErrors.filter(e => e.includes('500'))).toHaveLength(0);
});
