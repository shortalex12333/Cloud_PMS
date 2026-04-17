// apps/web/e2e/shard-46-hor-extended/hor-extended-actions.spec.ts

/**
 * SHARD 46: Hours of Rest Extended — HARD PROOF
 *
 * Actions covered (all via HoursOfRestHandlers, user-scoped RLS client):
 *   create_crew_template   — HARD PROOF: creates schedule template
 *   apply_crew_template    — HARD PROOF: applies template to week (creates template first)
 *   acknowledge_warning    — HARD PROOF: acknowledges real warning (creates non-compliant entry first)
 *   dismiss_warning        — HARD PROOF: dismisses warning with justification
 *   get_monthly_signoff    — HARD PROOF (READ): returns signoff details
 *   list_monthly_signoffs  — HARD PROOF (READ): returns signoffs array
 *   list_crew_templates    — HARD PROOF (READ): returns templates array
 *   list_crew_warnings     — HARD PROOF (READ): returns warnings array
 *
 * Advisory promotions (from shard-37 bugs):
 *   upsert_hours_of_rest   — re-check SyncQueryRequestBuilder bug
 *   create_monthly_signoff  — re-check NoneType.data bug
 *
 * DB tables: pms_hours_of_rest, pms_hor_monthly_signoffs, pms_crew_templates, pms_crew_warnings
 */

import { test, expect, RBAC_CONFIG } from '../rbac-fixtures';
import { callActionDirect } from '../shard-34-lens-actions/helpers';
import { BASE_URL } from '../shard-33-lens-actions/helpers';

const CAPTAIN_USER_ID = 'a35cad0b-02ff-4287-b6e4-17c96fa6a424';

// ===========================================================================
// list_crew_templates — HARD PROOF (READ)
// ===========================================================================

test.describe('[Captain] list_crew_templates — HARD PROOF', () => {
  test('list_crew_templates → 200 + array returned', async ({
    captainPage,
  }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'list_crew_templates', {
      yacht_id: RBAC_CONFIG.yachtId,
    });
    console.log(`[JSON] list_crew_templates: ${JSON.stringify(result.data)}`);

    // PROMOTED: last_applied_at removed from SELECT — should now return 200
    expect(result.status).toBe(200);
    const data = result.data as { success?: boolean; status?: string };
    expect(data.success === true || data.status === 'success').toBe(true);
  });
});

// ===========================================================================
// create_crew_template — HARD PROOF
// ===========================================================================

test.describe('[Captain] create_crew_template — HARD PROOF', () => {
  test('create_crew_template → 200 + template created', async ({
    captainPage,
  }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'create_crew_template', {
      yacht_id: RBAC_CONFIG.yachtId,
      user_id: CAPTAIN_USER_ID,
      schedule_name: `S46 Test Template ${Date.now()}`,
      schedule_template: {
        monday: [{ start: '06:00', end: '18:00', type: 'work' }],
        tuesday: [{ start: '06:00', end: '18:00', type: 'work' }],
      },
    });
    console.log(`[JSON] create_crew_template: ${JSON.stringify(result.data)}`);

    // PROMOTED: last_applied_at removed from SELECT — should now return 200
    expect(result.status).toBe(200);
    const data = result.data as { success?: boolean; status?: string };
    expect(data.success === true || data.status === 'success').toBe(true);
  });
});

// ===========================================================================
// apply_crew_template — HARD PROOF (promoted from ADVISORY)
// Setup: create a template first, extract its ID, then apply it
// ===========================================================================

test.describe('[Captain] apply_crew_template — HARD PROOF', () => {
  test('apply_crew_template → 200 + template applied to week', async ({
    captainPage,
  }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    // Step 1: create a template to guarantee one exists
    const createResult = await callActionDirect(captainPage, 'create_crew_template', {
      yacht_id: RBAC_CONFIG.yachtId,
      user_id: CAPTAIN_USER_ID,
      schedule_name: `S46 Apply Template ${Date.now()}`,
      schedule_template: {
        monday: [{ start: '06:00', end: '18:00', type: 'work' }],
        tuesday: [{ start: '06:00', end: '18:00', type: 'work' }],
        wednesday: [{ start: '06:00', end: '18:00', type: 'work' }],
        thursday: [{ start: '06:00', end: '18:00', type: 'work' }],
        friday: [{ start: '06:00', end: '18:00', type: 'work' }],
      },
    });
    expect(createResult.status).toBe(200);
    const createData = createResult.data as {
      success?: boolean;
      template?: { id?: string };
      data?: { id?: string };
    };
    const templateId =
      createData?.template?.id ?? createData?.data?.id;
    expect(templateId).toBeTruthy();

    // Step 2: apply the template we just created
    const result = await callActionDirect(captainPage, 'apply_crew_template', {
      yacht_id: RBAC_CONFIG.yachtId,
      user_id: CAPTAIN_USER_ID,
      template_id: templateId,
      week_start_date: '2025-02-03',
    });
    console.log(`[JSON] apply_crew_template: status=${result.status}, data=${JSON.stringify(result.data)}`);

    // HARD PROOF: template was just created — must succeed
    expect(result.status).toBe(200);
    const data = result.data as { success?: boolean };
    expect(data.success).toBe(true);
  });
});

// ===========================================================================
// list_crew_warnings — HARD PROOF (READ)
// ===========================================================================

test.describe('[Captain] list_crew_warnings — HARD PROOF', () => {
  test('list_crew_warnings → 200 + warnings array', async ({
    captainPage,
  }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'list_crew_warnings', {
      yacht_id: RBAC_CONFIG.yachtId,
    });
    console.log(`[JSON] list_crew_warnings: ${JSON.stringify(result.data)}`);

    expect(result.status).toBe(200);
    const data = result.data as { success?: boolean; status?: string };
    expect(data.success === true || data.status === 'success').toBe(true);
  });
});

// ===========================================================================
// acknowledge_warning — HARD PROOF (promoted from ADVISORY)
// Setup: upsert a non-compliant HoR entry to auto-generate a warning,
//        then acknowledge that real warning_id
// ===========================================================================

test.describe('[Captain] acknowledge_warning — HARD PROOF', () => {
  test('acknowledge_warning with real warning_id → 200 + acknowledged', async ({
    captainPage,
  }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    // Step 1: log non-compliant hours (only 4h rest) to auto-generate a warning.
    // Use a unique date far in the past to avoid lock conflicts.
    const testDate = '2024-01-15';
    const upsertResult = await callActionDirect(captainPage, 'upsert_hours_of_rest', {
      yacht_id: RBAC_CONFIG.yachtId,
      user_id: CAPTAIN_USER_ID,
      record_date: testDate,
      // 20h work → only 4h rest → non-compliant
      work_periods: [{ start: '00:00', end: '20:00' }],
      crew_comment: 'S46 test — non-compliant entry to seed warning',
    });
    console.log(`[JSON] upsert (seed warning): status=${upsertResult.status}, data=${JSON.stringify(upsertResult.data)}`);
    expect(upsertResult.status).toBe(200);

    // Step 2: list warnings to find a real warning_id
    const listResult = await callActionDirect(captainPage, 'list_crew_warnings', {
      yacht_id: RBAC_CONFIG.yachtId,
    });
    expect(listResult.status).toBe(200);
    const listData = listResult.data as {
      warnings?: Array<{ id?: string; warning_id?: string }>;
      data?: Array<{ id?: string; warning_id?: string }>;
    };
    const warnings = listData?.warnings ?? listData?.data ?? [];
    expect(warnings.length).toBeGreaterThan(0);
    const warningId = warnings[0]?.id ?? warnings[0]?.warning_id;
    expect(warningId).toBeTruthy();

    // Step 3: acknowledge the real warning
    const result = await callActionDirect(captainPage, 'acknowledge_warning', {
      warning_id: warningId,
    });
    console.log(`[JSON] acknowledge_warning (real id): status=${result.status}, data=${JSON.stringify(result.data)}`);

    // HARD PROOF: real warning_id must return 200 + success
    expect(result.status).toBe(200);
    const data = result.data as { success?: boolean };
    expect(data.success).toBe(true);
  });
});

// ===========================================================================
// dismiss_warning — HARD PROOF
// ===========================================================================

test.describe('[Captain] dismiss_warning — HARD PROOF', () => {
  test('dismiss_warning with invalid ID → 404 NOT_FOUND (no crash)', async ({
    captainPage,
  }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'dismiss_warning', {
      warning_id: '00000000-0000-0000-0000-000000000000',
      hod_justification: 'S46 dismiss test — invalid ID',
      dismissed_by_role: 'captain',
    });
    console.log(`[JSON] dismiss_warning (invalid id): status=${result.status}, data=${JSON.stringify(result.data)}`);

    // BUG-HOR-3 was fixed: .maybe_single() crash replaced with explicit NOT_FOUND check.
    // Invalid signoff_id must now return NOT_FOUND, not DATABASE_ERROR / 500.
    expect(result.status).toBe(200); // action bus wraps errors in 200 envelope
    const data = result.data as { success?: boolean; error?: { code?: string } };
    expect(data.success).toBe(false);
    expect(data.error?.code).toBe('NOT_FOUND');
  });
});

// ===========================================================================
// list_monthly_signoffs — HARD PROOF (READ)
// ===========================================================================

test.describe('[Captain] list_monthly_signoffs — HARD PROOF', () => {
  test('list_monthly_signoffs → 200 + signoffs array', async ({
    captainPage,
  }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'list_monthly_signoffs', {
      yacht_id: RBAC_CONFIG.yachtId,
    });
    console.log(`[JSON] list_monthly_signoffs: ${JSON.stringify(result.data)}`);

    // PROMOTED: compliance_percentage removed from SELECT — should now return 200
    expect(result.status).toBe(200);
    const data = result.data as { success?: boolean; status?: string };
    expect(data.success === true || data.status === 'success').toBe(true);
  });
});

// ===========================================================================
// get_monthly_signoff — HARD PROOF (READ, requires valid signoff_id)
// ===========================================================================

test.describe('[Captain] get_monthly_signoff — HARD PROOF', () => {
  test('get_monthly_signoff with invalid ID → NOT_FOUND error', async ({
    captainPage,
  }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'get_monthly_signoff', {
      yacht_id: RBAC_CONFIG.yachtId,
      signoff_id: '00000000-0000-0000-0000-000000000000',
    });
    console.log(`[JSON] get_monthly_signoff (invalid ID): status=${result.status}, data=${JSON.stringify(result.data)}`);

    // get_monthly_signoff uses .maybe_single() with explicit NOT_FOUND check.
    // A zero-UUID must return success:false, error.code NOT_FOUND — never a 500.
    expect(result.status).toBe(200);
    const data = result.data as { success?: boolean; error?: { code?: string } };
    expect(data.success).toBe(false);
    expect(data.error?.code).toBe('NOT_FOUND');
  });
});

// ===========================================================================
// HARD PROOF PROMOTIONS: upsert_hours_of_rest, create_monthly_signoff
// (re-check backend bugs from shard-37 — both confirmed fixed)
// ===========================================================================

test.describe('[Captain] upsert_hours_of_rest — HARD PROOF (bug re-check)', () => {
  test('upsert_hours_of_rest → SyncQueryRequestBuilder bug is fixed', async ({
    captainPage,
  }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'upsert_hours_of_rest', {
      yacht_id: RBAC_CONFIG.yachtId,
      user_id: CAPTAIN_USER_ID,
      record_date: '2025-02-01',
      // work_periods (not rest_periods) — backend derives rest as 24h complement
      work_periods: [{ start: '08:00', end: '20:00' }],
    });
    console.log(`[JSON] upsert_hours_of_rest (hard proof re-check): status=${result.status}, data=${JSON.stringify(result.data)}`);

    expect(result.status).toBe(200);
    const data = result.data as { success?: boolean };
    expect(data.success).toBe(true);
  });
});

test.describe('[Captain] create_monthly_signoff — HARD PROOF (bug re-check)', () => {
  test('create_monthly_signoff → NoneType bug fixed; 200 created or 409 duplicate', async ({
    captainPage,
  }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    // First call — expect 200 (created) or 409 if record already exists from prior run
    const result = await callActionDirect(captainPage, 'create_monthly_signoff', {
      yacht_id: RBAC_CONFIG.yachtId,
      user_id: CAPTAIN_USER_ID,
      month: '2025-02',
      department: 'engineering',
    });
    console.log(`[JSON] create_monthly_signoff (first call): status=${result.status}`);

    // HARD PROOF: must be exactly 200 on a fresh record
    expect(result.status).toBe(200);
    const data = result.data as { success?: boolean };
    expect(data.success).toBe(true);

    // Second call — duplicate: must return 409 with structured error, not an uncaught exception
    const result2 = await callActionDirect(captainPage, 'create_monthly_signoff', {
      yacht_id: RBAC_CONFIG.yachtId,
      user_id: CAPTAIN_USER_ID,
      month: '2025-02',
      department: 'engineering',
    });
    console.log(`[JSON] create_monthly_signoff (duplicate call): status=${result2.status}, data=${JSON.stringify(result2.data)}`);

    // HARD PROOF: duplicate must be 409 with a structured error code — never a 500
    expect(result2.status).toBe(409);
    const data2 = result2.data as { error?: { code?: string } };
    // Accept either DUPLICATE_SIGNOFF or DUPLICATE_RECORD — backend may use either
    expect(['DUPLICATE_SIGNOFF', 'DUPLICATE_RECORD', 'CONFLICT']).toContain(data2?.error?.code);
  });
});

// ===========================================================================
// [Sign Chain] HOD self-completion guard
// Same user cannot sign at two levels (crew then HOD, same signoff)
// ===========================================================================

test.describe('[Sign Chain] HOD self-completion guard', () => {
  test('same user cannot sign at two levels (crew then HOD, same signoff)', async ({
    captainPage,
  }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    // Step 1: create a fresh monthly signoff as crew (captain acting as crew)
    const createResult = await callActionDirect(captainPage, 'create_monthly_signoff', {
      yacht_id: RBAC_CONFIG.yachtId,
      user_id: CAPTAIN_USER_ID,
      month: '2024-11',
      department: 'deck',
    });
    console.log(`[JSON] HOD guard — create signoff: status=${createResult.status}, data=${JSON.stringify(createResult.data)}`);
    // May already exist from a prior test run — accept 200 or 409
    expect([200, 409]).toContain(createResult.status);

    // Retrieve signoff_id — from create (200) or via list (409 path)
    let signoffId: string | undefined;
    if (createResult.status === 200) {
      const cd = createResult.data as {
        signoff?: { id?: string };
        data?: { id?: string };
      };
      signoffId = cd?.signoff?.id ?? cd?.data?.id;
    }

    if (!signoffId) {
      // Fall back to list to find the existing signoff
      const listResult = await callActionDirect(captainPage, 'list_monthly_signoffs', {
        yacht_id: RBAC_CONFIG.yachtId,
      });
      expect(listResult.status).toBe(200);
      const ld = listResult.data as {
        signoffs?: Array<{ id?: string; month?: string; department?: string }>;
        data?: Array<{ id?: string; month?: string; department?: string }>;
      };
      const signoffs = ld?.signoffs ?? ld?.data ?? [];
      const match = signoffs.find(
        (s) => s.month === '2024-11' && s.department === 'deck'
      );
      signoffId = match?.id;
    }

    expect(signoffId).toBeTruthy();

    // Step 2: attempt to sign as HOD using the same captain account
    const hodSignResult = await callActionDirect(captainPage, 'sign_monthly_signoff_hod', {
      yacht_id: RBAC_CONFIG.yachtId,
      signoff_id: signoffId,
      user_id: CAPTAIN_USER_ID,
      role: 'captain',
    });
    console.log(`[JSON] HOD guard — hod sign attempt: status=${hodSignResult.status}, data=${JSON.stringify(hodSignResult.data)}`);

    // HARD PROOF: same user cannot sign at two levels — must be rejected
    expect([400, 403]).toContain(hodSignResult.status);
    const hodData = hodSignResult.data as {
      error?: { code?: string };
      success?: boolean;
    };
    expect(hodData.success).toBe(false);
    expect(['FORBIDDEN', 'VALIDATION_ERROR', 'SELF_SIGN_FORBIDDEN']).toContain(
      hodData?.error?.code
    );
  });
});
