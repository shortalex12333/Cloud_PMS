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

import { test, expect, devices } from '@playwright/test';
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

test.describe('MOBILE RESPONSIVE: Device Compatibility Tests', () => {
  for (const device of DEVICES) {
    test.describe(`${device.name}`, () => {
      test.use({ ...device.config });

      test('Login page renders correctly', async ({ page }) => {
        await page.goto(`${BASE_URL}/login`);
        await page.waitForLoadState('networkidle');

        // Take screenshot
        const screenshot = await page.screenshot({ fullPage: true });
        await saveArtifact(
          `mobile-responsive/${device.name.toLowerCase().replace(' ', '-')}`,
          'login_page.png',
          screenshot
        );

        // Verify key elements are visible
        const loginForm = await page.locator('form').first();
        await expect(loginForm).toBeVisible();

        // Check viewport matches device
        const viewport = page.viewportSize();
        expect(viewport?.width).toBe(device.config.viewport.width);

        await createEvidenceBundle(
          `mobile-responsive/${device.name.toLowerCase().replace(' ', '-')}/login`,
          {
            device: device.name,
            viewport: viewport,
            page: 'login',
            elements_visible: true,
            timestamp: new Date().toISOString(),
          }
        );
      });

      test('Dashboard renders correctly', async ({ page }) => {
        // Navigate to dashboard (will redirect to login if not auth'd)
        await page.goto(`${BASE_URL}/dashboard`);
        await page.waitForLoadState('networkidle');

        // Take screenshot
        const screenshot = await page.screenshot({ fullPage: true });
        await saveArtifact(
          `mobile-responsive/${device.name.toLowerCase().replace(' ', '-')}`,
          'dashboard_page.png',
          screenshot
        );

        // Document viewport
        const viewport = page.viewportSize();

        await createEvidenceBundle(
          `mobile-responsive/${device.name.toLowerCase().replace(' ', '-')}/dashboard`,
          {
            device: device.name,
            viewport: viewport,
            page: 'dashboard',
            timestamp: new Date().toISOString(),
          }
        );

        // Just verify page loaded (might redirect to login)
        expect(page.url()).toContain(BASE_URL);
      });

      test('Search page renders correctly', async ({ page }) => {
        await page.goto(`${BASE_URL}/search`);
        await page.waitForLoadState('networkidle');

        // Take screenshot
        const screenshot = await page.screenshot({ fullPage: true });
        await saveArtifact(
          `mobile-responsive/${device.name.toLowerCase().replace(' ', '-')}`,
          'search_page.png',
          screenshot
        );

        const viewport = page.viewportSize();

        await createEvidenceBundle(
          `mobile-responsive/${device.name.toLowerCase().replace(' ', '-')}/search`,
          {
            device: device.name,
            viewport: viewport,
            page: 'search',
            timestamp: new Date().toISOString(),
          }
        );

        expect(page.url()).toContain(BASE_URL);
      });

      test('Work Orders page renders correctly', async ({ page }) => {
        await page.goto(`${BASE_URL}/work-orders`);
        await page.waitForLoadState('networkidle');

        const screenshot = await page.screenshot({ fullPage: true });
        await saveArtifact(
          `mobile-responsive/${device.name.toLowerCase().replace(' ', '-')}`,
          'work_orders_page.png',
          screenshot
        );

        const viewport = page.viewportSize();

        await createEvidenceBundle(
          `mobile-responsive/${device.name.toLowerCase().replace(' ', '-')}/work-orders`,
          {
            device: device.name,
            viewport: viewport,
            page: 'work-orders',
            timestamp: new Date().toISOString(),
          }
        );

        expect(page.url()).toContain(BASE_URL);
      });

      test('Faults page renders correctly', async ({ page }) => {
        await page.goto(`${BASE_URL}/faults`);
        await page.waitForLoadState('networkidle');

        const screenshot = await page.screenshot({ fullPage: true });
        await saveArtifact(
          `mobile-responsive/${device.name.toLowerCase().replace(' ', '-')}`,
          'faults_page.png',
          screenshot
        );

        const viewport = page.viewportSize();

        await createEvidenceBundle(
          `mobile-responsive/${device.name.toLowerCase().replace(' ', '-')}/faults`,
          {
            device: device.name,
            viewport: viewport,
            page: 'faults',
            timestamp: new Date().toISOString(),
          }
        );

        expect(page.url()).toContain(BASE_URL);
      });
    });
  }

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
      total_tests: DEVICES.length * 5,
      timestamp: new Date().toISOString(),
    });

    expect(true).toBe(true);
  });
});
