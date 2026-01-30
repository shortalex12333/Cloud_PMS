/**
 * Global Setup: Receiving Lens E2E Tests
 *
 * Authenticates test accounts and saves storage states:
 * - crew.tenant@alex-short.com (CREW - read-only)
 * - hod.tenant@alex-short.com (HOD/Chief Engineer - MUTATE)
 * - captain.tenant@alex-short.com (CAPTAIN - SIGNED)
 *
 * All accounts use: Password2!
 * Yacht ID: 85fe1119-b04c-41ac-80f1-829d23322598 (server-resolved from auth)
 */

import { chromium, FullConfig } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

const AUTH_STATES_DIR = path.join(process.cwd(), 'test-results', '.auth-states');

// Ensure auth states directory exists
if (!fs.existsSync(AUTH_STATES_DIR)) {
  fs.mkdirSync(AUTH_STATES_DIR, { recursive: true });
}

// Test accounts (all use Password2!)
const TEST_ACCOUNTS = [
  {
    email: 'crew.tenant@alex-short.com',
    password: 'Password2!',
    role: 'crew',
    stateFile: 'crew-state.json',
  },
  {
    email: 'hod.tenant@alex-short.com',
    password: 'Password2!',
    role: 'hod',
    stateFile: 'hod-state.json',
  },
  {
    email: 'captain.tenant@alex-short.com',
    password: 'Password2!',
    role: 'captain',
    stateFile: 'captain-state.json',
  },
];

async function globalSetup(config: FullConfig) {
  console.log('[Global Setup] Starting authentication for Receiving Lens E2E tests...');

  const browser = await chromium.launch();

  for (const account of TEST_ACCOUNTS) {
    console.log(`[Global Setup] Authenticating ${account.role}: ${account.email}`);

    const context = await browser.newContext({
      baseURL: 'https://app.celeste7.ai',
    });

    const page = await context.newPage();

    try {
      // Navigate to login page
      await page.goto('/');

      // Wait for auth form to load
      await page.waitForLoadState('networkidle');

      // Check if already authenticated
      const isAuthenticated = await page.evaluate(() => {
        const authKey = Object.keys(localStorage).find((key) => key.includes('auth-token'));
        return !!authKey;
      });

      if (!isAuthenticated) {
        console.log(`[Global Setup] ${account.role}: Entering credentials...`);

        // Fill in login form
        const emailInput = page.locator('input[type="email"], input[name="email"]').first();
        const passwordInput = page.locator('input[type="password"], input[name="password"]').first();

        await emailInput.waitFor({ state: 'visible', timeout: 10000 });
        await emailInput.fill(account.email);

        await passwordInput.waitFor({ state: 'visible', timeout: 10000 });
        await passwordInput.fill(account.password);

        // Submit login form
        const submitButton = page.locator('button[type="submit"], button:has-text("Sign in"), button:has-text("Login")').first();
        await submitButton.click();

        // Wait for navigation after login
        await page.waitForURL('/', { timeout: 15000 });
        await page.waitForLoadState('networkidle');

        console.log(`[Global Setup] ${account.role}: Login successful`);
      } else {
        console.log(`[Global Setup] ${account.role}: Already authenticated`);
      }

      // Verify JWT is present
      const jwt = await page.evaluate(() => {
        const authKey = Object.keys(localStorage).find((key) => key.includes('auth-token'));
        if (!authKey) return null;

        const authData = JSON.parse(localStorage.getItem(authKey) || '{}');
        return authData.access_token || null;
      });

      if (!jwt) {
        throw new Error(`${account.role}: No JWT found after login`);
      }

      console.log(`[Global Setup] ${account.role}: JWT verified (length: ${jwt.length})`);

      // Save storage state
      const statePath = path.join(AUTH_STATES_DIR, account.stateFile);
      await context.storageState({ path: statePath });

      console.log(`[Global Setup] ${account.role}: Storage state saved to ${statePath}`);

    } catch (error) {
      console.error(`[Global Setup] ${account.role}: Authentication failed:`, error);
      throw error;
    } finally {
      await context.close();
    }
  }

  await browser.close();

  console.log('[Global Setup] All accounts authenticated successfully ✅');
}

export default globalSetup;
