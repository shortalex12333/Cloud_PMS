// apps/web/e2e/shard-32-ledger/ledger-read-beacon.spec.ts

import { test, expect, generateTestId } from '../rbac-fixtures';

/**
 * SHARD 32: Ledger — Read beacon DB verification
 *
 * The useReadBeacon hook fires POST /v1/ledger/read-event on every entity page mount.
 * This test verifies the event is actually written to ledger_events in Supabase.
 *
 * Strategy:
 * 1. Seed a fresh work order (guaranteed unique entity_id, 0 existing read events)
 * 2. Navigate to /work-orders/{id} — triggers useReadBeacon
 * 3. Intercept the beacon RESPONSE (30s timeout — entity fetch + React effects)
 * 4. Wait 3s for async DB write
 * 5. Count ledger rows AFTER — expect >= 1 with event_category='read'
 *
 * Uses supabaseAdmin fixture (service role — bypasses RLS).
 */

const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:3000';

test.describe('Read beacon DB persistence', () => {
  test.use({ storageState: './playwright/.auth/hod.json' });

  test('navigating to work-order page writes event_category=read row to ledger_events', async ({
    hodPage,
    seedWorkOrder,
    supabaseAdmin,
  }) => {
    const wo = await seedWorkOrder(`Beacon DB Test ${generateTestId('db')}`);

    // 1. Pre-navigation count — should be 0 for this brand-new entity
    const { count: beforeCount, error: beforeErr } = await supabaseAdmin
      .from('ledger_events')
      .select('*', { count: 'exact', head: true })
      .eq('entity_id', wo.id)
      .eq('event_category', 'read');

    if (beforeErr) throw new Error(`Pre-count query failed: ${beforeErr.message}`);
    console.log(`Before navigation: ${beforeCount} read events for WO ${wo.id}`);
    expect(beforeCount).toBe(0);

    // 2. Watch for beacon RESPONSE before navigating
    const beaconResponsePromise = hodPage.waitForResponse(
      (res) =>
        res.url().includes('/v1/ledger/read-event') && res.request().method() === 'POST',
      { timeout: 30_000 }
    );

    // 3. Navigate (triggers useReadBeacon on mount)
    // Avoid networkidle — AuthContext bootstrap retries keep network busy for 30s
    await hodPage.goto(`${BASE_URL}/work-orders/${wo.id}`);

    // 4. Verify beacon request fired with correct body
    const beaconRes = await beaconResponsePromise;
    const req = beaconRes.request();
    const body = req.postDataJSON();
    expect(body.entity_type).toBe('work_order');
    expect(body.entity_id).toBe(wo.id);
    expect(req.headers()['authorization']).toMatch(/^Bearer eyJ/);
    console.log(`Beacon fired: ${JSON.stringify(body)}`);
    expect(beaconRes.status()).toBe(200);

    // 5. Poll for DB write — replaces fixed sleep with adaptive polling (max 8s, 500ms intervals)
    await expect.poll(
      async () => {
        const { count } = await supabaseAdmin
          .from('ledger_events')
          .select('*', { count: 'exact', head: true })
          .eq('entity_id', wo.id)
          .eq('event_category', 'read');
        const current = count ?? 0;
        console.log(`After navigation: ${current} read events for WO ${wo.id}`);
        return current;
      },
      { intervals: [500, 1000, 1500, 2000], timeout: 8_000, message: 'Expected read beacon row in DB within 8s' }
    ).toBeGreaterThanOrEqual((beforeCount || 0) + 1);
    console.log(`✅ Read beacon created ledger_events row(s) with event_category=read`);
  });

  test('read beacon row has correct fields stamped (user_role, department, proof_hash)', async ({
    hodPage,
    seedWorkOrder,
    supabaseAdmin,
  }) => {
    const wo = await seedWorkOrder(`Beacon Fields Test ${generateTestId('fld')}`);

    const beaconResponsePromise = hodPage.waitForResponse(
      (res) =>
        res.url().includes('/v1/ledger/read-event') && res.request().method() === 'POST',
      { timeout: 30_000 }
    );

    // Avoid networkidle — AuthContext bootstrap retries keep network busy for 30s
    await hodPage.goto(`${BASE_URL}/work-orders/${wo.id}`);

    // Wait for beacon to complete
    await beaconResponsePromise;

    // Poll for DB write — replaces fixed 3s sleep
    let row: {
      user_role: string;
      department: string | null;
      proof_hash: string;
      event_category: string;
      source_context: string;
      action: string;
    } | null = null;

    await expect.poll(
      async () => {
        const { data: rows } = await supabaseAdmin
          .from('ledger_events')
          .select('user_role, department, proof_hash, event_category, source_context, action')
          .eq('entity_id', wo.id)
          .eq('event_category', 'read')
          .limit(1);
        row = rows?.[0] ?? null;
        return !!row;
      },
      { intervals: [500, 1000, 1500, 2000], timeout: 8_000, message: 'Expected read event row in DB within 8s' }
    ).toBe(true);

    const r = row!; // guaranteed non-null by poll above
    console.log(`DB row: ${JSON.stringify(r)}`);

    expect(r.event_category).toBe('read');
    expect(r.source_context).toBe('microaction');
    // Strengthen proof_hash: must be a non-trivial string (SHA-256 hex = 64 chars)
    expect(r.proof_hash.length).toBeGreaterThan(8);
    // Strengthen user_role: must be a known valid role enum value
    expect(['captain', 'hod', 'chief_engineer', 'eto', 'crew', 'manager', 'interior']).toContain(r.user_role);
    // C: department was SELECTed but never asserted — assert it is stamped
    expect(r.department).toBeTruthy();
    // action should be view_work_order (format: `view_{entity_type}`)
    expect(r.action).toBe('view_work_order');
  });
});
