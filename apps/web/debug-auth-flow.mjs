/**
 * Debug script to trace the auth flow and DeepLinkHandler state
 */

import { chromium } from 'playwright';
import fs from 'fs';

const TEST_WORK_ORDER_ID = 'b36238da-b0fa-4815-883c-0be61fc190d0';

async function debug() {
  console.log('=== DEBUG AUTH FLOW ===\n');

  // Load auth state
  const authState = JSON.parse(fs.readFileSync('./playwright/.auth/user.json', 'utf-8'));
  const session = JSON.parse(authState.origins[0].localStorage[0].value);

  console.log('Auth State:');
  console.log('  User ID:', session.user?.id);
  console.log('  Email:', session.user?.email);
  console.log('  Expires At:', new Date(session.expires_at * 1000).toISOString());
  console.log('  Token valid for:', Math.floor((session.expires_at - Date.now()/1000) / 60), 'minutes');
  console.log('');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    storageState: './playwright/.auth/user.json',
  });
  const page = await context.newPage();

  // Collect console logs
  const consoleLogs = [];
  page.on('console', msg => {
    const text = msg.text();
    consoleLogs.push({ type: msg.type(), text });
    if (text.includes('Auth') || text.includes('DeepLink') || text.includes('Bootstrap') || text.includes('bootstrap')) {
      console.log(`  [${msg.type().toUpperCase()}]`, text);
    }
  });

  // Intercept network requests to bootstrap endpoint
  page.on('request', request => {
    if (request.url().includes('bootstrap')) {
      console.log('  [NETWORK] Bootstrap request:', request.url());
    }
  });

  page.on('response', response => {
    if (response.url().includes('bootstrap')) {
      console.log('  [NETWORK] Bootstrap response:', response.status());
    }
  });

  console.log('1. Navigating to deep link URL...');
  await page.goto(`http://localhost:3000/app?entity=work_order&id=${TEST_WORK_ORDER_ID}`, {
    waitUntil: 'domcontentloaded',
    timeout: 30000,
  });

  console.log('\n2. Waiting for page to settle...');
  await page.waitForTimeout(5000);

  console.log('\n3. Checking DeepLinkHandler state...');
  const handler = await page.$('[data-testid="deep-link-handler"]');
  if (handler) {
    const status = await handler.getAttribute('data-deep-link-status');
    const entity = await handler.getAttribute('data-deep-link-entity');
    const id = await handler.getAttribute('data-deep-link-id');
    const error = await handler.getAttribute('data-deep-link-error');
    console.log('  status:', status);
    console.log('  entity:', entity);
    console.log('  id:', id?.substring(0, 8) + '...');
    console.log('  error:', error || '(none)');
  } else {
    console.log('  DeepLinkHandler NOT found');
  }

  console.log('\n4. Checking auth context via window...');
  const authInfo = await page.evaluate(() => {
    // Try to find auth state in the page
    const authKey = Object.keys(localStorage).find(k => k.includes('auth-token'));
    if (authKey) {
      try {
        const session = JSON.parse(localStorage.getItem(authKey));
        return {
          hasSession: true,
          userId: session.user?.id,
          email: session.user?.email,
          expiresAt: session.expires_at,
        };
      } catch (e) {
        return { hasSession: false, error: e.message };
      }
    }
    return { hasSession: false };
  });
  console.log('  Auth info from localStorage:', authInfo);

  console.log('\n5. Current URL:', page.url());

  console.log('\n6. Waiting longer for bootstrap to complete...');
  await page.waitForTimeout(10000);

  // Check state again
  console.log('\n7. Final DeepLinkHandler state...');
  if (handler) {
    const status = await handler.getAttribute('data-deep-link-status');
    const error = await handler.getAttribute('data-deep-link-error');
    console.log('  status:', status);
    console.log('  error:', error || '(none)');
  }

  // Take screenshot
  await page.screenshot({ path: 'debug-auth-screenshot.png', fullPage: true });
  console.log('\n8. Screenshot saved to debug-auth-screenshot.png');

  // Print relevant console logs
  console.log('\n9. Relevant console logs:');
  consoleLogs.filter(l =>
    l.text.includes('Auth') ||
    l.text.includes('DeepLink') ||
    l.text.includes('bootstrap') ||
    l.text.includes('Bootstrap')
  ).forEach(l => {
    console.log(`  [${l.type}]`, l.text);
  });

  await browser.close();
}

debug().catch(err => {
  console.error('Error:', err);
  process.exit(1);
});
