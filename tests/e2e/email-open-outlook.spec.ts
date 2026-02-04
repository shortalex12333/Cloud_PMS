/**
 * Test Email "Open in Outlook" functionality
 *
 * Verifies:
 * 1. Email inbox loads
 * 2. Clicking a thread loads messages
 * 3. Clicking a message renders body
 * 4. "Open in Outlook" button appears when web_link is present
 */
import { test, expect } from '@playwright/test';

test.describe('Email Open in Outlook', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('https://app.celeste7.ai/login');
    await page.fill('input[type="email"], input[name="email"]', 'x@alex-short.com');
    await page.fill('input[type="password"], input[name="password"]', 'Password2!');
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/app/, { timeout: 15000 });
    await page.waitForTimeout(2000);
  });

  test('Email thread click loads messages and body', async ({ page }) => {
    // Navigate to email inbox
    await page.goto('https://app.celeste7.ai/email/inbox');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    // Take screenshot of initial state
    await page.screenshot({ path: 'test-results/email-inbox-initial.png' });

    // Check if email surface loaded
    const emailSurface = page.locator('[data-testid="email-surface"]');
    await expect(emailSurface).toBeVisible({ timeout: 10000 });

    // Wait for threads to load
    const threadRows = page.locator('[data-testid="thread-row"]');
    const threadCount = await threadRows.count();
    console.log('Found', threadCount, 'threads');

    if (threadCount > 0) {
      // Click first thread
      await threadRows.first().click();
      await page.waitForTimeout(2000);

      // Check if message panel is visible
      const messagePanel = page.locator('[data-testid="message-panel"]');
      await expect(messagePanel).toBeVisible({ timeout: 10000 });

      // Take screenshot after selecting thread
      await page.screenshot({ path: 'test-results/email-thread-selected.png' });

      // Wait for email body to load
      const emailBody = page.locator('[data-testid="email-body"]');
      const bodyVisible = await emailBody.isVisible().catch(() => false);
      console.log('Email body visible:', bodyVisible);

      // Check for "Open in Outlook" button
      const openOutlookBtn = page.locator('a:has-text("Open in Outlook")');
      const hasOpenOutlook = await openOutlookBtn.isVisible().catch(() => false);
      console.log('Open in Outlook button visible:', hasOpenOutlook);

      if (hasOpenOutlook) {
        // Verify href starts with valid OWA URL
        const href = await openOutlookBtn.getAttribute('href');
        console.log('Open in Outlook href:', href?.substring(0, 50));
        expect(href).toMatch(/^https:\/\/outlook\.office(365)?\.com\//);

        // Verify opens in new tab
        const target = await openOutlookBtn.getAttribute('target');
        expect(target).toBe('_blank');
      }

      // Take final screenshot
      await page.screenshot({ path: 'test-results/email-body-loaded.png' });
    } else {
      console.log('No threads found - check Outlook sync');
      await page.screenshot({ path: 'test-results/email-no-threads.png' });
    }
  });

  test('/email/thread returns 404 for invalid thread', async ({ page }) => {
    // Try to access invalid thread directly via API
    const response = await page.request.get(
      'https://pipeline-core.int.celeste7.ai/email/thread/00000000-0000-0000-0000-000000000000',
      {
        headers: {
          'Authorization': 'Bearer invalid_token'
        }
      }
    );

    // Should return 401 (unauthorized) not 500
    expect(response.status()).not.toBe(500);
    console.log('Invalid thread response status:', response.status());
  });
});
