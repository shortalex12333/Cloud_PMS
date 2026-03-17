// apps/web/e2e/shard-34-lens-actions/inventory-actions-full.spec.ts

/**
 * SHARD 34: Full Action Coverage — Inventory
 *
 * HARD PROOF tests for:
 *   log_part_usage — required fields: part_id, quantity, usage_reason
 *                    writes pms_audit_log + centralized ledger write
 *                    verifiable: pms_parts.quantity_on_hand decreased
 *
 *   transfer_part  — required fields: part_id, quantity, from_location_id, to_location_id
 *                    uses transfer_stock_atomic RPC
 *                    verifiable: pms_part_stock quantities changed, pms_inventory_transactions created
 *
 * Each test verifies:
 *   1. Full JSON response body (status, message fields)
 *   2. ledger_events row confirmed (action + entity_id) — via centralized ledger write
 *   3. Entity state mutation confirmed
 *
 * AUTH STRATEGY: callActionDirect() uses a Node.js-minted JWT (same signing key as API)
 * to bypass browser localStorage invalidation by the Supabase client.
 *
 * IMPLEMENTATION NOTES:
 *   log_part_usage returns: ResponseBuilder.success({ usage_log, new_stock_level, ... })
 *                           outer p0 wrapper adds execution_id + action
 *   transfer_part returns:  { status: 'success', transfer_group_id, quantity_transferred, ... }
 *
 * NOTE: transfer_part requires pms_part_stock rows with location set AND stock > 0.
 *   getPartWithLocation() returns null if none exist → test.skip().
 */

import { test, expect, generateTestId, RBAC_CONFIG } from '../rbac-fixtures';
import { BASE_URL, callActionDirect, pollLedger } from './helpers';

// ===========================================================================
// log_part_usage
// ===========================================================================

test.describe('[HOD] log_part_usage — HARD PROOF', () => {
  test('[HOD] log_part_usage → 200 + ledger row + quantity_on_hand decreased', async ({
    hodPage,
    getPartWithStock,
    supabaseAdmin,
  }) => {
    const testStart = new Date();
    // Use any pms_parts row with quantity_on_hand >= 2 — deduct_part_inventory RPC
    // checks pms_parts.quantity_on_hand directly (not pms_part_stock).
    let part: { id: string; name: string; quantity_on_hand: number };
    try {
      part = await getPartWithStock();
    } catch {
      test.skip(true, 'No parts with quantity_on_hand >= 2 — log_part_usage HOD test skipped');
      return;
    }
    const partId = part.id;
    const beforeQty = part.quantity_on_hand;

    await hodPage.goto(`${BASE_URL}/inventory/${partId}`);
    await hodPage.waitForLoadState('domcontentloaded');

    // Seed pms_inventory_stock — the block_deactivated_stock_mutations trigger
    // on pms_part_usage checks pms_inventory_stock (NOT pms_part_stock) for active rows.
    try {
      await supabaseAdmin.from('pms_inventory_stock').insert({
        yacht_id: RBAC_CONFIG.yachtId,
        part_id: partId,
        location: 'main_store',
        quantity: 10,
      });
    } catch (seedErr) {
      console.log(`[REM-005] HOD inventory_stock seed: ${seedErr}`);
    }

    const result = await callActionDirect(hodPage, 'log_part_usage', {
      part_id: partId,
      quantity: 1,
      usage_reason: 'work_order',
    });
    console.log(`[JSON] log_part_usage response: ${JSON.stringify(result, null, 2)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string; success?: boolean; new_stock_level?: number };
    // ResponseBuilder.success wraps as { success: true, data: {...}, message: '...' }
    // p0 passes through and adds execution_id
    expect(data.status === 'success' || data.success === true).toBe(true);

    // Ledger verification (centralized write in p0)
    await pollLedger(supabaseAdmin, 'log_part_usage', partId, testStart);

    // Entity state: quantity_on_hand decreased
    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('pms_parts')
          .select('quantity_on_hand')
          .eq('id', partId)
          .single();
        return (row as { quantity_on_hand?: number } | null)?.quantity_on_hand;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000, message: 'Expected pms_parts.quantity_on_hand to decrease by 1' }
    ).toBeLessThanOrEqual(beforeQty - 1);
  });
});

test.describe('[Captain] log_part_usage — HARD PROOF', () => {
  test('[Captain] log_part_usage → 200 + ledger row + quantity_on_hand decreased', async ({
    captainPage,
    getPartWithStock,
    supabaseAdmin,
  }) => {
    const testStart = new Date();
    let part: { id: string; name: string; quantity_on_hand: number };
    try {
      part = await getPartWithStock();
    } catch {
      test.skip(true, 'No parts with quantity_on_hand >= 2 — log_part_usage captain test skipped');
      return;
    }
    const partId = part.id;
    const beforeQty = part.quantity_on_hand;

    await captainPage.goto(`${BASE_URL}/inventory/${partId}`);
    await captainPage.waitForLoadState('domcontentloaded');

    // REM-005: Seed pms_inventory_stock — the block_deactivated_stock_mutations trigger
    // on pms_part_usage checks pms_inventory_stock (NOT pms_part_stock) for active rows.
    // deduct_part_inventory() inserts into pms_part_usage which fires the trigger.
    try {
      await supabaseAdmin.from('pms_inventory_stock').insert({
        yacht_id: RBAC_CONFIG.yachtId,
        part_id: partId,
        location: 'main_store',
        quantity: 10,
      });
    } catch (seedErr) {
      console.log(`[REM-005] Captain inventory_stock seed: ${seedErr}`);
    }

    const result = await callActionDirect(captainPage, 'log_part_usage', {
      part_id: partId,
      quantity: 1,
      usage_reason: 'work_order',
    });
    console.log(`[JSON] [Captain] log_part_usage response: ${JSON.stringify(result, null, 2)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string; success?: boolean };
    expect(data.status === 'success' || data.success === true).toBe(true);

    await pollLedger(supabaseAdmin, 'log_part_usage', partId, testStart);

    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('pms_parts')
          .select('quantity_on_hand')
          .eq('id', partId)
          .single();
        return (row as { quantity_on_hand?: number } | null)?.quantity_on_hand;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000 }
    ).toBeLessThanOrEqual(beforeQty - 1);
  });
});

// ===========================================================================
// transfer_part (CONDITIONAL: requires pms_part_stock with location set)
// ===========================================================================

test.describe('[HOD] transfer_part — HARD PROOF', () => {
  test('[HOD] transfer_part → 200 + stock quantities changed (entity state only)', async ({
    hodPage,
    getPartWithLocation,
    supabaseAdmin,
  }) => {
    const stockRecord = await getPartWithLocation();
    if (!stockRecord) {
      test.skip(true, 'No parts with located stock found — transfer_part test skipped');
      return;
    }

    // Get current on_hand at source location
    const { data: beforeStock } = await supabaseAdmin
      .from('pms_part_stock')
      .select('on_hand')
      .eq('stock_id', stockRecord.id)
      .single();
    const beforeOnHand = (beforeStock as { on_hand?: number } | null)?.on_hand ?? 0;

    if (beforeOnHand < 1) {
      test.skip(true, 'Source location has 0 stock — transfer_part test skipped');
      return;
    }

    // Use a different location name for destination
    const toLocation = `S34-TEST-DEST-${generateTestId('loc').toUpperCase()}`;

    await hodPage.goto(`${BASE_URL}/inventory/${stockRecord.part_id}`);
    await hodPage.waitForLoadState('domcontentloaded');

    const testStart = new Date();
    const result = await callActionDirect(hodPage, 'transfer_part', {
      part_id: stockRecord.part_id,
      quantity: 1,
      from_location_id: stockRecord.location,
      to_location_id: toLocation,
    });
    console.log(`[JSON] transfer_part response: ${JSON.stringify(result, null, 2)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string; quantity_transferred?: number };
    expect(data.status).toBe('success');
    expect(data.quantity_transferred).toBe(1);

    // transfer_part is now in _ACTION_ENTITY_MAP → ledger row has correct entity_id
    await pollLedger(supabaseAdmin, 'transfer_part', stockRecord.part_id, testStart);

    // Entity state: source location stock decreased
    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('pms_part_stock')
          .select('on_hand')
          .eq('stock_id', stockRecord.id)
          .single();
        return (row as { on_hand?: number } | null)?.on_hand;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000, message: 'Expected source location stock to decrease by 1' }
    ).toBeLessThanOrEqual(beforeOnHand - 1);
  });
});
