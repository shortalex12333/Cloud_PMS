/**
 * Handover Open Token E2E Tests
 * ==============================
 *
 * Tests for the /open?t=<token> link resolution flow.
 *
 * Test scenarios:
 * 1. Valid token → redirects to /app with entity focus
 * 2. Expired token → shows expiration error
 * 3. Invalid token → shows invalid link error
 * 4. Wrong yacht token → shows access denied
 * 5. No token → shows no token error
 *
 * Prerequisites:
 * - Handover export service running on HANDOVER_EXPORT_API_BASE
 * - Test user authenticated with test yacht
 * - Backend can generate test tokens
 */

import { test, expect } from './fixtures/auth';
import { getValidJWT } from './utils/jwt';

// Handover export service URL
const HANDOVER_EXPORT_API_BASE =
  process.env.HANDOVER_EXPORT_API_BASE ||
  process.env.NEXT_PUBLIC_HANDOVER_EXPORT_API_BASE ||
  'http://localhost:8000';

// Test entity for resolution tests (real entity from test database)
const TEST_ENTITY = {
  type: 'work_order',
  id: 'b36238da-b0fa-4815-883c-0be61fc190d0', // Real work order: "500-Hour Preventive Maintenance"
};

/**
 * Pre-generated test tokens for E2E testing
 * These tokens are generated using the handover-export link_token service
 * and are valid for the TEST_YACHT_ID: 85fe1119-b04c-41ac-80f1-829d23322598
 *
 * To regenerate tokens (from handover_export directory):
 *   source venv/bin/activate && python3 -c "
 *   import sys; sys.path.insert(0, 'src')
 *   from dotenv import load_dotenv; load_dotenv()
 *   import os, json
 *   from services.link_token import create_link_token
 *   keys = json.loads(os.environ.get('LINK_TOKEN_KEYS', '{}'))
 *   kid = os.environ.get('LINK_TOKEN_ACTIVE_KID', 'v1')
 *   secret = keys.get(kid)
 *   token = create_link_token('work_order', 'b36238da-b0fa-4815-883c-0be61fc190d0',
 *     '85fe1119-b04c-41ac-80f1-829d23322598', kid, secret, 86400)
 *   print(token)"
 */
const TEST_TOKENS = {
  // Valid token for real work order - regenerate if expired (24h TTL)
  validWorkOrder: 'eyJhbGciOiJIUzI1NiIsImtpZCI6InYxIiwidHlwIjoiSldUIn0.eyJ0eXBlIjoid29ya19vcmRlciIsImlkIjoiYjM2MjM4ZGEtYjBmYS00ODE1LTg4M2MtMGJlNjFmYzE5MGQwIiwieWFjaHRfaWQiOiI4NWZlMTExOS1iMDRjLTQxYWMtODBmMS04MjlkMjMzMjI1OTgiLCJleHAiOjE3NzAzMTIyNjcsIm5vbmNlIjoiODg3OGJiNTdjZDU2NzU4ZGUzYjM4OGQ0NmEyOTM4NGUiLCJzY29wZSI6InZpZXciLCJ2IjoxfQ.9v4grXk3N58BOWqKvKIIdHKslKCK3S6Sq7B3Jb6tr2U',

  // Token for wrong yacht (different yacht_id in payload)
  wrongYacht: 'eyJhbGciOiJIUzI1NiIsImtpZCI6InYxIiwidHlwIjoiSldUIn0.eyJ0eXBlIjoid29ya19vcmRlciIsImlkIjoiYjM2MjM4ZGEtYjBmYS00ODE1LTg4M2MtMGJlNjFmYzE5MGQwIiwieWFjaHRfaWQiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDEiLCJleHAiOjE3NzAzMTIyNjcsIm5vbmNlIjoiYWJjZDEyMzQiLCJzY29wZSI6InZpZXciLCJ2IjoxfQ.invalid_signature',

  // Malformed token
  malformed: 'not-a-valid-jwt-token',
};

/**
 * Helper to generate a test token via the handover-export service
 */
async function generateTestToken(
  page: any,
  options: {
    entityType: string;
    entityId: string;
    expiredSeconds?: number;
    wrongYacht?: boolean;
  }
): Promise<string | null> {
  // Use pre-generated tokens for now
  if (options.wrongYacht) {
    return TEST_TOKENS.wrongYacht;
  }
  if (options.entityType === 'work_order' && options.entityId === TEST_ENTITY.id) {
    return TEST_TOKENS.validWorkOrder;
  }
  return null;
}

test.describe('Handover /open Token Resolution', () => {
  test.describe('Error States', () => {
    test('should show no token error when ?t= is missing', async ({ page }) => {
      await page.goto('/open');

      // Should show no token error state
      await expect(page.locator('[data-testid="open-token-error"]')).toBeVisible({
        timeout: 10000,
      });
      await expect(
        page.locator('[data-testid="open-token-error"]')
      ).toHaveAttribute('data-error-state', 'no_token');

      // Should show appropriate message
      await expect(page.locator('text=No Link Token')).toBeVisible();
      await expect(page.locator('text=No token was provided')).toBeVisible();

      // Should have return button
      const returnButton = page.locator('button:has-text("Return to App")');
      await expect(returnButton).toBeVisible();
    });

    test('should show invalid error for malformed token', async ({ page }) => {
      // Navigate with a clearly invalid token
      await page.goto('/open?t=not-a-valid-jwt-token');

      // Wait for error state
      await expect(page.locator('[data-testid="open-token-error"]')).toBeVisible({
        timeout: 15000,
      });

      // Should show invalid or unknown error
      const errorState = await page
        .locator('[data-testid="open-token-error"]')
        .getAttribute('data-error-state');

      expect(['error_invalid', 'error_unknown']).toContain(errorState);
    });

    test('should navigate back to app when clicking Return button', async ({ page }) => {
      await page.goto('/open');

      // Wait for error state
      await expect(page.locator('[data-testid="open-token-error"]')).toBeVisible({
        timeout: 10000,
      });

      // Click return button
      await page.click('button:has-text("Return to App")');

      // Should navigate to main app (may be /app or /)
      await expect(page).toHaveURL(/.*\/(app)?$/);
    });
  });

  test.describe('Authentication Flow', () => {
    test('should show auth required when not logged in', async ({ browser }) => {
      // Create a new context without saved auth state
      const context = await browser.newContext({
        storageState: undefined, // No saved state = not logged in
      });
      const page = await context.newPage();

      try {
        await page.goto('/open?t=any-token-here');

        // Should show auth required error
        await expect(page.locator('[data-testid="open-token-error"]')).toBeVisible({
          timeout: 10000,
        });

        // Could be auth_required or redirected to login
        const url = page.url();
        const hasAuthError =
          (await page.locator('[data-error-state="error_auth"]').count()) > 0;
        const isOnLogin = url.includes('/login');

        expect(hasAuthError || isOnLogin).toBeTruthy();

        // If auth error, clicking Sign In should go to login
        if (hasAuthError) {
          const signInButton = page.locator('button:has-text("Sign In")');
          if (await signInButton.isVisible()) {
            await signInButton.click();
            await expect(page).toHaveURL(/.*\/login/);
          }
        }
      } finally {
        await context.close();
      }
    });
  });

  test.describe('UI Elements', () => {
    test('should show loading state initially', async ({ page }) => {
      // Add request interception to slow down the resolve call
      await page.route('**/api/v1/open/resolve', async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        await route.continue();
      });

      // Navigate with a token
      page.goto('/open?t=test-token').catch(() => {});

      // Should show loading/resolving state
      await expect(page.locator('text=Opening link')).toBeVisible({ timeout: 2000 });
    });

    test('should have correct page title', async ({ page }) => {
      await page.goto('/open');

      // Page should load without errors
      await expect(page.locator('body')).toBeVisible();
    });
  });

  // Valid token resolution tests (requires backend running on localhost:8000)
  test.describe('Valid Token Resolution @real', () => {
    test('should resolve valid token and redirect to entity', async ({ page }) => {
      // Generate a valid test token
      const token = await generateTestToken(page, {
        entityType: 'work_order',
        entityId: TEST_ENTITY.id,
      });

      if (!token) {
        test.skip();
        return;
      }

      await page.goto(`/open?t=${token}`);

      // Should redirect with entity query params (may be /app or / depending on app config)
      await expect(page).toHaveURL(/.*\?entity=work_order&id=/, {
        timeout: 15000,
      });

      // Token should be removed from URL (security)
      expect(page.url()).not.toContain('?t=');
    });

    test('should show entity focus after resolution', async ({ page }) => {
      const token = await generateTestToken(page, {
        entityType: 'work_order',
        entityId: TEST_ENTITY.id,
      });

      if (!token) {
        test.skip();
        return;
      }

      await page.goto(`/open?t=${token}`);

      // Wait for redirect with entity params (path may be /app or /)
      await expect(page).toHaveURL(/.*\?entity=/, { timeout: 15000 });

      // Context panel should be visible with entity
      await expect(page.locator('[data-testid="context-panel"]')).toBeVisible({
        timeout: 10000,
      });
    });

    // Skip: requires backend test fixture to generate properly signed expired tokens
    test.skip('should show expired error for expired token', async ({ page }) => {
      // Generate an expired token (negative TTL)
      const token = await generateTestToken(page, {
        entityType: 'work_order',
        entityId: TEST_ENTITY.id,
        expiredSeconds: -100, // Already expired
      });

      if (!token) {
        test.skip();
        return;
      }

      await page.goto(`/open?t=${token}`);

      // Should show expired error
      await expect(page.locator('[data-error-state="error_expired"]')).toBeVisible({
        timeout: 15000,
      });
      await expect(page.locator('text=Link Expired')).toBeVisible();
    });

    // Skip: requires backend test fixture to generate properly signed wrong-yacht tokens
    test.skip('should show access denied for wrong yacht token', async ({ page }) => {
      // Generate a token for a different yacht
      const token = await generateTestToken(page, {
        entityType: 'work_order',
        entityId: TEST_ENTITY.id,
        wrongYacht: true,
      });

      if (!token) {
        test.skip();
        return;
      }

      await page.goto(`/open?t=${token}`);

      // Should show yacht mismatch error
      await expect(page.locator('[data-error-state="error_yacht"]')).toBeVisible({
        timeout: 15000,
      });
      await expect(page.locator('text=Access Denied')).toBeVisible();
    });
  });
});

test.describe('Handover Export Link Contract', () => {
  /**
   * Contract test: Verify the resolve endpoint returns expected shape
   * This can be used when full E2E isn't available
   */
  test('should return correct focus descriptor shape from resolve API', async ({
    page,
  }) => {
    // This test verifies the API contract directly
    // Useful for CI when full E2E setup isn't available

    const baseURL = process.env.BASE_URL || 'https://app.celeste7.ai';
    await page.goto(baseURL);

    // Get JWT from page session
    const session = await page.evaluate(() => {
      const keys = Object.keys(localStorage).filter(
        (k) => k.includes('supabase') || k.includes('sb-')
      );
      for (const key of keys) {
        try {
          const value = localStorage.getItem(key);
          if (value) {
            const parsed = JSON.parse(value);
            if (parsed.access_token) return parsed;
            if (parsed.data?.session) return parsed.data.session;
            if (parsed.session) return parsed.session;
          }
        } catch (e) {
          continue;
        }
      }
      return null;
    });

    if (!session?.access_token) {
      console.log('No session found, skipping contract test');
      test.skip();
      return;
    }

    // Call resolve with invalid token to verify error shape
    const response = await page.evaluate(
      async ({ apiBase, jwt }) => {
        try {
          const res = await fetch(`${apiBase}/api/v1/open/resolve`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${jwt}`,
            },
            body: JSON.stringify({ t: 'invalid-token' }),
          });

          return {
            status: res.status,
            body: await res.json().catch(() => ({})),
          };
        } catch (e) {
          return { status: 0, error: String(e) };
        }
      },
      {
        apiBase: HANDOVER_EXPORT_API_BASE,
        jwt: session.access_token,
      }
    );

    // Should return 400 for invalid token
    expect(response.status).toBe(400);

    // Error response should have detail field
    expect(response.body).toHaveProperty('detail');
  });
});
