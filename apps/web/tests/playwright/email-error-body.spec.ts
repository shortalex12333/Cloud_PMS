import { test } from '@playwright/test';

test('Get error response body from message render 404', async ({ page }) => {
  // Capture response bodies
  let errorBody = '';
  page.on('response', async (response) => {
    if (response.url().includes('/email/message') && response.status() === 404) {
      try {
        errorBody = await response.text();
      } catch {}
    }
  });

  // Login
  await page.goto('https://app.celeste7.ai/login');
  await page.waitForSelector('input[type="email"]', { timeout: 15000 });
  await page.fill('input[type="email"]', 'x@alex-short.com');
  await page.fill('input[type="password"]', 'Password2!');
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 20000 });
  await page.waitForTimeout(2000);

  // Open email
  await page.locator('button:has-text("Email"), a:has-text("Email")').first().click();
  await page.waitForTimeout(2000);

  // Click first thread
  await page.locator('button[data-testid="thread-row"]').first().click();
  await page.waitForTimeout(2000);

  // Click "View first message"
  const viewBtn = page.locator('button:has-text("View first message")');
  if (await viewBtn.isVisible().catch(() => false)) {
    await viewBtn.click();
    await page.waitForTimeout(3000);
  }

  console.log('\n=== 404 Error Response Body ===');
  console.log(errorBody || '(no error body captured)');
});
