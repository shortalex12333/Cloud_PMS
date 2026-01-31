/**
 * Playwright Global Setup - Authentication
 * =========================================
 *
 * Runs ONCE before all tests to:
 * 1. Log in to the application
 * 2. Get fresh JWT tokens
 * 3. Save authentication state for all tests to reuse
 *
 * This ensures:
 * - Tests don't need to log in individually (faster)
 * - All tests start with a fresh, valid JWT
 * - JWT expiry is logged for debugging
 */

import { chromium, FullConfig } from '@playwright/test';
import { logJWTStatus, isJWTExpiring, formatTimeRemaining, getTimeUntilExpiry } from './utils/jwt.js';
import path from 'path';
import fs from 'fs';

async function globalSetup(config: FullConfig) {
  console.log('\n========================================');
  console.log('Playwright Global Setup - Authentication');
  console.log('========================================\n');

  // Get test credentials from environment
  const baseURL = process.env.BASE_URL || 'https://app.celeste7.ai';
  const testEmail = process.env.TEST_USER_EMAIL || 'test@yacht.com';
  const testPassword = process.env.TEST_USER_PASSWORD;

  if (!testPassword) {
    throw new Error('TEST_USER_PASSWORD environment variable not set');
  }

  console.log(`🌐 Base URL: ${baseURL}`);
  console.log(`👤 Test User: ${testEmail}`);
  console.log('');

  // Launch browser
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
  });
  const page = await context.newPage();

  try {
    console.log('🔐 Logging in...');

    // Navigate to login page
    await page.goto(`${baseURL}/login`, { waitUntil: 'networkidle' });

    // Fill login form
    // Adjust selectors based on your actual login form
    await page.fill('input[name="email"], input[type="email"]', testEmail);
    await page.fill('input[name="password"], input[type="password"]', testPassword);
    await page.click('button[type="submit"], button:has-text("Sign in"), button:has-text("Log in")');

    // Wait for redirect to main page (adjust URL pattern as needed)
    console.log('⏳ Waiting for authentication...');
    await page.waitForURL('**/dashboard', { timeout: 15000 }).catch(() => {
      // Fallback: check if we're no longer on login page
      return page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 15000 });
    });

    console.log('✅ Login successful');
    console.log('');

    // Extract JWT from localStorage
    console.log('🔑 Extracting JWT tokens...');

    // First, log all localStorage keys for debugging
    const allKeys = await page.evaluate(() => Object.keys(localStorage));
    console.log('📋 localStorage keys found:', allKeys);

    const authState = await page.evaluate(() => {
      // Supabase stores session in localStorage
      // Key format: supabase.auth.token or sb-<project-id>-auth-token
      const allKeys = Object.keys(localStorage);
      console.log('All localStorage keys:', allKeys);

      const keys = allKeys.filter(k =>
        k.includes('supabase') || k.includes('auth') || k.includes('sb-')
      );

      console.log('Filtered auth keys:', keys);

      for (const key of keys) {
        try {
          const value = localStorage.getItem(key);
          console.log(`Checking key: ${key}`);
          if (value) {
            const parsed = JSON.parse(value);
            console.log(`Parsed value for ${key}:`, typeof parsed, Object.keys(parsed || {}));

            // Check if it looks like a session object
            if (parsed.access_token && parsed.refresh_token) {
              console.log('Found session in top level');
              return parsed;
            }
            // Check if it's wrapped in a data object
            if (parsed.data?.session) {
              console.log('Found session in data.session');
              return parsed.data.session;
            }
            // Check if it's in session property
            if (parsed.session?.access_token) {
              console.log('Found session in session property');
              return parsed.session;
            }
          }
        } catch (e) {
          console.log(`Error parsing ${key}:`, e);
          continue;
        }
      }

      return null;
    });

    if (!authState || !authState.access_token) {
      throw new Error('Failed to extract JWT from localStorage. Check login flow.');
    }

    console.log('✅ JWT tokens extracted');
    console.log('');

    // Log JWT status
    logJWTStatus(authState.access_token, 'Access Token');
    console.log('');

    // Check if JWT is expiring soon
    const timeRemaining = getTimeUntilExpiry(authState.access_token);
    if (isJWTExpiring(authState.access_token, 10)) {
      console.warn('⚠️  WARNING: JWT expires in less than 10 minutes');
      console.warn('   Tests may fail if suite runs longer than this.');
      console.warn('   Consider using a longer-lived test user JWT or implementing refresh.');
      console.log('');
    } else {
      console.log(`✅ JWT valid for ${formatTimeRemaining(timeRemaining)}`);
      console.log('');
    }

    // Ensure auth directory exists
    const authDir = path.resolve(__dirname, '../../playwright/.auth');
    if (!fs.existsSync(authDir)) {
      fs.mkdirSync(authDir, { recursive: true });
    }

    // Save authentication state with JWT
    const authFilePath = path.resolve(authDir, 'user.json');
    await context.storageState({ path: authFilePath });

    console.log(`💾 Auth state saved to: ${authFilePath}`);
    console.log('');

    // Also save a JSON file with just the tokens for debugging/inspection
    const tokensFilePath = path.resolve(authDir, 'tokens.json');
    fs.writeFileSync(
      tokensFilePath,
      JSON.stringify(
        {
          access_token: authState.access_token,
          refresh_token: authState.refresh_token,
          expires_at: authState.expires_at,
          extracted_at: new Date().toISOString(),
        },
        null,
        2
      )
    );

    console.log(`💾 Tokens saved to: ${tokensFilePath}`);
    console.log('');

    console.log('========================================');
    console.log('✅ Global Setup Complete');
    console.log('========================================\n');

  } catch (error) {
    console.error('❌ Global Setup Failed:', error);

    // Take screenshot for debugging
    const screenshotPath = path.resolve(__dirname, '../../test-results/global-setup-failure.png');
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.error(`📸 Screenshot saved to: ${screenshotPath}`);

    throw error;
  } finally {
    await browser.close();
  }
}

export default globalSetup;
