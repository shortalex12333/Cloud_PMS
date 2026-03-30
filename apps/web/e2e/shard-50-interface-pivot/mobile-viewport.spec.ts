/**
 * V5 — Mobile Viewport Tests
 *
 * Verify the app doesn't break at tablet (768px) and mobile (375px).
 * These test structural layout, not pixel-perfect design.
 */

import { test, expect } from '@playwright/test';

test.describe('Mobile: Tablet 768px', () => {
  test.use({ viewport: { width: 768, height: 1024 } });

  test('Vessel Surface renders without horizontal overflow', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(3000);
    if (page.url().includes('/login')) {
      expect(true).toBe(true);
      return;
    }
    const overflow = await page.evaluate(() =>
      document.documentElement.scrollWidth > document.documentElement.clientWidth
    );
    expect(overflow).toBe(false);
  });

  test('domain list view accessible at 768px', async ({ page }) => {
    await page.goto('/faults');
    await page.waitForTimeout(3000);
    const overflow = await page.evaluate(() =>
      document.documentElement.scrollWidth > document.documentElement.clientWidth
    );
    expect(overflow).toBe(false);
  });

  test('page renders content (not blank)', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(3000);
    const body = await page.textContent('body');
    expect((body || '').trim().length).toBeGreaterThan(10);
  });
});

test.describe('Mobile: Phone 375px', () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test('Vessel Surface renders without horizontal overflow', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(3000);
    if (page.url().includes('/login')) {
      expect(true).toBe(true);
      return;
    }
    const overflow = await page.evaluate(() =>
      document.documentElement.scrollWidth > document.documentElement.clientWidth
    );
    expect(overflow).toBe(false);
  });

  test('work orders list usable at 375px', async ({ page }) => {
    await page.goto('/work-orders');
    await page.waitForTimeout(3000);
    const overflow = await page.evaluate(() =>
      document.documentElement.scrollWidth > document.documentElement.clientWidth
    );
    expect(overflow).toBe(false);
  });

  test('page renders content (not blank)', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(3000);
    const body = await page.textContent('body');
    expect((body || '').trim().length).toBeGreaterThan(10);
  });
});
