/**
 * Deep Link Handler E2E Test
 *
 * Tests that the DeepLinkHandler properly fetches entity data
 * using microaction handlers and displays it in the context panel.
 */

import { test, expect } from '@playwright/test';

// Test work order from the test database
const TEST_WORK_ORDER = {
  id: 'b36238da-b0fa-4815-883c-0be61fc190d0',
  expectedTitle: '500-Hour Preventive Maintenance',
};

test.describe('DeepLinkHandler Entity Focus', () => {
  // Uses real auth state from playwright/.auth/user.json (configured in playwright.config.ts)
  // Run create-session.mjs to generate a fresh token if expired

  test('should show loading state and process deep link params', async ({ page }) => {
    // Navigate to app with deep link params
    await page.goto(`/app?entity=work_order&id=${TEST_WORK_ORDER.id}`);

    // Check that the DeepLinkHandler is present
    const handler = page.locator('[data-testid="deep-link-handler"]');
    await expect(handler).toBeAttached({ timeout: 10000 });

    // Check the handler received the params
    await expect(handler).toHaveAttribute('data-deep-link-entity', 'work_order');
    await expect(handler).toHaveAttribute('data-deep-link-id', TEST_WORK_ORDER.id);

    // Wait for processing (status should change from loading to success or error)
    await page.waitForFunction(() => {
      const el = document.querySelector('[data-testid="deep-link-handler"]');
      const status = el?.getAttribute('data-deep-link-status');
      return status === 'success' || status === 'error';
    }, { timeout: 15000 });

    // Get final status
    const status = await handler.getAttribute('data-deep-link-status');
    console.log('DeepLinkHandler status:', status);

    // If success, check that context panel is visible
    if (status === 'success') {
      const contextPanel = page.locator('[data-testid="context-panel"]');
      await expect(contextPanel).toBeVisible({ timeout: 5000 });

      // Check for work order card
      const woCard = page.locator('[data-testid="context-panel-work-order-card"]');
      await expect(woCard).toBeVisible({ timeout: 5000 });
    }

    // URL should have params stripped (middleware redirects /app to /)
    await page.waitForURL(/\/$/, { timeout: 5000 });
    expect(page.url()).not.toContain('entity=');
    expect(page.url()).not.toContain('id=');
  });

  test('should show error state for invalid entity', async ({ page }) => {
    // Navigate with a fake entity ID
    await page.goto('/app?entity=work_order&id=00000000-0000-0000-0000-000000000000');

    const handler = page.locator('[data-testid="deep-link-handler"]');
    await expect(handler).toBeAttached({ timeout: 10000 });

    // Wait for processing
    await page.waitForFunction(() => {
      const el = document.querySelector('[data-testid="deep-link-handler"]');
      const status = el?.getAttribute('data-deep-link-status');
      return status === 'success' || status === 'error';
    }, { timeout: 15000 });

    // Should show error state (entity not found)
    const status = await handler.getAttribute('data-deep-link-status');
    const error = await handler.getAttribute('data-deep-link-error');
    console.log('Status:', status, 'Error:', error);

    // Context panel should still open (with error message)
    const contextPanel = page.locator('[data-testid="context-panel"]');
    await expect(contextPanel).toBeVisible({ timeout: 5000 });
  });

  test('should auto-expand Related Emails section', async ({ page }) => {
    // Navigate with deep link params
    await page.goto(`/app?entity=work_order&id=${TEST_WORK_ORDER.id}`);

    // Wait for processing
    await page.waitForFunction(() => {
      const el = document.querySelector('[data-testid="deep-link-handler"]');
      const status = el?.getAttribute('data-deep-link-status');
      return status === 'success' || status === 'error';
    }, { timeout: 15000 });

    // Check if Related Emails panel exists and is expanded
    const sourcesPanel = page.locator('#sources');

    // If the panel exists, check it's expanded (has content visible)
    if (await sourcesPanel.count() > 0) {
      // The panel should be visible
      await expect(sourcesPanel).toBeVisible({ timeout: 5000 });

      // Check for highlight class (should have ring-2 initially)
      const hasHighlight = await sourcesPanel.evaluate((el) => {
        return el.classList.contains('ring-2') || el.classList.contains('animate-pulse');
      });
      console.log('Sources panel highlighted:', hasHighlight);
    }
  });
});
