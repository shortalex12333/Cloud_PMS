import { test } from '@playwright/test';

test('Click View first message and check body renders', async ({ page }) => {
  // Track network
  const requests: { url: string; status: number }[] = [];
  page.on('response', async (response) => {
    if (response.url().includes('/email/')) {
      requests.push({ url: response.url(), status: response.status() });
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

  // Look for "View first message" button
  const viewBtn = page.locator('button:has-text("View first message")');
  const viewBtnCount = await viewBtn.count();
  console.log('\n"View first message" button found:', viewBtnCount);

  if (viewBtnCount > 0) {
    requests.length = 0;
    console.log('Clicking "View first message"...');
    await viewBtn.click();
    await page.waitForTimeout(3000);

    console.log('\n=== Network after clicking View first message ===');
    requests.forEach(r => {
      console.log('  ' + r.status + ' ' + r.url.substring(0, 100));
    });

    await page.screenshot({ path: '/tmp/email-after-view-click.png', fullPage: true });
    console.log('\nScreenshot: /tmp/email-after-view-click.png');

    // Check what's visible now
    const iframe = await page.locator('iframe').count();
    const emailBody = await page.locator('[class*="email-body"], [class*="message-content"], [data-testid*="body"]').count();
    const fromTo = await page.locator('text=/From:|To:/').count();
    const selectMsg = await page.locator('text="Select a message"').count();

    console.log('\n=== UI After clicking View ===');
    console.log('  iframes:', iframe);
    console.log('  email body elements:', emailBody);
    console.log('  From/To labels:', fromTo);
    console.log('  "Select a message" still showing:', selectMsg);
  }
});
