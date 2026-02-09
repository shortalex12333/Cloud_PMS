/**
 * Debug work order query
 */

import { chromium } from 'playwright';
import fs from 'fs';

const TEST_WO_ID = 'b36238da-b0fa-4815-883c-0be61fc190d0';

async function debug() {
  console.log('=== DEBUG WORK ORDER QUERY ===\n');

  // Load auth state
  const authState = JSON.parse(fs.readFileSync('./playwright/.auth/user.json', 'utf-8'));
  const session = JSON.parse(authState.origins[0].localStorage[0].value);
  console.log('Token:', session.access_token.substring(0, 50) + '...');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ storageState: './playwright/.auth/user.json' });
  const page = await context.newPage();

  // Track network
  page.on('response', async response => {
    const url = response.url();
    if (url.includes('pms_work_orders')) {
      console.log('\n[RESPONSE]', response.status(), url);
      try {
        const body = await response.text();
        console.log('Body:', body.substring(0, 500));
      } catch (e) {}
    }
  });

  // Track console
  page.on('console', msg => {
    const text = msg.text();
    if (text.includes('DeepLink') || text.includes('fetch') || text.includes('error')) {
      console.log('[LOG]', text);
    }
  });

  console.log('Navigating...');
  await page.goto(`http://localhost:3000/?entity=work_order&id=${TEST_WO_ID}`, {
    waitUntil: 'networkidle',
  });

  await page.waitForTimeout(5000);

  console.log('\nFinal status:');
  const handler = await page.$('[data-testid="deep-link-handler"]');
  if (handler) {
    console.log('  status:', await handler.getAttribute('data-deep-link-status'));
    console.log('  error:', await handler.getAttribute('data-deep-link-error'));
  }

  await browser.close();
}

debug().catch(console.error);
