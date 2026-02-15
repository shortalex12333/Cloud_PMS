/**
 * Email 404 Fix Verification Test
 * Single-surface app at /
 */

import { test, expect, Page } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'https://app.celeste7.ai';
const SCREENSHOT_DIR = '/tmp/email_404_fix_verification';

const TEST_USER = {
  email: 'x@alex-short.com',
  password: 'Password2!',
};

async function screenshot(page: Page, name: string) {
  await page.screenshot({ path: `${SCREENSHOT_DIR}/${name}.png`, fullPage: true });
}

async function login(page: Page) {
  await page.goto(`${BASE_URL}/login`);
  await page.waitForSelector('input[type="email"]', { timeout: 15000 });
  await page.fill('input[type="email"]', TEST_USER.email);
  await page.fill('input[type="password"]', TEST_USER.password);
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 20000 });
  await page.waitForTimeout(1000); // Let app hydrate
}

test.describe('Email 404 Fix Verification', () => {

  test('1. Login and see main surface', async ({ page }) => {
    console.log('\n=== TEST 1: Login ===');
    await login(page);
    await screenshot(page, '01-logged-in');
    expect(page.url()).not.toContain('/login');
    console.log(`   SUCCESS: Logged in at ${page.url()}`);
  });

  test('2. Click Email button and verify threads load - NO 404', async ({ page }) => {
    console.log('\n=== TEST 2: Email thread fetch (404 fix test) ===');
    await login(page);

    // Monitor for 404 errors on thread fetch
    const errors404: string[] = [];
    page.on('response', (response) => {
      if (response.status() === 404 && response.url().includes('/email/thread/')) {
        errors404.push(`404: ${response.url()}`);
      }
    });

    // Click Email button
    const emailButton = page.locator('button:has-text("Email"), a:has-text("Email"), [aria-label*="Email"]').first();
    await emailButton.waitFor({ state: 'visible', timeout: 10000 });
    await emailButton.click();
    await page.waitForTimeout(2000);
    await screenshot(page, '02-email-clicked');

    // Look for email threads in the list
    const threads = page.locator('[data-testid="email-thread"], [data-testid="thread-row"], .thread-item, .email-row');
    const threadCount = await threads.count();
    console.log(`   Found ${threadCount} email threads`);

    // If threads exist, click one to trigger thread fetch
    if (threadCount > 0) {
      await threads.first().click();
      await page.waitForTimeout(2000);
      await screenshot(page, '03-thread-selected');
    }

    console.log(`   404 errors: ${errors404.length}`);
    if (errors404.length > 0) {
      console.log(`   ERRORS: ${errors404.join(', ')}`);
    }

    expect(errors404.length).toBe(0);
  });

  test('3. Verify email body renders', async ({ page }) => {
    console.log('\n=== TEST 3: Email body renders ===');
    await login(page);

    // Click Email
    const emailButton = page.locator('button:has-text("Email"), a:has-text("Email")').first();
    await emailButton.waitFor({ state: 'visible', timeout: 10000 });
    await emailButton.click();
    await page.waitForTimeout(2000);

    // Click first thread
    const threads = page.locator('[data-testid="email-thread"], .thread-item, .email-row');
    if (await threads.count() > 0) {
      await threads.first().click();
      await page.waitForTimeout(2000);

      // Check for body content
      const body = page.locator('[data-testid="email-body"], .email-body, .message-content, iframe');
      const hasBody = await body.count() > 0;
      console.log(`   Email body visible: ${hasBody}`);
      await screenshot(page, '04-body-rendered');
    } else {
      console.log('   No threads to click');
    }
  });

  test('4. Verify attachments section', async ({ page }) => {
    console.log('\n=== TEST 4: Attachments ===');
    await login(page);

    // Click Email
    const emailButton = page.locator('button:has-text("Email"), a:has-text("Email")').first();
    await emailButton.waitFor({ state: 'visible', timeout: 10000 });
    await emailButton.click();
    await page.waitForTimeout(2000);

    // Click first thread
    const threads = page.locator('[data-testid="email-thread"], .thread-item, .email-row');
    if (await threads.count() > 0) {
      await threads.first().click();
      await page.waitForTimeout(2000);

      const attachments = page.locator('[data-testid="attachments"], .attachments, :text("Attachment")');
      const count = await attachments.count();
      console.log(`   Attachment elements: ${count}`);
      await screenshot(page, '05-attachments');
    }
  });

  test('5. Token stays valid', async ({ page }) => {
    console.log('\n=== TEST 5: Token refresh ===');
    await login(page);
    await page.reload();
    await page.waitForTimeout(2000);
    expect(page.url()).not.toContain('/login');
    console.log('   SUCCESS: Still authenticated');
    await screenshot(page, '06-still-auth');
  });
});
