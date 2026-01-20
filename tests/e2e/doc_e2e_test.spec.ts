import { test, expect } from '@playwright/test';

const PROD_URL = 'https://app.celeste7.ai';
const TEST_EMAIL = 'x@alex-short.com';
const TEST_PASSWORD = 'Password2!';

test('Document loading E2E - capture all errors', async ({ page }) => {
  const errors: string[] = [];
  const networkErrors: string[] = [];

  // Capture console errors
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push('[CONSOLE] ' + msg.text());
    }
  });

  // Capture page errors
  page.on('pageerror', err => {
    errors.push('[PAGE ERROR] ' + err.message);
  });

  // Capture failed network requests
  page.on('response', response => {
    if (response.status() >= 400) {
      networkErrors.push('[HTTP ' + response.status() + '] ' + response.url());
    }
  });

  // Login
  console.log('Step 1: Logging in...');
  await page.goto(PROD_URL + '/login');
  await page.fill('input[type="email"]', TEST_EMAIL);
  await page.fill('input[type="password"]', TEST_PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForURL('**/app**', { timeout: 15000 });
  console.log('Logged in successfully');

  // Wait for app to load
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/01_app_loaded.png', fullPage: true });

  // Search for manual/document
  console.log('Step 2: Searching for documents...');
  const searchInput = page.locator('input').first();
  await searchInput.fill('watermaker manual');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/02_search_results.png', fullPage: true });

  // Look for any clickable result
  console.log('Step 3: Looking for document results...');
  const results = page.locator('[class*="result"], [class*="Result"], [data-testid*="result"]');
  const count = await results.count();
  console.log('Found ' + count + ' result elements');

  if (count > 0) {
    console.log('Step 4: Clicking first result...');
    await results.first().click();
    await page.waitForTimeout(3000);
    await page.screenshot({ path: '/tmp/03_after_click.png', fullPage: true });
  }

  // Print summary
  console.log('\n========== ERROR SUMMARY ==========');
  console.log('Console errors: ' + errors.length);
  errors.forEach(e => console.log('  ' + e));

  console.log('Network errors (4xx/5xx): ' + networkErrors.length);
  networkErrors.forEach(e => console.log('  ' + e));

  console.log('\nScreenshots saved to /tmp/');
  console.log('=====================================');
});
