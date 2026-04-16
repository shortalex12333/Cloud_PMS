/**
 * Shard-49: Handover Export E2E — Full Lifecycle
 *
 * Covers:
 *   1. Captain exports handover — HARD PROOF (response + DB + ledger)
 *   2. Entity endpoint returns export metadata + review_status
 *   3. Full lifecycle: export -> submit -> countersign -> complete — HARD PROOF
 *   4. Countersign on wrong state -> 400
 *
 * API contracts (from handover_export_routes.py):
 *   POST /v1/handover/export           — generate export
 *   GET  /v1/entity/handover_export/:id — entity detail
 *   POST /v1/handover/export/:id/submit — user signs
 *   POST /v1/handover/export/:id/countersign — HOD countersigns
 *
 * Note: Production uses local export (HANDOVER_USE_MICROSERVICE=false).
 * edited_content stores { item_ids: [...] }, NOT { sections: [...] }.
 * Sections come from v_handover_draft_complete view only when microservice runs.
 *
 * Test users:
 *   Captain: x@alex-short.com / Password2! (role: captain)
 */

import { test, expect, RBAC_CONFIG } from '../rbac-fixtures';
import { createClient, SupabaseClient } from '@supabase/supabase-js';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// TENANT Supabase client — handover_exports, ledger_events live here (not MASTER).
const TENANT_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const TENANT_SERVICE_KEY = process.env.TENANT_SERVICE_KEY
  || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY';

function tenantAdmin(): SupabaseClient {
  return createClient(TENANT_URL, TENANT_SERVICE_KEY, {
    auth: { autoRefreshToken: false, persistSession: false },
  });
}

// 1x1 transparent PNG — valid minimal image for signature payloads
const FAKE_SIGNATURE_BASE64 =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';

/** Helper: sign in as captain via MASTER auth and return session */
async function captainSession(supabaseAdmin: any) {
  const { data: { session }, error } = await supabaseAdmin.auth.signInWithPassword({
    email: 'x@alex-short.com',
    password: 'Password2!',
  });
  if (error || !session) throw new Error(`Captain auth failed: ${error?.message ?? 'no session'}`);
  return session;
}

/** Helper: common headers for API calls */
function authHeaders(accessToken: string) {
  return {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json',
  };
}

/** Helper: create an export and return the parsed result */
async function createExport(
  request: any,
  accessToken: string,
): Promise<{ export_id: string; sections_count: number; total_items: number; status: string; [key: string]: any }> {
  const response = await request.post(`${API_URL}/v1/handover/export`, {
    headers: authHeaders(accessToken),
    data: { export_type: 'html', filter_by_user: false },
  });
  expect(response.status()).toBe(200);
  const result = await response.json();
  expect(result.status).toBe('success');
  expect(result.export_id).toBeTruthy();
  return result;
}

/**
 * Helper: build a minimal valid sections payload for the submit endpoint.
 * The SubmitRequest model expects Section[] with { id, title, content, items, is_critical, order }.
 * When microservice isn't running, edited_content has no sections — we construct one.
 */
function buildMinimalSections() {
  return [
    {
      id: 'section-test-1',
      title: 'Test Section',
      content: 'E2E test section',
      items: [
        {
          id: 'item-test-1',
          content: 'E2E test item for lifecycle verification',
          priority: 'normal',
        },
      ],
      is_critical: false,
      order: 0,
    },
  ];
}

test.describe('Handover Export E2E', () => {

  // ─────────────────────────────────────────────────────────────────────────
  // TEST 1: Captain exports handover — HARD PROOF
  // ─────────────────────────────────────────────────────────────────────────
  test('Captain exports handover — HARD PROOF', async ({ captainPage, supabaseAdmin }) => {
    console.log('[Test 1] Authenticating as captain...');
    const session = await captainSession(supabaseAdmin);

    console.log('[Test 1] POST /v1/handover/export — creating export...');
    const response = await captainPage.request.post(`${API_URL}/v1/handover/export`, {
      headers: authHeaders(session.access_token),
      data: { export_type: 'html', filter_by_user: false },
    });

    // --- Response assertions ---
    expect(response.status()).toBe(200);
    const result = await response.json();
    console.log('[Test 1] Response:', JSON.stringify({
      status: result.status,
      export_id: result.export_id,
      sections_count: result.sections_count,
      total_items: result.total_items,
    }));

    expect(result.status).toBe('success');
    expect(result.export_id).toBeTruthy();
    expect(result.sections_count).toBeGreaterThan(0);

    // --- DB: handover_exports row (TENANT DB) ---
    console.log('[Test 1] DB verification: handover_exports...');
    const db = tenantAdmin();
    const { data: exportRecord, error: dbError } = await db
      .from('handover_exports')
      .select('id, export_status, review_status, edited_content, document_hash, yacht_id')
      .eq('id', result.export_id)
      .single();

    expect(dbError).toBeNull();
    expect(exportRecord).toBeTruthy();
    expect(exportRecord.export_status).toBe('completed');
    expect(exportRecord.review_status).toBe('pending_review');
    expect(exportRecord.edited_content).toBeTruthy();
    // Local export stores { item_ids: [...] }; microservice stores { sections: [...] }
    // Either way, edited_content must be a non-empty object
    console.log('[Test 1] edited_content keys:', Object.keys(exportRecord.edited_content));

    // --- DB: ledger_events row ---
    console.log('[Test 1] DB verification: ledger_events...');
    const { data: ledgerEvents } = await db
      .from('ledger_events')
      .select('id, action, entity_type, entity_id')
      .eq('entity_id', result.export_id)
      .limit(5);

    expect(ledgerEvents).toBeTruthy();
    expect(ledgerEvents!.length).toBeGreaterThan(0);
    console.log(`[Test 1] Found ${ledgerEvents!.length} ledger event(s) for export ${result.export_id}`);
    console.log('[Test 1] PASSED');
  });

  // ─────────────────────────────────────────────────────────────────────────
  // TEST 2: Entity endpoint returns export metadata
  // ─────────────────────────────────────────────────────────────────────────
  test('Entity endpoint returns export metadata + review_status', async ({ captainPage, supabaseAdmin }) => {
    console.log('[Test 2] Authenticating as captain...');
    const session = await captainSession(supabaseAdmin);

    console.log('[Test 2] Creating export for entity endpoint test...');
    const exportResult = await createExport(captainPage.request, session.access_token);
    const exportId = exportResult.export_id;

    console.log(`[Test 2] GET /v1/entity/handover_export/${exportId}...`);
    const entityResponse = await captainPage.request.get(
      `${API_URL}/v1/entity/handover_export/${exportId}`,
      { headers: authHeaders(session.access_token) },
    );

    expect(entityResponse.status()).toBe(200);
    const entity = await entityResponse.json();
    console.log('[Test 2] Entity response keys:', Object.keys(entity));

    // --- Core metadata ---
    expect(entity.id).toBe(exportId);
    expect(entity.review_status).toBe('pending_review');
    expect(entity.export_status).toBe('completed');

    // --- sections is always an array (may be empty if microservice off) ---
    expect(Array.isArray(entity.sections)).toBe(true);
    console.log(`[Test 2] Sections: ${entity.sections.length} (may be 0 if microservice off)`);

    // --- Signature fields exist (null initially) ---
    expect('user_signature' in entity || 'userSignature' in entity).toBe(true);
    expect('hod_signature' in entity).toBe(true);

    // --- available_actions present ---
    expect(entity.available_actions).toBeTruthy();

    console.log('[Test 2] PASSED');
  });

  // ─────────────────────────────────────────────────────────────────────────
  // TEST 3: Full lifecycle: export -> submit -> countersign -> complete
  // ─────────────────────────────────────────────────────────────────────────
  test('Full lifecycle: export → submit → countersign → complete — HARD PROOF', async ({
    captainPage,
    supabaseAdmin,
  }) => {
    console.log('[Test 3] Authenticating as captain...');
    const session = await captainSession(supabaseAdmin);
    const headers = authHeaders(session.access_token);
    const db = tenantAdmin();

    // ── Step A: Create export ──────────────────────────────────────────────
    console.log('[Test 3] Step A: Creating export...');
    const exportResult = await createExport(captainPage.request, session.access_token);
    const exportId = exportResult.export_id;
    console.log(`[Test 3] Step A: export_id = ${exportId}, sections_count = ${exportResult.sections_count}`);

    // DB verify: pending_review
    const { data: afterCreate } = await db
      .from('handover_exports')
      .select('review_status')
      .eq('id', exportId)
      .single();
    expect(afterCreate!.review_status).toBe('pending_review');

    // ── Step B: Submit with user signature ─────────────────────────────────
    // Use minimal sections — local export path doesn't populate edited_content.sections
    const submitSections = buildMinimalSections();
    console.log('[Test 3] Step B: POST submit with user signature...');
    const submitResponse = await captainPage.request.post(
      `${API_URL}/v1/handover/export/${exportId}/submit`,
      {
        headers,
        data: {
          sections: submitSections,
          userSignature: {
            image_base64: FAKE_SIGNATURE_BASE64,
            signed_at: new Date().toISOString(),
            signer_name: 'Captain Test',
            signer_id: session.user.id,
          },
        },
      },
    );

    const submitResult = await submitResponse.json();
    console.log('[Test 3] Step B: submit response:', submitResponse.status(), JSON.stringify(submitResult));
    expect(submitResponse.status()).toBe(200);
    expect(submitResult.success).toBe(true);
    expect(submitResult.review_status).toBe('pending_hod_signature');

    // DB verify: review_status changed, user_signature + user_signed_at populated
    const { data: afterSubmit } = await db
      .from('handover_exports')
      .select('review_status, user_signature, user_signed_at')
      .eq('id', exportId)
      .single();
    expect(afterSubmit!.review_status).toBe('pending_hod_signature');
    expect(afterSubmit!.user_signature).toBeTruthy();
    expect(afterSubmit!.user_signed_at).toBeTruthy();
    console.log('[Test 3] Step B: DB confirmed pending_hod_signature');

    // ── Step C: Countersign (captain can countersign — role is in allowed list) ──
    console.log('[Test 3] Step C: POST countersign...');
    const countersignResponse = await captainPage.request.post(
      `${API_URL}/v1/handover/export/${exportId}/countersign`,
      {
        headers,
        data: {
          hodSignature: {
            image_base64: FAKE_SIGNATURE_BASE64,
            signed_at: new Date().toISOString(),
            signer_name: 'Captain Test (HOD)',
            signer_id: session.user.id,
          },
        },
      },
    );

    const countersignResult = await countersignResponse.json();
    console.log('[Test 3] Step C: countersign response:', countersignResponse.status(), JSON.stringify(countersignResult));
    expect(countersignResponse.status()).toBe(200);
    expect(countersignResult.success).toBe(true);
    expect(countersignResult.review_status).toBe('complete');

    // DB verify: review_status = complete, hod_signature + hod_signed_at populated
    const { data: afterCountersign } = await db
      .from('handover_exports')
      .select('review_status, hod_signature, hod_signed_at')
      .eq('id', exportId)
      .single();
    expect(afterCountersign!.review_status).toBe('complete');
    expect(afterCountersign!.hod_signature).toBeTruthy();
    expect(afterCountersign!.hod_signed_at).toBeTruthy();
    console.log('[Test 3] Step C: DB confirmed complete');

    // ── Step D: Ledger cascade verification ────────────────────────────────
    console.log('[Test 3] Step D: Verifying ledger cascade...');
    const { data: ledgerEvents } = await db
      .from('ledger_events')
      .select('id, action, entity_type, entity_id, created_at')
      .eq('entity_id', exportId)
      .eq('action', 'handover_countersigned')
      .limit(10);

    console.log(`[Test 3] Step D: Found ${ledgerEvents?.length ?? 0} 'handover_countersigned' ledger event(s)`);
    expect(ledgerEvents).toBeTruthy();
    expect(ledgerEvents!.length).toBeGreaterThan(0);

    console.log('[Test 3] PASSED — full lifecycle verified end-to-end');
  });

  // ─────────────────────────────────────────────────────────────────────────
  // TEST 4: Countersign on wrong state -> 400
  // ─────────────────────────────────────────────────────────────────────────
  test('Countersign on wrong state → 400', async ({ captainPage, supabaseAdmin }) => {
    console.log('[Test 4] Authenticating as captain...');
    const session = await captainSession(supabaseAdmin);
    const headers = authHeaders(session.access_token);
    const db = tenantAdmin();

    // Create a fresh export — it starts at pending_review, NOT pending_hod_signature
    console.log('[Test 4] Creating export (will be in pending_review state)...');
    const exportResult = await createExport(captainPage.request, session.access_token);
    const exportId = exportResult.export_id;

    // DB sanity check: confirm it is pending_review
    const { data: beforeAttempt } = await db
      .from('handover_exports')
      .select('review_status')
      .eq('id', exportId)
      .single();
    expect(beforeAttempt!.review_status).toBe('pending_review');
    console.log(`[Test 4] Export ${exportId} is in state: ${beforeAttempt!.review_status}`);

    // Attempt countersign WITHOUT submit first — should be rejected
    console.log('[Test 4] Attempting countersign on pending_review export (expect 400)...');
    const countersignResponse = await captainPage.request.post(
      `${API_URL}/v1/handover/export/${exportId}/countersign`,
      {
        headers,
        data: {
          hodSignature: {
            image_base64: FAKE_SIGNATURE_BASE64,
            signed_at: new Date().toISOString(),
            signer_name: 'Captain Test',
            signer_id: session.user.id,
          },
        },
      },
    );

    const errorBody = await countersignResponse.json().catch(() => ({}));
    console.log('[Test 4] Countersign response:', countersignResponse.status(), JSON.stringify(errorBody));

    expect(countersignResponse.status()).toBe(400);

    // DB verify: review_status did NOT change
    const { data: afterAttempt } = await db
      .from('handover_exports')
      .select('review_status')
      .eq('id', exportId)
      .single();
    expect(afterAttempt!.review_status).toBe('pending_review');
    console.log('[Test 4] DB confirmed review_status unchanged (still pending_review)');

    console.log('[Test 4] PASSED — wrong-state countersign correctly rejected');
  });

});
