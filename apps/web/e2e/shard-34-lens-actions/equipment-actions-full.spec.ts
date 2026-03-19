// apps/web/e2e/shard-34-lens-actions/equipment-actions-full.spec.ts

/**
 * SHARD 34: Full Action Coverage — Equipment
 *
 * HARD PROOF tests for:
 *   add_equipment_note      — required fields: equipment_id, note_text
 *                             stores in pms_equipment.metadata.notes JSONB
 *                             DOES write ledger_events row
 *
 * HARD PROOF tests for:
 *   update_equipment_status — DB trigger bug fixed (migration 20260316_004: 'closed' added to
 *                             work_order_status enum); fixture excludes decommissioned equipment
 *
 * Each test verifies:
 *   1. Full JSON response body (status, message fields)
 *   2. ledger_events row confirmed (action + entity_id) — where applicable
 *   3. Entity state mutation confirmed (pms_equipment.metadata.notes / status)
 *
 * AUTH STRATEGY: callActionDirect() uses a Node.js-minted JWT (same signing key as API)
 * to bypass browser localStorage invalidation by the Supabase client.
 *
 * IMPLEMENTATION NOTES:
 *   add_equipment_note returns: { status: 'success', message: 'Note added to equipment', notes_count: N }
 *   update_equipment_status returns: { status: 'success', new_status, old_status }
 */

import { test, expect, generateTestId } from '../rbac-fixtures';
import { BASE_URL, callActionDirect, pollLedger } from './helpers';

// ===========================================================================
// update_equipment_status — ADVISORY (API has DB bug: work_order enum conflict)
// ===========================================================================

test.describe('[HOD] update_equipment_status — HARD PROOF', () => {
  test('[HOD] update_equipment_status → 200 + pms_equipment status=degraded', async ({
    hodPage,
    getExistingEquipment,
    supabaseAdmin,
  }) => {
    const equipment = await getExistingEquipment();

    await hodPage.goto(`${BASE_URL}/equipment/${equipment.id}`);
    await hodPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(hodPage, 'update_equipment_status', {
      equipment_id: equipment.id,
      new_status: 'degraded',
      reason: 'S34 smoke test',
    });
    console.log(`[JSON] update_equipment_status: ${JSON.stringify(result.data)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string; new_status?: string };
    expect(data.status).toBe('success');

    // Entity state: verify pms_equipment.status set to 'degraded'
    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('pms_equipment')
          .select('status')
          .eq('id', equipment.id)
          .single();
        return (row as { status?: string } | null)?.status;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000,
        message: 'Expected pms_equipment.status=degraded' }
    ).toBe('degraded');
  });
});

// ===========================================================================
// add_equipment_note — HARD PROOF
// ===========================================================================

test.describe('[HOD] add_equipment_note — HARD PROOF', () => {
  test('[HOD] add_equipment_note → 200 + ledger row + metadata.notes grew', async ({
    hodPage,
    getExistingEquipment,
    supabaseAdmin,
  }) => {
    const testStart = new Date();
    const equipment = await getExistingEquipment();
    const noteText = `S34 HOD equipment note ${generateTestId('en')}`;

    // Count notes in metadata before
    const { data: beforeData } = await supabaseAdmin
      .from('pms_equipment')
      .select('metadata')
      .eq('id', equipment.id)
      .single();
    const beforeCount = ((beforeData as { metadata?: { notes?: unknown[] } } | null)?.metadata?.notes ?? []).length;

    await hodPage.goto(`${BASE_URL}/equipment/${equipment.id}`);
    await hodPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(hodPage, 'add_equipment_note', {
      equipment_id: equipment.id,
      note_text: noteText,
    });
    console.log(`[JSON] add_equipment_note response: ${JSON.stringify(result, null, 2)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string; message?: string; notes_count?: number };
    expect(data.status).toBe('success');
    expect(data.message).toBe('Note added to equipment');
    expect(typeof data.notes_count).toBe('number');
    expect(data.notes_count).toBeGreaterThanOrEqual(1);

    // Ledger verification — add_equipment_note DOES write ledger_events
    await pollLedger(supabaseAdmin, 'add_equipment_note', equipment.id, testStart);

    // Entity state: metadata.notes array grew
    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('pms_equipment')
          .select('metadata')
          .eq('id', equipment.id)
          .single();
        return ((row as { metadata?: { notes?: unknown[] } } | null)?.metadata?.notes ?? []).length;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000, message: 'Expected pms_equipment.metadata.notes to grow' }
    ).toBeGreaterThanOrEqual(beforeCount + 1);
  });
});

test.describe('[Captain] add_equipment_note — HARD PROOF', () => {
  test('[Captain] add_equipment_note → 200 + ledger row + metadata.notes grew', async ({
    captainPage,
    getExistingEquipment,
    supabaseAdmin,
  }) => {
    const testStart = new Date();
    const equipment = await getExistingEquipment();
    const noteText = `S34 Captain equipment note ${generateTestId('en')}`;

    const { data: beforeData } = await supabaseAdmin
      .from('pms_equipment')
      .select('metadata')
      .eq('id', equipment.id)
      .single();
    const beforeCount = ((beforeData as { metadata?: { notes?: unknown[] } } | null)?.metadata?.notes ?? []).length;

    await captainPage.goto(`${BASE_URL}/equipment/${equipment.id}`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'add_equipment_note', {
      equipment_id: equipment.id,
      note_text: noteText,
    });
    console.log(`[JSON] [Captain] add_equipment_note response: ${JSON.stringify(result, null, 2)}`);

    expect(result.status).toBe(200);
    expect((result.data as { status?: string }).status).toBe('success');
    expect((result.data as { notes_count?: number }).notes_count).toBeGreaterThanOrEqual(1);

    await pollLedger(supabaseAdmin, 'add_equipment_note', equipment.id, testStart);

    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('pms_equipment')
          .select('metadata')
          .eq('id', equipment.id)
          .single();
        return ((row as { metadata?: { notes?: unknown[] } } | null)?.metadata?.notes ?? []).length;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000 }
    ).toBeGreaterThanOrEqual(beforeCount + 1);
  });
});
