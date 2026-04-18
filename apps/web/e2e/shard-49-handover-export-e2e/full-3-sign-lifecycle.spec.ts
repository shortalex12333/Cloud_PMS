/**
 * Shard-49: Handover — Full 3-signature lifecycle (feat/handover04-incoming-sign)
 * ==============================================================================
 *
 * The CEO-ready compliance proof: one export walks the full chain.
 *
 *   Step A  Captain creates export          → review_status=pending_review
 *   Step B  Captain signs outgoing          → pending_hod_signature + user_sig
 *   Step C  Captain countersigns            → complete + hod_sig
 *   Step D  Chief officer acknowledges      → signoff_complete=true + incoming_sig
 *   Step E  Verify all three DB signatures, review_status, signoff_complete
 *   Step F  Verify ledger + notification cascade for all 3 compliance events
 *
 * This is the ONLY test that sits across all three sign surfaces — the
 * per-stage unit & shard-47/49 tests cover their pieces in isolation.
 * Here we prove the full chain holds together.
 */

import { test, expect } from '../rbac-fixtures';
import { createClient, SupabaseClient } from '@supabase/supabase-js';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

const MASTER_URL = 'https://qvzmkaamzaqxpzbewjxe.supabase.co';
const MASTER_ANON =
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
  user: { id: string; email: string };
}

async function masterSignIn(role: Role): Promise<MasterSession> {
  const { email, password } = CREDS[role];
  const r = await fetch(`${MASTER_URL}/auth/v1/token?grant_type=password`, {
    method: 'POST',
    headers: { apikey: MASTER_ANON, 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) throw new Error(`masterSignIn(${role}): ${r.status}`);
  return (await r.json()) as MasterSession;
}

function tenantDb(): SupabaseClient {
  return createClient(TENANT_URL, TENANT_SERVICE_KEY, {
    auth: { autoRefreshToken: false, persistSession: false },
  });
}

function authHeaders(token: string) {
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
}

const SEEDED_IDS: string[] = [];
test.afterAll(async () => {
  for (const id of SEEDED_IDS) {
    try {
      const { error } = await tenantDb()
        .from('handover_exports')
        .update({ review_status: 'archived' })
        .eq('id', id);
      if (error) throw new Error(`archive error: ${error.message}`);
    } catch (e) {
      console.warn(`[afterAll] archive ${id}: ${e}`);
    }
  }
});

test.describe('Full 3-signature compliance chain', () => {
  test('export → sign outgoing → countersign → acknowledge — all persist + cascade', async ({
    captainPage,
  }) => {
    test.setTimeout(600_000); // 10 min — worst-case Render cold-start × 3 calls

    await captainPage.goto('/');
    await captainPage.waitForLoadState('domcontentloaded');

    const db = tenantDb();
    const captainSession = await masterSignIn('captain');
    const captainUserId = captainSession.user.id;
    const captainToken = captainSession.access_token;

    // ── Step A: Create export ───────────────────────────────────────────────
    console.log('[LIFECYCLE] Step A: create export');
    let exportId = '';
    for (let a = 1; a <= 3; a++) {
      const r = await captainPage.request.post(`${API_URL}/v1/handover/export`, {
        headers: authHeaders(captainToken),
        data: { export_type: 'html', filter_by_user: false },
        timeout: 150_000,
      });
      if (r.status() === 200) {
        exportId = (await r.json()).export_id;
        break;
      }
      if (a === 3) throw new Error(`export failed ${r.status()}`);
      await new Promise((res) => setTimeout(res, 5000));
    }
    SEEDED_IDS.push(exportId);
    console.log(`[LIFECYCLE] export_id=${exportId}`);

    // DB: pending_review
    {
      const { data, error } = await db
        .from('handover_exports')
        .select('review_status, signoff_complete')
        .eq('id', exportId)
        .single();
      if (error) throw new Error(`step A query error: ${error.message}`);
      expect(data!.review_status).toBe('pending_review');
    }

    // ── Step B: Captain signs outgoing ──────────────────────────────────────
    console.log('[LIFECYCLE] Step B: outgoing sign');
    const submitRes = await captainPage.request.post(
      `${API_URL}/v1/handover/export/${exportId}/submit`,
      {
        headers: authHeaders(captainToken),
        data: {
          sections: [
            {
              id: 'sec-1',
              title: 'Test Section',
              content: 'Full-lifecycle seed',
              items: [{ id: 'item-1', content: 'Item one', priority: 'normal' }],
              is_critical: false,
              order: 0,
            },
          ],
          userSignature: {
            image_base64: FAKE_SIG_PNG,
            signed_at: new Date().toISOString(),
            signer_name: 'Captain Outgoing',
            signer_id: captainUserId,
          },
        },
        timeout: 60_000,
      },
    );
    expect(submitRes.status()).toBe(200);

    // DB: pending_hod_signature + user_sig populated
    {
      const { data, error } = await db
        .from('handover_exports')
        .select('review_status, user_signature, user_signed_at')
        .eq('id', exportId)
        .single();
      if (error) throw new Error(`step B query error: ${error.message}`);
      expect(data!.review_status).toBe('pending_hod_signature');
      expect(data!.user_signature).toBeTruthy();
      expect(data!.user_signed_at).toBeTruthy();
    }

    // ── Step C: Captain countersigns ────────────────────────────────────────
    console.log('[LIFECYCLE] Step C: countersign');
    let countersigned = false;
    for (let a = 1; a <= 3; a++) {
      const r = await captainPage.request.post(
        `${API_URL}/v1/handover/export/${exportId}/countersign`,
        {
          headers: authHeaders(captainToken),
          data: {
            hodSignature: {
              image_base64: FAKE_SIG_PNG,
              signed_at: new Date().toISOString(),
              signer_name: 'Captain HOD',
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
      if (a === 3) throw new Error(`countersign failed ${r.status()}`);
      await new Promise((res) => setTimeout(res, 5000));
    }
    expect(countersigned).toBe(true);

    // DB: complete + hod_sig populated
    {
      const { data, error } = await db
        .from('handover_exports')
        .select('review_status, hod_signature, hod_signed_at')
        .eq('id', exportId)
        .single();
      if (error) throw new Error(`step C query error: ${error.message}`);
      expect(data!.review_status).toBe('complete');
      expect(data!.hod_signature).toBeTruthy();
      expect(data!.hod_signed_at).toBeTruthy();
    }

    // ── Step D: Different user acknowledges incoming ────────────────────────
    //
    // We impersonate `crew` for the ack because in the seed, captain is
    // BOTH outgoing + HOD, so self-ack prevention would block captain from
    // acknowledging. The handler only blocks when userId === outgoing or HOD
    // signer id — crew is neither.
    console.log('[LIFECYCLE] Step D: incoming ack (crew)');
    const crewSession = await masterSignIn('crew');
    const crewUserId = crewSession.user.id;

    const ackRes = await captainPage.request.post(
      `${API_URL}/v1/actions/handover/${exportId}/sign/incoming?acknowledge_critical=true&method=typed`,
      { headers: authHeaders(crewSession.access_token), timeout: 60_000 },
    );
    const ackBody: any = await ackRes.json().catch(() => ({}));
    console.log(`[LIFECYCLE] ack status=${ackRes.status()} body=${JSON.stringify(ackBody)}`);
    expect(ackRes.status()).toBe(200);
    expect(ackBody.signoff_complete).toBe(true);

    // ── Step E: Final DB state — all 3 signatures present ───────────────────
    console.log('[LIFECYCLE] Step E: final DB snapshot');
    const { data: finalRow, error: finalErr } = await db
      .from('handover_exports')
      .select(
        'review_status, signoff_complete, user_signature, hod_signature, incoming_user_id, incoming_signed_at, signatures',
      )
      .eq('id', exportId)
      .single();
    if (finalErr) throw new Error(`step E query error: ${finalErr.message}`);
    expect(finalRow).toBeTruthy();
    expect(finalRow!.review_status).toBe('complete');
    expect(finalRow!.signoff_complete).toBe(true);
    expect(finalRow!.user_signature).toBeTruthy();
    expect(finalRow!.hod_signature).toBeTruthy();
    expect(finalRow!.incoming_user_id).toBe(crewUserId);
    expect(typeof finalRow!.incoming_signed_at).toBe('string');
    expect(!Number.isNaN(Date.parse(finalRow!.incoming_signed_at as string))).toBe(true);

    // ── Step F: Ledger cascade — all three compliance events present ────────
    console.log('[LIFECYCLE] Step F: ledger cascade');
    const expectedActions = [
      'requires_countersignature',
      'handover_countersigned',
      'handover_acknowledged',
    ];
    for (const action of expectedActions) {
      // ledger_events columns from build_ledger_event (ledger_utils.py) —
      // no actor_id column, user_id holds the emitting user.
      const { data: rows, error: rowsErr } = await db
        .from('ledger_events')
        .select('id, action, user_id, entity_id')
        .eq('entity_id', exportId)
        .eq('action', action);
      if (rowsErr) throw new Error(`ledger query (${action}) error: ${rowsErr.message}`);
      expect(rows, `ledger rows for action=${action}`).toBeTruthy();
      expect(
        (rows as any[]).length,
        `expected >=1 ledger row for action=${action}, got ${(rows as any[]).length}`,
      ).toBeGreaterThanOrEqual(1);
      console.log(`[LIFECYCLE] ledger '${action}': ${(rows as any[]).length} row(s)`);
    }

    // Notification cascade — each compliance event fans out to multiple
    // user_id rows in ledger_events (the "notification" is the ledger row
    // itself, per the domain model). We assert at least 2 distinct user_ids
    // on the acknowledge cascade (actor + outgoing + captain/manager fan-out).
    {
      const { data: ackRows, error: ackRowsErr } = await db
        .from('ledger_events')
        .select('user_id')
        .eq('entity_id', exportId)
        .eq('action', 'handover_acknowledged');
      if (ackRowsErr) throw new Error(`ack fan-out query error: ${ackRowsErr.message}`);
      const distinct = new Set((ackRows as any[]).map((r) => r.user_id));
      expect(
        distinct.size,
        `handover_acknowledged fan-out — expected >=2 distinct users, got ${distinct.size}`,
      ).toBeGreaterThanOrEqual(2);
      expect(distinct.has(crewUserId)).toBe(true);
      expect(distinct.has(captainUserId)).toBe(true);
    }

    console.log('[LIFECYCLE] PASSED — full 3-signature chain verified');
  });
});
