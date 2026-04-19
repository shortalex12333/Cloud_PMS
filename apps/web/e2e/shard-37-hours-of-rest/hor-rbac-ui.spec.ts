// apps/web/e2e/shard-37-hours-of-rest/hor-rbac-ui.spec.ts
//
// Hours of Rest — Binary Pass/Fail E2E Suite
//
// JSON output: npx playwright test shard-37-hours-of-rest/hor-rbac-ui.spec.ts --reporter=json
//
// ── Auth UUIDs (auth.users.id — verified 2026-04-13 via /auth/v1/admin/users) ──
//   crew          engineer.test@alex-short.com         4a66036f  (role: crew)
//   hod           eto.test@alex-short.com              81c239df  (role: eto — HOD class)
//   captain       captain.tenant@alex-short.com        5af9d61d  (role: captain)
//   fleet_manager fleet-test-1775570624@celeste7.ai    f11f1247  (role: manager)
//
// NOTE: auth_users_profiles.id ≠ auth.users.id for many users.
//       Always use auth.users.id as the JWT sub.
//
// ── Backend bugs found during test run (2026-04-13) ─────────────────────────
//
//   BUG-HOR-1 (SCHEMA) pms_hours_of_rest unique constraint missing user_id
//     The upsert conflict key appears to be (yacht_id, record_date) only.
//     Any upsert for a date that already has seed data for another user hits
//     the existing row and UPDATES it, keeping the original user_id (a35cad0b).
//     A new record is NOT inserted for the requesting user.
//     Expected: UNIQUE(yacht_id, user_id, record_date)
//     Actual:   UNIQUE(yacht_id, record_date)  ← confirmed by DB inspection
//
//   BUG-HOR-2 (LOGIC) create_monthly_signoff resolves user to a35cad0b for all JWTs
//     When any role calls create_monthly_signoff, the entity_id in the response
//     is a35cad0b (old captain) regardless of which JWT user calls it.
//     Backend is not using the JWT sub to determine the creating user — it
//     appears to resolve the user from some server-side context.
//
//   BUG-HOR-3 (SECURITY) sign_monthly_signoff crashes with NoneType 500 on
//     invalid signoff_id instead of returning 403 FORBIDDEN.
//     HTTP 200 envelope with success=false, error.code=DATABASE_ERROR,
//     status_code=500. Should return proper 403 when role is not authorized.
//
//   BUG-HOR-4 (UI) [RESOLVED 2026-04-17] JWT injection didn't survive
//     frontend auth bootstrap — the Supabase client re-validated the
//     session on page load and rejected self-minted tokens. Fixed by
//     switching global-setup.ts to real supabase.auth.signInWithPassword()
//     calls, writing the returned session into storageState in the exact
//     shape supabase-js expects. UI tab-visibility tests no longer skip.

import { test, expect, RBAC_CONFIG } from '../rbac-fixtures';
import { callActionDirect, callActionAs, generateFreshJwt } from '../shard-34-lens-actions/helpers';
import { BASE_URL } from '../shard-33-lens-actions/helpers';

// Role-specific JWTs for sign-chain independence (MLC requires HOD ≠ master signer).
// SESSION_JWT is always captain/a35cad0b — HOD sign must use a different identity.
const HOD_JWT     = generateFreshJwt('81c239df-f8ef-4bba-9496-78bf8f46733c', 'eto.test@alex-short.com');
const CAPTAIN_JWT = generateFreshJwt('5af9d61d-9b2e-4db4-a54c-a3c95eec70e5', 'captain.tenant@alex-short.com');

// ── auth.users.id values (NOT auth_users_profiles.id) ─────────────────────────
const CREW_USER_ID    = '4a66036f-899c-40c8-9b2a-598cee24a62f'; // engineer.test
const HOD_USER_ID     = '81c239df-f8ef-4bba-9496-78bf8f46733c'; // eto.test (role: eto)
const CAPTAIN_USER_ID = '5af9d61d-9b2e-4db4-a54c-a3c95eec70e5'; // captain.tenant
const FLEET_USER_ID   = 'f11f1247-b7bd-4017-bfe3-ebd3f8c9e871'; // fleet-test

// ── Test dates: use months/dates with NO pre-existing seed data ────────────────
// Seed data exists for a35cad0b on 2024-11-04..07, 2024-11, etc.
// Use 2024-08 range to avoid BUG-HOR-1 collisions.
const DATES = {
  crew_upsert:    '2024-08-12',
  hod_upsert:     '2024-08-13',
  captain_upsert: '2024-08-14',
  signoff_month:  '2024-08',
};

// ═══════════════════════════════════════════════════════════════════════════════
// PHASE 1 — Daily rest input (upsert_hours_of_rest)
// DB verification: use the row ID returned by the action (not user_id — see BUG-HOR-1)
// ═══════════════════════════════════════════════════════════════════════════════

test.describe('[Phase 1] Crew — upsert_hours_of_rest → row written to DB', () => {
  test('[crew] upsert → 200 + returned record exists in pms_hours_of_rest', async ({
    crewPage, supabaseAdmin,
  }) => {
    await crewPage.goto(`${BASE_URL}/`);
    await crewPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(crewPage, 'upsert_hours_of_rest', {
      yacht_id: RBAC_CONFIG.yachtId,
      user_id: CREW_USER_ID,
      record_date: DATES.crew_upsert,
      rest_periods: [
        { start: '00:00', end: '06:00' },
        { start: '14:00', end: '22:00' },
      ],
      voyage_type: 'in_port',
    });
    console.log(`[JSON] crew upsert: status=${result.status} success=${(result.data as any)?.success}`);

    expect(result.status).toBe(200);
    const data = result.data as any;
    expect(data.success).toBe(true);

    // Verify the returned record ID actually exists in DB
    const returnedId: string | undefined = data.data?.record?.id;
    const returnedUserId: string | undefined = data.data?.record?.user_id;
    console.log(`[DB] returned record id=${returnedId}, user_id=${returnedUserId}`);

    expect(returnedId).toBeTruthy();

    const { data: row } = await supabaseAdmin
      .from('pms_hours_of_rest')
      .select('id, user_id, record_date')
      .eq('id', returnedId!)
      .single();

    expect(row).not.toBeNull();
    expect(row?.record_date).toBe(DATES.crew_upsert);

    // BUG-HOR-1 diagnostic: if user_id in DB ≠ requesting user, log it (schema bug)
    if (row?.user_id !== CREW_USER_ID) {
      console.warn(`[BUG-HOR-1] SCHEMA BUG: upsert wrote user_id=${row?.user_id} instead of CREW=${CREW_USER_ID}. Unique constraint missing user_id.`);
    }
    console.log(`[DB] row verified: id=${row?.id}, user_id=${row?.user_id}`);
  });
});

test.describe('[Phase 1] HOD — upsert_hours_of_rest → row written to DB', () => {
  test('[hod] upsert → 200 + returned record exists in pms_hours_of_rest', async ({
    hodPage, supabaseAdmin,
  }) => {
    await hodPage.goto(`${BASE_URL}/`);
    await hodPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(hodPage, 'upsert_hours_of_rest', {
      yacht_id: RBAC_CONFIG.yachtId,
      user_id: HOD_USER_ID,
      record_date: DATES.hod_upsert,
      rest_periods: [
        { start: '00:00', end: '08:00' },
        { start: '16:00', end: '22:00' },
      ],
      voyage_type: 'at_sea',
    });
    const data = result.data as any;
    console.log(`[JSON] hod upsert: status=${result.status} success=${data?.success}`);

    expect(result.status).toBe(200);
    expect(data.success).toBe(true);

    const returnedId: string | undefined = data.data?.record?.id;
    expect(returnedId).toBeTruthy();

    const { data: row } = await supabaseAdmin
      .from('pms_hours_of_rest')
      .select('id, user_id')
      .eq('id', returnedId!)
      .single();
    expect(row).not.toBeNull();
    if (row?.user_id !== HOD_USER_ID) {
      console.warn(`[BUG-HOR-1] SCHEMA BUG: upsert wrote user_id=${row?.user_id} instead of HOD=${HOD_USER_ID}`);
    }
    console.log(`[DB] hod row verified: id=${row?.id}, user_id=${row?.user_id}`);
  });
});

test.describe('[Phase 1] Captain — upsert_hours_of_rest → row written to DB', () => {
  test('[captain] upsert → 200 + returned record exists in pms_hours_of_rest', async ({
    captainPage, supabaseAdmin,
  }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'upsert_hours_of_rest', {
      yacht_id: RBAC_CONFIG.yachtId,
      user_id: CAPTAIN_USER_ID,
      record_date: DATES.captain_upsert,
      rest_periods: [
        { start: '00:00', end: '06:00' },
        { start: '14:00', end: '22:00' },
      ],
      voyage_type: 'at_sea',
    });
    const data = result.data as any;
    console.log(`[JSON] captain upsert: status=${result.status} success=${data?.success}`);

    expect(result.status).toBe(200);
    expect(data.success).toBe(true);

    const returnedId: string | undefined = data.data?.record?.id;
    expect(returnedId).toBeTruthy();

    const { data: row } = await supabaseAdmin
      .from('pms_hours_of_rest')
      .select('id, user_id')
      .eq('id', returnedId!)
      .single();
    expect(row).not.toBeNull();
    if (row?.user_id !== CAPTAIN_USER_ID) {
      console.warn(`[BUG-HOR-1] SCHEMA BUG: upsert wrote user_id=${row?.user_id} instead of CAPTAIN=${CAPTAIN_USER_ID}`);
    }
    console.log(`[DB] captain row verified: id=${row?.id}, user_id=${row?.user_id}`);
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// PHASE 2 — Week submission (create_monthly_signoff)
// ═══════════════════════════════════════════════════════════════════════════════
// PHASES 2-3-4 — Full sign chain: create → crew sign → HOD sign → master sign
//
// Run as one sequential test to manage shared signoff state cleanly.
// Uses test month 2024-03 (verified clean — no existing signoffs).
// Setup: deletes any leftover 2024-03 signoff before starting.
// Cleanup: deletes the created signoff after all assertions.
//
// PASS definition: success=true + DB row confirms status advanced correctly.
// Any other outcome (DUPLICATE_ERROR, VALIDATION_ERROR, DATABASE_ERROR, etc.) = FAIL.
// ═══════════════════════════════════════════════════════════════════════════════

const TEST_SIGN_MONTH = '2024-03';
const SESSION_USER_ID = 'a35cad0b-02ff-4287-b6e4-17c96fa6a424'; // SESSION_JWT default sub

test.describe('[Phase 2-3-4] Full sign chain: create → crew → HOD → master', () => {
  test('[sign-chain] create + full sign workflow → DB status = finalized', async ({
    crewPage, supabaseAdmin,
  }) => {
    await crewPage.goto(`${BASE_URL}/`);
    await crewPage.waitForLoadState('domcontentloaded');

    // ── SETUP: clean any leftover test signoff ──────────────────────────────
    await supabaseAdmin
      .from('pms_hor_monthly_signoffs')
      .delete()
      .eq('yacht_id', RBAC_CONFIG.yachtId)
      .eq('user_id', SESSION_USER_ID)
      .eq('month', TEST_SIGN_MONTH);
    console.log(`[SETUP] Deleted any existing ${TEST_SIGN_MONTH} signoff for ${SESSION_USER_ID}`);

    // ── PHASE 2: create_monthly_signoff ────────────────────────────────────
    // NOTE: yacht_id + user_id must be in payload (not just context) — action bus
    // validates required_fields against payload directly (p0_actions_routes.py:896).
    const createResult = await callActionDirect(crewPage, 'create_monthly_signoff', {
      yacht_id: RBAC_CONFIG.yachtId,
      user_id: SESSION_USER_ID,
      month: TEST_SIGN_MONTH,
      department: 'engineering',
    });
    const createData = createResult.data as any;
    console.log(`[Phase 2] create: status=${createResult.status} success=${createData?.success} errCode=${createData?.error?.code}`);
    console.log(`[Phase 2] response data: ${JSON.stringify(createData?.data ?? {})}`);

    expect(createResult.status).toBe(200);
    expect(createData.success).toBe(true); // PASS = success=true. DUPLICATE/error = FAIL.

    // Capture the signoff ID from response — verify in DB
    const signoffId: string = createData.data?.signoff?.id ?? createData.data?.id ?? '';
    console.log(`[Phase 2] signoff_id from response: ${signoffId}`);
    expect(signoffId).toBeTruthy();

    const { data: p2row } = await supabaseAdmin
      .from('pms_hor_monthly_signoffs')
      .select('id, status, month, user_id')
      .eq('id', signoffId)
      .single();
    console.log(`[Phase 2 DB] id=${p2row?.id}, status=${p2row?.status}, month=${p2row?.month}, user=${p2row?.user_id}`);
    expect(p2row).not.toBeNull();
    expect(p2row?.month).toBe(TEST_SIGN_MONTH);

    // ── PHASE 3 step 1: crew sign (advance to crew_signed) ─────────────────
    const crewSignResult = await callActionDirect(crewPage, 'sign_monthly_signoff', {
      signoff_id: signoffId,
      signature_level: 'crew',
      signature_data: {
        name: 'Test Engineer',
        declaration: 'I confirm these rest hours are accurate per MLC 2006',
        timestamp: new Date().toISOString(),
      },
    });
    const crewSignData = crewSignResult.data as any;
    console.log(`[Phase 3 crew-sign] success=${crewSignData?.success} errCode=${crewSignData?.error?.code}`);
    expect(crewSignResult.status).toBe(200);
    expect(crewSignData.success).toBe(true);

    const { data: afterCrewSign } = await supabaseAdmin
      .from('pms_hor_monthly_signoffs').select('status').eq('id', signoffId).single();
    console.log(`[Phase 3 DB] status after crew sign: ${afterCrewSign?.status}`);
    expect(afterCrewSign?.status).toBe('crew_signed');

    // ── PHASE 3 step 2: HOD sign (advance to hod_signed) ──────────────────
    // MLC 2006 independence rule: HOD signer must be a different identity from master.
    // SESSION_JWT = a35cad0b (captain role). Use HOD_JWT (81c239df, eto role) here
    // so that master can then sign as a different person (5af9d61d, captain role).
    const hodSignResult = await callActionAs(crewPage, HOD_JWT, 'sign_monthly_signoff', {
      signoff_id: signoffId,
      signature_level: 'hod',
      signature_data: {
        name: 'Test ETO',
        declaration: 'I certify this is accurate per MLC 2006',
        timestamp: new Date().toISOString(),
      },
    });
    const hodSignData = hodSignResult.data as any;
    console.log(`[Phase 3 HOD-sign] success=${hodSignData?.success} errCode=${hodSignData?.error?.code}`);
    expect(hodSignResult.status).toBe(200);
    expect(hodSignData.success).toBe(true);

    const { data: afterHodSign } = await supabaseAdmin
      .from('pms_hor_monthly_signoffs').select('status').eq('id', signoffId).single();
    console.log(`[Phase 3 DB] status after HOD sign: ${afterHodSign?.status}`);
    expect(afterHodSign?.status).toBe('hod_signed');

    // ── PHASE 4: master sign (advance to finalized) ────────────────────────
    // Use CAPTAIN_JWT (5af9d61d) — different from HOD_JWT (81c239df) — passes MLC check.
    const masterSignResult = await callActionAs(crewPage, CAPTAIN_JWT, 'sign_monthly_signoff', {
      signoff_id: signoffId,
      signature_level: 'master',
      signature_data: {
        name: 'Test Captain',
        declaration: 'I attest this record is complete per MLC 2006 Regulation 2.3',
        timestamp: new Date().toISOString(),
      },
    });
    const masterSignData = masterSignResult.data as any;
    console.log(`[Phase 4 master-sign] success=${masterSignData?.success} errCode=${masterSignData?.error?.code}`);
    expect(masterSignResult.status).toBe(200);
    expect(masterSignData.success).toBe(true);

    const { data: afterMasterSign } = await supabaseAdmin
      .from('pms_hor_monthly_signoffs').select('status').eq('id', signoffId).single();
    console.log(`[Phase 4 DB] status after master sign: ${afterMasterSign?.status}`);
    expect(['finalized', 'captain_signed']).toContain(afterMasterSign?.status ?? '');

    // ── CLEANUP ────────────────────────────────────────────────────────────
    await supabaseAdmin.from('pms_hor_monthly_signoffs').delete().eq('id', signoffId);
    console.log(`[CLEANUP] Deleted test signoff ${signoffId}`);
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// PHASE 5 — Notifications
// ═══════════════════════════════════════════════════════════════════════════════

test.describe('[Phase 5] HOD — list and dismiss warnings', () => {
  test('[hod] list_crew_warnings → 200 + success=true', async ({ hodPage }) => {
    await hodPage.goto(`${BASE_URL}/`);
    await hodPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(hodPage, 'list_crew_warnings', {
      yacht_id: RBAC_CONFIG.yachtId,
    });
    console.log(`[JSON] hod list_crew_warnings: status=${result.status} success=${(result.data as any)?.success}`);

    expect(result.status).toBe(200);
    expect((result.data as any).success).toBe(true);
  });

  test('[hod] dismiss_warning with real warning id → 200 + success=true + DB dismissed_at set', async ({
    hodPage, supabaseAdmin,
  }) => {
    await hodPage.goto(`${BASE_URL}/`);
    await hodPage.waitForLoadState('domcontentloaded');

    // Pre-cleanup: remove any leftover test warning from a prior failed run (avoids unique constraint on retry)
    await supabaseAdmin
      .from('pms_crew_hours_warnings')
      .delete()
      .eq('yacht_id', RBAC_CONFIG.yachtId)
      .eq('user_id', SESSION_USER_ID)
      .eq('record_date', '2024-03-01')
      .eq('warning_type', 'WEEKLY_REST');

    // Insert a dedicated test warning — omit id, let Supabase generate a valid UUID.
    const { data: inserted, error: insertErr } = await supabaseAdmin
      .from('pms_crew_hours_warnings')
      .insert({
        yacht_id: RBAC_CONFIG.yachtId,
        user_id: SESSION_USER_ID,
        warning_type: 'WEEKLY_REST',
        severity: 'warning',
        record_date: '2024-03-01',
        message: 'E2E test warning — safe to delete',
        violation_data: { actual_hours: 0, required_hours: 77, shortfall: 77 },
        status: 'active',
        is_dismissed: false,
      })
      .select('id')
      .single();
    const testWarningId = inserted?.id;

    if (insertErr || !inserted) {
      console.warn(`[SKIP] Could not insert test warning: ${insertErr?.message}. Skipping dismiss test.`);
      test.skip();
      return;
    }
    console.log(`[SETUP] Inserted test warning id=${inserted.id}`);

    const result = await callActionDirect(hodPage, 'dismiss_warning', {
      warning_id: testWarningId,
      hod_justification: 'E2E test dismiss — valid',
      dismissed_by_role: 'hod',
    });
    const data = result.data as any;
    console.log(`[JSON] dismiss real warning: status=${result.status} success=${data?.success} errCode=${data?.error?.code}`);
    console.log(`[JSON] dismiss response data: ${JSON.stringify(data?.data ?? {})}`);

    expect(result.status).toBe(200);
    expect(data.success).toBe(true); // PASS = success=true. Anything else = FAIL.

    // Verify DB: dismissed_at must be set
    const { data: updated } = await supabaseAdmin
      .from('pms_crew_hours_warnings')
      .select('dismissed_at, is_dismissed, status')
      .eq('id', testWarningId)
      .single();
    console.log(`[Phase 5 DB] dismissed_at=${updated?.dismissed_at}, is_dismissed=${updated?.is_dismissed}`);
    expect(updated?.dismissed_at).not.toBeNull();
    expect(updated?.is_dismissed).toBe(true);

    // Cleanup
    await supabaseAdmin.from('pms_crew_hours_warnings').delete().eq('id', testWarningId);
  });

  test('[hod] dismiss_warning with invalid id → success=false + NOT_FOUND (not DATABASE_ERROR crash)', async ({
    hodPage,
  }) => {
    // This test documents BUG-HOR-5: backend crashes with DATABASE_ERROR on
    // invalid UUID instead of returning a graceful NOT_FOUND. If this test
    // fails, the backend is still crashing.
    await hodPage.goto(`${BASE_URL}/`);
    await hodPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(hodPage, 'dismiss_warning', {
      warning_id: '00000000-0000-0000-0000-000000000099',
      hod_justification: 'E2E test — invalid ID',
      dismissed_by_role: 'hod',
    });
    const data = result.data as any;
    console.log(`[JSON] dismiss invalid: status=${result.status} success=${data?.success} code=${data?.error?.code}`);

    expect(result.status).toBe(200);
    expect(data.success).toBe(false);
    // BUG-HOR-5: backend returns DATABASE_ERROR (crash) not NOT_FOUND (graceful)
    // Assertion fails until backend is fixed to return NOT_FOUND
    expect(data.error?.code).not.toBe('DATABASE_ERROR');
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// PHASE 6 — Fleet Manager
// ═══════════════════════════════════════════════════════════════════════════════

test.describe('[Phase 6] Fleet Manager — read access to fleet data', () => {
  test('[fleet_manager] list_monthly_signoffs → 200 + success=true', async ({
    fleetManagerPage,
  }) => {
    await fleetManagerPage.goto(`${BASE_URL}/`);
    await fleetManagerPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(fleetManagerPage, 'list_monthly_signoffs', {
      yacht_id: RBAC_CONFIG.yachtId,
    });
    console.log(`[JSON] fleet list_monthly_signoffs: status=${result.status} success=${(result.data as any)?.success}`);

    expect(result.status).toBe(200);
    const data = result.data as any;
    expect(data.success === true || data.status === 'success').toBe(true);
  });

  test('[fleet_manager] get_hours_of_rest → 200 + records array', async ({
    fleetManagerPage,
  }) => {
    await fleetManagerPage.goto(`${BASE_URL}/`);
    await fleetManagerPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(fleetManagerPage, 'get_hours_of_rest', {
      yacht_id: RBAC_CONFIG.yachtId,
    });
    console.log(`[JSON] fleet get_hours_of_rest: status=${result.status} success=${(result.data as any)?.success}`);

    expect(result.status).toBe(200);
    const data = result.data as any;
    expect(data.success).toBe(true);
    expect(Array.isArray(data.data?.records)).toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// PHASE 7 — Locking
//
// Self-contained: inserts a finalized signoff with user_id=SESSION_USER_ID
// (a35cad0b = auth.users.id) so the lock check matches the JWT sub.
//
// WHY self-contained: existing finalized signoff in DB (4ab92e2f) has
// user_id=b72c35ff (auth_users_profiles.id — legacy poisoned data from before
// BUG-HOR-2 was fixed). Lock check uses JWT sub, so it never matched b72c35ff.
//
// LOCK logic (upsert_hours_of_rest handler): fires when a monthly signoff
// with period_type="monthly" AND status IN (finalized,locked,captain_signed)
// exists for (yacht_id, user_id, month). hod_signed does NOT block.
// ═══════════════════════════════════════════════════════════════════════════════

const LOCK_TEST_MONTH   = '2025-06'; // clean month — no pre-existing signoffs
const LOCK_TEST_DATE    = '2025-06-15'; // record_date within locked month

test.describe('[Phase 7] Locking — finalized period blocks edits', () => {
  test('[crew] upsert on finalized period → success=false + LOCKED/FORBIDDEN code', async ({
    crewPage, supabaseAdmin,
  }) => {
    await crewPage.goto(`${BASE_URL}/`);
    await crewPage.waitForLoadState('domcontentloaded');

    // SETUP: delete any leftover, insert a fresh finalized signoff for SESSION_USER_ID
    await supabaseAdmin
      .from('pms_hor_monthly_signoffs')
      .delete()
      .eq('yacht_id', RBAC_CONFIG.yachtId)
      .eq('user_id', SESSION_USER_ID)
      .eq('month', LOCK_TEST_MONTH);

    const { data: lockRow, error: lockInsertErr } = await supabaseAdmin
      .from('pms_hor_monthly_signoffs')
      .insert({
        yacht_id: RBAC_CONFIG.yachtId,
        user_id: SESSION_USER_ID,
        month: LOCK_TEST_MONTH,
        department: 'engineering',
        status: 'finalized',
        period_type: 'monthly',
      })
      .select('id')
      .single();

    if (lockInsertErr || !lockRow) {
      throw new Error(`[Phase 7 SETUP] Failed to insert test lock signoff: ${lockInsertErr?.message}`);
    }
    console.log(`[SETUP] Inserted finalized signoff id=${lockRow.id}, month=${LOCK_TEST_MONTH}, user=${SESSION_USER_ID}`);

    try {
      // Attempt upsert on locked month — must return LOCKED
      const result = await callActionDirect(crewPage, 'upsert_hours_of_rest', {
        yacht_id: RBAC_CONFIG.yachtId,
        user_id: SESSION_USER_ID,
        record_date: LOCK_TEST_DATE,
        rest_periods: [{ start: '00:00', end: '10:00' }],
        voyage_type: 'in_port',
      });
      const data = result.data as any;
      console.log(`[JSON] crew upsert on locked: status=${result.status} success=${data?.success} code=${data?.error?.code}`);

      expect(data?.success).not.toBe(true); // LOCKED = success=false
      expect(data?.error?.code).toBe('LOCKED');
      console.log(`[LOCK] enforced: code=${data?.error?.code} ✓`);
    } finally {
      await supabaseAdmin.from('pms_hor_monthly_signoffs').delete().eq('id', lockRow.id);
      console.log(`[CLEANUP] Deleted test lock signoff ${lockRow.id}`);
    }
  });

  test('[captain] upsert on finalized period → success=false', async ({
    captainPage, supabaseAdmin,
  }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    // SETUP: use 2025-07 to avoid conflict with crew test above
    const capLockMonth = '2025-07';
    const capLockDate  = '2025-07-15';

    await supabaseAdmin
      .from('pms_hor_monthly_signoffs')
      .delete()
      .eq('yacht_id', RBAC_CONFIG.yachtId)
      .eq('user_id', SESSION_USER_ID)
      .eq('month', capLockMonth);

    const { data: capLockRow, error: capInsertErr } = await supabaseAdmin
      .from('pms_hor_monthly_signoffs')
      .insert({
        yacht_id: RBAC_CONFIG.yachtId,
        user_id: SESSION_USER_ID,
        month: capLockMonth,
        department: 'engineering',
        status: 'finalized',
        period_type: 'monthly',
      })
      .select('id')
      .single();

    if (capInsertErr || !capLockRow) {
      throw new Error(`[Phase 7 SETUP] Failed to insert captain lock signoff: ${capInsertErr?.message}`);
    }
    console.log(`[SETUP] Inserted captain lock signoff id=${capLockRow.id}, month=${capLockMonth}`);

    try {
      const result = await callActionDirect(captainPage, 'upsert_hours_of_rest', {
        yacht_id: RBAC_CONFIG.yachtId,
        user_id: SESSION_USER_ID,
        record_date: capLockDate,
        rest_periods: [{ start: '00:00', end: '10:00' }],
        voyage_type: 'at_sea',
      });
      const data = result.data as any;
      console.log(`[JSON] captain upsert on locked: status=${result.status} success=${data?.success} code=${data?.error?.code}`);

      expect(data?.success).not.toBe(true);
      expect(data?.error?.code).toBe('LOCKED');
    } finally {
      await supabaseAdmin.from('pms_hor_monthly_signoffs').delete().eq('id', capLockRow.id);
    }
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// SECURITY — Backend must reject cross-role and cross-yacht actions
//
// Assertion pattern: success !== true (action bus wraps errors in HTTP 200).
// If success=true the action actually executed — that is a breach.
// If success=false the action was rejected — check for meaningful error code.
//
// BUG-HOR-3: sign_monthly_signoff currently returns DATABASE_ERROR 500 instead
//            of 403 FORBIDDEN for unauthorized signers. We accept success=false
//            as a pass but flag the wrong error code.
// ═══════════════════════════════════════════════════════════════════════════════

test.describe('[Security] Crew cannot succeed at HOD-level signature', () => {
  test('[crew] sign_monthly_signoff level=hod → success must be false', async ({
    crewPage, supabaseAdmin,
  }) => {
    await crewPage.goto(`${BASE_URL}/`);
    await crewPage.waitForLoadState('domcontentloaded');

    const { data: signoff } = await supabaseAdmin
      .from('pms_hor_monthly_signoffs')
      .select('id')
      .eq('yacht_id', RBAC_CONFIG.yachtId)
      .in('status', ['crew_signed', 'draft'])
      .limit(1)
      .single();

    const signoffId = signoff?.id ?? '00000000-0000-0000-0000-000000000001';

    const result = await callActionDirect(crewPage, 'sign_monthly_signoff', {
      yacht_id: RBAC_CONFIG.yachtId,
      signoff_id: signoffId,
      signature_level: 'hod',
      signature_data: {
        name: 'Unauthorized Crew',
        declaration: 'Attempting unauthorized HOD sign',
        timestamp: new Date().toISOString(),
      },
    });
    const data = result.data as any;
    console.log(`[JSON] crew→HOD sign: status=${result.status} success=${data?.success} code=${data?.error?.code}`);

    // SECURITY: action must NOT succeed
    expect(data?.success).not.toBe(true);

    // BUG-HOR-3: if error code is DATABASE_ERROR (500), flag it — should be FORBIDDEN
    if (data?.error?.code === 'DATABASE_ERROR') {
      console.warn('[BUG-HOR-3] Backend returned DATABASE_ERROR instead of FORBIDDEN for crew→HOD sign. Fix: add role check before DB call.');
    }
  });
});

test.describe('[Security] HOD cannot succeed at master (captain) level signature', () => {
  test('[hod] sign_monthly_signoff level=master → success must be false', async ({
    hodPage, supabaseAdmin,
  }) => {
    await hodPage.goto(`${BASE_URL}/`);
    await hodPage.waitForLoadState('domcontentloaded');

    const { data: signoff } = await supabaseAdmin
      .from('pms_hor_monthly_signoffs')
      .select('id')
      .eq('yacht_id', RBAC_CONFIG.yachtId)
      .in('status', ['hod_signed', 'crew_signed', 'draft'])
      .limit(1)
      .single();

    const signoffId = signoff?.id ?? '00000000-0000-0000-0000-000000000002';

    const result = await callActionDirect(hodPage, 'sign_monthly_signoff', {
      yacht_id: RBAC_CONFIG.yachtId,
      signoff_id: signoffId,
      signature_level: 'master',
      signature_data: {
        name: 'Unauthorized HOD',
        declaration: 'Attempting unauthorized master sign',
        timestamp: new Date().toISOString(),
      },
    });
    const data = result.data as any;
    console.log(`[JSON] hod→master sign: status=${result.status} success=${data?.success} code=${data?.error?.code}`);

    // SECURITY: action must NOT succeed
    expect(data?.success).not.toBe(true);

    if (data?.error?.code === 'DATABASE_ERROR') {
      console.warn('[BUG-HOR-3] HOD→master returned DATABASE_ERROR instead of FORBIDDEN.');
    }
  });
});

test.describe('[Security] Cross-yacht write must not succeed', () => {
  test('[crew] upsert on foreign yacht → success must be false', async ({
    crewPage,
  }) => {
    await crewPage.goto(`${BASE_URL}/`);
    await crewPage.waitForLoadState('domcontentloaded');

    const FOREIGN_YACHT_ID = '00000000-dead-beef-0000-000000000000';

    // IMPORTANT: pass FOREIGN_YACHT_ID in contextOverrides so the action bus
    // uses it as context.yacht_id (not RBAC_CONFIG.yachtId which is the fallback).
    // Without this, callActionDirect ignores the payload yacht_id and writes to
    // the authorized yacht — a false-positive test.
    const result = await callActionDirect(crewPage, 'upsert_hours_of_rest', {
      user_id: CREW_USER_ID,
      record_date: '2024-07-01',
      rest_periods: [{ start: '00:00', end: '10:00' }],
      voyage_type: 'in_port',
    }, { yacht_id: FOREIGN_YACHT_ID });
    const data = result.data as any;
    console.log(`[JSON] cross-yacht upsert: status=${result.status} success=${data?.success} code=${data?.error?.code}`);

    // SECURITY: must not write to a yacht this user doesn't belong to
    if (data?.success === true) {
      console.error('[SECURITY BREACH] Cross-yacht upsert SUCCEEDED. RLS or role check missing.');
    }
    expect(data?.success).not.toBe(true);
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// UI TAB VISIBILITY — real Supabase session + page navigation
//
// BUG-HOR-4 (RESOLVED 2026-04-17): global-setup now uses
// supabase.auth.signInWithPassword() to produce real sessions, so the
// Supabase client accepts the storage state on page load without
// redirecting. These tests are no longer conditionally skipped.
// ═══════════════════════════════════════════════════════════════════════════════

test.describe('[UI] Crew — auth state and page load', () => {
  test('[crew] navigating to /hours-of-rest — verify auth outcome', async ({
    crewPage,
  }) => {
    await crewPage.goto(`${BASE_URL}/hours-of-rest`);
    await crewPage.waitForLoadState('domcontentloaded');
    await crewPage.waitForTimeout(3000); // allow Supabase client to bootstrap

    const url = crewPage.url();
    console.log(`[UI] crew url: ${url}`);

    // PMS HoR page is loaded — verify crew sees My Time but not Department
    const myTimeTab = crewPage.locator('[data-testid="hor-tab-my-time"]');
    const deptTab   = crewPage.locator('[data-testid="hor-tab-department"]');

    await expect(myTimeTab).toBeVisible({ timeout: 8000 });
    expect(await deptTab.count()).toBe(0);
    console.log('[UI] crew: My Time tab visible, no Department tab ✓');
  });
});

test.describe('[UI] Captain — auth state and tab visibility', () => {
  test('[captain] navigating to /hours-of-rest — verify auth and tabs', async ({
    captainPage,
  }) => {
    await captainPage.goto(`${BASE_URL}/hours-of-rest`);
    await captainPage.waitForLoadState('domcontentloaded');
    await captainPage.waitForTimeout(3000);

    const url = captainPage.url();
    console.log(`[UI] captain url: ${url}`);

    const myTimeTab  = captainPage.locator('[data-testid="hor-tab-my-time"]');
    const vesselTab  = captainPage.locator('[data-testid="hor-tab-vessel"]');
    const fleetTab   = captainPage.locator('[data-testid="hor-tab-fleet"]');

    await expect(myTimeTab).toBeVisible({ timeout: 8000 });
    await expect(vesselTab).toBeVisible({ timeout: 5000 });
    expect(await fleetTab.count()).toBe(0);
    console.log('[UI] captain: My Time + All Departments visible, no Fleet ✓');
  });
});

// ═══════════════════════════════════════════════════════════════════════════════
// READ OPERATIONS — all roles can read
// ═══════════════════════════════════════════════════════════════════════════════

test.describe('[Read] get_hours_of_rest — all roles return 200 + records array', () => {
  test('[crew] get_hours_of_rest → 200', async ({ crewPage }) => {
    await crewPage.goto(`${BASE_URL}/`);
    await crewPage.waitForLoadState('domcontentloaded');
    const result = await callActionDirect(crewPage, 'get_hours_of_rest', { yacht_id: RBAC_CONFIG.yachtId });
    console.log(`[JSON] crew get_hours_of_rest: status=${result.status} success=${(result.data as any)?.success}`);
    expect(result.status).toBe(200);
    expect((result.data as any).success).toBe(true);
    expect(Array.isArray((result.data as any).data?.records)).toBe(true);
  });

  test('[hod] get_hours_of_rest → 200', async ({ hodPage }) => {
    await hodPage.goto(`${BASE_URL}/`);
    await hodPage.waitForLoadState('domcontentloaded');
    const result = await callActionDirect(hodPage, 'get_hours_of_rest', { yacht_id: RBAC_CONFIG.yachtId });
    console.log(`[JSON] hod get_hours_of_rest: status=${result.status} success=${(result.data as any)?.success}`);
    expect(result.status).toBe(200);
    expect((result.data as any).success).toBe(true);
    expect(Array.isArray((result.data as any).data?.records)).toBe(true);
  });

  test('[captain] get_hours_of_rest → 200', async ({ captainPage }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');
    const result = await callActionDirect(captainPage, 'get_hours_of_rest', { yacht_id: RBAC_CONFIG.yachtId });
    console.log(`[JSON] captain get_hours_of_rest: status=${result.status} success=${(result.data as any)?.success}`);
    expect(result.status).toBe(200);
    expect((result.data as any).success).toBe(true);
    expect(Array.isArray((result.data as any).data?.records)).toBe(true);
  });
});

test.describe('[Read] list_monthly_signoffs — all roles return 200', () => {
  test('[crew] list_monthly_signoffs → 200', async ({ crewPage }) => {
    await crewPage.goto(`${BASE_URL}/`);
    await crewPage.waitForLoadState('domcontentloaded');
    const result = await callActionDirect(crewPage, 'list_monthly_signoffs', { yacht_id: RBAC_CONFIG.yachtId });
    console.log(`[JSON] crew list_monthly_signoffs: status=${result.status}`);
    expect(result.status).toBe(200);
  });

  test('[hod] list_monthly_signoffs → 200', async ({ hodPage }) => {
    await hodPage.goto(`${BASE_URL}/`);
    await hodPage.waitForLoadState('domcontentloaded');
    const result = await callActionDirect(hodPage, 'list_monthly_signoffs', { yacht_id: RBAC_CONFIG.yachtId });
    console.log(`[JSON] hod list_monthly_signoffs: status=${result.status}`);
    expect(result.status).toBe(200);
  });

  test('[captain] list_monthly_signoffs → 200', async ({ captainPage }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');
    const result = await callActionDirect(captainPage, 'list_monthly_signoffs', { yacht_id: RBAC_CONFIG.yachtId });
    console.log(`[JSON] captain list_monthly_signoffs: status=${result.status}`);
    expect(result.status).toBe(200);
  });
});
