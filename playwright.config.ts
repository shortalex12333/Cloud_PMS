import { defineConfig, devices } from '@playwright/test';
import * as dotenv from 'dotenv';
import * as path from 'path';

// Load environment variables
dotenv.config({ path: '.env.e2e.local' });
dotenv.config({ path: '.env.e2e' });

/**
 * Playwright Configuration for CelesteOS E2E Tests
 *
 * Run:
 *   npm run test:e2e           - All E2E tests
 *   npm run test:contracts     - Contract tests only
 *   npx playwright test --ui   - Interactive UI mode
 */
export default defineConfig({
  testDir: './tests',

  // Maximum time one test can run (fail fast)
  timeout: parseInt(process.env.TEST_TIMEOUT || '30000'),

  // Expect timeout (fail fast on element not found)
  expect: {
    timeout: 10000,
  },

  // Run tests in files in parallel
  fullyParallel: false, // Sequential for DB-dependent tests

  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,

  // Retry on CI only
  retries: process.env.CI ? 2 : 0,

  // Limit parallel workers on CI
  workers: process.env.CI ? 1 : undefined,

  // Reporter configuration
  reporter: [
    ['html', { outputFolder: 'test-results/report', open: 'never' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['list'],
  ],

  // Shared settings for all projects
  use: {
    // Base URL for relative paths
    // CI sets PLAYWRIGHT_BASE_URL to http://127.0.0.1:3000
    // Production uses VERCEL_PROD_URL (https://app.celeste7.ai)
    baseURL: process.env.PLAYWRIGHT_BASE_URL || process.env.VERCEL_PROD_URL || 'https://app.celeste7.ai',

    // Collect trace on failure
    trace: 'on-first-retry',

    // Capture screenshot on failure
    screenshot: 'only-on-failure',

    // Record video on failure
    video: 'on-first-retry',

    // Slow down for debugging
    launchOptions: {
      slowMo: parseInt(process.env.SLOWMO || '0'),
    },

    // Extra HTTP headers
    extraHTTPHeaders: {
      'Accept': 'application/json',
    },
  },

  // Output directory for test artifacts
  outputDir: 'test-results/artifacts',

  // Projects for different test types
  projects: [
    // Contract tests (no browser, just HTTP)
    {
      name: 'contracts',
      testDir: './tests/contracts',
      testMatch: '**/*.test.ts',
      use: {
        // No browser needed for contract tests
      },
    },

    // E2E tests with Chromium
    {
      name: 'e2e-chromium',
      testDir: './tests/e2e',
      testMatch: '**/*.spec.ts',
      use: {
        ...devices['Desktop Chrome'],
        headless: process.env.HEADLESS !== 'false',
        viewport: { width: 1280, height: 720 },
      },
    },
  ],

  // Global setup and teardown
  globalSetup: require.resolve('./tests/helpers/global-setup.ts'),
  globalTeardown: require.resolve('./tests/helpers/global-teardown.ts'),

  // Web server configuration (if running locally)
  // Uncomment if you want Playwright to start the frontend
  // webServer: {
  //   command: 'cd apps/web && npm run dev',
  //   url: 'http://localhost:3000',
  //   reuseExistingServer: !process.env.CI,
  //   timeout: 120000,
  // },
});
