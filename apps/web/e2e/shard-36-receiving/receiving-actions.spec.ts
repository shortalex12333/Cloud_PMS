// apps/web/e2e/shard-36-receiving/receiving-actions.spec.ts

import { test, expect, generateTestId } from '../rbac-fixtures';
import { callActionDirect } from '../shard-34-lens-actions/helpers';
import { BASE_URL } from '../shard-33-lens-actions/helpers';

/**
 * SHARD 36: Receiving Workflow Actions — HARD PROOF + ADVISORY
 *
 * Actions covered:
 *   create_receiving        — HARD PROOF: creates pms_receiving row (no PO required)
 *   add_receiving_item      — HARD PROOF: adds part item to a receiving draft
 *   update_receiving_fields — HARD PROOF: updates vendor_name on receiving draft
 *   submit_receiving_for_review — ADVISORY: may require signed payload → assert 400/200
 *   accept_receiving        — ADVISORY: signed action → assert 400/403
 *   reject_receiving        — ADVISORY: signed action → assert 400/403
 *
 * Chained pattern: create_receiving returns receiving_id used by all subsequent tests.
 * DB table: pms_receiving (confirmed to exist and accept rows).
 *
 * No purchase order pre-condition: create_receiving is a standalone "receiving draft"
 * that can later be linked to a PO. This matches the "+" quick-receive UI flow.
 */

// ===========================================================================
// create_receiving — HARD PROOF
// ===========================================================================

test.describe('[Captain] create_receiving — HARD PROOF', () => {
  test('[Captain] create_receiving → 200 + pms_receiving row created', async ({
    captainPage,
    supabaseAdmin,
  }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const testStart = new Date();
    const vendorName = `S36 Test Vendor ${generateTestId('v')}`;

    const result = await callActionDirect(captainPage, 'create_receiving', {
      vendor_name: vendorName,
      notes: `S36 smoke test receiving ${generateTestId('r')}`,
    });
    console.log(`[JSON] create_receiving: ${JSON.stringify(result.data)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string; receiving_id?: string };
    expect(data.status).toBe('success');
    expect(typeof data.receiving_id).toBe('string');

    const receivingId = data.receiving_id!;

    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('pms_receiving')
          .select('id, vendor_name')
          .eq('id', receivingId)
          .single();
        return (row as { id?: string } | null)?.id;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000, message: 'Expected pms_receiving row' }
    ).toBe(receivingId);
  });
});

// ===========================================================================
// add_receiving_item + update_receiving_fields — chained HARD PROOF
// ===========================================================================

test.describe('[Captain] receiving workflow — chained HARD PROOF', () => {
  test('[Captain] create → add_item → update_fields → all succeed with DB state', async ({
    captainPage,
    getExistingPart,
    supabaseAdmin,
  }) => {
    const part = await getExistingPart();

    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    // Step 1: create receiving draft
    const createResult = await callActionDirect(captainPage, 'create_receiving', {
      vendor_name: `S36 Chain Vendor ${generateTestId('v')}`,
    });
    expect(createResult.status).toBe(200);
    const receivingId = (createResult.data as { receiving_id?: string }).receiving_id!;
    expect(typeof receivingId).toBe('string');

    // Step 2: add_receiving_item
    const addItemResult = await callActionDirect(captainPage, 'add_receiving_item', {
      receiving_id: receivingId,
      part_id: part.id,
      quantity_received: 3,
      condition: 'good',
    });
    console.log(`[JSON] add_receiving_item: ${JSON.stringify(addItemResult.data)}`);
    expect(addItemResult.status).toBe(200);
    expect((addItemResult.data as { status?: string }).status).toBe('success');

    // Step 3: update_receiving_fields (update vendor reference)
    const updateRef = `S36-REF-${generateTestId('ref')}`;
    const updateResult = await callActionDirect(captainPage, 'update_receiving_fields', {
      receiving_id: receivingId,
      vendor_reference: updateRef,
    });
    console.log(`[JSON] update_receiving_fields: ${JSON.stringify(updateResult.data)}`);
    expect(updateResult.status).toBe(200);
    expect((updateResult.data as { status?: string }).status).toBe('success');

    // Step 4: verify DB — vendor_reference updated
    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('pms_receiving')
          .select('vendor_reference')
          .eq('id', receivingId)
          .single();
        return (row as { vendor_reference?: string } | null)?.vendor_reference;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000,
        message: 'Expected pms_receiving.vendor_reference to be updated' }
    ).toBe(updateRef);
  });
});

// ===========================================================================
// submit_receiving_for_review — HARD PROOF
// ===========================================================================

test.describe('[Captain] submit_receiving_for_review — HARD PROOF', () => {
  test('[Captain] create→add_item→submit → 200 + pms_receiving status=in_review', async ({
    captainPage,
    getExistingPart,
    supabaseAdmin,
  }) => {
    const part = await getExistingPart();

    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    // Step 1: create receiving draft
    const createResult = await callActionDirect(captainPage, 'create_receiving', {
      vendor_name: `S36 Submit Vendor ${generateTestId('v')}`,
    });
    expect(createResult.status).toBe(200);
    const receivingId = (createResult.data as { receiving_id?: string }).receiving_id!;

    // Step 2: add a receiving item (required before submission)
    const addResult = await callActionDirect(captainPage, 'add_receiving_item', {
      receiving_id: receivingId,
      part_id: part.id,
      quantity_received: 1,
    });
    expect(addResult.status).toBe(200);

    // Step 3: submit for review
    const result = await callActionDirect(captainPage, 'submit_receiving_for_review', {
      receiving_id: receivingId,
    });
    console.log(`[JSON] submit_receiving_for_review: ${JSON.stringify(result.data)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string };
    expect(data.status).toBe('success');

    // Entity state: verify pms_receiving.status updated to 'in_review'
    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('pms_receiving')
          .select('status')
          .eq('id', receivingId)
          .single();
        return (row as { status?: string } | null)?.status;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000,
        message: 'Expected pms_receiving.status=in_review' }
    ).toBe('in_review');
  });
});

// ===========================================================================
// accept_receiving — ADVISORY (SIGNED action)
// ===========================================================================

test.describe('[Captain] accept_receiving — ADVISORY (SIGNED)', () => {
  test('[Captain] accept_receiving without signature → 400/403 advisory', async ({
    captainPage,
  }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    // Use a known existing receiving ID (or a fresh draft — will fail state validation)
    const createResult = await callActionDirect(captainPage, 'create_receiving', {
      vendor_name: `S36 Accept Smoke ${generateTestId('v')}`,
    });
    const receivingId = (createResult.data as { receiving_id?: string }).receiving_id ?? 'unknown';

    const result = await callActionDirect(captainPage, 'accept_receiving', {
      receiving_id: receivingId,
    });
    console.log(`[JSON] accept_receiving (advisory): ${JSON.stringify(result.data)}`);

    // accept_receiving requires: items in draft, submission first, and a signature
    // Without prior submission → 400 (invalid state) or 403 (RBAC)
    expect([400, 403]).toContain(result.status);
  });
});

// ===========================================================================
// reject_receiving — ADVISORY (SIGNED action)
// ===========================================================================

test.describe('[Captain] reject_receiving — ADVISORY (SIGNED)', () => {
  test('[Captain] reject_receiving without valid pre-state → 400/403 advisory', async ({
    captainPage,
  }) => {
    await captainPage.goto(`${BASE_URL}/`);
    await captainPage.waitForLoadState('domcontentloaded');

    const createResult = await callActionDirect(captainPage, 'create_receiving', {
      vendor_name: `S36 Reject Smoke ${generateTestId('v')}`,
    });
    const receivingId = (createResult.data as { receiving_id?: string }).receiving_id ?? 'unknown';

    const result = await callActionDirect(captainPage, 'reject_receiving', {
      receiving_id: receivingId,
      rejection_reason: 'S36 advisory smoke rejection',
    });
    console.log(`[JSON] reject_receiving (advisory): ${JSON.stringify(result.data)}`);

    expect([400, 403]).toContain(result.status);
  });
});
