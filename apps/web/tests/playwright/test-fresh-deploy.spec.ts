/**
 * Test receiving with hard cache refresh to verify deployment
 */

import { test, expect, chromium } from '@playwright/test';
import { loginAs } from './auth.helper';

const BASE_URL = 'https://app.celeste7.ai';
const RECEIVING_ID = 'fc0e06af-9407-48a3-9ec3-41141cb7c459';

test('Test receiving with hard refresh (bypass CDN cache)', async () => {
  // Launch browser with no cache
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({
    ignoreHTTPSErrors: true,
    bypassCSP: true,
  });

  const page = await context.newPage();

  // Capture console errors
  const errors: string[] = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
      console.log(`[ERROR] ${msg.text()}`);
    }
  });

  page.on('pageerror', error => {
    errors.push(error.message);
    console.log(`[PAGE ERROR] ${error.message}`);
  });

  // Login
  console.log('\n=== LOGGING IN ===');
  await loginAs(page, 'captain');
  await page.waitForTimeout(3000);

  // Navigate with cache-busting parameter
  const url = `${BASE_URL}/?entity=receiving&id=${RECEIVING_ID}&_=${Date.now()}`;
  console.log(`\n=== NAVIGATING TO: ${url} ===`);

  // Navigate with hard reload
  await page.goto(url, { waitUntil: 'networkidle' });

  // Wait for page to stabilize
  await page.waitForTimeout(5000);

  // Check for error page
  const errorHeading = page.locator('h2:has-text("Application error")');
  const hasError = await errorHeading.isVisible().catch(() => false);

  console.log(`\n=== HAS ERROR: ${hasError} ===`);
  console.log(`\n=== ERRORS CAPTURED: ${errors.length} ===`);

  if (errors.length > 0) {
    console.log('\nErrors:');
    errors.forEach(err => console.log(`  - ${err}`));
  }

  // Take screenshot
  await page.screenshot({ path: '/tmp/fresh-deploy-test.png', fullPage: true });

  // Check if ContextPanel is visible (should be if no crash)
  const contextPanel = page.locator('[data-testid="context-panel"]');
  const panelVisible = await contextPanel.isVisible().catch(() => false);

  console.log(`\n=== CONTEXT PANEL VISIBLE: ${panelVisible} ===`);

  await browser.close();

  // Assert no crash
  expect(hasError).toBe(false);
  expect(panelVisible).toBe(true);
});
