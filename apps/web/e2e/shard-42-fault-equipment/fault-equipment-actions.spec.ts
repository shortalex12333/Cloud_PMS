// apps/web/e2e/shard-42-fault-equipment/fault-equipment-actions.spec.ts

/**
 * SHARD 42: Fault + Equipment Extended — HARD PROOF
 *
 * Actions covered:
 *   add_fault_photo      — HARD PROOF: appends photo to pms_faults.metadata.photos
 *   view_fault_detail    — HARD PROOF (READ): returns fault + equipment join
 *   view_fault_history   — HARD PROOF (READ): returns faults array for equipment
 *
 * OUT OF SCOPE (not in _ACTION_DISPATCH):
 *   decommission_equipment, restore_archived_equipment — no API route exists
 *   create_work_order_from_fault — tested in shard-41
 *
 * DB tables: pms_faults (metadata.photos), ledger_events
 */

import { test, expect, generateTestId } from '../rbac-fixtures';
import { callActionDirect } from '../shard-34-lens-actions/helpers';
import { BASE_URL } from '../shard-33-lens-actions/helpers';

// ===========================================================================
// add_fault_photo — HARD PROOF
// ===========================================================================

test.describe('[Captain] add_fault_photo — HARD PROOF', () => {
  test('add_fault_photo → 200 + metadata.photos updated', async ({
    captainPage,
    seedFault,
    supabaseAdmin,
  }) => {
    const fault = await seedFault(`S42 AddPhoto ${generateTestId('p')}`);
    const photoUrl = `https://storage.celeste7.ai/test/s42-smoke-${generateTestId('img')}.jpg`;

    await captainPage.goto(`${BASE_URL}/faults/${fault.id}`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'add_fault_photo', {
      fault_id: fault.id,
      photo_url: photoUrl,
    });
    console.log(`[JSON] add_fault_photo: ${JSON.stringify(result.data)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string; message?: string };
    expect(data.status).toBe('success');
    expect(data.message).toContain('Photo added');

    // Entity state: metadata.photos includes our URL
    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('pms_faults')
          .select('metadata')
          .eq('id', fault.id)
          .single();
        const photos = (row as { metadata?: { photos?: { url: string }[] } } | null)?.metadata?.photos ?? [];
        return photos.some(p => p.url === photoUrl);
      },
      { intervals: [500, 1000, 1500], timeout: 8_000,
        message: 'Expected metadata.photos to contain our URL' }
    ).toBe(true);
  });
});

// ===========================================================================
// view_fault_detail — HARD PROOF (READ)
// ===========================================================================

test.describe('[Captain] view_fault_detail — HARD PROOF', () => {
  test('view_fault_detail → 200 + fault object with equipment join', async ({
    captainPage,
    seedFault,
  }) => {
    const fault = await seedFault(`S42 ViewDetail ${generateTestId('d')}`);

    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'view_fault_detail', {
      fault_id: fault.id,
    });
    console.log(`[JSON] view_fault_detail: ${JSON.stringify(result.data)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string; fault?: { id: string; title: string; pms_equipment?: unknown } };
    expect(data.status).toBe('success');
    expect(data.fault).toBeTruthy();
    expect(data.fault!.id).toBe(fault.id);
    // Equipment join should be present (may be null if orphaned)
    expect('pms_equipment' in data.fault!).toBe(true);
  });
});

// ===========================================================================
// view_fault_history — HARD PROOF (READ)
// ===========================================================================

test.describe('[Captain] view_fault_history — HARD PROOF', () => {
  test('view_fault_history → 200 + faults array for equipment', async ({
    captainPage,
    getExistingEquipment,
  }) => {
    const equipment = await getExistingEquipment();

    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'view_fault_history', {
      equipment_id: equipment.id,
    });
    console.log(`[JSON] view_fault_history: ${JSON.stringify(result.data)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string; faults?: unknown[]; count?: number };
    expect(data.status).toBe('success');
    expect(Array.isArray(data.faults)).toBe(true);
    expect(typeof data.count).toBe('number');
  });
});
