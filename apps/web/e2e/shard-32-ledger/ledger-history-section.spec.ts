// apps/web/e2e/shard-32-ledger/ledger-history-section.spec.ts

import { test, expect, generateTestId } from '../rbac-fixtures';

/**
 * SHARD 32: Ledger — HistorySection on entity detail pages
 *
 * Pass criteria:
 * - Entity detail pages load without crash (title visible, no error state)
 * - Read beacon POST fires within 30s of page load (intercepted by Playwright)
 * - HistorySection <h2>History</h2> renders exactly when events exist
 */

const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:3000';

test.describe('HistorySection renders on entity detail pages', () => {
  test.use({ storageState: './playwright/.auth/hod.json' });

  test('work-order detail page: entity loads without crash (no error state)', async ({
    hodPage,
    seedWorkOrder,
  }) => {
    const wo = await seedWorkOrder(`WO Load Test ${generateTestId('load')}`);

    await hodPage.goto(`${BASE_URL}/work-orders/${wo.id}`);
    await hodPage.waitForLoadState('networkidle');

    // Page must show the WO title (WorkOrderContent mounted), not an error
    await expect(
      hodPage.getByRole('heading', { name: wo.title, exact: true }).first()
    ).toBeVisible({ timeout: 15_000 });

    // No crash states
    await expect(hodPage.getByText('Failed to Load').first()).not.toBeVisible();
    await expect(hodPage.getByText('Work Order Not Found').first()).not.toBeVisible();
  });

  test('fault detail page: entity loads without crash (no error state)', async ({
    hodPage,
    seedFault,
  }) => {
    const fault = await seedFault(`Fault Load Test ${generateTestId('load')}`);

    await hodPage.goto(`${BASE_URL}/faults/${fault.id}`);
    await hodPage.waitForLoadState('networkidle');

    await expect(
      hodPage.getByRole('heading', { name: fault.title, exact: true }).first()
    ).toBeVisible({ timeout: 15_000 });

    await expect(hodPage.getByText('Failed to Load').first()).not.toBeVisible();
  });

  test('work-order detail page: read beacon fires on mount', async ({
    hodPage,
    seedWorkOrder,
  }) => {
    const wo = await seedWorkOrder(`Beacon Test WO ${generateTestId('bcn')}`);

    // Watch for the beacon response (fires-and-forgets, but Playwright catches it)
    const beaconResponsePromise = hodPage.waitForResponse(
      (res) =>
        res.url().includes('/v1/ledger/read-event') && res.request().method() === 'POST',
      { timeout: 30_000 }
    );

    // NOTE: avoid waitForLoadState('networkidle') — AuthContext bootstrap retries
    // keep the network busy for up to 30s, which would timeout before the beacon promise.
    await hodPage.goto(`${BASE_URL}/work-orders/${wo.id}`);

    const beaconRes = await beaconResponsePromise;
    const req = beaconRes.request();
    const body = req.postDataJSON();

    expect(body).toHaveProperty('entity_type', 'work_order');
    expect(body).toHaveProperty('entity_id', wo.id);

    // Auth header must be Bearer JWT
    const authHeader = req.headers()['authorization'];
    expect(authHeader).toMatch(/^Bearer eyJ/);

    // Beacon must succeed
    expect(beaconRes.status()).toBe(200);
  });

  test('fault detail page: read beacon fires with correct entity_type', async ({
    hodPage,
    seedFault,
  }) => {
    const fault = await seedFault(`Beacon Test Fault ${generateTestId('bcn')}`);

    const beaconResponsePromise = hodPage.waitForResponse(
      (res) =>
        res.url().includes('/v1/ledger/read-event') && res.request().method() === 'POST',
      { timeout: 30_000 }
    );

    // Avoid networkidle — bootstrap retries keep network busy
    await hodPage.goto(`${BASE_URL}/faults/${fault.id}`);

    const beaconRes = await beaconResponsePromise;
    const body = beaconRes.request().postDataJSON();
    expect(body.entity_type).toBe('fault');
    expect(body.entity_id).toBe(fault.id);
    expect(beaconRes.status()).toBe(200);
  });

  test('HistorySection <h2>History</h2> renders when events exist for entity', async ({
    hodPage,
    supabaseAdmin,
    seedWorkOrder,
  }) => {
    const wo = await seedWorkOrder(`Ledger Row Test WO ${generateTestId('row')}`);

    const YACHT_ID = process.env.TEST_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';

    // Insert a ledger event via service role to make history.length > 0
    await supabaseAdmin.from('ledger_events').insert({
      yacht_id: YACHT_ID,
      user_id: '00000000-0000-0000-0000-000000000001',
      user_role: 'captain',
      actor_name: 'Test Suite',
      department: 'deck',
      event_category: 'mutation',
      event_type: 'create',
      action: 'create_work_order',
      entity_type: 'work_order',
      entity_id: wo.id,
      change_summary: 'Work order created by test suite',
      source_context: 'microaction',
      proof_hash: 'test-hash-' + wo.id,
    });

    // Register waitForResponse BEFORE navigating — the by-entity fetch fires during page load
    // Avoid networkidle: bootstrap retries keep the network busy for 30s
    const byEntityPromise = hodPage.waitForResponse(
      (res) =>
        res.url().includes('/v1/ledger/events/by-entity/work_order/') &&
        res.status() === 200,
      { timeout: 20_000 }
    );

    await hodPage.goto(`${BASE_URL}/work-orders/${wo.id}`);
    await byEntityPromise;

    // History section heading must be exactly "History" (h2 from SectionContainer)
    // Using exact:true to avoid matching WO title which may contain "History"
    await expect(
      hodPage.getByRole('heading', { name: 'History', exact: true })
    ).toBeVisible({ timeout: 10_000 });
  });
});
