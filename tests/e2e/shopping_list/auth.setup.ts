/**
 * Shopping List E2E - Authentication Setup
 *
 * Handles sign-in for test users with fresh JWT generation.
 * Supports CREW, HOD (Chief Engineer), and CAPTAIN roles.
 */

import { test as setup, expect } from '@playwright/test';
import path from 'path';

// Test user credentials from environment
const TEST_USERS = {
  crew: {
    email: process.env.TEST_CREW_USER_EMAIL || 'crew.test@alex-short.com',
    password: process.env.ALL_TEST_USER_PASSWORD || 'Password2!',
    role: 'crew',
    storageState: path.join(__dirname, '.auth/crew.json'),
  },
  hod: {
    email: process.env.TEST_HOD_USER_EMAIL || 'hod.test@alex-short.com',
    password: process.env.ALL_TEST_USER_PASSWORD || 'Password2!',
    role: 'chief_engineer',  // HOD equivalent
    storageState: path.join(__dirname, '.auth/hod.json'),
  },
  captain: {
    email: process.env.TEST_CAPTAIN_USER_EMAIL || 'x@alex-short.com',
    password: process.env.ALL_TEST_USER_PASSWORD || 'Password2!',
    role: 'captain',
    storageState: path.join(__dirname, '.auth/captain.json'),
  },
};

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const YACHT_ID = process.env.TEST_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';

/**
 * Authenticate and save session storage for each user
 */
for (const [key, user] of Object.entries(TEST_USERS)) {
  setup(`authenticate as ${key}`, async ({ page }) => {
    console.log(`\n🔐 Authenticating as ${key}: ${user.email}`);

    // Navigate to login page
    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState('networkidle');

    // Fill login form
    const emailInput = page.locator('input[type="email"], input[name="email"]').first();
    const passwordInput = page.locator('input[type="password"], input[name="password"]').first();
    const submitButton = page.locator('button[type="submit"]').first();

    await expect(emailInput).toBeVisible({ timeout: 5000 });
    await emailInput.fill(user.email);
    await passwordInput.fill(user.password);

    console.log(`   Email: ${user.email}`);
    console.log(`   Password: ${'*'.repeat(user.password.length)}`);

    // Click submit and wait for redirect
    await submitButton.click();

    // Wait for successful login (redirect to dashboard or home)
    try {
      await page.waitForURL(/\/(dashboard|home)/, { timeout: 10000 });
      console.log(`   ✅ Login successful - redirected to dashboard`);
    } catch (e) {
      console.error(`   ❌ Login failed - no redirect to dashboard`);
      console.error(`   Current URL: ${page.url()}`);

      // Take screenshot for debugging
      await page.screenshot({
        path: path.join(__dirname, `.auth/${key}-login-failed.png`),
        fullPage: true
      });

      throw new Error(`Login failed for ${key}`);
    }

    // Verify we're logged in
    const isLoggedIn = await page.locator('[data-testid="user-menu"], [data-testid="profile"]').isVisible()
      .catch(() => false);

    if (!isLoggedIn) {
      console.warn(`   ⚠️  User menu not found - may still be logged in`);
    } else {
      console.log(`   ✅ User menu visible`);
    }

    // Extract JWT from localStorage or cookies
    const jwt = await page.evaluate(() => {
      // Try localStorage first
      const storedAuth = localStorage.getItem('supabase.auth.token');
      if (storedAuth) {
        try {
          const parsed = JSON.parse(storedAuth);
          return parsed.currentSession?.access_token || null;
        } catch {
          return null;
        }
      }

      // Try cookies
      const cookies = document.cookie.split(';');
      for (const cookie of cookies) {
        if (cookie.includes('sb-access-token') || cookie.includes('access_token')) {
          return cookie.split('=')[1];
        }
      }

      return null;
    });

    if (jwt) {
      console.log(`   ✅ JWT extracted (${jwt.substring(0, 50)}...)`);

      // Save JWT to file for later use
      const fs = require('fs');
      const jwtPath = path.join(__dirname, `.auth/${key}-jwt.txt`);
      fs.writeFileSync(jwtPath, jwt, 'utf-8');
      console.log(`   ✅ JWT saved to ${jwtPath}`);
    } else {
      console.warn(`   ⚠️  Could not extract JWT from page`);
    }

    // Save authenticated session state
    await page.context().storageState({ path: user.storageState });
    console.log(`   ✅ Session state saved to ${user.storageState}`);
    console.log(`   Role: ${user.role}`);
    console.log(`   Yacht ID: ${YACHT_ID}\n`);
  });
}

/**
 * Export user configurations for use in tests
 */
export { TEST_USERS, BASE_URL, YACHT_ID };
