// apps/web/e2e/shard-33-lens-actions/work-order-actions.spec.ts

import { test, expect, generateTestId, ActionModalPO, RBAC_CONFIG } from '../rbac-fixtures';
import { BASE_URL, API_URL, callAction, assertNoRenderCrash } from './helpers';
import { generateFreshJwt, callActionAs } from '../shard-34-lens-actions/helpers';

/**
 * SHARD 33: Lens Actions — Work Orders (3 roles)
 *
 * Three-step pattern per test:
 *   1. Navigate + verify render
 *   2. Invoke action (UI button with waitForResponse, or fetchFromPage)
 *   3. Verify frontend JSON response + backend DB state
 *
 * Role matrix for WO actions:
 *   add_wo_note:      HOD ✓  Captain ✓  Crew → 403
 *   start_work_order: HOD ✓  Captain ✓  Crew → 403
 *   mark_complete:    HOD ✓  Captain ✓  Crew → 403
 *
 * NOTE: Until dedicated role users are provisioned, all 3 auth files may
 * map to the same captain account. 403 tests become meaningful once
 * crew.test@alex-short.com is in the master DB routing table as "crew" role.
 */

// ---------------------------------------------------------------------------
// HOD role — positive tests (all actions should succeed)
// ---------------------------------------------------------------------------
test.describe('[HOD] Work Order lens actions', () => {
  test('renders work-order detail without crash', async ({ hodPage, seedWorkOrder }) => {
    const wo = await seedWorkOrder(`S33 HOD Render ${generateTestId('r')}`);

    await hodPage.goto(`${BASE_URL}/work-orders/${wo.id}`);
    await hodPage.waitForLoadState('domcontentloaded');

    await expect(hodPage.getByRole('heading', { name: wo.title, exact: true }))
      .toBeVisible({ timeout: 15_000 });
    await assertNoRenderCrash(hodPage);
  });

  test('[HOD] add-note via UI → 200 + pms_work_order_notes write', async ({
    hodPage,
    seedWorkOrder,
    supabaseAdmin,
  }) => {
    const wo = await seedWorkOrder(`S33 HOD Note ${generateTestId('n')}`);

    // STEP 1
    await hodPage.goto(`${BASE_URL}/work-orders/${wo.id}`);
    await hodPage.waitForLoadState('domcontentloaded');
    await expect(hodPage.getByRole('heading', { name: wo.title, exact: true }))
      .toBeVisible({ timeout: 15_000 });
    await assertNoRenderCrash(hodPage);

    // STEP 2 — register listener BEFORE click
    const responsePromise = hodPage.waitForResponse(
      (res) => res.url().includes('/v1/actions/execute') && res.request().method() === 'POST',
      { timeout: 15_000 }
    );

    const btn = hodPage.locator('button:has-text("Add Note")').first();
    await expect(btn).toBeVisible({ timeout: 10_000 });
    await btn.click();

    const modal = new ActionModalPO(hodPage);
    await modal.waitForOpen();
    await modal.fillTextarea(`HOD smoke note ${generateTestId('s')}`);
    await modal.submit();

    // STEP 3 — frontend
    const res = await responsePromise;
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.status).toBe('success');

    // STEP 3 — backend
    await expect.poll(
      async () => {
        const { count } = await supabaseAdmin
          .from('pms_work_order_notes')
          .select('*', { count: 'exact', head: true })
          .eq('work_order_id', wo.id);
        return count ?? 0;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000,
        message: 'Expected pms_work_order_notes row within 8s' }
    ).toBeGreaterThanOrEqual(1);
  });

  test('[HOD] mark-complete → 200 + pms_work_orders.status=completed', async ({
    hodPage,
    seedWorkOrder,
    supabaseAdmin,
  }) => {
    const wo = await seedWorkOrder(`S33 HOD Complete ${generateTestId('c')}`);
    await supabaseAdmin.from('pms_work_orders').update({ status: 'in_progress' }).eq('id', wo.id);

    // STEP 1
    await hodPage.goto(`${BASE_URL}/work-orders/${wo.id}`);
    await hodPage.waitForLoadState('domcontentloaded');
    await assertNoRenderCrash(hodPage);

    // STEP 2 — call close_work_order (UI button = "Mark Complete" → modal or direct)
    // The hook calls mark_work_order_complete which maps to close_work_order endpoint
    const result = await callAction(hodPage, 'close_work_order', { work_order_id: wo.id });

    // STEP 3 — frontend
    expect(result.status).toBe(200);
    expect((result.data as { status?: string }).status).toBe('success');

    // STEP 3 — backend
    await expect.poll(
      async () => {
        const { data } = await supabaseAdmin
          .from('pms_work_orders')
          .select('status')
          .eq('id', wo.id)
          .single();
        return (data as { status?: string } | null)?.status;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000,
        message: 'Expected pms_work_orders.status = completed within 8s' }
    ).toBe('completed');
  });

  test('[HOD] start-work-order → 200 + status=in_progress', async ({
    hodPage,
    seedWorkOrder,
    supabaseAdmin,
  }) => {
    const wo = await seedWorkOrder(`S33 HOD Start ${generateTestId('s')}`);
    await supabaseAdmin.from('pms_work_orders').update({ status: 'open' }).eq('id', wo.id);

    await hodPage.goto(`${BASE_URL}/work-orders/${wo.id}`);
    await hodPage.waitForLoadState('domcontentloaded');
    await assertNoRenderCrash(hodPage);

    const result = await callAction(hodPage, 'start_work_order', { work_order_id: wo.id });

    expect(result.status).toBe(200);
    expect((result.data as { status?: string }).status).toBe('success');

    await expect.poll(
      async () => {
        const { data } = await supabaseAdmin
          .from('pms_work_orders')
          .select('status')
          .eq('id', wo.id)
          .single();
        return (data as { status?: string } | null)?.status;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000,
        message: 'Expected pms_work_orders.status = in_progress within 8s' }
    ).toBe('in_progress');
  });
});

// ---------------------------------------------------------------------------
// Captain role — positive tests
// ---------------------------------------------------------------------------
test.describe('[Captain] Work Order lens actions', () => {
  test('renders work-order detail without crash', async ({ captainPage, seedWorkOrder }) => {
    const wo = await seedWorkOrder(`S33 CAP Render ${generateTestId('r')}`);

    await captainPage.goto(`${BASE_URL}/work-orders/${wo.id}`);
    await captainPage.waitForLoadState('domcontentloaded');

    await expect(captainPage.getByRole('heading', { name: wo.title, exact: true }))
      .toBeVisible({ timeout: 15_000 });
    await assertNoRenderCrash(captainPage);
  });

  test('[Captain] add-note → 200 + DB write', async ({
    captainPage,
    seedWorkOrder,
    supabaseAdmin,
  }) => {
    const wo = await seedWorkOrder(`S33 CAP Note ${generateTestId('n')}`);

    await captainPage.goto(`${BASE_URL}/work-orders/${wo.id}`);
    await captainPage.waitForLoadState('domcontentloaded');
    await assertNoRenderCrash(captainPage);

    const result = await callAction(captainPage, 'add_wo_note', {
      work_order_id: wo.id,
      note_text: `Captain smoke note ${generateTestId('s')}`,
    });

    expect(result.status).toBe(200);
    expect((result.data as { status?: string }).status).toBe('success');

    await expect.poll(
      async () => {
        const { count } = await supabaseAdmin
          .from('pms_work_order_notes')
          .select('*', { count: 'exact', head: true })
          .eq('work_order_id', wo.id);
        return count ?? 0;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000 }
    ).toBeGreaterThanOrEqual(1);
  });
});

// ---------------------------------------------------------------------------
// Crew role — render (no crash) + permission enforcement (403)
// ---------------------------------------------------------------------------
test.describe('[Crew] Work Order lens actions', () => {
  test('renders work-order page without 500 crash', async ({ crewPage, seedWorkOrder }) => {
    const wo = await seedWorkOrder(`S33 CREW Render ${generateTestId('r')}`);

    await crewPage.goto(`${BASE_URL}/work-orders/${wo.id}`);
    await crewPage.waitForLoadState('domcontentloaded');

    // Crew may see "Not Found" or "Failed to Load" if they lack entity access.
    // Smoke check: page doesn't crash with a 500 (server error), only graceful states.
    await expect(crewPage.getByText('500', { exact: true }).first()).not.toBeVisible({ timeout: 10_000 });
  });

  test('[Crew] add-note → 403 (RBAC)', async ({
    crewPage,
    seedWorkOrder,
    getCrewUserId,
  }) => {
    let crewUserId: string;
    try {
      crewUserId = await getCrewUserId();
    } catch (e) {
      const err = e as Error;
      if (err.message?.startsWith('SKIP:')) {
        test.skip(true, err.message.replace('SKIP:', '').trim());
        return;
      }
      throw e;
    }

    const wo = await seedWorkOrder(`S33 Crew AddNote RBAC ${generateTestId('r')}`);
    await crewPage.goto(`${BASE_URL}/work-orders/${wo.id}`);
    await crewPage.waitForLoadState('domcontentloaded');

    const crewJwt = generateFreshJwt(crewUserId, 'e2e-crew@celeste.internal');
    const result = await callActionAs(crewPage, crewJwt, 'add_wo_note', {
      work_order_id: wo.id,
      note_text: 'crew rbac probe',
    });

    expect(result.status).toBe(403);
    expect((result.data as { error_code?: string }).error_code).toBe('FORBIDDEN');
  });

  test('[Crew] start-work-order → 403 (RBAC)', async ({
    crewPage,
    seedWorkOrder,
    getCrewUserId,
  }) => {
    let crewUserId: string;
    try {
      crewUserId = await getCrewUserId();
    } catch (e) {
      const err = e as Error;
      if (err.message?.startsWith('SKIP:')) {
        test.skip(true, err.message.replace('SKIP:', '').trim());
        return;
      }
      throw e;
    }

    const wo = await seedWorkOrder(`S33 Crew StartWO RBAC ${generateTestId('r')}`);
    await crewPage.goto(`${BASE_URL}/work-orders/${wo.id}`);
    await crewPage.waitForLoadState('domcontentloaded');

    const crewJwt = generateFreshJwt(crewUserId, 'e2e-crew@celeste.internal');
    const result = await callActionAs(crewPage, crewJwt, 'start_work_order', { work_order_id: wo.id });

    expect(result.status).toBe(403);
    expect((result.data as { error_code?: string }).error_code).toBe('FORBIDDEN');
  });
});
