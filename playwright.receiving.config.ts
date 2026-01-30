/**
 * Playwright Configuration: Receiving Lens E2E Tests
 *
 * Architecture Validation:
 * - Search-first navigation (NO /receiving page)
 * - Entity extraction via search queries
 * - Backend-frontend parity (UI renders only backend actions)
 * - Role-based action surfacing
 * - Server-resolved yacht_id (never sent by client)
 * - Zero 5xx errors
 *
 * Test Accounts:
 * - crew.tenant@alex-short.com (CREW - read-only)
 * - hod.tenant@alex-short.com (HOD - MUTATE)
 * - captain.tenant@alex-short.com (CAPTAIN - SIGNED)
 */

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e/receiving',

  // Global setup to authenticate all test accounts
  globalSetup: './tests/e2e/receiving/global-setup.ts',

  // Artifacts and output
  outputDir: 'test-results/receiving',

  // Test execution
  fullyParallel: false, // Run tests sequentially for stability
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : 1,

  // Reporter configuration
  reporter: [
    ['html', { outputFolder: 'test-results/receiving/html-report', open: 'never' }],
    ['json', { outputFile: 'test-results/receiving/results.json' }],
    ['list'],
  ],

  // Shared settings
  use: {
    // Base URL
    baseURL: 'https://app.celeste7.ai',

    // Browser options
    headless: true,
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',

    // Timeouts
    actionTimeout: 10000,
    navigationTimeout: 15000,
  },

  // Projects for different browsers
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Environment variables
  env: {
    RENDER_API_URL: process.env.RENDER_API_URL || 'https://pipeline-core.int.celeste7.ai',
  },
});
