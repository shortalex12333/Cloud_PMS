// apps/web/e2e/shard-33-lens-actions/fault-actions.spec.ts

import { test, expect, generateTestId, RBAC_CONFIG } from '../rbac-fixtures';
import { BASE_URL, callAction, assertNoRenderCrash } from './helpers';
import { generateFreshJwt, callActionAs } from '../shard-34-lens-actions/helpers';

/**
 * SHARD 33: Lens Actions — Faults (3 roles)
 *
 * Role matrix for fault actions:
 *   acknowledge_fault: HOD ✓  Captain ✓  Crew → 403
 *
 * "Acknowledge" button only renders when fault.status = 'open' | 'reported'.
 * Each test seeds its own fault to avoid state bleed.
 */

// ---------------------------------------------------------------------------
// HOD role — positive tests
// ---------------------------------------------------------------------------
test.describe('[HOD] Fault lens actions', () => {
  test('renders fault detail without crash', async ({ hodPage, seedFault }) => {
    const fault = await seedFault(`S33 HOD Render ${generateTestId('r')}`);

    await hodPage.goto(`${BASE_URL}/faults/${fault.id}`);
    await hodPage.waitForLoadState('domcontentloaded');

    await expect(hodPage.getByRole('heading', { name: fault.title, exact: true }).first())
      .toBeVisible({ timeout: 15_000 });
    await assertNoRenderCrash(hodPage);
  });

  test('[HOD] acknowledge-fault → 200 + status=investigating', async ({
    hodPage,
    seedFault,
    supabaseAdmin,
  }) => {
    const fault = await seedFault(`S33 HOD Ack ${generateTestId('a')}`);
    await supabaseAdmin.from('pms_faults').update({ status: 'reported' }).eq('id', fault.id);

    // STEP 1
    await hodPage.goto(`${BASE_URL}/faults/${fault.id}`);
    await hodPage.waitForLoadState('domcontentloaded');
    await expect(hodPage.getByRole('heading', { name: fault.title, exact: true }).first())
      .toBeVisible({ timeout: 15_000 });
    await assertNoRenderCrash(hodPage);

    // STEP 2 — try UI button, fall back to API
    const btn = hodPage.locator('button:has-text("Acknowledge")').first();
    const btnVisible = await btn.isVisible().catch(() => false);

    let responseStatus: number;
    let responseBody: { status?: string };

    if (btnVisible) {
      const responsePromise = hodPage.waitForResponse(
        (res) => res.url().includes('/v1/actions/execute') && res.request().method() === 'POST',
        { timeout: 15_000 }
      );
      await btn.click();
      const res = await responsePromise;
      responseStatus = res.status();
      responseBody = await res.json();
    } else {
      const result = await callAction(hodPage, 'acknowledge_fault', { fault_id: fault.id });
      responseStatus = result.status;
      responseBody = result.data as { status?: string };
    }

    // STEP 3 — frontend
    expect(responseStatus).toBe(200);
    expect(responseBody.status).toBe('success');

    // STEP 3 — backend
    await expect.poll(
      async () => {
        const { data } = await supabaseAdmin
          .from('pms_faults')
          .select('status')
          .eq('id', fault.id)
          .single();
        return (data as { status?: string } | null)?.status;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000,
        message: 'Expected pms_faults.status = acknowledged within 8s' }
    ).toBe('investigating'); // acknowledge_fault always transitions to 'investigating' (see p0_actions_routes.py)
  });
});

// ---------------------------------------------------------------------------
// Captain role — positive tests
// ---------------------------------------------------------------------------
test.describe('[Captain] Fault lens actions', () => {
  test('renders fault detail without crash', async ({ captainPage, seedFault }) => {
    const fault = await seedFault(`S33 CAP Render ${generateTestId('r')}`);

    await captainPage.goto(`${BASE_URL}/faults/${fault.id}`);
    await captainPage.waitForLoadState('domcontentloaded');

    await expect(captainPage.getByRole('heading', { name: fault.title, exact: true }).first())
      .toBeVisible({ timeout: 15_000 });
    await assertNoRenderCrash(captainPage);
  });

  test('[Captain] acknowledge-fault → 200 + status=investigating', async ({
    captainPage,
    seedFault,
    supabaseAdmin,
  }) => {
    const fault = await seedFault(`S33 CAP Ack ${generateTestId('a')}`);
    await supabaseAdmin.from('pms_faults').update({ status: 'reported' }).eq('id', fault.id);

    await captainPage.goto(`${BASE_URL}/faults/${fault.id}`);
    await captainPage.waitForLoadState('domcontentloaded');
    await assertNoRenderCrash(captainPage);

    const result = await callAction(captainPage, 'acknowledge_fault', { fault_id: fault.id });

    expect(result.status).toBe(200);
    expect((result.data as { status?: string }).status).toBe('success');

    await expect.poll(
      async () => {
        const { data } = await supabaseAdmin
          .from('pms_faults')
          .select('status')
          .eq('id', fault.id)
          .single();
        return (data as { status?: string } | null)?.status;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000 }
    ).toBe('investigating'); // acknowledge_fault always transitions to 'investigating' (see p0_actions_routes.py)
  });
});

// ---------------------------------------------------------------------------
// Crew role — render smoke + permission enforcement
// ---------------------------------------------------------------------------
test.describe('[Crew] Fault lens actions', () => {
  test('renders fault page without 500 crash', async ({ crewPage, seedFault }) => {
    const fault = await seedFault(`S33 CREW Render ${generateTestId('r')}`);

    await crewPage.goto(`${BASE_URL}/faults/${fault.id}`);
    await crewPage.waitForLoadState('domcontentloaded');

    await expect(crewPage.getByText('500', { exact: true }).first()).not.toBeVisible({ timeout: 10_000 });
  });

  test('[Crew] acknowledge-fault → 403 (RBAC)', async ({
    crewPage,
    seedFault,
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

    const fault = await seedFault(`S33 Crew AckFault RBAC ${generateTestId('r')}`);
    await crewPage.goto(`${BASE_URL}/faults/${fault.id}`);
    await crewPage.waitForLoadState('domcontentloaded');

    // Mint a crew-role JWT and call the action directly (bypasses localStorage)
    const crewJwt = generateFreshJwt(crewUserId, 'e2e-crew@celeste.internal');
    const result = await callActionAs(crewPage, crewJwt, 'acknowledge_fault', { fault_id: fault.id });

    // RBAC must deny crew — backend enforces, not just UI.
    // error_code='FORBIDDEN' distinguishes genuine RBAC denial from
    // 'RLS_DENIED' (user not found in MASTER DB), which is also 403.
    expect(result.status).toBe(403);
    expect((result.data as { error_code?: string }).error_code).toBe('FORBIDDEN');
  });
});
