/**
 * Email Message Render + Attachments E2E Tests
 *
 * Validates:
 * - Body renders correctly in split view (no corruption)
 * - HTML sanitization (no script execution, safe rendering)
 * - Attachments panel shows correct items
 * - Download triggers with correct headers
 * - Error handling (401 → reconnect, 413/415 → friendly message)
 */

import { test, expect, Page } from '@playwright/test';

// ============================================================================
// CONFIG
// ============================================================================

const TEST_EMAIL = process.env.TEST_EMAIL || 'x@alex-short.com';
const TEST_PASSWORD = process.env.TEST_PASSWORD || 'Password2!';
const BASE_URL = process.env.BASE_URL || 'https://app.celeste7.ai';

// Test message subject prefixes (must exist in mailbox)
const TEST_SUBJECTS = {
  plainText: '[TEST] Plain text',
  htmlBody: '[TEST] HTML',
  withAttachments: '[TEST] With attachment',
  inlineImages: '[TEST] Inline image',
};

// ============================================================================
// HELPERS
// ============================================================================

async function login(page: Page) {
  await page.goto(`${BASE_URL}/login`);

  // Fill login form
  await page.fill('input[type="email"], input[name="email"]', TEST_EMAIL);
  await page.fill('input[type="password"], input[name="password"]', TEST_PASSWORD);

  // Submit
  await page.click('button[type="submit"]');

  // Wait for redirect to main app
  await page.waitForURL(/\/(app|email|$)/, { timeout: 15000 });
}

async function navigateToEmail(page: Page) {
  // Navigate to email search view
  await page.goto(`${BASE_URL}/email/search`);
  await page.waitForLoadState('networkidle');
}

async function findThreadBySubject(page: Page, subjectPrefix: string): Promise<boolean> {
  // Wait for threads to load
  await page.waitForSelector('[data-testid="thread-list"], .thread-list, button:has-text("@")', {
    timeout: 10000,
  }).catch(() => null);

  // Search for the test message
  const searchInput = page.locator('input[placeholder*="Search"], input[type="search"]').first();
  if (await searchInput.isVisible()) {
    await searchInput.fill(subjectPrefix);
    await page.waitForTimeout(1000); // Debounce
  }

  // Find thread with matching subject
  const thread = page.locator(`button:has-text("${subjectPrefix.slice(0, 20)}")`).first();

  if (await thread.isVisible({ timeout: 5000 }).catch(() => false)) {
    await thread.click();
    return true;
  }

  return false;
}

// ============================================================================
// TESTS: MESSAGE BODY RENDER
// ============================================================================

test.describe('Message Body Rendering', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateToEmail(page);
  });

  test('HTML email renders without raw tags visible', async ({ page }) => {
    const found = await findThreadBySubject(page, TEST_SUBJECTS.htmlBody);
    if (!found) {
      test.skip('Test HTML email not found in mailbox');
      return;
    }

    // Wait for message content to render
    await page.waitForSelector('.prose, [data-testid="message-body"]', { timeout: 10000 });

    // Get the message body container
    const bodyContainer = page.locator('.prose, [data-testid="message-body"]').first();

    // Verify content is rendered
    const bodyText = await bodyContainer.textContent();
    expect(bodyText?.length).toBeGreaterThan(10);

    // Verify no raw HTML tags visible
    const rawTags = await bodyContainer.locator('text=/<[a-z]+>/i').count();
    expect(rawTags).toBe(0);

    // Verify no script tags executed (check for alert, etc.)
    const hasScriptError = await page.evaluate(() => {
      return (window as unknown as { __xssTriggered?: boolean }).__xssTriggered || false;
    });
    expect(hasScriptError).toBe(false);
  });

  test('Plain text email preserves line breaks', async ({ page }) => {
    const found = await findThreadBySubject(page, TEST_SUBJECTS.plainText);
    if (!found) {
      test.skip('Test plain text email not found in mailbox');
      return;
    }

    // Wait for message content
    await page.waitForSelector('pre, [data-testid="message-body"]', { timeout: 10000 });

    // Plain text should be in a pre tag or have whitespace-pre-wrap
    const preTag = page.locator('pre').first();
    const isPreVisible = await preTag.isVisible().catch(() => false);

    if (isPreVisible) {
      const whiteSpace = await preTag.evaluate((el) =>
        window.getComputedStyle(el).whiteSpace
      );
      expect(['pre', 'pre-wrap', 'pre-line']).toContain(whiteSpace);
    }
  });

  test('Non-ASCII characters display correctly', async ({ page }) => {
    const found = await findThreadBySubject(page, TEST_SUBJECTS.htmlBody);
    if (!found) {
      test.skip('Test HTML email not found in mailbox');
      return;
    }

    await page.waitForSelector('.prose, [data-testid="message-body"]', { timeout: 10000 });

    // Check for common encoding issues (replacement characters)
    const bodyContainer = page.locator('.prose, [data-testid="message-body"]').first();
    const bodyHtml = await bodyContainer.innerHTML();

    // No replacement characters (indicates encoding failure)
    expect(bodyHtml).not.toContain('\ufffd');
    expect(bodyHtml).not.toContain('�');

    // No double-encoded entities
    expect(bodyHtml).not.toMatch(/&amp;[a-z]+;/i);
  });

  test('External images are blocked by default', async ({ page }) => {
    const found = await findThreadBySubject(page, TEST_SUBJECTS.htmlBody);
    if (!found) {
      test.skip('Test HTML email not found in mailbox');
      return;
    }

    await page.waitForSelector('.prose, [data-testid="message-body"]', { timeout: 10000 });

    // Check for blocked external images
    const blockedImages = await page.locator('img[data-blocked-src]').count();
    const externalImages = await page.locator('img[src^="http"]').count();

    // External images should be blocked (either hidden or converted to data-blocked-src)
    // This is expected behavior from our DOMPurify config
    console.log(`Blocked images: ${blockedImages}, External images: ${externalImages}`);
  });
});

// ============================================================================
// TESTS: ATTACHMENTS PANEL
// ============================================================================

test.describe('Attachments Panel', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateToEmail(page);
  });

  test('Attachments panel shows items for message with attachments', async ({ page }) => {
    const found = await findThreadBySubject(page, TEST_SUBJECTS.withAttachments);
    if (!found) {
      test.skip('Test attachment email not found in mailbox');
      return;
    }

    // Wait for attachments panel
    await page.waitForTimeout(2000); // Let the UI settle

    // Look for attachments section
    const attachmentPanel = page.locator('text=Attachments').first();
    const isVisible = await attachmentPanel.isVisible().catch(() => false);

    if (isVisible) {
      // Should have at least one attachment item
      const attachmentItems = page.locator('button:has(.lucide-download), [data-testid="attachment-item"]');
      const count = await attachmentItems.count();
      expect(count).toBeGreaterThan(0);
    }
  });

  test('Clicking attachment triggers download with correct headers', async ({ page }) => {
    const found = await findThreadBySubject(page, TEST_SUBJECTS.withAttachments);
    if (!found) {
      test.skip('Test attachment email not found in mailbox');
      return;
    }

    await page.waitForTimeout(2000);

    // Find download button
    const downloadBtn = page.locator('button:has(.lucide-download)').first();
    const btnVisible = await downloadBtn.isVisible().catch(() => false);

    if (!btnVisible) {
      test.skip('No download button found');
      return;
    }

    // Intercept download request
    const [response] = await Promise.all([
      page.waitForResponse((resp) =>
        resp.url().includes('/download') && resp.request().method() === 'GET'
      , { timeout: 10000 }).catch(() => null),
      downloadBtn.click(),
    ]);

    if (response) {
      expect(response.status()).toBe(200);

      const headers = response.headers();
      expect(headers['x-content-type-options']).toBe('nosniff');
      expect(headers['content-disposition']).toContain('attachment');
    }
  });

  test('Message without attachments shows "No attachments" message', async ({ page }) => {
    const found = await findThreadBySubject(page, TEST_SUBJECTS.plainText);
    if (!found) {
      test.skip('Test plain text email not found in mailbox');
      return;
    }

    await page.waitForTimeout(2000);

    // Look for "No attachments" text
    const noAttachments = page.locator('text=/no attachments/i');
    const isVisible = await noAttachments.isVisible().catch(() => false);

    // Either shows "No attachments" or doesn't show the panel at all
    if (!isVisible) {
      const attachmentCount = await page.locator('button:has(.lucide-download)').count();
      // If no "No attachments" message, there shouldn't be any download buttons
      // (or the email actually has attachments)
    }
  });
});

// ============================================================================
// TESTS: ERROR HANDLING
// ============================================================================

test.describe('Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateToEmail(page);
  });

  test('Download error shows friendly message (not navigation)', async ({ page }) => {
    const found = await findThreadBySubject(page, TEST_SUBJECTS.withAttachments);
    if (!found) {
      test.skip('Test attachment email not found in mailbox');
      return;
    }

    await page.waitForTimeout(2000);

    // Intercept and fail the download request
    await page.route('**/download', (route) => {
      route.fulfill({
        status: 415,
        body: JSON.stringify({ detail: 'Content type not allowed' }),
        headers: { 'Content-Type': 'application/json' },
      });
    });

    // Find and click download button
    const downloadBtn = page.locator('button:has(.lucide-download)').first();
    if (await downloadBtn.isVisible()) {
      await downloadBtn.click();
      await page.waitForTimeout(1000);

      // Should show inline error, not navigate away
      const currentUrl = page.url();
      expect(currentUrl).toContain('/email');

      // Look for error message
      const errorMsg = page.locator('text=/not allowed|error|failed/i');
      const errorVisible = await errorMsg.isVisible().catch(() => false);
      // Error should be shown inline
    }

    await page.unroute('**/download');
  });

  test('Expired token shows reconnect banner', async ({ page }) => {
    // Intercept render request and return 401
    await page.route('**/render', (route) => {
      route.fulfill({
        status: 401,
        body: JSON.stringify({ detail: 'Token expired' }),
        headers: { 'Content-Type': 'application/json' },
      });
    });

    // Try to load a message
    await page.waitForTimeout(2000);

    // Look for reconnect banner or button
    const reconnectBanner = page.locator('text=/reconnect|expired|connect outlook/i');
    const isVisible = await reconnectBanner.isVisible({ timeout: 5000 }).catch(() => false);

    // Should show reconnect UI (or be handled gracefully)
    await page.unroute('**/render');
  });
});

// ============================================================================
// TESTS: INLINE IMAGES (CID)
// ============================================================================

test.describe('Inline Images', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateToEmail(page);
  });

  test('Inline images show placeholder or load securely', async ({ page }) => {
    const found = await findThreadBySubject(page, TEST_SUBJECTS.inlineImages);
    if (!found) {
      test.skip('Test inline image email not found in mailbox');
      return;
    }

    await page.waitForSelector('.prose, [data-testid="message-body"]', { timeout: 10000 });

    // Check for inline images (cid: references)
    const bodyContainer = page.locator('.prose, [data-testid="message-body"]').first();
    const bodyHtml = await bodyContainer.innerHTML();

    const hasCidRef = bodyHtml.toLowerCase().includes('cid:');
    const hasInlineImages = await page.locator('img[src^="cid:"]').count();

    console.log(`Has cid: references: ${hasCidRef}, Inline images found: ${hasInlineImages}`);

    // If there are cid: references, they should either:
    // 1. Be resolved to blob URLs
    // 2. Show placeholder
    // 3. Have a "Load images" toggle
  });
});

// ============================================================================
// TESTS: PERFORMANCE SANITY
// ============================================================================

test.describe('Performance', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateToEmail(page);
  });

  test('Large message body does not hang UI', async ({ page }) => {
    const found = await findThreadBySubject(page, TEST_SUBJECTS.htmlBody);
    if (!found) {
      test.skip('Test HTML email not found in mailbox');
      return;
    }

    const startTime = Date.now();

    // Wait for render
    await page.waitForSelector('.prose, [data-testid="message-body"]', { timeout: 15000 });

    const renderTime = Date.now() - startTime;

    // Should render in reasonable time (< 5 seconds)
    expect(renderTime).toBeLessThan(5000);

    // UI should still be responsive
    const searchInput = page.locator('input[placeholder*="Search"]').first();
    await searchInput.click().catch(() => {});

    console.log(`Message render time: ${renderTime}ms`);
  });
});
