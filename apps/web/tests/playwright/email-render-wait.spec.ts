import { test } from '@playwright/test';

test('Test email body render with longer wait', async ({ page }) => {
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

  // Click thread 5 (FW: Re: Stern thruster...)
  const threads = page.locator('button[data-testid="thread-row"]');
  await threads.nth(4).click();  // 0-indexed, so 4 = thread 5
  await page.waitForTimeout(2000);

  console.log('\n=== Clicked thread 5 (Stern thruster) ===');

  // Click "View first message"
  const viewBtn = page.locator('button:has-text("View first message")');
  if (await viewBtn.isVisible().catch(() => false)) {
    console.log('Clicking "View first message"...');
    await viewBtn.click();
  }

  // Wait longer for render
  console.log('Waiting 10 seconds for render...');
  await page.waitForTimeout(10000);

  // Take screenshots
  await page.screenshot({ path: '/tmp/email-render-1.png', fullPage: true });

  // Check what's visible
  const spinner = await page.locator('.animate-spin').count();
  const iframe = await page.locator('iframe').count();
  const proseContent = await page.locator('[class*="prose"]').count();
  const emailBody = await page.locator('[class*="email"], [class*="body"], [class*="content"]').count();
  const fromLabel = await page.locator('text=/From:/i').count();
  const errorText = await page.locator('text=/error|failed|not found/i').count();

  console.log('\n=== UI State after 10s ===');
  console.log('  Spinners:', spinner);
  console.log('  iframes:', iframe);
  console.log('  prose divs:', proseContent);
  console.log('  email/body/content divs:', emailBody);
  console.log('  From label:', fromLabel);
  console.log('  Error text:', errorText);

  // Get visible text in detail panel
  const detailText = await page.locator('main').last().textContent();
  console.log('\n  Detail panel text (first 500 chars):');
  console.log('  ' + (detailText || '').substring(0, 500));

  console.log('\n  Screenshot: /tmp/email-render-1.png');
});
