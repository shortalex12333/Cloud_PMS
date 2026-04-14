import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  testMatch: 'hor-proof.spec.ts',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  workers: 1,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL || 'https://app.celeste7.ai',
    viewport: { width: 1440, height: 2000 },
    deviceScaleFactor: 2,
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
    screenshot: 'off',
    video: 'off',
    trace: 'off',
  },
});
