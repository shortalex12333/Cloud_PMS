import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: '.',
  timeout: 180000,
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3010',
    headless: true,
    viewport: { width: 1440, height: 900 },
    screenshot: 'on',
    video: 'off',
  },
});
