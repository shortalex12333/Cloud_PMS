import { test } from '@playwright/test';

test('Check email body renders', async ({ page }) => {
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
  await page.waitForTimeout(3000);

  // Screenshot
  await page.screenshot({ path: '/tmp/email-detail-render.png', fullPage: true });

  // Check what's visible
  const hasIframe = await page.locator('iframe').count();
  const hasFromTo = await page.locator('text=/From:|To:/').count();
  const selectMessage = await page.locator('text="Select a message"').count();
  const viewFirstBtn = await page.locator('button:has-text("View first message")').count();
  const h2Text = await page.locator('h2').allTextContents();
  
  console.log('\n=== Email Detail Render Check ===');
  console.log('  iframes:', hasIframe);
  console.log('  From/To labels:', hasFromTo);
  console.log('  "Select a message":', selectMessage);
  console.log('  "View first message" btn:', viewFirstBtn);
  console.log('  h2 headings:', JSON.stringify(h2Text));
  console.log('\n  Screenshot: /tmp/email-detail-render.png');
});
