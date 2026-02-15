/**
 * Debug test to see why thread detail isn't loading
 */
import { test, expect, Page } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'https://app.celeste7.ai';

test('Debug: Click thread and watch network', async ({ page }) => {
  // Collect all network responses
  const responses: { url: string; status: number }[] = [];
  page.on('response', (response) => {
    if (response.url().includes('/email/')) {
      responses.push({ url: response.url(), status: response.status() });
    }
  });

  // Login
  await page.goto(`${BASE_URL}/login`);
  await page.waitForSelector('input[type="email"]', { timeout: 15000 });
  await page.fill('input[type="email"]', 'x@alex-short.com');
  await page.fill('input[type="password"]', 'Password2!');
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 20000 });
  await page.waitForTimeout(2000);

  // Click Email button
  const emailButton = page.locator('button:has-text("Email"), a:has-text("Email")').first();
  await emailButton.click();
  await page.waitForTimeout(3000);

  console.log('\n=== After clicking Email button ===');
  responses.forEach(r => console.log(`  ${r.status} ${r.url.substring(0, 100)}`));
  responses.length = 0;

  // Click first thread
  const thread = page.locator('button[data-testid="thread-row"]').first();
  await thread.click();
  console.log('\n=== Clicked thread, waiting 5 seconds... ===');
  await page.waitForTimeout(5000);

  console.log('\n=== Network responses after thread click ===');
  responses.forEach(r => console.log(`  ${r.status} ${r.url.substring(0, 100)}`));

  // Take screenshot
  await page.screenshot({ path: '/tmp/email-debug-detail.png', fullPage: true });

  // Check what's visible in the detail area
  const loadingSpinner = await page.locator('.animate-spin, [class*="loading"], [class*="spinner"]').count();
  const errorMessage = await page.locator('text=/error|failed|not found/i').count();
  const selectMessage = await page.locator('text="Select a message"').count();

  console.log('\n=== UI State ===');
  console.log(`  Loading spinners: ${loadingSpinner}`);
  console.log(`  Error messages: ${errorMessage}`);
  console.log(`  "Select a message" text: ${selectMessage}`);

  // Check for 404s
  const has404 = responses.some(r => r.status === 404);
  console.log(`\n=== Result ===`);
  console.log(`  Has 404: ${has404}`);
});
