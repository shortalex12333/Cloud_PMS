// apps/web/e2e/shard-33-lens-actions/equipment-actions.spec.ts

import { test, expect, generateTestId, RBAC_CONFIG } from '../rbac-fixtures';
import { BASE_URL, callAction, assertNoRenderCrash } from './helpers';
import { generateFreshJwt, callActionAs } from '../shard-34-lens-actions/helpers';

/**
 * SHARD 33: Lens Actions — Equipment (3 roles)
 *
 * add_equipment_note allowed_roles: ["crew", "chief_engineer", "chief_officer", "captain", "manager"]
 * (see p0_actions_routes.py:3681 — Security Fix 2026-02-10 added crew to allow notes).
 * Crew IS allowed → asserts 200, not 403.
 *
 * Uses getExistingEquipment (read-only, no insert).
 * Notes cleanup: delete rows matching the smoke test prefix after each write test.
 */

// ---------------------------------------------------------------------------
// HOD role — positive tests
// ---------------------------------------------------------------------------
test.describe('[HOD] Equipment lens actions', () => {
  test('renders equipment detail without crash', async ({
    hodPage,
    getExistingEquipment,
  }) => {
    const eq = await getExistingEquipment();

    await hodPage.goto(`${BASE_URL}/equipment/${eq.id}`);
    await hodPage.waitForLoadState('domcontentloaded');

    await expect(hodPage.getByRole('heading', { name: eq.name }).first())
      .toBeVisible({ timeout: 15_000 });
    await assertNoRenderCrash(hodPage);
  });

  test('[HOD] add-equipment-note → 200 + pms_equipment_notes write', async ({
    hodPage,
    getExistingEquipment,
    supabaseAdmin,
  }) => {
    const eq = await getExistingEquipment();

    // add_equipment_note stores notes in pms_equipment.metadata.notes JSONB array
    const { data: beforeEq } = await supabaseAdmin
      .from('pms_equipment')
      .select('metadata')
      .eq('id', eq.id)
      .single();
    const before = ((beforeEq as { metadata?: { notes?: unknown[] } } | null)?.metadata?.notes ?? []).length;

    // STEP 1
    await hodPage.goto(`${BASE_URL}/equipment/${eq.id}`);
    await hodPage.waitForLoadState('domcontentloaded');
    await assertNoRenderCrash(hodPage);

    // STEP 2 — via action API (no dedicated Add Note modal on equipment page)
    const noteText = `HOD smoke eq note ${generateTestId('eq')}`;
    const result = await callAction(hodPage, 'add_equipment_note', {
      equipment_id: eq.id,
      note_text: noteText,
    });

    // STEP 3 — frontend
    expect(result.status).toBe(200);
    expect((result.data as { status?: string }).status).toBe('success');

    // STEP 3 — backend: note is stored in pms_equipment.metadata.notes JSONB array
    await expect.poll(
      async () => {
        const { data } = await supabaseAdmin
          .from('pms_equipment')
          .select('metadata')
          .eq('id', eq.id)
          .single();
        return ((data as { metadata?: { notes?: unknown[] } } | null)?.metadata?.notes ?? []).length;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000,
        message: 'Expected pms_equipment.metadata.notes to grow within 8s' }
    ).toBeGreaterThanOrEqual(before + 1);
    // Note: JSONB metadata notes are not cleaned up (smoke test; one extra note is harmless)
  });
});

// ---------------------------------------------------------------------------
// Captain role — positive tests
// ---------------------------------------------------------------------------
test.describe('[Captain] Equipment lens actions', () => {
  test('renders equipment detail without crash', async ({
    captainPage,
    getExistingEquipment,
  }) => {
    const eq = await getExistingEquipment();

    await captainPage.goto(`${BASE_URL}/equipment/${eq.id}`);
    await captainPage.waitForLoadState('domcontentloaded');

    await expect(captainPage.getByRole('heading', { name: eq.name }).first())
      .toBeVisible({ timeout: 15_000 });
    await assertNoRenderCrash(captainPage);
  });

  test('[Captain] add-equipment-note → 200 + DB write', async ({
    captainPage,
    getExistingEquipment,
    supabaseAdmin,
  }) => {
    const eq = await getExistingEquipment();

    const { data: beforeEq2 } = await supabaseAdmin
      .from('pms_equipment')
      .select('metadata')
      .eq('id', eq.id)
      .single();
    const before2 = ((beforeEq2 as { metadata?: { notes?: unknown[] } } | null)?.metadata?.notes ?? []).length;

    await captainPage.goto(`${BASE_URL}/equipment/${eq.id}`);
    await captainPage.waitForLoadState('domcontentloaded');
    await assertNoRenderCrash(captainPage);

    const noteText = `Captain smoke eq note ${generateTestId('eq')}`;
    const result = await callAction(captainPage, 'add_equipment_note', {
      equipment_id: eq.id,
      note_text: noteText,
    });

    expect(result.status).toBe(200);
    expect((result.data as { status?: string }).status).toBe('success');

    await expect.poll(
      async () => {
        const { data } = await supabaseAdmin
          .from('pms_equipment')
          .select('metadata')
          .eq('id', eq.id)
          .single();
        return ((data as { metadata?: { notes?: unknown[] } } | null)?.metadata?.notes ?? []).length;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000 }
    ).toBeGreaterThanOrEqual(before2 + 1);
    // Note: JSONB metadata notes are not cleaned up (smoke test; one extra note is harmless)
  });
});

// ---------------------------------------------------------------------------
// Crew role — render smoke + permission enforcement
// ---------------------------------------------------------------------------
test.describe('[Crew] Equipment lens actions', () => {
  test('renders equipment page without 500 crash', async ({
    crewPage,
    getExistingEquipment,
  }) => {
    const eq = await getExistingEquipment();

    await crewPage.goto(`${BASE_URL}/equipment/${eq.id}`);
    await crewPage.waitForLoadState('domcontentloaded');

    await expect(crewPage.getByText('500', { exact: true }).first()).not.toBeVisible({ timeout: 10_000 });
  });

  test('[Crew] add-equipment-note → 200 (crew IS allowed)', async ({
    crewPage,
    getExistingEquipment,
    getCrewUserId,
    supabaseAdmin,
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

    const eq = await getExistingEquipment();
    await crewPage.goto(`${BASE_URL}/equipment/${eq.id}`);
    await crewPage.waitForLoadState('domcontentloaded');

    // Capture note count before
    const { data: before } = await supabaseAdmin
      .from('pms_equipment')
      .select('metadata')
      .eq('id', eq.id)
      .single();
    const beforeCount = ((before as { metadata?: { notes?: unknown[] } } | null)?.metadata?.notes ?? []).length;

    // Crew is in equipment_note_roles — must succeed with 200
    const crewJwt = generateFreshJwt(crewUserId, 'e2e-crew@celeste.internal');
    const result = await callActionAs(crewPage, crewJwt, 'add_equipment_note', {
      equipment_id: eq.id,
      note_text: `Crew RBAC proof note ${generateTestId('cn')}`,
    });

    expect(result.status).toBe(200);
    expect((result.data as { status?: string }).status).toBe('success');

    // Verify note was written (entity state proof)
    await expect.poll(
      async () => {
        const { data } = await supabaseAdmin
          .from('pms_equipment')
          .select('metadata')
          .eq('id', eq.id)
          .single();
        return ((data as { metadata?: { notes?: unknown[] } } | null)?.metadata?.notes ?? []).length;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000,
        message: 'Expected crew note to appear in pms_equipment.metadata.notes' }
    ).toBeGreaterThanOrEqual(beforeCount + 1);
  });
});
