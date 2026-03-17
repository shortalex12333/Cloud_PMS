// apps/web/e2e/shard-34-lens-actions/helpers.ts

// Re-export from shard-33 helpers — identical transport layer
export { BASE_URL, API_URL, fetchFromPage, callAction, assertNoRenderCrash } from '../shard-33-lens-actions/helpers';

import type { Page } from '@playwright/test';
import { RBAC_CONFIG } from '../rbac-fixtures';
import * as crypto from 'crypto';

const API_URL_VAL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const BASE_URL_VAL = process.env.E2E_BASE_URL || 'http://localhost:3000';

/**
 * Generate a fresh JWT signed with the tenant Supabase JWT secret.
 *
 * PyJWT (in the API) uses the secret string directly as UTF-8 bytes.
 * We replicate the same signing here.
 *
 * @param sub   User UUID (must exist in MASTER DB user_accounts + tenant DB auth_users_roles)
 * @param email User email (informational only — role comes from tenant DB, not JWT claims)
 * @param expiresInSeconds Token lifetime (default 8 hours)
 */
export function generateFreshJwt(
  sub = 'a35cad0b-02ff-4287-b6e4-17c96fa6a424',
  email = 'x@alex-short.com',
  expiresInSeconds = 8 * 3600
): string {
  // The tenant JWT signing secret — must be set as SUPABASE_JWT_SECRET env var.
  // PyJWT (in the API) uses the secret string directly as UTF-8 bytes.
  const secretString = process.env.SUPABASE_JWT_SECRET;
  if (!secretString) throw new Error('SUPABASE_JWT_SECRET env var is required for E2E tests');
  const secretBytes = Buffer.from(secretString, 'utf8');

  const now = Math.floor(Date.now() / 1000);
  const exp = now + expiresInSeconds;

  function b64url(obj: object | string): string {
    const json = typeof obj === 'string' ? obj : JSON.stringify(obj);
    return Buffer.from(json).toString('base64url');
  }

  const header = b64url({ alg: 'HS256', typ: 'JWT' });
  const jwtPayload = b64url({
    sub,
    aud: 'authenticated',
    role: 'authenticated',
    email,
    iat: now,
    exp,
    iss: 'https://vzsohavtuotocgrfkfyd.supabase.co/auth/v1',
  });

  const sig = crypto
    .createHmac('sha256', secretBytes)
    .update(`${header}.${jwtPayload}`)
    .digest('base64url');

  return `${header}.${jwtPayload}.${sig}`;
}

// Pre-generate the captain JWT for this test session (valid for 8 hours).
// Used by callActionDirect and all shard-34 positive (HOD/Captain) tests.
export const SESSION_JWT = generateFreshJwt();

/**
 * Call an action via direct HTTP fetch using a pre-generated JWT.
 *
 * This bypasses the browser localStorage session entirely, which is
 * unreliable when Supabase client clears self-minted tokens.
 */
export async function callActionDirect(
  page: Page,
  action: string,
  payload: Record<string, unknown>,
  contextOverrides: Record<string, string> = {}
): Promise<{ status: number; data: Record<string, unknown> }> {
  const jwt = SESSION_JWT;
  const body = JSON.stringify({
    action,
    context: { yacht_id: RBAC_CONFIG.yachtId, ...contextOverrides },
    payload,
  });

  return page.evaluate(
    async ([fetchUrl, authToken, reqBody]) => {
      const res = await fetch(fetchUrl as string, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
        body: reqBody as string,
      });
      const data = await res.json().catch(() => ({}));
      return { status: res.status, data };
    },
    [
      `${API_URL_VAL}/v1/actions/execute`,
      jwt,
      body,
    ] as [string, string, string]
  );
}

/**
 * Call an action with an explicit JWT — use this for RBAC tests where the
 * caller identity must differ from the SESSION_JWT captain token.
 *
 * The page is only used as a fetch execution context; localStorage is ignored.
 * Pass any page fixture (crewPage, hodPage, etc.) — the JWT determines identity.
 */
export async function callActionAs(
  page: Page,
  jwt: string,
  action: string,
  payload: Record<string, unknown>,
  contextOverrides: Record<string, string> = {}
): Promise<{ status: number; data: Record<string, unknown> }> {
  const body = JSON.stringify({
    action,
    context: { yacht_id: RBAC_CONFIG.yachtId, ...contextOverrides },
    payload,
  });

  return page.evaluate(
    async ([fetchUrl, authToken, reqBody]) => {
      const res = await fetch(fetchUrl as string, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
        body: reqBody as string,
      });
      const data = await res.json().catch(() => ({}));
      return { status: res.status, data };
    },
    [
      `${API_URL_VAL}/v1/actions/execute`,
      jwt,
      body,
    ] as [string, string, string]
  );
}

export { BASE_URL_VAL as BASE_URL_DIRECT };

/**
 * Poll ledger_events for a specific action + entity_id written after testStart.
 * Shared across all shard-34 spec files — do not re-define locally.
 */
export async function pollLedger(
  supabaseAdmin: import('@supabase/supabase-js').SupabaseClient,
  action: string,
  entityId: string,
  testStart: Date
): Promise<void> {
  const { expect } = await import('@playwright/test');
  await expect.poll(
    async () => {
      const { data } = await supabaseAdmin
        .from('ledger_events')
        .select('id, action, entity_id')
        .eq('action', action)
        .eq('entity_id', entityId)
        .gte('created_at', testStart.toISOString())
        .limit(1);
      return data?.length ?? 0;
    },
    {
      intervals: [500, 1000, 1500, 2000],
      timeout: 10_000,
      message: `Expected ledger_events row for ${action} on ${entityId}`,
    }
  ).toBeGreaterThanOrEqual(1);
}
