import { test, expect } from '../fixtures';

/**
 * SHARD 6: Email Button Navigation Tests
 *
 * Tests the email button in the utility bar navigates to /email route.
 *
 * NOTE: Email route functionality (inbox, threads, linking, attachments)
 * is tested in shard-31-fragmented-routes/route-email.spec.ts (19 tests).
 *
 * This shard only tests the button exists and navigates correctly.
 */

test.describe('Email Button', () => {
  test('should display email button in utility bar', async ({ page }) => {
    await page.goto('/');
    const emailButton = page.getByTestId('utility-email-button');
    await expect(emailButton).toBeVisible();
  });

  test('should navigate to /email when clicked', async ({ page }) => {
    await page.goto('/');

    const emailButton = page.getByTestId('utility-email-button');
    await emailButton.click();

    // Should navigate to email route (or /app if feature flag disabled)
    await page.waitForURL(/\/(email|app)/, { timeout: 10_000 });
    expect(page.url()).toMatch(/\/(email|app)/);
  });
});
