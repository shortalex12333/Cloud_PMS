import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  testMatch: 'hor-pr614-verify.spec.ts',
  timeout: 90_000,
  expect: { timeout: 15_000 },
  workers: 1,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: 'https://app.celeste7.ai',
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
    actionTimeout: 20_000,
    navigationTimeout: 60_000,
    screenshot: 'off',
    video: 'off',
    trace: 'off',
  },
});
