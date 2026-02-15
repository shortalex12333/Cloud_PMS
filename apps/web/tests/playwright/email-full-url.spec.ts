import { test } from '@playwright/test';

test('Check full URL for message fetch', async ({ page }) => {
  // Track ALL /email/ requests with FULL URLs
  const requests: string[] = [];
  page.on('response', async (response) => {
    if (response.url().includes('/email/message')) {
      requests.push(response.status() + ' ' + response.url());
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
  if (await viewBtn.count() > 0) {
    requests.length = 0;
    await viewBtn.click();
    await page.waitForTimeout(3000);
  }

  console.log('\n=== Full URLs for /email/message requests ===');
  requests.forEach(r => console.log(r));
});
