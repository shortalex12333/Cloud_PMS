import { test } from '@playwright/test';

test('Check all requests after View first message', async ({ page }) => {
  // Track ALL requests
  const allRequests: string[] = [];
  page.on('request', (request) => {
    allRequests.push('REQ: ' + request.method() + ' ' + request.url());
  });
  page.on('response', (response) => {
    if (response.url().includes('pipeline-core') || response.url().includes('celeste')) {
      allRequests.push('RES: ' + response.status() + ' ' + response.url());
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

  // Clear and click "View first message"
  const viewBtn = page.locator('button:has-text("View first message")');
  const viewBtnVisible = await viewBtn.isVisible().catch(() => false);
  console.log('\n"View first message" button visible:', viewBtnVisible);

  if (viewBtnVisible) {
    allRequests.length = 0;
    console.log('Clicking "View first message"...');
    await viewBtn.click();
    await page.waitForTimeout(5000);

    console.log('\n=== All network activity after click ===');
    allRequests.filter(r => r.includes('email') || r.includes('message')).forEach(r => console.log(r));

    if (allRequests.filter(r => r.includes('email')).length === 0) {
      console.log('(No email-related requests found)');
      console.log('\nAll requests:');
      allRequests.slice(0, 20).forEach(r => console.log(r));
    }
  } else {
    console.log('Button not visible, checking page state...');
    await page.screenshot({ path: '/tmp/no-view-btn.png', fullPage: true });
  }

  await page.screenshot({ path: '/tmp/after-view-click.png', fullPage: true });
});
