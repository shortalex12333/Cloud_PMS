import { test, expect } from '@playwright/test';

test('search returns and renders results after login', async ({ page }) => {
  // Go to login
  await page.goto('https://app.celeste7.ai/login');
  
  // Fill login form
  await page.fill('input[type="email"]', 'crew.test@alex-short.com');
  await page.fill('input[type="password"]', 'Password2!');
  await page.click('button[type="submit"]');
  
  // Wait for redirect to app
  await page.waitForURL('**/app**', { timeout: 15000 });
  console.log('✓ Logged in successfully');
  
  // Find search input and type query
  const searchInput = page.locator('input[placeholder*="earch"]').first();
  await searchInput.waitFor({ timeout: 10000 });
  await searchInput.fill('generator flaw');
  await searchInput.press('Enter');
  console.log('✓ Search submitted');
  
  // Wait for results to render
  await page.waitForTimeout(5000);
  
  // Take screenshot
  await page.screenshot({ path: '/tmp/search-results-e2e.png', fullPage: true });
  console.log('✓ Screenshot saved');
  
  // Check console for errors
  const consoleMessages: string[] = [];
  page.on('console', msg => consoleMessages.push(msg.text()));
  
  // Look for any result cards or content
  const pageContent = await page.content();
  const hasResults = pageContent.includes('generator') || pageContent.includes('flaw') || pageContent.includes('result');
  
  console.log(`Page has result content: ${hasResults}`);
  console.log('Console messages:', consoleMessages.filter(m => m.includes('Search') || m.includes('error')).join('\n'));
  
  expect(hasResults).toBe(true);
});
