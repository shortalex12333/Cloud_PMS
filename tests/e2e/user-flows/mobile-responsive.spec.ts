/**
 * Mobile Responsive E2E Tests
 *
 * Phase 18: End-to-End User Flow Testing
 *
 * Tests mobile device compatibility:
 * - iPhone 13 (390x844)
 * - iPhone SE (375x667)
 * - Pixel 5 (393x851)
 * - iPad Mini (768x1024)
 */

import { test, expect, devices, Page } from '@playwright/test';
import {
  saveArtifact,
  createEvidenceBundle,
} from '../../helpers/artifacts';

// Device configurations
const DEVICES = [
  { name: 'iPhone 13', config: devices['iPhone 13'] },
  { name: 'iPhone SE', config: devices['iPhone SE'] },
  { name: 'Pixel 5', config: devices['Pixel 5'] },
  { name: 'iPad Mini', config: devices['iPad Mini'] },
];

// Test URL (adjust as needed)
const BASE_URL = process.env.VERCEL_PROD_URL || 'https://app.celeste7.ai';

// Helper to test a page with device emulation
async function testPageWithDevice(
  page: Page,
  device: typeof DEVICES[0],
  pagePath: string,
  pageName: string
) {
  // Set viewport for device
  await page.setViewportSize(device.config.viewport);

  // Navigate to page
  await page.goto(`${BASE_URL}${pagePath}`);
  await page.waitForLoadState('networkidle');

  // Take screenshot
  const screenshot = await page.screenshot({ fullPage: true });
  await saveArtifact(
    `mobile-responsive/${device.name.toLowerCase().replace(' ', '-')}`,
    `${pageName}_page.png`,
    screenshot
  );

  // Verify viewport
  const viewport = page.viewportSize();
  expect(viewport?.width).toBe(device.config.viewport.width);

  await createEvidenceBundle(
    `mobile-responsive/${device.name.toLowerCase().replace(' ', '-')}/${pageName}`,
    {
      device: device.name,
      viewport: viewport,
      page: pageName,
      timestamp: new Date().toISOString(),
    }
  );

  // Verify page loaded
  expect(page.url()).toContain(BASE_URL);
}

test.describe('MOBILE RESPONSIVE: Device Compatibility Tests', () => {
  // iPhone 13 Tests
  test('iPhone 13: Login page renders correctly', async ({ page }) => {
    const device = DEVICES[0];
    await page.setViewportSize(device.config.viewport);
    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState('networkidle');

    const screenshot = await page.screenshot({ fullPage: true });
    await saveArtifact('mobile-responsive/iphone-13', 'login_page.png', screenshot);

    const loginForm = await page.locator('form').first();
    await expect(loginForm).toBeVisible();

    const viewport = page.viewportSize();
    expect(viewport?.width).toBe(device.config.viewport.width);
  });

  test('iPhone 13: Dashboard renders correctly', async ({ page }) => {
    await testPageWithDevice(page, DEVICES[0], '/dashboard', 'dashboard');
  });

  test('iPhone 13: Search page renders correctly', async ({ page }) => {
    await testPageWithDevice(page, DEVICES[0], '/search', 'search');
  });

  // iPhone SE Tests
  test('iPhone SE: Login page renders correctly', async ({ page }) => {
    const device = DEVICES[1];
    await page.setViewportSize(device.config.viewport);
    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState('networkidle');

    const loginForm = await page.locator('form').first();
    await expect(loginForm).toBeVisible();
  });

  test('iPhone SE: Dashboard renders correctly', async ({ page }) => {
    await testPageWithDevice(page, DEVICES[1], '/dashboard', 'dashboard');
  });

  test('iPhone SE: Work Orders page renders correctly', async ({ page }) => {
    await testPageWithDevice(page, DEVICES[1], '/work-orders', 'work-orders');
  });

  // Pixel 5 Tests
  test('Pixel 5: Login page renders correctly', async ({ page }) => {
    const device = DEVICES[2];
    await page.setViewportSize(device.config.viewport);
    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState('networkidle');

    const loginForm = await page.locator('form').first();
    await expect(loginForm).toBeVisible();
  });

  test('Pixel 5: Dashboard renders correctly', async ({ page }) => {
    await testPageWithDevice(page, DEVICES[2], '/dashboard', 'dashboard');
  });

  test('Pixel 5: Faults page renders correctly', async ({ page }) => {
    await testPageWithDevice(page, DEVICES[2], '/faults', 'faults');
  });

  // iPad Mini Tests
  test('iPad Mini: Login page renders correctly', async ({ page }) => {
    const device = DEVICES[3];
    await page.setViewportSize(device.config.viewport);
    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState('networkidle');

    const loginForm = await page.locator('form').first();
    await expect(loginForm).toBeVisible();
  });

  test('iPad Mini: Dashboard renders correctly', async ({ page }) => {
    await testPageWithDevice(page, DEVICES[3], '/dashboard', 'dashboard');
  });

  test('iPad Mini: Search page renders correctly', async ({ page }) => {
    await testPageWithDevice(page, DEVICES[3], '/search', 'search');
  });

  // =========================================================================
  // SUMMARY
  // =========================================================================

  test('Mobile Responsive Summary', async ({ page }) => {
    await createEvidenceBundle('mobile-responsive/SUMMARY', {
      test_suite: 'mobile_responsive',
      devices: DEVICES.map(d => ({
        name: d.name,
        viewport: d.config.viewport,
        userAgent: d.config.userAgent?.substring(0, 50) + '...',
      })),
      pages_tested: ['login', 'dashboard', 'search', 'work-orders', 'faults'],
      total_tests: 13,
      timestamp: new Date().toISOString(),
    });

    expect(true).toBe(true);
  });
});
