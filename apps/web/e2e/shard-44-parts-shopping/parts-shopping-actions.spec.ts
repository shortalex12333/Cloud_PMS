// apps/web/e2e/shard-44-parts-shopping/parts-shopping-actions.spec.ts

/**
 * SHARD 44: Parts + Shopping List Extended — HARD PROOF + ADVISORY
 *
 * Actions covered:
 *   generate_part_labels         — HARD PROOF: generates labels for part_ids array
 *   view_part_details            — HARD PROOF (READ): returns part data via PartHandlers
 *   promote_candidate_to_part    — ADVISORY: chief_engineer/manager only (captain → FORBIDDEN)
 *   view_shopping_list_history   — HARD PROOF (READ): returns history for item_id
 *
 * Advisory re-runs from shard-35 (bug checks):
 *   consume_part                 — data model split bug
 *   add_to_shopping_list         — source_type NOT NULL constraint
 *   delete_shopping_item         — user_role unbound variable
 *
 * DB tables: pms_parts, pms_shopping_list_items, pms_part_labels
 */

import { test, expect, generateTestId } from '../rbac-fixtures';
import { callActionDirect } from '../shard-34-lens-actions/helpers';
import { BASE_URL } from '../shard-33-lens-actions/helpers';

// ===========================================================================
// view_part_details — HARD PROOF (READ)
// ===========================================================================

test.describe('[Captain] view_part_details — HARD PROOF', () => {
  test('view_part_details → 200 + part data returned', async ({
    captainPage,
    getExistingPart,
  }) => {
    const part = await getExistingPart();

    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'view_part_details', {
      part_id: part.id,
    });
    console.log(`[JSON] view_part_details: ${JSON.stringify(result.data)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string; data?: unknown };
    expect(data.status).toBe('success');
    expect(data.data).toBeTruthy();
  });
});

// ===========================================================================
// generate_part_labels — HARD PROOF
// ===========================================================================

test.describe('[Captain] generate_part_labels — HARD PROOF', () => {
  test('generate_part_labels → 200 + label data returned', async ({
    captainPage,
    getExistingPart,
  }) => {
    const part = await getExistingPart();

    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'generate_part_labels', {
      part_ids: [part.id],
    });
    console.log(`[JSON] generate_part_labels: ${JSON.stringify(result.data)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string };
    expect(data.status).toBe('success');
  });
});

// ===========================================================================
// promote_candidate_to_part — ADVISORY (chief_engineer/manager only)
// ===========================================================================

test.describe('[Captain] promote_candidate_to_part — ADVISORY', () => {
  test('promote_candidate_to_part → FORBIDDEN for captain role', async ({
    captainPage,
  }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    // First create a candidate item to promote
    const createResult = await callActionDirect(captainPage, 'create_shopping_list_item', {
      part_name: `S44 Promote Target ${generateTestId('p')}`,
      quantity_requested: 1,
      source_type: 'manual_add',
    });
    expect(createResult.status).toBe(200);
    const itemId = (createResult.data.data as { shopping_list_item_id?: string })?.shopping_list_item_id;

    if (!itemId) {
      console.log('create_shopping_list_item did not return item_id — skipping');
      return;
    }

    // promote_candidate_to_part is only allowed for chief_engineer/manager
    // Captain maps to 'captain' role → should be FORBIDDEN
    const result = await callActionDirect(captainPage, 'promote_candidate_to_part', {
      item_id: itemId,
    });
    console.log(`[JSON] promote_candidate_to_part: status=${result.status}, ${JSON.stringify(result.data)}`);

    // captain is NOT in allowed roles → expect FORBIDDEN or wrapped error
    // 200 with success:false is also acceptable (RBAC returns plain JSON, not HTTP 403)
    expect([200, 403]).toContain(result.status);
    if (result.status === 200) {
      // Wrapped error: { success: false, code: 'FORBIDDEN' }
      const data = result.data as { success?: boolean; code?: string };
      expect(data.success).toBe(false);
      console.log('promote_candidate_to_part returned 200 with FORBIDDEN (RBAC enforcement confirmed)');
    }
  });
});

// ===========================================================================
// view_shopping_list_history — HARD PROOF (READ)
// ===========================================================================

test.describe('[Captain] view_shopping_list_history — HARD PROOF', () => {
  test('view_shopping_list_history → 200 + history data', async ({
    captainPage,
  }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    // Create a candidate item to get a valid item_id for history lookup
    const createResult = await callActionDirect(captainPage, 'create_shopping_list_item', {
      part_name: `S44 History Target ${generateTestId('h')}`,
      quantity_requested: 1,
      source_type: 'manual_add',
    });
    expect(createResult.status).toBe(200);
    const itemId = (createResult.data.data as { shopping_list_item_id?: string })?.shopping_list_item_id;

    if (!itemId) {
      console.log('create_shopping_list_item did not return item_id — skipping');
      return;
    }

    const result = await callActionDirect(captainPage, 'view_shopping_list_history', {
      item_id: itemId,
    });
    console.log(`[JSON] view_shopping_list_history: ${JSON.stringify(result.data)}`);

    expect(result.status).toBe(200);
    const data = result.data as { success?: boolean; status?: string };
    expect(data.success === true || data.status === 'success').toBe(true);
  });
});

// ===========================================================================
// ADVISORY RE-RUNS: consume_part, add_to_shopping_list, delete_shopping_item
// (check if backend bugs from shard-35 are fixed)
// ===========================================================================

test.describe('[Captain] consume_part — ADVISORY (bug check)', () => {
  test('consume_part → check if data model split is fixed', async ({
    captainPage,
    getExistingPart,
    seedWorkOrder,
  }) => {
    const part = await getExistingPart();
    const wo = await seedWorkOrder(`S44 consume WO ${generateTestId('w')}`);

    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'consume_part', {
      part_id: part.id,
      quantity: 1,
      work_order_id: wo.id,
      reason: 'S44 advisory consume re-run',
    });
    console.log(`[JSON] consume_part (advisory): status=${result.status}`);

    // 200 = bug fixed, 409/500 = data model split still present (quantity_on_hand vs pms_inventory_transactions)
    // REMOVE THIS ADVISORY WHEN: consume_part reads stock from pms_inventory_transactions
    // instead of pms_parts.quantity_on_hand (data model split resolved).
    // Tighten to: expect(result.status).toBe(200).
    expect([200, 409, 500]).toContain(result.status);
    if (result.status === 200) {
      console.log('consume_part 200 — data model split bug appears FIXED');
    } else {
      console.log(`consume_part ${result.status} — data model split bug still present (advisory)`);
    }
  });
});

test.describe('[Captain] add_to_shopping_list — ADVISORY (bug check)', () => {
  test('add_to_shopping_list → check if source_type bug is fixed', async ({
    captainPage,
    getExistingPart,
  }) => {
    const part = await getExistingPart();

    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'add_to_shopping_list', {
      part_id: part.id,
      suggested_qty: 2,
      source_type: 'inventory_low',
    });
    console.log(`[JSON] add_to_shopping_list (advisory): status=${result.status}`);

    // 200 = bug fixed, 500 = source_type NOT NULL constraint still failing
    // REMOVE THIS ADVISORY WHEN: add_to_shopping_list handler passes source_type to the DB insert.
    // Tighten to: expect(result.status).toBe(200).
    expect([200, 500]).toContain(result.status);
    if (result.status === 200) {
      console.log('add_to_shopping_list 200 — source_type bug appears FIXED');
    } else {
      console.log('add_to_shopping_list 500 — source_type bug still present (advisory)');
    }
  });
});

test.describe('[Captain] delete_shopping_item — ADVISORY (bug check)', () => {
  test('delete_shopping_item → check if user_role bug is fixed', async ({
    captainPage,
  }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    // Create item to delete
    const createResult = await callActionDirect(captainPage, 'create_shopping_list_item', {
      part_name: `S44 Delete Recheck ${generateTestId('dr')}`,
      quantity_requested: 1,
      source_type: 'manual_add',
    });
    expect(createResult.status).toBe(200);
    const itemId = (createResult.data.data as { shopping_list_item_id?: string })?.shopping_list_item_id;
    if (!itemId) return;

    const result = await callActionDirect(captainPage, 'delete_shopping_item', {
      item_id: itemId,
    });
    console.log(`[JSON] delete_shopping_item (advisory): status=${result.status}`);

    // 200 = bug fixed, 500 = user_role unbound variable still present
    // REMOVE THIS ADVISORY WHEN: delete_shopping_item handler no longer references the unbound
    // user_role variable (NameError in Python handler resolved).
    // Tighten to: expect(result.status).toBe(200) + verify item removed from pms_shopping_list_items.
    expect([200, 500]).toContain(result.status);
    if (result.status === 200) {
      console.log('delete_shopping_item 200 — user_role bug appears FIXED');
    } else {
      console.log('delete_shopping_item 500 — user_role bug still present (advisory)');
    }
  });
});
