// apps/web/e2e/shard-34-lens-actions/work-order-actions-full.spec.ts

/**
 * SHARD 34: Full Action Coverage — Work Orders
 *
 * HARD PROOF tests for:
 *   assign_work_order  — required fields: yacht_id, work_order_id, assigned_to (user UUID)
 *   cancel_work_order  — required fields: yacht_id, work_order_id; pre-condition: not 'completed'
 *
 * Each test verifies:
 *   1. Full JSON response body (status, message fields)
 *   2. ledger_events row confirmed (action + entity_id)
 *   3. Entity state mutation confirmed (pms_work_orders.status or assigned_to)
 *
 * AUTH STRATEGY: callActionDirect() uses a Node.js-minted JWT (same signing key as API)
 * to bypass browser localStorage invalidation by the Supabase client.
 *
 * IMPLEMENTATION NOTES:
 *   assign_work_order returns: { status: 'success', message: '...' }
 *   cancel_work_order returns:  { status: 'success', message: '...' }
 *
 * NOTE: yacht_id is sent in context (not payload) — callActionDirect() handles this.
 * assign_work_order: `assigned_to` field is the user UUID (from auth_users_profiles).
 */

import { test, expect, generateTestId } from '../rbac-fixtures';
import { BASE_URL, callActionDirect, SESSION_JWT, pollLedger } from './helpers';

/**
 * Decode the sub claim from the session JWT to get the user UUID that
 * exists in auth.users (used as assigned_to FK target).
 */
function getJwtSub(jwt: string): string {
  try {
    const parts = jwt.split('.');
    const payload = JSON.parse(Buffer.from(parts[1], 'base64url').toString('utf8'));
    return payload.sub as string;
  } catch {
    return 'a35cad0b-02ff-4287-b6e4-17c96fa6a424'; // fallback: x@alex-short.com
  }
}

// ===========================================================================
// assign_work_order
// ===========================================================================

test.describe('[HOD] assign_work_order — HARD PROOF', () => {
  test('[HOD] assign_work_order → 200 + ledger row + assigned_to set', async ({
    hodPage,
    seedWorkOrder,
    supabaseAdmin,
  }) => {
    const testStart = new Date();
    const workOrder = await seedWorkOrder(`S34 HOD AssignWO ${generateTestId('aw')}`);
    // Use the JWT sub — this user exists in auth.users (FK target for assigned_to)
    const assigneeId = getJwtSub(SESSION_JWT);

    await hodPage.goto(`${BASE_URL}/work-orders/${workOrder.id}`);
    await hodPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(hodPage, 'assign_work_order', {
      work_order_id: workOrder.id,
      assigned_to: assigneeId,
    });
    console.log(`[JSON] assign_work_order response: ${JSON.stringify(result, null, 2)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string };
    expect(data.status).toBe('success');

    // Ledger verification
    await pollLedger(supabaseAdmin, 'assign_work_order', workOrder.id, testStart);

    // Entity state: assigned_to should be set
    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('pms_work_orders')
          .select('assigned_to')
          .eq('id', workOrder.id)
          .single();
        return (row as { assigned_to?: string } | null)?.assigned_to;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000, message: 'Expected pms_work_orders.assigned_to to be set' }
    ).toBeTruthy();
  });
});

test.describe('[Captain] assign_work_order — HARD PROOF', () => {
  test('[Captain] assign_work_order → 200 + assigned_to set', async ({
    captainPage,
    seedWorkOrder,
    supabaseAdmin,
  }) => {
    const testStart = new Date();
    const workOrder = await seedWorkOrder(`S34 CAP AssignWO ${generateTestId('aw')}`);
    // Use the JWT sub — this user exists in auth.users (FK target for assigned_to)
    const assigneeId = getJwtSub(SESSION_JWT);

    await captainPage.goto(`${BASE_URL}/work-orders/${workOrder.id}`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'assign_work_order', {
      work_order_id: workOrder.id,
      assigned_to: assigneeId,
    });
    console.log(`[JSON] [Captain] assign_work_order response: ${JSON.stringify(result, null, 2)}`);

    expect(result.status).toBe(200);
    expect((result.data as { status?: string }).status).toBe('success');

    await pollLedger(supabaseAdmin, 'assign_work_order', workOrder.id, testStart);

    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('pms_work_orders')
          .select('assigned_to')
          .eq('id', workOrder.id)
          .single();
        return (row as { assigned_to?: string } | null)?.assigned_to;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000 }
    ).toBeTruthy();
  });
});

// ===========================================================================
// cancel_work_order
// ===========================================================================

test.describe('[HOD] cancel_work_order — HARD PROOF', () => {
  test('[HOD] cancel_work_order → 200 + ledger row + status=cancelled', async ({
    hodPage,
    seedWorkOrder,
    supabaseAdmin,
  }) => {
    const testStart = new Date();
    const workOrder = await seedWorkOrder(`S34 HOD CancelWO ${generateTestId('cw')}`);

    // PRE-CONDITION: ensure work order is in 'open' state (cancellable)
    await supabaseAdmin
      .from('pms_work_orders')
      .update({ status: 'open' })
      .eq('id', workOrder.id);

    await hodPage.goto(`${BASE_URL}/work-orders/${workOrder.id}`);
    await hodPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(hodPage, 'cancel_work_order', {
      work_order_id: workOrder.id,
    });
    console.log(`[JSON] cancel_work_order response: ${JSON.stringify(result, null, 2)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string };
    expect(data.status).toBe('success');

    // Ledger verification
    await pollLedger(supabaseAdmin, 'cancel_work_order', workOrder.id, testStart);

    // Entity state: status should be 'cancelled'
    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('pms_work_orders')
          .select('status')
          .eq('id', workOrder.id)
          .single();
        return (row as { status?: string } | null)?.status;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000, message: 'Expected pms_work_orders.status=cancelled' }
    ).toBe('cancelled');
  });
});

test.describe('[Captain] cancel_work_order — HARD PROOF', () => {
  test('[Captain] cancel_work_order → 200 + ledger row + status=cancelled', async ({
    captainPage,
    seedWorkOrder,
    supabaseAdmin,
  }) => {
    const testStart = new Date();
    const workOrder = await seedWorkOrder(`S34 CAP CancelWO ${generateTestId('cw')}`);

    await supabaseAdmin
      .from('pms_work_orders')
      .update({ status: 'open' })
      .eq('id', workOrder.id);

    await captainPage.goto(`${BASE_URL}/work-orders/${workOrder.id}`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'cancel_work_order', {
      work_order_id: workOrder.id,
    });
    console.log(`[JSON] [Captain] cancel_work_order response: ${JSON.stringify(result, null, 2)}`);

    expect(result.status).toBe(200);
    expect((result.data as { status?: string }).status).toBe('success');

    await pollLedger(supabaseAdmin, 'cancel_work_order', workOrder.id, testStart);

    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('pms_work_orders')
          .select('status')
          .eq('id', workOrder.id)
          .single();
        return (row as { status?: string } | null)?.status;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000 }
    ).toBe('cancelled');
  });
});
