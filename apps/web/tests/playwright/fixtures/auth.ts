/**
 * Playwright Auth Fixtures
 * =========================
 *
 * Extends Playwright's test with JWT refresh capability.
 *
 * Usage:
 *   import { test, expect } from './fixtures/auth';
 *
 *   test('my test', async ({ page }) => {
 *     // JWT is automatically checked and refreshed before this test runs
 *     await page.goto('/dashboard');
 *     // ...
 *   });
 */

import { test as base, Page } from '@playwright/test';
import { isJWTExpiring, logJWTStatus, getTimeUntilExpiry, formatTimeRemaining } from '../utils/jwt.js';

/**
 * Extract Supabase session from page's localStorage
 */
async function getSessionFromPage(page: Page): Promise<any> {
  return await page.evaluate(() => {
    const allKeys = Object.keys(localStorage);
    const keys = allKeys.filter(k =>
      k.includes('supabase') || k.includes('auth') || k.includes('sb-')
    );

    for (const key of keys) {
      try {
        const value = localStorage.getItem(key);
        if (value) {
          const parsed = JSON.parse(value);
          // Check if it looks like a session object
          if (parsed.access_token && parsed.refresh_token) {
            return parsed;
          }
          // Check if it's wrapped in a data object
          if (parsed.data?.session) {
            return parsed.data.session;
          }
          // Check if it's in session property
          if (parsed.session?.access_token) {
            return parsed.session;
          }
        }
      } catch (e) {
        continue;
      }
    }

    return null;
  });
}

/**
 * Refresh JWT using Supabase refresh token
 */
async function refreshJWT(page: Page, refreshToken: string): Promise<void> {
  console.log('🔄 Refreshing JWT...');

  const supabaseUrl = process.env.SUPABASE_URL || 'https://qvzmkaamzaqxpzbewjxe.supabase.co';
  const supabaseAnonKey = process.env.SUPABASE_ANON_KEY;

  if (!supabaseAnonKey) {
    throw new Error('SUPABASE_ANON_KEY environment variable not set');
  }

  // Call Supabase refresh endpoint
  const newSession = await page.evaluate(
    async ({ url, anonKey, token }) => {
      const response = await fetch(`${url}/auth/v1/token?grant_type=refresh_token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'apikey': anonKey,
        },
        body: JSON.stringify({
          refresh_token: token,
        }),
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Refresh failed: ${response.status} ${error}`);
      }

      return await response.json();
    },
    {
      url: supabaseUrl,
      anonKey: supabaseAnonKey,
      token: refreshToken,
    }
  );

  // Update localStorage with new session
  await page.evaluate((session) => {
    // Find the Supabase auth key
    const allKeys = Object.keys(localStorage);
    const keys = allKeys.filter(k =>
      k.includes('supabase') || k.includes('auth') || k.includes('sb-')
    );

    if (keys.length > 0) {
      const key = keys[0];
      const existing = localStorage.getItem(key);

      if (existing) {
        try {
          const parsed = JSON.parse(existing);
          // Update with new session data
          if (parsed.data?.session) {
            parsed.data.session = session;
          } else if (parsed.session) {
            parsed.session = session;
          } else {
            Object.assign(parsed, session);
          }
          localStorage.setItem(key, JSON.stringify(parsed));
        } catch (e) {
          // Fallback: just set the new session
          localStorage.setItem(key, JSON.stringify(session));
        }
      }
    } else {
      // No existing key, create new one (shouldn't happen with saved state)
      const supabaseUrl = window.location.origin;
      const projectRef = supabaseUrl.match(/https:\/\/([^.]+)/)?.[1] || 'unknown';
      localStorage.setItem(`sb-${projectRef}-auth-token`, JSON.stringify(session));
    }
  }, newSession);

  console.log('✅ JWT refreshed successfully');
}

/**
 * Ensure JWT is valid before each test
 */
async function ensureValidJWT(page: Page): Promise<void> {
  // First, navigate to a page so we can access localStorage
  // Use a lightweight page to avoid unnecessary loading
  const baseURL = process.env.BASE_URL || 'https://app.celeste7.ai';
  await page.goto(baseURL, { waitUntil: 'domcontentloaded' });

  const session = await getSessionFromPage(page);

  if (!session || !session.access_token) {
    throw new Error('No JWT found in localStorage. Global setup may have failed.');
  }

  // Check if JWT is expiring soon (within 5 minutes)
  if (isJWTExpiring(session.access_token, 5)) {
    const timeRemaining = getTimeUntilExpiry(session.access_token);
    console.warn(`⚠️  JWT expiring in ${formatTimeRemaining(timeRemaining)}, refreshing...`);

    if (!session.refresh_token) {
      throw new Error('No refresh token available. Cannot refresh JWT.');
    }

    await refreshJWT(page, session.refresh_token);

    // Verify refresh worked
    const newSession = await getSessionFromPage(page);
    if (newSession && newSession.access_token) {
      logJWTStatus(newSession.access_token, 'Refreshed JWT');
    }
  } else {
    // JWT is still valid
    const timeRemaining = getTimeUntilExpiry(session.access_token);
    console.log(`✅ JWT valid for ${formatTimeRemaining(timeRemaining)}`);
  }
}

/**
 * Extended test fixture with JWT refresh
 */
export const test = base.extend({
  page: async ({ page }, use) => {
    // Before each test: ensure JWT is valid
    await ensureValidJWT(page);

    // Run the test
    await use(page);

    // After each test: cleanup if needed
  },
});

export { expect } from '@playwright/test';
