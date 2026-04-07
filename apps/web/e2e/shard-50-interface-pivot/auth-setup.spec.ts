/**
 * Auth Setup — Real Browser Login
 *
 * Performs actual login with staging credentials via the /login page.
 * Saves browser storageState for reuse by all subsequent tests.
 *
 * This replaces the self-minted JWT approach which was not accepted
 * by the ShellWrapper auth guard.
 *
 * If this test fails, ALL other shard-50 tests should fail too —
 * they depend on this auth state.
 */

import { test, expect } from '@playwright/test';
import path from 'path';

const AUTH_FILE = path.join(__dirname, '../../playwright/.auth/real-login.json');

test('authenticate via real browser login', async ({ page }) => {
  // Navigate to login
  await page.goto('/login');
  await page.waitForTimeout(2000);

  // If already authenticated (redirected), save state and return
  if (!page.url().includes('/login')) {
    await page.context().storageState({ path: AUTH_FILE });
    return;
  }

  // Fill login form
  const emailInput = page.locator('input[type="email"], input[name="email"], input[placeholder*="email" i]').first();
  const passInput = page.locator('input[type="password"]').first();
  const submitBtn = page.locator('button[type="submit"], button:has-text("Sign in"), button:has-text("Log in")').first();

  await expect(emailInput).toBeVisible({ timeout: 10_000 });
  await emailInput.fill('x@alex-short.com');
  await passInput.fill('Password2!');
  await submitBtn.click();

  // Wait for redirect away from login (auth complete)
  await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 20_000 });

  // Wait for bootstrap to complete (role badge, data loading)
  await page.waitForTimeout(5000);

  // Verify we're actually authenticated
  const url = page.url();
  expect(url).not.toContain('/login');

  // Verify the page has real content (not blank)
  const body = await page.textContent('body');
  expect(body!.length).toBeGreaterThan(100);

  // Save authenticated state
  await page.context().storageState({ path: AUTH_FILE });
});
