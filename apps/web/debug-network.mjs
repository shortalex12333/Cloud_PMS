/**
 * Debug script to trace network requests during auth flow
 */

import { chromium } from 'playwright';
import fs from 'fs';

const TEST_WORK_ORDER_ID = 'b36238da-b0fa-4815-883c-0be61fc190d0';

async function debug() {
  console.log('=== DEBUG NETWORK FLOW ===\n');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    storageState: './playwright/.auth/user.json',
  });
  const page = await context.newPage();

  // Track ALL network requests
  const requests = [];
  page.on('request', request => {
    const url = request.url();
    if (!url.includes('_next') && !url.includes('.js') && !url.includes('.css')) {
      requests.push({ type: 'request', method: request.method(), url });
      console.log(`  [REQ] ${request.method()} ${url.substring(0, 100)}`);
    }
  });

  page.on('response', async response => {
    const url = response.url();
    if (!url.includes('_next') && !url.includes('.js') && !url.includes('.css')) {
      let body = '';
      try {
        if (response.headers()['content-type']?.includes('application/json')) {
          body = await response.text();
          if (body.length > 200) body = body.substring(0, 200) + '...';
        }
      } catch (e) {}
      console.log(`  [RES] ${response.status()} ${url.substring(0, 80)} ${body ? '\n       ' + body : ''}`);
    }
  });

  // Track console
  page.on('console', msg => {
    console.log(`  [CONSOLE ${msg.type()}] ${msg.text()}`);
  });

  // Track page errors
  page.on('pageerror', err => {
    console.log(`  [PAGE ERROR] ${err.message}`);
  });

  console.log('1. Navigating to root with deep link params...');
  await page.goto(`http://localhost:3000/?entity=work_order&id=${TEST_WORK_ORDER_ID}`, {
    waitUntil: 'networkidle',
    timeout: 30000,
  });

  console.log('\n2. Page loaded, waiting...');
  await page.waitForTimeout(3000);

  console.log('\n3. Checking DeepLinkHandler...');
  const handler = await page.$('[data-testid="deep-link-handler"]');
  if (handler) {
    const status = await handler.getAttribute('data-deep-link-status');
    const error = await handler.getAttribute('data-deep-link-error');
    console.log('  status:', status);
    console.log('  error:', error || '(none)');
  }

  console.log('\n4. Final URL:', page.url());

  // Take screenshot
  await page.screenshot({ path: 'debug-network-screenshot.png', fullPage: true });
  console.log('\n5. Screenshot saved');

  await browser.close();
}

debug().catch(err => {
  console.error('Error:', err);
  process.exit(1);
});
