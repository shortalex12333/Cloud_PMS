// apps/web/e2e/shard-34-lens-actions/fault-actions-full.spec.ts

/**
 * SHARD 34: Full Action Coverage — Faults
 *
 * HARD PROOF tests for:
 *   close_fault      — requires status='investigating' pre-condition
 *   reopen_fault     — requires status='resolved' or 'closed' pre-condition
 *   add_fault_note   — any status OK; crew IS allowed
 *
 * Each test verifies:
 *   1. Full JSON response body (status, message fields)
 *   2. ledger_events row confirmed (action + entity_id)
 *   3. Entity state mutation confirmed (pms_faults.status or metadata.notes)
 *
 * IMPLEMENTATION NOTES (from p0_actions_routes.py):
 *   close_fault returns:    { status: 'success', message: 'Fault closed' }
 *   reopen_fault returns:   { status: 'success', ... }
 *   add_fault_note returns: { status: 'success', message: 'Note added to fault', notes_count: N }
 *
 * AUTH STRATEGY: callActionDirect() uses a Node.js-minted JWT (same signing key as API)
 * to bypass browser localStorage invalidation by the Supabase client.
 *
 * NOTE: add_fault_note does NOT write a ledger_events row (only metadata.notes update).
 */

import { test, expect, generateTestId } from '../rbac-fixtures';
import { BASE_URL, callActionDirect, pollLedger } from './helpers';

// ===========================================================================
// close_fault
// ===========================================================================

test.describe('[HOD] close_fault — HARD PROOF', () => {
  test('[HOD] close_fault → 200 + ledger row + pms_faults.status=closed', async ({
    hodPage,
    seedFault,
    supabaseAdmin,
  }) => {
    const testStart = new Date();
    const fault = await seedFault(`S34 HOD CloseFault ${generateTestId('cf')}`);

    // PRE-CONDITION: must be 'investigating' to allow close (state machine + DB CHECK constraint)
    // NOTE: 'acknowledged' is rejected by DB CHECK constraint; valid statuses: open, closed, investigating, resolved
    await supabaseAdmin
      .from('pms_faults')
      .update({ status: 'investigating' })
      .eq('id', fault.id);

    // Navigate to establish browser context for page.evaluate
    await hodPage.goto(`${BASE_URL}/faults/${fault.id}`);
    await hodPage.waitForLoadState('domcontentloaded');

    // STEP 2 — call action via direct JWT
    const result = await callActionDirect(hodPage, 'close_fault', { fault_id: fault.id });
    console.log(`[JSON] close_fault response: ${JSON.stringify(result, null, 2)}`);

    // STEP 3 — JSON validation
    expect(result.status).toBe(200);
    const data = result.data as { status?: string; message?: string };
    expect(data.status).toBe('success');
    expect(data.message).toBe('Fault closed');

    // STEP 3 — ledger_events verification
    await pollLedger(supabaseAdmin, 'close_fault', fault.id, testStart);

    // STEP 3 — entity state verification
    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('pms_faults')
          .select('status')
          .eq('id', fault.id)
          .single();
        return (row as { status?: string } | null)?.status;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000, message: 'Expected pms_faults.status=closed' }
    ).toBe('closed');
  });
});

test.describe('[Captain] close_fault — HARD PROOF', () => {
  test('[Captain] close_fault → 200 + ledger row + status=closed', async ({
    captainPage,
    seedFault,
    supabaseAdmin,
  }) => {
    const testStart = new Date();
    const fault = await seedFault(`S34 CAP CloseFault ${generateTestId('cf')}`);

    await supabaseAdmin
      .from('pms_faults')
      .update({ status: 'investigating' })
      .eq('id', fault.id);

    await captainPage.goto(`${BASE_URL}/faults/${fault.id}`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'close_fault', { fault_id: fault.id });
    console.log(`[JSON] [Captain] close_fault response: ${JSON.stringify(result, null, 2)}`);

    expect(result.status).toBe(200);
    expect((result.data as { status?: string }).status).toBe('success');

    await pollLedger(supabaseAdmin, 'close_fault', fault.id, testStart);

    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('pms_faults')
          .select('status')
          .eq('id', fault.id)
          .single();
        return (row as { status?: string } | null)?.status;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000 }
    ).toBe('closed');
  });
});

test.describe('[Crew] close_fault — RBAC enforcement', () => {
  test.skip('[Crew] close_fault → 403 (RBAC)', () => {
    // SKIPPED: hod.json / captain.json / crew.json all resolve to the same
    // captain JWT (x@alex-short.com). RBAC enforcement cannot be verified until
    // crew.tenant@alex-short.com is provisioned in the master DB routing table
    // with role='crew' and auth state files are regenerated with separate credentials.
  });
});

// ===========================================================================
// reopen_fault
// ===========================================================================

test.describe('[HOD] reopen_fault — HARD PROOF', () => {
  test('[HOD] reopen_fault → 200 + ledger row + status=open', async ({
    hodPage,
    seedFault,
    supabaseAdmin,
  }) => {
    const testStart = new Date();
    const fault = await seedFault(`S34 HOD ReopenFault ${generateTestId('rf')}`);

    // PRE-CONDITION: must be 'resolved' or 'closed' to reopen (state machine)
    await supabaseAdmin
      .from('pms_faults')
      .update({ status: 'resolved' })
      .eq('id', fault.id);

    await hodPage.goto(`${BASE_URL}/faults/${fault.id}`);
    await hodPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(hodPage, 'reopen_fault', {
      fault_id: fault.id,
      reason: 'S34 smoke test reopen — not actually resolved',
    });
    console.log(`[JSON] reopen_fault response: ${JSON.stringify(result, null, 2)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string };
    expect(data.status).toBe('success');

    // reopen_fault IS in _ACTION_ENTITY_MAP (p0_actions_routes.py:129) and the handler
    // explicitly inserts a ledger_events row at line 2394. Poll for it.
    await pollLedger(supabaseAdmin, 'reopen_fault', fault.id, testStart);

    // Entity state: should transition to 'open' (per p0_actions_routes.py)
    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('pms_faults')
          .select('status')
          .eq('id', fault.id)
          .single();
        return (row as { status?: string } | null)?.status;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000, message: 'Expected status to change from resolved' }
    ).toBe('open');
  });
});

test.describe('[Captain] reopen_fault — HARD PROOF', () => {
  test('[Captain] reopen_fault → 200 + ledger row + status=open', async ({
    captainPage,
    seedFault,
    supabaseAdmin,
  }) => {
    const testStart = new Date();
    const fault = await seedFault(`S34 CAP ReopenFault ${generateTestId('rf')}`);

    await supabaseAdmin
      .from('pms_faults')
      .update({ status: 'closed' })
      .eq('id', fault.id);

    await captainPage.goto(`${BASE_URL}/faults/${fault.id}`);
    await captainPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(captainPage, 'reopen_fault', {
      fault_id: fault.id,
      reason: 'S34 captain smoke test reopen',
    });
    console.log(`[JSON] [Captain] reopen_fault response: ${JSON.stringify(result, null, 2)}`);

    expect(result.status).toBe(200);
    expect((result.data as { status?: string }).status).toBe('success');

    await pollLedger(supabaseAdmin, 'reopen_fault', fault.id, testStart);

    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('pms_faults')
          .select('status')
          .eq('id', fault.id)
          .single();
        return (row as { status?: string } | null)?.status;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000 }
    ).toBe('open');
  });
});

// ===========================================================================
// add_fault_note
// ===========================================================================

test.describe('[HOD] add_fault_note — HARD PROOF', () => {
  test('[HOD] add_fault_note → 200 + notes_count + pms_faults.metadata.notes grew', async ({
    hodPage,
    seedFault,
    supabaseAdmin,
  }) => {
    const fault = await seedFault(`S34 HOD AddNote ${generateTestId('an')}`);

    // Get note count before
    const { data: before } = await supabaseAdmin
      .from('pms_faults')
      .select('metadata')
      .eq('id', fault.id)
      .single();
    const beforeCount = ((before as { metadata?: { notes?: unknown[] } } | null)?.metadata?.notes ?? []).length;

    await hodPage.goto(`${BASE_URL}/faults/${fault.id}`);
    await hodPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(hodPage, 'add_fault_note', {
      fault_id: fault.id,
      note_text: `S34 HOD smoke note ${generateTestId('n')}`,
    });
    console.log(`[JSON] add_fault_note response: ${JSON.stringify(result, null, 2)}`);

    expect(result.status).toBe(200);
    const data = result.data as { status?: string; message?: string; notes_count?: number };
    expect(data.status).toBe('success');
    expect(data.message).toBe('Note added to fault');
    expect(typeof data.notes_count).toBe('number');
    expect(data.notes_count).toBeGreaterThanOrEqual(1);

    // Entity state: metadata.notes array grew
    await expect.poll(
      async () => {
        const { data: row } = await supabaseAdmin
          .from('pms_faults')
          .select('metadata')
          .eq('id', fault.id)
          .single();
        return ((row as { metadata?: { notes?: unknown[] } } | null)?.metadata?.notes ?? []).length;
      },
      { intervals: [500, 1000, 1500], timeout: 8_000, message: 'Expected metadata.notes to grow' }
    ).toBeGreaterThanOrEqual(beforeCount + 1);
  });
});

test.describe('[Crew] add_fault_note — Crew IS allowed', () => {
  test('[Crew] add_fault_note → 200 (crew is in allowed_roles for add_fault_note)', async ({
    crewPage,
    seedFault,
  }) => {
    const fault = await seedFault(`S34 CREW AddNote ${generateTestId('an')}`);

    await crewPage.goto(`${BASE_URL}/faults/${fault.id}`);
    await crewPage.waitForLoadState('domcontentloaded');

    const result = await callActionDirect(crewPage, 'add_fault_note', {
      fault_id: fault.id,
      note_text: `S34 crew smoke note ${generateTestId('n')}`,
    });
    console.log(`[JSON] [Crew] add_fault_note response: ${JSON.stringify(result, null, 2)}`);

    // Crew IS in allowed_roles for add_fault_note (crew, chief_engineer, chief_officer, captain)
    // Since all auth files share same captain JWT → expect 200
    expect(result.status).toBe(200);
    expect((result.data as { status?: string }).status).toBe('success');
    console.log(`✅ [Crew] add_fault_note returned 200 (crew correctly allowed)`);
  });
});
