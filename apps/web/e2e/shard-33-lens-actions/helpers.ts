// apps/web/e2e/shard-33-lens-actions/helpers.ts

import type { Page } from '@playwright/test';
import { RBAC_CONFIG } from '../rbac-fixtures';

export const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:3000';
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Runs fetch() from within the browser page context so it carries
 * the Supabase auth token stored in localStorage automatically.
 *
 * Polls for the token for up to 8 seconds: Supabase's client initialises
 * asynchronously after domcontentloaded (it restores the session from
 * cookies and writes the access_token to localStorage). Polling lets us
 * call the action API without an explicit waitFor in every test.
 */
export async function fetchFromPage(
  page: Page,
  url: string,
  options: { method?: string; body?: string } = {}
): Promise<{ status: number; data: Record<string, unknown> }> {
  return page.evaluate(
    async ([fetchUrl, fetchOptions]) => {
      // Poll up to 10 s for a valid (non-expired) Supabase access_token.
      // If the stored token is expired, Supabase's client will refresh it
      // asynchronously and update the same localStorage key — we wait for that.
      let token = '';
      const deadline = Date.now() + 10_000;
      while (Date.now() < deadline) {
        for (const key of Object.keys(localStorage)) {
          if (key.includes('-auth-token') || (key.startsWith('sb-') && key.includes('auth'))) {
            try {
              const parsed = JSON.parse(localStorage.getItem(key) || '{}');
              if (parsed.access_token) {
                // Validate JWT expiry before using it
                const parts = (parsed.access_token as string).split('.');
                if (parts.length >= 2) {
                  const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
                  if ((payload.exp as number) > Date.now() / 1000 + 5) {
                    token = parsed.access_token as string;
                    break;
                  }
                  // Expired — wait for Supabase to refresh
                }
              }
            } catch { /* try next key */ }
          }
        }
        if (token) break;
        await new Promise<void>(r => setTimeout(r, 300));
      }
      const res = await fetch(fetchUrl as string, {
        method: (fetchOptions as { method?: string }).method || 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: (fetchOptions as { body?: string }).body,
      });
      const data = await res.json().catch(() => ({}));
      return { status: res.status, data };
    },
    [url, options] as [string, { method?: string; body?: string }]
  );
}

/**
 * Calls POST /v1/actions/execute via the browser's fetch (carries localStorage auth).
 */
export async function callAction(
  page: Page,
  action: string,
  payload: Record<string, unknown>,
  contextOverrides: Record<string, string> = {}
): Promise<{ status: number; data: Record<string, unknown> }> {
  return fetchFromPage(page, `${API_URL}/v1/actions/execute`, {
    method: 'POST',
    body: JSON.stringify({
      action,
      context: { yacht_id: RBAC_CONFIG.yachtId, ...contextOverrides },
      payload,
    }),
  });
}

/**
 * Standard render verification — call after waitForLoadState.
 * Asserts: no "Failed to Load" banner, no bare "500" text.
 */
export async function assertNoRenderCrash(page: Page): Promise<void> {
  const { expect } = await import('@playwright/test');
  await expect(page.getByText('Failed to Load').first()).not.toBeVisible();
  await expect(page.getByText('500', { exact: true }).first()).not.toBeVisible();
}
