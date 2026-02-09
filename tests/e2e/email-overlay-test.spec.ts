/**
 * Quick test for email overlay functionality
 */
import { test, expect } from '@playwright/test';

test.describe('Email Overlay Test', () => {
  test('clicking email button opens overlay', async ({ page }) => {
    // Go to app
    await page.goto('/app');
    await page.waitForTimeout(3000);

    // Log page HTML structure
    const html = await page.content();
    console.log('Page has email-overlay element:', html.includes('email-overlay'));
    console.log('Page has email-surface element:', html.includes('email-surface'));
    console.log('Page has SurfaceProvider:', html.includes('SurfaceProvider'));

    // Find and click email toggle
    const emailToggle = page.locator('[data-testid="email-scope-toggle"]');
    await expect(emailToggle).toBeVisible();
    console.log('Email toggle found');

    // Check console for errors
    page.on('console', msg => console.log('Browser:', msg.type(), msg.text()));

    // Click it
    await emailToggle.click();
    await page.waitForTimeout(2000);

    // Take screenshot before checks
    await page.screenshot({ path: 'test-results/email-overlay-test.png', fullPage: true });

    // Log HTML after click
    const htmlAfter = await page.content();
    console.log('After click - has email-overlay:', htmlAfter.includes('data-testid="email-overlay"'));
    console.log('After click - has visible overlay:', htmlAfter.includes('translate-x-0'));

    // Check for email overlay
    const emailOverlay = page.locator('[data-testid="email-overlay"]');
    const overlayCount = await emailOverlay.count();
    console.log('Email overlay count:', overlayCount);

    const isVisible = await emailOverlay.isVisible().catch(() => false);
    console.log('Email overlay visible:', isVisible);

    // Check for email surface inside overlay
    const emailSurface = page.locator('[data-testid="email-surface"]');
    const surfaceCount = await emailSurface.count();
    console.log('Email surface count:', surfaceCount);

    const surfaceVisible = await emailSurface.isVisible().catch(() => false);
    console.log('Email surface visible:', surfaceVisible);

    // Check for email-inbox (old behavior)
    const emailInbox = page.locator('[data-testid="email-inbox"]');
    const inboxVisible = await emailInbox.isVisible().catch(() => false);
    console.log('Email inbox (old) visible:', inboxVisible);

    expect(isVisible || surfaceVisible).toBe(true);
  });
});
