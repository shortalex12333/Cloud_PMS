import { chromium, FullConfig } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Global Setup - Authenticates test users and saves session state
 *
 * This runs ONCE before all tests, creating authenticated browser states
 * that individual tests can reuse without re-logging in.
 *
 * Test Users:
 * - HOD (Head of Department): Full access to yacht data
 * - Crew: Limited access
 * - Captain: Administrative access
 */

// Test credentials from environment
const TEST_USERS = {
  hod: {
    email: process.env.TEST_HOD_USER_EMAIL || 'hod.test@alex-short.com',
    password: process.env.TEST_USER_PASSWORD || 'Password2!',
  },
  crew: {
    email: process.env.TEST_CREW_USER_EMAIL || 'crew.test@alex-short.com',
    password: process.env.TEST_USER_PASSWORD || 'Password2!',
  },
  captain: {
    email: process.env.TEST_CAPTAIN_USER_EMAIL || 'x@alex-short.com',
    password: process.env.TEST_USER_PASSWORD || 'Password2!',
  },
};

const BASE_URL = process.env.E2E_BASE_URL || 'https://app.celeste7.ai';
const AUTH_DIR = path.join(__dirname, '../playwright/.auth');

async function authenticateUser(
  userType: 'hod' | 'crew' | 'captain',
  baseURL: string
): Promise<void> {
  const user = TEST_USERS[userType];
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log(`[GlobalSetup] Authenticating ${userType}: ${user.email}`);

  try {
    // Navigate to login page
    await page.goto(`${baseURL}/login`, { waitUntil: 'networkidle' });

    // Fill login form
    await page.fill('input[type="email"]', user.email);
    await page.fill('input[type="password"]', user.password);

    // Submit and wait for redirect
    await page.click('button[type="submit"]');

    // Wait for successful authentication (redirect to main app)
    await page.waitForURL(`${baseURL}/`, { timeout: 30_000 });

    // Verify we're logged in by checking for search input
    await page.waitForSelector('[data-testid="search-input"]', { timeout: 10_000 });

    console.log(`[GlobalSetup] ${userType} authenticated successfully`);

    // Save storage state
    const statePath = path.join(AUTH_DIR, `${userType}.json`);
    await context.storageState({ path: statePath });

    console.log(`[GlobalSetup] Saved auth state: ${statePath}`);
  } catch (error) {
    console.error(`[GlobalSetup] Failed to authenticate ${userType}:`, error);
    throw error;
  } finally {
    await browser.close();
  }
}

async function globalSetup(config: FullConfig): Promise<void> {
  console.log('[GlobalSetup] Starting authentication...');
  console.log(`[GlobalSetup] Base URL: ${BASE_URL}`);

  // Ensure auth directory exists
  if (!fs.existsSync(AUTH_DIR)) {
    fs.mkdirSync(AUTH_DIR, { recursive: true });
  }

  // Authenticate all test users in sequence to avoid rate limiting
  await authenticateUser('hod', BASE_URL);
  await authenticateUser('crew', BASE_URL);
  await authenticateUser('captain', BASE_URL);

  // Create a symlink for default auth state (HOD)
  const defaultStatePath = path.join(AUTH_DIR, 'user.json');
  const hodStatePath = path.join(AUTH_DIR, 'hod.json');

  if (fs.existsSync(hodStatePath)) {
    if (fs.existsSync(defaultStatePath)) {
      fs.unlinkSync(defaultStatePath);
    }
    fs.copyFileSync(hodStatePath, defaultStatePath);
    console.log('[GlobalSetup] Created default auth state (HOD)');
  }

  console.log('[GlobalSetup] All users authenticated. Ready for tests.');
}

export default globalSetup;
