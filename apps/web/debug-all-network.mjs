/**
 * Debug script - trace ALL network including errors
 */

import { chromium } from 'playwright';

const TEST_WORK_ORDER_ID = 'b36238da-b0fa-4815-883c-0be61fc190d0';

async function debug() {
  console.log('=== DEBUG ALL NETWORK ===\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    storageState: './playwright/.auth/user.json',
  });
  const page = await context.newPage();

  // Track ALL network
  page.on('requestfailed', request => {
    console.log(`  [FAILED] ${request.url()}`);
    console.log(`           ${request.failure()?.errorText}`);
  });

  page.on('response', async response => {
    const status = response.status();
    const url = response.url();
    if (status >= 400 || url.includes('supabase') || url.includes('bootstrap') || url.includes('auth')) {
      console.log(`  [${status}] ${url}`);
    }
  });

  // Track console logs
  page.on('console', msg => {
    const text = msg.text();
    // Show important logs
    if (text.includes('Auth') || text.includes('bootstrap') || text.includes('DeepLink') ||
        text.includes('error') || text.includes('Error') || text.includes('404')) {
      console.log(`  [LOG] ${text}`);
    }
  });

  console.log('Navigating...');
  await page.goto(`http://localhost:3000/?entity=work_order&id=${TEST_WORK_ORDER_ID}`, {
    waitUntil: 'networkidle',
    timeout: 30000,
  });

  console.log('\nWaiting 5s...');
  await page.waitForTimeout(5000);

  console.log('\nDeepLinkHandler status:', await page.$eval('[data-testid="deep-link-handler"]', el => ({
    status: el.getAttribute('data-deep-link-status'),
    error: el.getAttribute('data-deep-link-error'),
  })).catch(() => 'not found'));

  // Check what's in window for auth
  const authState = await page.evaluate(() => {
    // @ts-ignore
    return {
      hasWindow: typeof window !== 'undefined',
      localStorage: Object.keys(localStorage).filter(k => k.includes('auth')),
    };
  });
  console.log('\nAuth state in browser:', authState);

  await browser.close();
}

debug().catch(console.error);
