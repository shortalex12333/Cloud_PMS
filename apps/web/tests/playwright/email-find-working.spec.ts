import { test } from '@playwright/test';

test('Find a thread with working message render', async ({ page }) => {
  // Track message render responses
  const renderResults: { url: string; status: number; error?: string }[] = [];
  page.on('response', async (response) => {
    if (response.url().includes('/email/message') && response.url().includes('/render')) {
      const entry: any = { url: response.url(), status: response.status() };
      if (response.status() !== 200) {
        try {
          const body = await response.json();
          entry.error = body.error;
        } catch {}
      }
      renderResults.push(entry);
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

  const threads = page.locator('button[data-testid="thread-row"]');
  const count = await threads.count();
  console.log('\n=== Testing ' + Math.min(count, 10) + ' threads for working message render ===\n');

  for (let i = 0; i < Math.min(count, 10); i++) {
    renderResults.length = 0;

    // Get thread subject
    const subject = await threads.nth(i).textContent();

    // Click thread
    await threads.nth(i).click();
    await page.waitForTimeout(1500);

    // Click "View first message" if visible
    const viewBtn = page.locator('button:has-text("View first message")');
    if (await viewBtn.isVisible().catch(() => false)) {
      await viewBtn.click();
      await page.waitForTimeout(2000);
    }

    // Check result
    const result = renderResults[0];
    if (result) {
      const status = result.status === 200 ? '✓ 200' : '✗ ' + result.status;
      const error = result.error ? ' - ' + result.error.substring(0, 50) : '';
      console.log('Thread ' + (i + 1) + ': ' + status + error);
      console.log('  Subject: ' + (subject || '').substring(0, 60));

      if (result.status === 200) {
        console.log('\n  *** FOUND WORKING THREAD ***');
        await page.screenshot({ path: '/tmp/working-email-body.png', fullPage: true });
        console.log('  Screenshot: /tmp/working-email-body.png');

        // Check what's rendered
        const iframe = await page.locator('iframe').count();
        const emailContent = await page.locator('[class*="prose"], [class*="email-body"]').count();
        console.log('  iframe count: ' + iframe);
        console.log('  email content divs: ' + emailContent);
        break;
      }
    } else {
      console.log('Thread ' + (i + 1) + ': No render request');
      console.log('  Subject: ' + (subject || '').substring(0, 60));
    }
  }
});
