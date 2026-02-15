/**
 * Try clicking different threads to find one that works
 */
import { test, Page } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'https://app.celeste7.ai';

test('Find a working thread', async ({ page }) => {
  // Track responses
  const threadResponses: { id: string; status: number }[] = [];
  page.on('response', (response) => {
    const match = response.url().match(/\/email\/thread\/([a-f0-9-]+)$/);
    if (match) {
      threadResponses.push({ id: match[1], status: response.status() });
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

  // Open email
  await page.locator('button:has-text("Email"), a:has-text("Email")').first().click();
  await page.waitForTimeout(3000);

  // Try clicking each thread
  const threads = page.locator('button[data-testid="thread-row"]');
  const count = await threads.count();
  console.log(`\n=== Found ${count} threads ===\n`);

  for (let i = 0; i < Math.min(count, 10); i++) {
    threadResponses.length = 0;
    await threads.nth(i).click();
    await page.waitForTimeout(2000);

    const subject = await threads.nth(i).textContent();
    const response = threadResponses.find(r => r.status !== 200) || threadResponses[0];

    if (response) {
      const status = response.status === 200 ? '✓ 200' : `✗ ${response.status}`;
      console.log(`Thread ${i + 1}: ${status} - ${subject?.substring(0, 50)}`);

      if (response.status === 200) {
        // Check if body rendered
        await page.waitForTimeout(1000);
        const hasContent = await page.locator('iframe, [data-testid="email-body"], .email-content').count() > 0;
        console.log(`         Body rendered: ${hasContent}`);

        await page.screenshot({ path: `/tmp/working-thread-${i + 1}.png`, fullPage: true });
        console.log(`         Screenshot saved: /tmp/working-thread-${i + 1}.png`);
      }
    } else {
      console.log(`Thread ${i + 1}: No response - ${subject?.substring(0, 50)}`);
    }
  }

  console.log('\n=== Summary ===');
  const working = threadResponses.filter(r => r.status === 200).length;
  const failing = threadResponses.filter(r => r.status !== 200).length;
  console.log(`Working: ${working}, Failing: ${failing}`);
});
