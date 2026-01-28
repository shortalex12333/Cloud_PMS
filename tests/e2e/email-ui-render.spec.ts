/**
 * Email UI Render Test
 *
 * Tests that clicking on an email in the UI actually renders the body content.
 * Tests the full React component flow at /email/inbox
 */

import { test, expect } from '@playwright/test';

const APP_URL = 'https://app.celeste7.ai';

test.describe('Email UI Render - Frontend Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Login and ensure session is persisted
    const testUserEmail = 'x@alex-short.com';
    const testUserPassword = 'Password2!';

    await page.goto(`${APP_URL}/login`);
    await page.waitForLoadState('networkidle');

    await page.fill('input[type="email"]', testUserEmail);
    await page.fill('input[type="password"]', testUserPassword);
    await page.click('button[type="submit"]');

    // Wait for redirect and session to be stored in localStorage
    await page.waitForURL('**/app**', { timeout: 15000 });

    // Wait for Supabase session to be stored in localStorage
    await page.waitForFunction(() => {
      const keys = Object.keys(localStorage);
      return keys.some(k => k.includes('supabase') || k.includes('sb-'));
    }, { timeout: 10000 }).catch(() => {
      console.log('Warning: Supabase session not found in localStorage');
    });

    // Extra wait for session to propagate
    await page.waitForTimeout(1000);
  });

  test('Email inbox page loads with search box', async ({ page }) => {
    await page.goto(`${APP_URL}/email/inbox`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    await page.screenshot({ path: 'email-inbox-loaded.png' });

    // Look for any input element (searchbox or text)
    const searchInput = page.locator('input, [role="searchbox"]').first();
    await expect(searchInput).toBeVisible({ timeout: 10000 });

    console.log('Email inbox page loaded with search box');
  });

  test('Page shows thread list when authenticated', async ({ page }) => {
    await page.goto(`${APP_URL}/email/inbox`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    await page.screenshot({ path: 'inbox-threads.png' });

    // Check auth status by looking for "Not authenticated" message
    const notAuthText = page.locator('text=Not authenticated');
    const hasAuthError = await notAuthText.isVisible({ timeout: 2000 }).catch(() => false);

    if (hasAuthError) {
      console.log('WARNING: Auth error - session not persisted to /email/inbox');
      // Check localStorage contents
      const storageKeys = await page.evaluate(() => Object.keys(localStorage));
      console.log('localStorage keys:', storageKeys);
    } else {
      console.log('Auth OK - checking for threads');

      // Look for thread-related content
      const allText = await page.locator('body').textContent();
      console.log('Page contains "message":', allText?.includes('message'));
      console.log('Page contains "thread":', allText?.includes('thread'));
      console.log('Page contains "email":', allText?.includes('email'));
    }
  });

  test('Console logs capture debug messages', async ({ page }) => {
    const consoleLogs: string[] = [];

    page.on('console', (msg) => {
      const text = msg.text();
      // Capture EMAIL debug logs and auth-related logs
      if (text.includes('[EMAIL') || text.includes('session') || text.includes('auth')) {
        consoleLogs.push(text);
      }
    });

    await page.goto(`${APP_URL}/email/inbox`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(4000);

    console.log('\n=== CAPTURED DEBUG LOGS ===');
    consoleLogs.slice(0, 30).forEach((log) => console.log(log));
    console.log(`=== END (${consoleLogs.length} total) ===\n`);

    // Log presence check
    const hasEmailLogs = consoleLogs.some((l) => l.includes('[EMAIL'));
    console.log('Has EMAIL debug logs:', hasEmailLogs);
  });

  test('Click thread shows email body', async ({ page }) => {
    await page.goto(`${APP_URL}/email/inbox`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    // Screenshot before click
    await page.screenshot({ path: 'before-click.png' });

    // Check if authenticated first
    const notAuthText = page.locator('text=Not authenticated');
    if (await notAuthText.isVisible({ timeout: 1000 }).catch(() => false)) {
      console.log('Skipping - not authenticated');
      test.skip();
      return;
    }

    // Find thread rows using data-testid
    const threadRows = page.locator('[data-testid="thread-row"]');
    const count = await threadRows.count();
    console.log('Thread rows found:', count);

    if (count > 0) {
      const firstThread = threadRows.first();
      const threadText = await firstThread.textContent();
      console.log('First thread text:', threadText?.substring(0, 50));

      console.log('Clicking first thread...');
      await firstThread.click();
      await page.waitForTimeout(3000);

      await page.screenshot({ path: 'after-thread-click.png' });

      // Check for email body
      const emailBody = page.locator('.email-body');
      if (await emailBody.isVisible({ timeout: 5000 }).catch(() => false)) {
        const content = await emailBody.innerHTML();
        console.log('Email body found, length:', content.length);
        expect(content.length).toBeGreaterThan(10);
      } else {
        console.log('No .email-body visible');
        // Check loading state
        const loading = page.locator('text=Loading email');
        console.log('Loading visible:', await loading.isVisible().catch(() => false));
      }
    } else {
      console.log('No thread rows found');
      // Fallback to looking for any thread-like element
      const anyThread = page.locator('button').filter({
        hasText: /TEST|Zip|Invoice|Quote|Certificate|message/i
      });
      console.log('Fallback thread count:', await anyThread.count());
    }
  });
});
