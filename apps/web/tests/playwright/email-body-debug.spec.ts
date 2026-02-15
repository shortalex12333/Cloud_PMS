import { test } from '@playwright/test';

test('Debug email body loading', async ({ page }) => {
  // Track ALL network requests
  const requests: { url: string; status: number; body?: string }[] = [];
  page.on('response', async (response) => {
    if (response.url().includes('celeste') || response.url().includes('supabase')) {
      const entry: { url: string; status: number; body?: string } = {
        url: response.url(),
        status: response.status()
      };
      if (response.url().includes('/email/')) {
        try {
          entry.body = (await response.text()).substring(0, 500);
        } catch {}
      }
      requests.push(entry);
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

  requests.length = 0; // Clear pre-login requests

  // Open email
  await page.locator('button:has-text("Email"), a:has-text("Email")').first().click();
  await page.waitForTimeout(3000);

  console.log('\n=== After opening email panel ===');
  requests.filter(r => r.url.includes('/email/')).forEach(r => {
    console.log('  ' + r.status + ' ' + r.url.split('?')[0]);
  });

  requests.length = 0;

  // Click first thread
  const threadText = await page.locator('button[data-testid="thread-row"]').first().textContent();
  console.log('\nClicking thread: ' + (threadText || '').substring(0, 50));
  await page.locator('button[data-testid="thread-row"]').first().click();

  // Wait longer
  await page.waitForTimeout(8000);

  console.log('\n=== Network after thread click (8s wait) ===');
  requests.forEach(r => {
    console.log('  ' + r.status + ' ' + r.url.split('?')[0]);
    if (r.body) {
      console.log('      Response: ' + r.body.substring(0, 300) + '...');
    }
  });

  // Check for errors in console
  const spinner = await page.locator('.animate-spin').count();
  const errorText = await page.locator('text=/error|failed|unauthorized/i').count();

  console.log('\n=== UI State ===');
  console.log('  Spinners: ' + spinner);
  console.log('  Error text: ' + errorText);

  await page.screenshot({ path: '/tmp/email-body-debug.png', fullPage: true });
  console.log('\n  Screenshot: /tmp/email-body-debug.png');
});
