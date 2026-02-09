/**
 * DEBUG: Find exact error causing receiving deep link crash
 */

import { test, expect, Page } from '@playwright/test';
import { loginAs } from './auth.helper';

const BASE_URL = 'https://app.celeste7.ai';
const RECEIVING_ID = 'fc0e06af-9407-48a3-9ec3-41141cb7c459';

test('Debug receiving deep link crash', async ({ page }) => {
  // Capture all console messages
  const consoleMessages: string[] = [];
  const errors: string[] = [];

  page.on('console', msg => {
    const text = `[${msg.type()}] ${msg.text()}`;
    consoleMessages.push(text);
    console.log(text);
  });

  page.on('pageerror', error => {
    const errorText = `PAGE ERROR: ${error.message}\n${error.stack}`;
    errors.push(errorText);
    console.log(errorText);
  });

  // Login
  console.log('\n=== LOGGING IN ===');
  await loginAs(page, 'captain');
  await page.waitForTimeout(3000);

  console.log('\n=== NAVIGATING TO RECEIVING ===');
  console.log(`URL: ${BASE_URL}/?entity=receiving&id=${RECEIVING_ID}`);

  // Navigate and wait for error
  await page.goto(`${BASE_URL}/?entity=receiving&id=${RECEIVING_ID}`);
  await page.waitForTimeout(5000);

  // Take screenshot
  await page.screenshot({ path: '/tmp/debug-crash.png', fullPage: true });

  // Print all captured errors
  console.log('\n=== CONSOLE MESSAGES ===');
  consoleMessages.forEach(msg => console.log(msg));

  console.log('\n=== PAGE ERRORS ===');
  errors.forEach(err => console.log(err));

  // Check if error page appeared
  const errorHeading = page.locator('h2:has-text("Application error")');
  const hasError = await errorHeading.isVisible().catch(() => false);

  console.log(`\n=== ERROR PAGE VISIBLE: ${hasError} ===`);

  if (hasError) {
    console.log('✓ Confirmed app crash');
  }

  // Write errors to file
  await page.evaluate(() => {
    return JSON.stringify({
      localStorage: Object.fromEntries(Object.entries(localStorage)),
      sessionStorage: Object.fromEntries(Object.entries(sessionStorage)),
    });
  }).then(data => {
    console.log('\n=== STORAGE ===');
    console.log(data);
  });
});
