/**
 * Shard-54: Handover Domain — sign_incoming UI wire walk (feat/handover04-incoming-sign)
 * =====================================================================================
 *
 * DOM-level verification of the new "Acknowledge Handover" button and the
 * dynamic 3-column signature block in HandoverContent.tsx. Uses the same
 * MASTER-JWT localStorage injection pattern as handover-ui.spec.ts so the
 * browser boots app.celeste7.ai with a real Supabase session (no fake JWTs).
 *
 *   U1  Three-column block renders (Prepared / Reviewed / Acknowledged)
 *       — Acknowledged column shows "Pending"; others show Signed + mono ts
 *   U2  Button visible for eligible incoming user (chief_officer / hod)
 *   U3  Button NOT visible for the outgoing signer (self-ack prevention)
 *   U4  Click Acknowledge → modal opens with canvas + critical checkbox
 *       (when the export has critical items)
 *   U5  Draw + confirm → POST /api/handover-export/{id}/acknowledge 200;
 *       reload → Acknowledged column flips to SIGNED + signer name + ts.
 *
 * Every test seeds its own export via the API (POST /v1/handover/export →
 * submit → countersign) and archives it in afterAll. No shared fixture
 * state between tests.
 */

import { test, expect, type Page, type BrowserContext } from '@playwright/test';
import { createClient, SupabaseClient } from '@supabase/supabase-js';

// Honor docker-stack overrides so the same spec runs against both prod
// (default) and the handover04 local stack (E2E_BASE_URL=http://localhost:3030
// NEXT_PUBLIC_API_URL=http://localhost:8020). Hardcoding prod URLs here
// silently ignored the env vars and made the suite impossible to run
// against a fresh feature-branch build.
const APP_URL = process.env.E2E_BASE_URL || 'https://app.celeste7.ai';
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
const MASTER_URL = 'https://qvzmkaamzaqxpzbewjxe.supabase.co';
const MASTER_REF = 'qvzmkaamzaqxpzbewjxe';
const MASTER_ANON_KEY =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM5NzkwNDYsImV4cCI6MjA3OTU1NTA0Nn0.MMzzsRkvbug-u19GBUnD0qLDtMVWEbOf6KE8mAADaxw';

const TENANT_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const TENANT_SERVICE_KEY =
  process.env.TENANT_SERVICE_KEY ||
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

const FAKE_SIG_PNG =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';

type Role = 'crew' | 'hod' | 'captain';

const CREDS: Record<Role, { email: string; password: string }> = {
  crew: { email: 'crew.test@alex-short.com', password: 'Password2!' },
  hod: { email: 'hod.test@alex-short.com', password: 'Password2!' },
  captain: { email: 'captain.tenant@alex-short.com', password: 'Password2!' },
};

interface MasterSession {
  access_token: string;
  refresh_token: string;
  expires_at: number;
  expires_in: number;
  token_type: string;
  user: { id: string; email: string };
}

async function masterSignIn(role: Role): Promise<MasterSession> {
  const { email, password } = CREDS[role];
  const res = await fetch(`${MASTER_URL}/auth/v1/token?grant_type=password`, {
    method: 'POST',
    headers: { apikey: MASTER_ANON_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(`masterSignIn(${role}): ${res.status}`);
  return (await res.json()) as MasterSession;
}

async function contextForRole(browser: any, role: Role): Promise<BrowserContext> {
  const session = await masterSignIn(role);
  const storageKey = `sb-${MASTER_REF}-auth-token`;
  const storageValue = JSON.stringify({
    access_token: session.access_token,
    refresh_token: session.refresh_token,
    expires_at: session.expires_at,
    expires_in: session.expires_in,
    token_type: session.token_type,
    user: session.user,
  });
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    baseURL: APP_URL,
  });
  await ctx.addInitScript(
    ({ key, value }: { key: string; value: string }) => {
      try {
        window.localStorage.setItem(key, value);
      } catch {
        /* noop */
      }
    },
    { key: storageKey, value: storageValue },
  );
  return ctx;
}

function tenantDb(): SupabaseClient {
  return createClient(TENANT_URL, TENANT_SERVICE_KEY, {
    auth: { autoRefreshToken: false, persistSession: false },
  });
}

/** POST helper with 3-attempt retry on 5xx (Render rolling-deploy window). */
async function postWithRetry(
  page: Page,
  token: string,
  url: string,
  data: unknown,
  attempts = 3,
) {
  for (let i = 0; i < attempts; i++) {
    const r = await page.request.post(url, {
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      data,
      timeout: 150_000,
    });
    if (r.status() < 500) return r;
    if (i < attempts - 1) await page.waitForTimeout(4000);
  }
  throw new Error(`POST ${url}: still 5xx after ${attempts} attempts`);
}

/**
 * Seed a handover_exports row in review_status='complete' with
 * incoming_signed_at=null. Uses the captain session for all three
 * writes (export + submit + countersign) because captain is in the
 * countersign allowed_roles list on the test tenant.
 *
 * Returns { exportId, outgoingUserId } so tests that need to impersonate
 * the outgoing signer (U3) have the right user.
 */
async function seedCompleteExport(page: Page): Promise<{ exportId: string; outgoingUserId: string }> {
  const captainSession = await masterSignIn('captain');
  const token = captainSession.access_token;

  const expRes = await postWithRetry(page, token, `${API_URL}/v1/handover/export`, {
    export_type: 'html',
    filter_by_user: false,
  });
  if (expRes.status() !== 200) throw new Error(`seed export ${expRes.status()}`);
  const { export_id } = (await expRes.json()) as { export_id: string };

  const submitRes = await postWithRetry(
    page,
    token,
    `${API_URL}/v1/handover/export/${export_id}/submit`,
    {
      sections: [
        {
          id: 's',
          title: 'S',
          content: 'c',
          items: [{ id: 'i', content: 'x', priority: 'normal' }],
          is_critical: false,
          order: 0,
        },
      ],
      userSignature: {
        image_base64: FAKE_SIG_PNG,
        signed_at: new Date().toISOString(),
        signer_name: 'Captain Seed',
        signer_id: captainSession.user.id,
      },
    },
  );
  if (submitRes.status() !== 200) throw new Error(`seed submit ${submitRes.status()}`);

  const csRes = await postWithRetry(
    page,
    token,
    `${API_URL}/v1/handover/export/${export_id}/countersign`,
    {
      hodSignature: {
        image_base64: FAKE_SIG_PNG,
        signed_at: new Date().toISOString(),
        signer_name: 'Captain Countersign',
        signer_id: captainSession.user.id,
      },
    },
  );
  if (csRes.status() !== 200) throw new Error(`seed countersign ${csRes.status()}`);

  return { exportId: export_id, outgoingUserId: captainSession.user.id };
}

/** "Archive" a seeded export. handover_exports has DENY DELETE, no metadata
 *  column, and no safe-to-overwrite textual column (edited_content is real
 *  data; incoming_comments is user-facing). Log the orphan id and return —
 *  a separate sweep script owns cleanup. */
async function archiveExport(exportId: string): Promise<void> {
  console.log(`[afterAll] orphan handover_exports row ${exportId} (handover04-sign-incoming)`);
}

// Track seeds for teardown.
const SEEDED_IDS: string[] = [];
test.afterAll(async () => {
  for (const id of SEEDED_IDS) {
    try {
      await archiveExport(id);
    } catch (e) {
      console.warn(`[afterAll] archive ${id}: ${e}`);
    }
  }
});

// ═══════════════════════════════════════════════════════════════════════════
// U1 — Three-column signature block
// ═══════════════════════════════════════════════════════════════════════════

test.describe('sign_incoming UI — wire walk', () => {
  // Each test seeds a full export (create + submit + countersign — each ~90s
  // cold on docker) then navigates the lens. Bump per-test budget to 10min.
  test.setTimeout(600_000);

  test('U1 | signature block renders Prepared / Reviewed / Acknowledged with mono timestamps', async ({
    browser,
  }) => {
    const seedCtx = await contextForRole(browser, 'captain');
    const seedPage = await seedCtx.newPage();
    const { exportId } = await seedCompleteExport(seedPage);
    SEEDED_IDS.push(exportId);
    await seedCtx.close();

    const ctx = await contextForRole(browser, 'hod');
    const page = await ctx.newPage();
    await page.goto(`/handover-export/${exportId}`);
    await page.waitForLoadState('domcontentloaded');

    // Signature block mounts via SignatureBlock component — it has
    // data-testid="signature-block" so we assert on that, not on text
    // (the three labels also appear in other UI strings).
    const block = page.locator('[data-testid="signature-block"]');
    await expect(block).toBeVisible({ timeout: 25_000 });

    // Three labels are present in the three columns.
    await expect(block.getByText('Prepared By', { exact: true })).toBeVisible();
    await expect(block.getByText('Reviewed By', { exact: true })).toBeVisible();
    await expect(block.getByText('Acknowledged By', { exact: true })).toBeVisible();

    // Acknowledged column has NO timestamp yet — the pending slot has
    // data-testid="sig-pending". At least one such element must exist.
    const pendingSlots = block.locator('[data-testid="sig-pending"]');
    expect(await pendingSlots.count()).toBeGreaterThanOrEqual(1);

    // Timestamps on the two SIGNED columns are monospace. The signed slot
    // renders the IBM Plex Mono font via inline style on the <span>.
    // Find a sibling timestamp span in the Prepared / Reviewed columns by
    // walking from the signed badge. We use a broad selector and then
    // getComputedStyle to assert the font-family chain.
    const monoFont = await page.evaluate(() => {
      const block = document.querySelector('[data-testid="signature-block"]');
      if (!block) return null;
      // Timestamps live in <span> with fontFamily set in inline style.
      const spans = Array.from(block.querySelectorAll('span'));
      for (const s of spans) {
        const fam = window.getComputedStyle(s).fontFamily;
        if (fam && fam.toLowerCase().includes('plex mono')) {
          return fam;
        }
      }
      return null;
    });
    expect(monoFont).not.toBeNull();
    expect((monoFont as string).toLowerCase()).toContain('plex mono');

    await ctx.close();
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // U2 — Eligible user sees Acknowledge button
  // ═══════════════════════════════════════════════════════════════════════════

  test('U2 | chief_officer/hod sees Acknowledge Handover button on complete export', async ({
    browser,
  }) => {
    const seedCtx = await contextForRole(browser, 'captain');
    const seedPage = await seedCtx.newPage();
    const { exportId } = await seedCompleteExport(seedPage);
    SEEDED_IDS.push(exportId);
    await seedCtx.close();

    const ctx = await contextForRole(browser, 'hod');
    const page = await ctx.newPage();
    await page.goto(`/handover-export/${exportId}`);
    await page.waitForLoadState('domcontentloaded');

    // 40s — cold Render + lens hydration + user.role propagation.
    await expect(page.getByText('Acknowledge Handover', { exact: false }).first()).toBeVisible({
      timeout: 40_000,
    });
    // Sibling buttons should NOT be present on a complete export.
    await expect(page.getByText('Countersign Handover', { exact: true })).not.toBeVisible();

    await ctx.close();
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // U3 — Outgoing signer does NOT see Acknowledge button
  // ═══════════════════════════════════════════════════════════════════════════

  test('U3 | captain who signed outgoing does NOT see Acknowledge button (self-ack prevention)', async ({
    browser,
  }) => {
    const seedCtx = await contextForRole(browser, 'captain');
    const seedPage = await seedCtx.newPage();
    // Captain is both the outgoing signer and the HOD countersigner in the seed.
    const { exportId } = await seedCompleteExport(seedPage);
    SEEDED_IDS.push(exportId);
    await seedCtx.close();

    const ctx = await contextForRole(browser, 'captain');
    const page = await ctx.newPage();
    await page.goto(`/handover-export/${exportId}`);
    await page.waitForLoadState('domcontentloaded');

    // The signature block still renders (visible proof page is alive),
    // but the Acknowledge button must not — canUserAcknowledgeHandover
    // returns false when userId === outgoingSignerId OR hodSignerId.
    await expect(page.locator('[data-testid="signature-block"]')).toBeVisible({
      timeout: 25_000,
    });
    // Give the lens 3s to potentially render any buttons before asserting absence.
    await page.waitForTimeout(3000);
    await expect(page.getByText('Acknowledge Handover', { exact: false })).not.toBeVisible();

    await ctx.close();
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // U4 — Click Acknowledge → modal + canvas appear
  // ═══════════════════════════════════════════════════════════════════════════

  test('U4 | click Acknowledge → canvas modal opens', async ({ browser }) => {
    const seedCtx = await contextForRole(browser, 'captain');
    const seedPage = await seedCtx.newPage();
    const { exportId } = await seedCompleteExport(seedPage);
    SEEDED_IDS.push(exportId);
    await seedCtx.close();

    const ctx = await contextForRole(browser, 'hod');
    const page = await ctx.newPage();
    await page.goto(`/handover-export/${exportId}`);
    await page.waitForLoadState('domcontentloaded');

    const ackBtn = page.getByText('Acknowledge Handover', { exact: false }).first();
    await expect(ackBtn).toBeVisible({ timeout: 40_000 });
    await ackBtn.click();

    // The same signature canvas (416×160) as sign/countersign.
    const canvas = page.locator('canvas[width="416"][height="160"]');
    await expect(canvas).toBeVisible({ timeout: 5_000 });

    // Clear and Cancel buttons are rendered in the modal.
    await expect(page.getByRole('button', { name: 'Clear' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Cancel' })).toBeVisible();

    await ctx.close();
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // U5 — Draw + confirm → proxy 200 + reload shows SIGNED
  // ═══════════════════════════════════════════════════════════════════════════

  test('U5 | draw + confirm → /api/.../acknowledge 200 + Acknowledged flips to SIGNED on reload', async ({
    browser,
  }) => {
    const seedCtx = await contextForRole(browser, 'captain');
    const seedPage = await seedCtx.newPage();
    const { exportId } = await seedCompleteExport(seedPage);
    SEEDED_IDS.push(exportId);
    await seedCtx.close();

    const ctx = await contextForRole(browser, 'hod');
    const page = await ctx.newPage();
    await page.goto(`/handover-export/${exportId}`);
    await page.waitForLoadState('domcontentloaded');

    const ackBtn = page.getByText('Acknowledge Handover', { exact: false }).first();
    await expect(ackBtn).toBeVisible({ timeout: 40_000 });
    await ackBtn.click();

    const canvas = page.locator('canvas[width="416"][height="160"]');
    await expect(canvas).toBeVisible({ timeout: 5_000 });

    // Draw a short stroke on the canvas via mouse events so the signature
    // image_base64 payload is a non-empty PNG (handler records it verbatim).
    const box = await canvas.boundingBox();
    if (!box) throw new Error('canvas has no bounding box');
    await page.mouse.move(box.x + 40, box.y + 40);
    await page.mouse.down();
    await page.mouse.move(box.x + 120, box.y + 90, { steps: 8 });
    await page.mouse.move(box.x + 200, box.y + 60, { steps: 8 });
    await page.mouse.up();

    // Capture the proxy POST response.
    const ackResponsePromise = page.waitForResponse(
      (r) =>
        r.url().includes(`/api/handover-export/${exportId}/acknowledge`) &&
        r.request().method() === 'POST',
      { timeout: 60_000 },
    );

    // The confirm button label in the sign modal is "Confirm" (shared with
    // sign/countersign flow; see HandoverContent handleSignConfirm).
    await page.getByRole('button', { name: /^Confirm/i }).click();

    const ackResp = await ackResponsePromise;
    expect(ackResp.status()).toBe(200);

    // Reload → entity endpoint now returns incoming_signed_at populated and
    // the SignatureColumn flips from pending (sig-pending) to signed badge.
    await page.reload();
    await page.waitForLoadState('domcontentloaded');

    const block = page.locator('[data-testid="signature-block"]');
    await expect(block).toBeVisible({ timeout: 25_000 });

    // The Acknowledged column is the third column. We assert the block
    // contains a SIGNED badge (green "Signed" label rendered by
    // SignatureColumn when slot is populated) — and we DB-verify the
    // incoming_signed_at is now set so we know the UI is showing real data.
    const { data: row, error: rowErr } = await tenantDb()
      .from('handover_exports')
      .select('incoming_signed_at, incoming_user_id')
      .eq('id', exportId)
      .single();
    if (rowErr) throw new Error(`U5 handover_exports query error: ${rowErr.message}`);
    expect(row).toBeTruthy();
    expect(typeof row!.incoming_signed_at).toBe('string');

    // After reload, at least one Signed badge still shows in the block
    // (outgoing + HOD were signed; incoming is now signed — expect 3).
    // We do a soft assertion: >=3 Signed labels in the block.
    const signedCount = await block.getByText('Signed', { exact: true }).count();
    expect(signedCount).toBeGreaterThanOrEqual(3);

    await ctx.close();
  });
});
