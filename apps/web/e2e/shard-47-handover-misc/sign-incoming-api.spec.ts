/**
 * Shard-47: Handover — sign_incoming API wire walk (feat/handover04-incoming-sign)
 * ==============================================================================
 *
 * Full-stack verification of POST /v1/actions/handover/{id}/sign/incoming:
 *   N1  Happy path — 200 + DB fields + ledger cascade + audit row
 *   N2  Rejection on wrong review_status → 409 INVALID_STATUS
 *   N3  Rejection on double-ack → 409 already-acknowledged
 *   N4  Rejection on unacknowledged critical → 400/409
 *   N5  Crew role NOT 403 (regression guard for Bug 1 fix)
 *
 * Contract (apps/api/routes/p0_actions_routes.py:2210):
 *   POST /v1/actions/handover/{export_id}/sign/incoming
 *        ?acknowledge_critical=<bool>[&note=<str>][&method=<str>]
 *   Request body is empty — FastAPI reads scalar query params, not JSON.
 *
 * Seeding strategy:
 *   The SESSION_JWT (captain x@alex-short.com) signs the OUTGOING side,
 *   then a different identity (crew or hod, masterSignIn'd per test) hits
 *   /sign/incoming. This matches reality — the incoming signer is never
 *   the same user who wrote the handover.
 *
 * Cleanup (per CEO archive-not-delete rule):
 *   handover_exports has a DENY DELETE grant; there is no archived_at
 *   column. We flip `review_status='archived'` on every seeded row in
 *   afterAll so seeds don't pollute the queue. Ledger / audit rows are
 *   append-only — we do NOT touch them.
 */

import { test, expect, generateTestId } from '../rbac-fixtures';
import { SESSION_JWT } from '../shard-34-lens-actions/helpers';
import { BASE_URL } from '../shard-33-lens-actions/helpers';
import { createClient, SupabaseClient } from '@supabase/supabase-js';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// TENANT Supabase — where handover_exports, ledger_events, pms_audit_log live.
// Shard-47/49 already use this key; we reuse rather than re-plumbing.
const TENANT_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const TENANT_SERVICE_KEY =
  process.env.TENANT_SERVICE_KEY ||
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

// MASTER auth — app.celeste7.ai authenticates here; TENANT holds the data.
const MASTER_URL = 'https://qvzmkaamzaqxpzbewjxe.supabase.co';
const MASTER_ANON =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM5NzkwNDYsImV4cCI6MjA3OTU1NTA0Nn0.MMzzsRkvbug-u19GBUnD0qLDtMVWEbOf6KE8mAADaxw';

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
  user: { id: string; email: string };
}

function tenantDb(): SupabaseClient {
  return createClient(TENANT_URL, TENANT_SERVICE_KEY, {
    auth: { autoRefreshToken: false, persistSession: false },
  });
}

/**
 * Exchange email+password for a MASTER access_token. Lives in shard-47
 * because N5 needs a crew identity distinct from the captain SESSION_JWT,
 * and shard-47 currently has no cross-role helper. Matches shard-54's
 * implementation so behaviour stays identical across shards.
 */
async function masterSignIn(role: Role): Promise<MasterSession> {
  const { email, password } = CREDS[role];
  const res = await fetch(`${MASTER_URL}/auth/v1/token?grant_type=password`, {
    method: 'POST',
    headers: { apikey: MASTER_ANON, 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    throw new Error(`masterSignIn(${role}): ${res.status} ${await res.text()}`);
  }
  return (await res.json()) as MasterSession;
}

function authHeaders(token: string) {
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
}

/**
 * Create a handover_exports row in review_status='complete' with
 * incoming_signed_at=null so the sign/incoming endpoint can fire.
 *
 * The flow: create → submit (outgoing sign) → countersign (HOD). We use
 * the captain SESSION_JWT for all three because the test-tenant only has
 * one HOD-capable account wired up in shard-47; countersign allows
 * captain role in its allow-list. This leaves incoming as the only
 * unsigned slot — exactly what N1/N3/N4 need.
 *
 * Returns the export_id. Retries the initial POST /v1/handover/export
 * 3× on 5xx (Render cold-start can take up to 120s; matches createExport
 * in shard-49).
 */
async function seedCompleteExport(
  request: import('@playwright/test').APIRequestContext,
  captainToken: string,
  captainUserId: string,
): Promise<string> {
  // 1. Export
  let exportId = '';
  for (let attempt = 1; attempt <= 3; attempt++) {
    const r = await request.post(`${API_URL}/v1/handover/export`, {
      headers: authHeaders(captainToken),
      data: { export_type: 'html', filter_by_user: false },
      timeout: 150_000,
    });
    if (r.status() === 200) {
      const j: any = await r.json();
      exportId = j.export_id;
      break;
    }
    if (attempt === 3) throw new Error(`seedCompleteExport: export failed ${r.status()}`);
    await new Promise((res) => setTimeout(res, 5000));
  }

  const sections = [
    {
      id: 'sec-1',
      title: 'Test Section',
      content: 'Seeded for sign-incoming wire walk',
      items: [{ id: 'item-1', content: 'Test item', priority: 'normal' }],
      is_critical: false,
      order: 0,
    },
  ];
  const nowIso = new Date().toISOString();

  // 2. Submit (outgoing sign)
  const submitR = await request.post(
    `${API_URL}/v1/handover/export/${exportId}/submit`,
    {
      headers: authHeaders(captainToken),
      data: {
        sections,
        userSignature: {
          image_base64: FAKE_SIG_PNG,
          signed_at: nowIso,
          signer_name: 'Captain Seed',
          signer_id: captainUserId,
        },
      },
      timeout: 60_000,
    },
  );
  if (submitR.status() !== 200) {
    throw new Error(`seedCompleteExport: submit failed ${submitR.status()} ${await submitR.text()}`);
  }

  // 3. Countersign (captain is in allowed_roles for countersign)
  let countersigned = false;
  for (let attempt = 1; attempt <= 3; attempt++) {
    const r = await request.post(
      `${API_URL}/v1/handover/export/${exportId}/countersign`,
      {
        headers: authHeaders(captainToken),
        data: {
          hodSignature: {
            image_base64: FAKE_SIG_PNG,
            signed_at: nowIso,
            signer_name: 'Captain Countersign Seed',
            signer_id: captainUserId,
          },
        },
        timeout: 150_000,
      },
    );
    if (r.status() === 200) {
      countersigned = true;
      break;
    }
    if (attempt === 3) throw new Error(`seedCompleteExport: countersign failed ${r.status()}`);
    await new Promise((res) => setTimeout(res, 5000));
  }
  if (!countersigned) throw new Error('seedCompleteExport: countersign never succeeded');

  return exportId;
}

/** Archive a seeded export by flipping review_status (no delete — handover_exports DENY DELETE). */
async function archiveExport(exportId: string): Promise<void> {
  await tenantDb().from('handover_exports').update({ review_status: 'archived' }).eq('id', exportId);
}

/** For N4: inject a critical item into edited_content so the sign/incoming handler
 *  fails the critical-ack gate when acknowledge_critical=false. The column is JSONB.
 *  We write this directly via the TENANT service key — it's test-fixture seeding,
 *  not a real user action, and the sign_incoming handler only reads the shape. */
async function markExportAsCritical(exportId: string): Promise<void> {
  const db = tenantDb();
  const { data } = await db
    .from('handover_exports')
    .select('edited_content')
    .eq('id', exportId)
    .single();
  const content = ((data?.edited_content as Record<string, unknown>) ?? {}) as any;
  content.sections = [
    ...(Array.isArray(content.sections) ? content.sections : []),
    {
      id: 'crit-sec-1',
      title: 'Critical Section',
      is_critical: true,
      items: [{ id: 'crit-i-1', content: 'Critical item', priority: 'critical' }],
    },
  ];
  await db.from('handover_exports').update({ edited_content: content }).eq('id', exportId);
}

// ═══════════════════════════════════════════════════════════════════════════
// Track seeded IDs so we can archive in afterAll.
// ═══════════════════════════════════════════════════════════════════════════

const SEEDED_EXPORT_IDS: string[] = [];

test.afterAll(async () => {
  for (const id of SEEDED_EXPORT_IDS) {
    try {
      await archiveExport(id);
    } catch (e) {
      console.warn(`[afterAll] archive failed for ${id}: ${e}`);
    }
  }
});

// ═══════════════════════════════════════════════════════════════════════════
// N1 — Happy path
// ═══════════════════════════════════════════════════════════════════════════

test.describe('sign_incoming API — wire walk', () => {
  // Each test seeds via the full export pipeline (up to 3× ~90s LLM runs for
  // export + submit + countersign on cold Render). Default 60s per-test
  // timeout would fail on the first seed call; we bump per-test to 10min.
  test.setTimeout(600_000);

  test('N1 | crew acks completed export → 200 + DB + ledger + audit', async ({
    captainPage,
  }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    // Need captain user.id for the outgoing-signer field on the seed.
    const captainSession = await masterSignIn('captain');
    const captainUserId = captainSession.user.id;

    const exportId = await seedCompleteExport(
      captainPage.request,
      captainSession.access_token,
      captainUserId,
    );
    SEEDED_EXPORT_IDS.push(exportId);
    console.log(`[N1] seeded export ${exportId}, outgoing=${captainUserId}`);

    // Crew token — distinct from captain so self-ack prevention doesn't fire.
    const crewSession = await masterSignIn('crew');
    const crewUserId = crewSession.user.id;

    const qs = new URLSearchParams({
      acknowledge_critical: 'true',
      method: 'typed',
    }).toString();
    const res = await captainPage.request.post(
      `${API_URL}/v1/actions/handover/${exportId}/sign/incoming?${qs}`,
      {
        headers: authHeaders(crewSession.access_token),
        timeout: 60_000,
      },
    );
    const body: any = await res.json().catch(() => ({}));
    console.log(`[N1] POST /sign/incoming status=${res.status()} body=${JSON.stringify(body)}`);

    expect(res.status()).toBe(200);
    expect(body.status).toBe('success');
    expect(body.signoff_complete).toBe(true);
    // Response uses generic `signed_at` (route is polymorphic outgoing/incoming);
    // the namespaced `incoming_signed_at` column is verified on the DB row below.
    expect(typeof body.signed_at).toBe('string');

    // DB: handover_exports row hydrated
    const db = tenantDb();
    const { data: row } = await db
      .from('handover_exports')
      .select('id, incoming_user_id, incoming_signed_at, signoff_complete, review_status')
      .eq('id', exportId)
      .single();
    expect(row).toBeTruthy();
    expect(row!.incoming_user_id).toBe(crewUserId);
    expect(typeof row!.incoming_signed_at).toBe('string');
    // ISO-8601 parse round-trip proves it's a real timestamp, not a stringified null.
    expect(!Number.isNaN(Date.parse(row!.incoming_signed_at as string))).toBe(true);
    expect(row!.signoff_complete).toBe(true);

    // Ledger: handover_acknowledged cascade — actor + outgoing + captains/managers.
    // Exact count varies by test yacht roster; we assert the floor (actor + outgoing)
    // AND that the actor row exists. Going for "exactly 4" would be brittle — see
    // handler `_emit_handover_acknowledged_events` which pulls captain/manager users
    // from auth_users_roles at run time.
    const { data: ledgerRows } = await db
      .from('ledger_events')
      .select('id, action, user_id, actor_id, entity_id, proof_hash')
      .eq('entity_id', exportId)
      .eq('action', 'handover_acknowledged');
    expect(ledgerRows).toBeTruthy();
    expect(ledgerRows!.length).toBeGreaterThanOrEqual(2);
    const recipientIds = (ledgerRows as any[]).map((r) => r.user_id);
    expect(recipientIds).toContain(crewUserId); // actor self-event
    expect(recipientIds).toContain(captainUserId); // outgoing signer
    for (const r of ledgerRows as any[]) {
      expect(typeof r.proof_hash).toBe('string');
      expect((r.proof_hash as string).length).toBe(64); // sha256 hex
    }

    // Audit: pms_audit_log row for the actor
    const { data: auditRows } = await db
      .from('pms_audit_log')
      .select('id, action, entity_id, actor_id')
      .eq('entity_id', exportId)
      .eq('action', 'handover_acknowledged');
    expect(auditRows).toBeTruthy();
    expect(auditRows!.length).toBeGreaterThanOrEqual(1);
    const actorAudit = (auditRows as any[]).find((r) => r.actor_id === crewUserId);
    expect(actorAudit).toBeTruthy();
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // N2 — Wrong review_status → 409
  // ═══════════════════════════════════════════════════════════════════════════

  test('N2 | sign/incoming on pending_hod_signature → 409 INVALID_STATUS', async ({
    captainPage,
  }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const captainSession = await masterSignIn('captain');

    // Create + submit (outgoing only) — leaves review_status=pending_hod_signature.
    let exportId = '';
    for (let attempt = 1; attempt <= 3; attempt++) {
      const r = await captainPage.request.post(`${API_URL}/v1/handover/export`, {
        headers: authHeaders(captainSession.access_token),
        data: { export_type: 'html', filter_by_user: false },
        timeout: 150_000,
      });
      if (r.status() === 200) {
        exportId = (await r.json()).export_id;
        break;
      }
      if (attempt === 3) throw new Error(`N2 seed export failed ${r.status()}`);
      await new Promise((res) => setTimeout(res, 5000));
    }
    SEEDED_EXPORT_IDS.push(exportId);

    await captainPage.request.post(
      `${API_URL}/v1/handover/export/${exportId}/submit`,
      {
        headers: authHeaders(captainSession.access_token),
        data: {
          sections: [
            {
              id: 's',
              title: 't',
              content: 'c',
              items: [{ id: 'i', content: 'x', priority: 'normal' }],
              is_critical: false,
              order: 0,
            },
          ],
          userSignature: {
            image_base64: FAKE_SIG_PNG,
            signed_at: new Date().toISOString(),
            signer_name: 'Captain N2',
            signer_id: captainSession.user.id,
          },
        },
        timeout: 60_000,
      },
    );

    const crewSession = await masterSignIn('crew');
    // DELIBERATE FAIL — use page.request.post directly, NO retry, fast fail.
    // (HANDOVER_MCP01 tip: retry on a test that's supposed to fail masks real regressions.)
    const res = await captainPage.request.post(
      `${API_URL}/v1/actions/handover/${exportId}/sign/incoming?acknowledge_critical=true`,
      { headers: authHeaders(crewSession.access_token), timeout: 30_000 },
    );
    const body: any = await res.json().catch(() => ({}));
    console.log(`[N2] status=${res.status()} body=${JSON.stringify(body)}`);

    expect(res.status()).toBe(409);
    // Error body: project error middleware emits {error, status_code, path}.
    // Keep `detail`/`message` as defensive fallbacks for other routes.
    const msg = String(body.error ?? body.detail ?? body.message ?? '');
    expect(msg.toLowerCase()).toMatch(/review_status|invalid|status/);
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // N3 — Double ack → 409
  // ═══════════════════════════════════════════════════════════════════════════

  test('N3 | sign/incoming twice on same export → second call 409 already', async ({
    captainPage,
  }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const captainSession = await masterSignIn('captain');
    const exportId = await seedCompleteExport(
      captainPage.request,
      captainSession.access_token,
      captainSession.user.id,
    );
    SEEDED_EXPORT_IDS.push(exportId);

    const crewSession = await masterSignIn('crew');
    const hdrs = authHeaders(crewSession.access_token);

    // First ack — should succeed.
    const first = await captainPage.request.post(
      `${API_URL}/v1/actions/handover/${exportId}/sign/incoming?acknowledge_critical=true`,
      { headers: hdrs, timeout: 60_000 },
    );
    expect(first.status()).toBe(200);

    // Second ack — NO retry. Must be 409.
    const second = await captainPage.request.post(
      `${API_URL}/v1/actions/handover/${exportId}/sign/incoming?acknowledge_critical=true`,
      { headers: hdrs, timeout: 30_000 },
    );
    const body: any = await second.json().catch(() => ({}));
    console.log(`[N3] second status=${second.status()} body=${JSON.stringify(body)}`);

    expect(second.status()).toBe(409);
    const msg = String(body.error ?? body.detail ?? body.message ?? '').toLowerCase();
    expect(msg).toContain('already');
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // N4 — Critical not acknowledged → 400/409
  // ═══════════════════════════════════════════════════════════════════════════

  test('N4 | critical item + acknowledge_critical=false → rejected', async ({
    captainPage,
  }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const captainSession = await masterSignIn('captain');
    const exportId = await seedCompleteExport(
      captainPage.request,
      captainSession.access_token,
      captainSession.user.id,
    );
    SEEDED_EXPORT_IDS.push(exportId);
    await markExportAsCritical(exportId);

    const crewSession = await masterSignIn('crew');

    // NO retry — failing-path tests should not mask regressions.
    const res = await captainPage.request.post(
      `${API_URL}/v1/actions/handover/${exportId}/sign/incoming?acknowledge_critical=false`,
      { headers: authHeaders(crewSession.access_token), timeout: 30_000 },
    );
    const body: any = await res.json().catch(() => ({}));
    console.log(`[N4] status=${res.status()} body=${JSON.stringify(body)}`);

    // Handler returns error_code=CRITICAL_NOT_ACKNOWLEDGED → route maps non-
    // INVALID_STATUS/NOT_FOUND errors to 400. Test spec says 400 OR 409.
    expect([400, 409]).toContain(res.status());
    const msg = String(body.error ?? body.detail ?? body.message ?? '').toLowerCase();
    expect(msg).toMatch(/critical|acknowledg/);
  });

  // ═══════════════════════════════════════════════════════════════════════════
  // N5 — Crew role must not get 403 (regression guard for Bug 1)
  // ═══════════════════════════════════════════════════════════════════════════

  test('N5 | crew role no longer 403 (Bug 1 regression)', async ({ captainPage }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const captainSession = await masterSignIn('captain');
    const exportId = await seedCompleteExport(
      captainPage.request,
      captainSession.access_token,
      captainSession.user.id,
    );
    SEEDED_EXPORT_IDS.push(exportId);

    const crewSession = await masterSignIn('crew');
    const res = await captainPage.request.post(
      `${API_URL}/v1/actions/handover/${exportId}/sign/incoming?acknowledge_critical=true`,
      { headers: authHeaders(crewSession.access_token), timeout: 60_000 },
    );
    console.log(`[N5] status=${res.status()}`);

    // The assertion that matters: NOT 403. 200 is the happy path; anything else
    // is NOT 403 so still passes the regression guard, but we log it.
    expect(res.status()).not.toBe(403);
    if (res.status() !== 200) {
      console.warn(`[N5] non-200 (${res.status()}) but not 403 — ${JSON.stringify(await res.json().catch(() => ({})))}`);
    }
  });
});
