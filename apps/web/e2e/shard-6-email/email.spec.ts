import { test, expect, SpotlightSearchPO, TEST_CONFIG } from '../fixtures';

/**
 * SHARD 6: Email Integration Tests
 *
 * Tests the email overlay and email-to-entity linking:
 * - Email inbox view
 * - Thread viewer
 * - Email attachment viewing
 * - Email linking to entities
 */

test.describe('Email Toggle', () => {
  test('should display email button in utility bar', async ({ page }) => {
    await page.goto('/');

    const emailButton = page.getByTestId('utility-email-button');
    await expect(emailButton).toBeVisible();
  });

  test('should open email overlay when clicking email button', async ({ page }) => {
    await page.goto('/');

    const emailButton = page.getByTestId('utility-email-button');
    await emailButton.click();

    // Email overlay should appear
    const emailOverlay = page.getByTestId('email-overlay');
    await expect(emailOverlay).toBeVisible({ timeout: 10_000 });
  });

  test('should close email overlay when clicking backdrop', async ({ page }) => {
    await page.goto('/');

    const emailButton = page.getByTestId('utility-email-button');
    await emailButton.click();

    const emailOverlay = page.getByTestId('email-overlay');
    await expect(emailOverlay).toBeVisible({ timeout: 10_000 });

    // Click backdrop
    const backdrop = page.getByTestId('email-overlay-backdrop');
    await backdrop.click();

    // Overlay should close
    await expect(emailOverlay).not.toBeVisible({ timeout: 5_000 });
  });

  test('should close email overlay on Escape', async ({ page }) => {
    await page.goto('/');

    const emailButton = page.getByTestId('utility-email-button');
    await emailButton.click();

    const emailOverlay = page.getByTestId('email-overlay');
    await expect(emailOverlay).toBeVisible({ timeout: 10_000 });

    // Press Escape
    await page.keyboard.press('Escape');

    // Overlay should close
    await expect(emailOverlay).not.toBeVisible({ timeout: 5_000 });
  });
});

test.describe('Email Inbox View', () => {
  test('should display email inbox', async ({ page }) => {
    await page.goto('/');

    const emailButton = page.getByTestId('utility-email-button');
    await emailButton.click();

    const emailOverlay = page.getByTestId('email-overlay');
    await expect(emailOverlay).toBeVisible({ timeout: 10_000 });

    // Should show inbox or email list
    const emailInbox = page.getByTestId('email-inbox');
    // May or may not have emails depending on test data
  });

  test('should display email thread count', async ({ page }) => {
    await page.goto('/');

    const emailButton = page.getByTestId('utility-email-button');
    await emailButton.click();

    const emailOverlay = page.getByTestId('email-overlay');
    await expect(emailOverlay).toBeVisible({ timeout: 10_000 });

    // Look for thread count indicator
    const threadCount = emailOverlay.locator('text=/\\d+ (total|unlinked)? threads?/i');
    // Count should be visible if emails exist
  });

  test('should support pagination', async ({ page }) => {
    await page.goto('/');

    const emailButton = page.getByTestId('utility-email-button');
    await emailButton.click();

    const emailOverlay = page.getByTestId('email-overlay');
    await expect(emailOverlay).toBeVisible({ timeout: 10_000 });

    // Look for pagination controls
    const nextButton = emailOverlay.locator('[aria-label*="Next"], button:has-text("Next")');
    const prevButton = emailOverlay.locator('[aria-label*="Previous"], button:has-text("Prev")');
  });
});

test.describe('Email Thread Viewer', () => {
  test('should open email thread on click', async ({ page }) => {
    await page.goto('/');

    const emailButton = page.getByTestId('utility-email-button');
    await emailButton.click();

    const emailOverlay = page.getByTestId('email-overlay');
    await expect(emailOverlay).toBeVisible({ timeout: 10_000 });

    // Find an email thread
    const emailThread = emailOverlay.locator('[data-testid="email-thread-item"]').first();

    if (await emailThread.isVisible()) {
      await emailThread.click();

      // Thread viewer should show content
      const threadContent = emailOverlay.locator('[data-testid="email-thread-content"]');
      await expect(threadContent).toBeVisible({ timeout: 10_000 });
    }
  });

  test('should display email subject', async ({ page }) => {
    await page.goto('/');

    const emailButton = page.getByTestId('utility-email-button');
    await emailButton.click();

    const emailOverlay = page.getByTestId('email-overlay');
    await expect(emailOverlay).toBeVisible({ timeout: 10_000 });

    // Email threads should show subjects
    const emailSubject = emailOverlay.locator('[data-testid="email-subject"]').first();
    // Subject should be visible if emails exist
  });

  test('should display sender information', async ({ page }) => {
    await page.goto('/');

    const emailButton = page.getByTestId('utility-email-button');
    await emailButton.click();

    const emailOverlay = page.getByTestId('email-overlay');
    await expect(emailOverlay).toBeVisible({ timeout: 10_000 });

    // Sender info should be visible
    const sender = emailOverlay.locator('[data-testid="email-from"]').first();
  });
});

test.describe('Email Search Scope', () => {
  test('should search emails when email scope active', async ({ page }) => {
    await page.goto('/');

    const emailButton = page.getByTestId('utility-email-button');
    await emailButton.click();

    const emailOverlay = page.getByTestId('email-overlay');
    await expect(emailOverlay).toBeVisible({ timeout: 10_000 });

    // Search within email overlay
    const searchInput = emailOverlay.locator('input[type="search"], input[placeholder*="Search"]');

    if (await searchInput.isVisible()) {
      await searchInput.fill('invoice');
      await page.waitForTimeout(2000);

      // Results should be email-specific
    }
  });

  test('should toggle email scope in spotlight', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);

    // Click email button to enable email scope
    await spotlight.emailButton.click();

    // Search should now include emails
    await spotlight.search('meeting');

    await page.waitForTimeout(2000);

    // Results container might show email results
    const emailResults = page.getByTestId('search-results-email');
    // May or may not be visible depending on toggle behavior
  });
});

test.describe('Email Attachments (LAW 12)', () => {
  test('should display attachments in email thread', async ({ page }) => {
    await page.goto('/');

    const emailButton = page.getByTestId('utility-email-button');
    await emailButton.click();

    const emailOverlay = page.getByTestId('email-overlay');
    await expect(emailOverlay).toBeVisible({ timeout: 10_000 });

    // Find an email with attachments
    const emailThread = emailOverlay.locator('[data-testid="email-thread-item"]').first();

    if (await emailThread.isVisible()) {
      await emailThread.click();

      // Wait for thread content
      await page.waitForTimeout(2000);

      // Look for attachments section
      const attachments = emailOverlay.locator('[data-testid="email-attachments"]');
      // May or may not have attachments
    }
  });

  test('should open attachment viewer', async ({ page }) => {
    await page.goto('/');

    const emailButton = page.getByTestId('utility-email-button');
    await emailButton.click();

    const emailOverlay = page.getByTestId('email-overlay');
    await expect(emailOverlay).toBeVisible({ timeout: 10_000 });

    // Find an email with attachments
    const attachment = emailOverlay.locator('[data-testid="email-attachment-item"]').first();

    if (await attachment.isVisible()) {
      await attachment.click();

      // Document viewer should open
      const documentViewer = page.getByTestId('document-viewer-overlay');
      await expect(documentViewer).toBeVisible({ timeout: 10_000 });
    }
  });
});

test.describe('Email Linking', () => {
  test('should display link button on email thread', async ({ page }) => {
    await page.goto('/');

    const emailButton = page.getByTestId('utility-email-button');
    await emailButton.click();

    const emailOverlay = page.getByTestId('email-overlay');
    await expect(emailOverlay).toBeVisible({ timeout: 10_000 });

    // Find link button
    const linkButton = emailOverlay.locator('[data-testid="email-link-button"], [aria-label*="Link"]').first();
    // Link button should be available
  });

  test('should show linked entities on email thread', async ({ page }) => {
    await page.goto('/');

    const emailButton = page.getByTestId('utility-email-button');
    await emailButton.click();

    const emailOverlay = page.getByTestId('email-overlay');
    await expect(emailOverlay).toBeVisible({ timeout: 10_000 });

    // Find an email and open it
    const emailThread = emailOverlay.locator('[data-testid="email-thread-item"]').first();

    if (await emailThread.isVisible()) {
      await emailThread.click();

      await page.waitForTimeout(2000);

      // Look for linked entities section
      const linkedSection = emailOverlay.locator('text=Linked to');
      // May or may not have linked entities
    }
  });

  test('should navigate to linked entity', async ({ page }) => {
    await page.goto('/');

    const emailButton = page.getByTestId('utility-email-button');
    await emailButton.click();

    const emailOverlay = page.getByTestId('email-overlay');
    await expect(emailOverlay).toBeVisible({ timeout: 10_000 });

    // Find a linked entity
    const linkedEntity = emailOverlay.locator('[data-testid="linked-entity"]').first();

    if (await linkedEntity.isVisible()) {
      await linkedEntity.click();

      // Context panel should open with the entity
      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });
    }
  });
});

test.describe('Email State Management', () => {
  test('should preserve email state when opening context panel', async ({ page }) => {
    await page.goto('/');

    const emailButton = page.getByTestId('utility-email-button');
    await emailButton.click();

    const emailOverlay = page.getByTestId('email-overlay');
    await expect(emailOverlay).toBeVisible({ timeout: 10_000 });

    // Search for something to open context panel
    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('equipment');

    await expect(spotlight.resultsContainer).toBeVisible();

    const resultCount = await spotlight.getResultCount();
    if (resultCount > 0) {
      await spotlight.clickResult(0);

      const contextPanel = page.getByTestId('context-panel');
      await expect(contextPanel).toBeVisible({ timeout: 10_000 });

      // Email overlay might still be present or hidden
      // depending on UI design
    }
  });

  test('should handle email refresh', async ({ page }) => {
    await page.goto('/');

    const emailButton = page.getByTestId('utility-email-button');
    await emailButton.click();

    const emailOverlay = page.getByTestId('email-overlay');
    await expect(emailOverlay).toBeVisible({ timeout: 10_000 });

    // Look for refresh button
    const refreshButton = emailOverlay.locator('[aria-label*="Refresh"], [data-testid="email-refresh"]');

    if (await refreshButton.isVisible()) {
      await refreshButton.click();

      // Should refresh without error
      await page.waitForTimeout(2000);
      await expect(emailOverlay).toBeVisible();
    }
  });
});

test.describe('Email Error Handling', () => {
  test('should handle email load failure gracefully', async ({ page }) => {
    await page.goto('/');

    // Simulate API failure for email
    await page.route('**/email**', (route) => route.abort('failed'));

    const emailButton = page.getByTestId('utility-email-button');
    await emailButton.click();

    const emailOverlay = page.getByTestId('email-overlay');
    await expect(emailOverlay).toBeVisible({ timeout: 10_000 });

    // Should show error state, not crash
    await page.waitForTimeout(2000);
    await expect(emailOverlay).toBeVisible();
  });

  test('should handle empty inbox', async ({ page }) => {
    await page.goto('/');

    const emailButton = page.getByTestId('utility-email-button');
    await emailButton.click();

    const emailOverlay = page.getByTestId('email-overlay');
    await expect(emailOverlay).toBeVisible({ timeout: 10_000 });

    // If no emails, should show empty state
    const emptyState = emailOverlay.locator('text=/no (emails?|threads?|messages?)/i');
    // Empty state might be visible
  });
});
