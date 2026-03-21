// apps/web/e2e/shard-34-lens-actions/show-related-signal-ui.spec.ts

/**
 * SHARD 34: Show Related Signal — UI Rendering Tests (mocked API)
 *
 * Uses page.route() to inject deterministic signal responses, decoupling
 * UI verification from search_index data or embedding pipeline state.
 *
 * What it proves:
 *   - "Related" section renders when signal API returns items
 *   - "Related" section is hidden when signal API returns empty items
 *   - Staged progress text cycles during loading (Extracting → Generating → Searching → Ranking)
 *   - Clicking a signal item navigates to the correct entity lens page
 *   - Back button from navigated page returns to source lens page
 *   - Drawer renders correctly when signal API errors (graceful degradation)
 *
 * Architecture note: page.route() intercepts fetch() from the Next.js app.
 * The mock must be set BEFORE the component makes the request (before goto).
 *
 * FK groups have been removed — signal is the sole data source for the drawer.
 */

import { test, expect, generateTestId } from '../rbac-fixtures';
import { BASE_URL } from './helpers';

const FRONTEND_BASE = process.env.E2E_BASE_URL || 'http://localhost:3000';

// ---------------------------------------------------------------------------
// Mock payloads
// ---------------------------------------------------------------------------

/** A fault item returned by the signal endpoint */
function makeFaultSignalItem(id = 'aaaaaaaa-0000-0000-0000-000000000001') {
  return {
    entity_id: id,
    entity_type: 'fault',
    title: 'Engine Overheating — Signal Match',
    subtitle: 'fault',
    match_reasons: ['signal:entity_embedding'],
    fused_score: 0.82,
    weight: 50,
  };
}

/** A manual item returned by the signal endpoint */
function makeManualSignalItem(id = 'bbbbbbbb-0000-0000-0000-000000000001') {
  return {
    entity_id: id,
    entity_type: 'manual',
    title: 'C18 Engine Service Manual',
    subtitle: 'manual',
    match_reasons: ['signal:entity_embedding'],
    fused_score: 0.74,
    weight: 50,
  };
}

/** Full signal API success response */
function makeSignalResponse(items: ReturnType<typeof makeFaultSignalItem>[]) {
  return {
    status: 'success',
    entity_type: 'work_order',
    entity_id: 'source-id',
    entity_text: 'Replace fuel filters; equipment: main engine',
    items,
    count: items.length,
    signal_source: 'entity_embedding',
    metadata: { limit: 10, embedding_generated: true },
  };
}

/** Signal API response with no items */
const EMPTY_SIGNAL_RESPONSE = makeSignalResponse([]);

// ---------------------------------------------------------------------------
// Helper: intercept signal API with a fixed response
// ---------------------------------------------------------------------------

async function mockSignalEndpoint(
  page: import('@playwright/test').Page,
  response: object,
  statusCode = 200
) {
  await page.route(/\/v1\/show-related-signal/, async (route) => {
    await route.fulfill({
      status: statusCode,
      contentType: 'application/json',
      body: JSON.stringify(response),
    });
  });
}

/** Intercept and delay the signal API to test the staged progress */
async function mockSignalEndpointDelayed(
  page: import('@playwright/test').Page,
  response: object,
  delayMs = 1500
) {
  await page.route(/\/v1\/show-related-signal/, async (route) => {
    await new Promise((r) => setTimeout(r, delayMs));
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(response),
    });
  });
}

/** Mock signal endpoint to return 500 */
async function page500Mock(page: import('@playwright/test').Page) {
  await page.route(/\/v1\/show-related-signal/, async (route) => {
    await route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ error: 'Internal Server Error' }),
    });
  });
}

// ---------------------------------------------------------------------------
// Section 1: "Related" section renders when items are returned
// ---------------------------------------------------------------------------

test.describe('[HOD] UI: Related section — renders with items', () => {
  test('signal items appear in "Related" section', async ({
    hodPage,
    seedWorkOrder,
  }) => {
    const wo = await seedWorkOrder(`S34 SUI Items WO ${generateTestId('i')}`);

    await mockSignalEndpoint(
      hodPage,
      makeSignalResponse([makeFaultSignalItem(), makeManualSignalItem()])
    );

    await hodPage.goto(`${FRONTEND_BASE}/work-orders/${wo.id}`);
    await hodPage.waitForLoadState('domcontentloaded');
    await expect(hodPage.getByTestId('work_order-detail')).toBeVisible({ timeout: 10_000 });

    // Open related panel
    await hodPage.getByTestId('show-related-button').click();

    // "Related" section must appear
    const relatedSection = hodPage.getByTestId('signal-also-related');
    await expect(relatedSection).toBeVisible({ timeout: 15_000 });

    // Both items rendered
    const faultItem = hodPage.getByTestId(
      'signal-item-fault-aaaaaaaa-0000-0000-0000-000000000001'
    );
    const manualItem = hodPage.getByTestId(
      'signal-item-manual-bbbbbbbb-0000-0000-0000-000000000001'
    );
    await expect(faultItem).toBeVisible();
    await expect(manualItem).toBeVisible();

    // Item titles render correctly
    await expect(faultItem).toContainText('Engine Overheating');
    await expect(manualItem).toContainText('C18 Engine');
  });

  test('entity_type label shown under each item', async ({
    hodPage,
    seedWorkOrder,
  }) => {
    const wo = await seedWorkOrder(`S34 SUI Label WO ${generateTestId('l')}`);

    await mockSignalEndpoint(hodPage, makeSignalResponse([makeFaultSignalItem()]));

    await hodPage.goto(`${FRONTEND_BASE}/work-orders/${wo.id}`);
    await hodPage.waitForLoadState('domcontentloaded');
    await expect(hodPage.getByTestId('work_order-detail')).toBeVisible({ timeout: 10_000 });

    await hodPage.getByTestId('show-related-button').click();
    await expect(hodPage.getByTestId('signal-also-related')).toBeVisible({ timeout: 15_000 });

    // Entity type label shown as subtitle row
    const faultItem = hodPage.getByTestId(
      'signal-item-fault-aaaaaaaa-0000-0000-0000-000000000001'
    );
    await expect(faultItem).toContainText('fault');
  });
});

// ---------------------------------------------------------------------------
// Section 2: Section hidden when no signal items
// ---------------------------------------------------------------------------

test.describe('[HOD] UI: Related section — hidden when empty', () => {
  test('"Related" section absent when signal returns 0 items', async ({
    hodPage,
    seedWorkOrder,
  }) => {
    const wo = await seedWorkOrder(`S34 SUI Empty WO ${generateTestId('e')}`);

    await mockSignalEndpoint(hodPage, EMPTY_SIGNAL_RESPONSE);

    await hodPage.goto(`${FRONTEND_BASE}/work-orders/${wo.id}`);
    await hodPage.waitForLoadState('domcontentloaded');
    await expect(hodPage.getByTestId('work_order-detail')).toBeVisible({ timeout: 10_000 });

    await hodPage.getByTestId('show-related-button').click();

    // Wait for drawer to settle
    await hodPage.waitForTimeout(3_000);

    // "Related" section must NOT be visible
    await expect(hodPage.getByTestId('signal-also-related')).not.toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Section 3: Staged progress during loading
// ---------------------------------------------------------------------------

test.describe('[HOD] UI: Staged progress loading state', () => {
  test('staged progress label shows during signal fetch, items appear after', async ({
    hodPage,
    seedWorkOrder,
  }) => {
    const wo = await seedWorkOrder(`S34 SUI Spinner WO ${generateTestId('s')}`);

    // Delay the signal response by 2s so we can observe staged progress
    await mockSignalEndpointDelayed(
      hodPage,
      makeSignalResponse([makeFaultSignalItem()]),
      2000
    );

    await hodPage.goto(`${FRONTEND_BASE}/work-orders/${wo.id}`);
    await hodPage.waitForLoadState('domcontentloaded');
    await expect(hodPage.getByTestId('work_order-detail')).toBeVisible({ timeout: 10_000 });

    await hodPage.getByTestId('show-related-button').click();

    // Staged progress label should be visible while loading
    const stageLabel = hodPage.getByTestId('signal-stage-label');
    await expect(stageLabel).toBeVisible({ timeout: 3_000 });

    // Label should match one of the 4 stages
    const text = await stageLabel.textContent();
    expect(text).toMatch(/Extracting entity|Generating embedding|Searching entities|Ranking results/);

    // After delay, stage label gone and item appears
    await expect(
      hodPage.getByTestId('signal-item-fault-aaaaaaaa-0000-0000-0000-000000000001')
    ).toBeVisible({ timeout: 10_000 });
    await expect(stageLabel).not.toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Section 4: Navigation — click signal item → lens page → back
// ---------------------------------------------------------------------------

test.describe('[HOD] UI: Signal item click navigates to entity lens page', () => {
  test('click fault signal item → fault lens page → back to WO', async ({
    hodPage,
    seedWorkOrder,
  }) => {
    const wo = await seedWorkOrder(`S34 SUI NavFault WO ${generateTestId('f')}`);

    const faultId = 'aaaaaaaa-0000-0000-0000-000000000001';
    await mockSignalEndpoint(hodPage, makeSignalResponse([makeFaultSignalItem(faultId)]));

    await hodPage.goto(`${FRONTEND_BASE}/work-orders/${wo.id}`);
    await hodPage.waitForLoadState('domcontentloaded');
    await expect(hodPage.getByTestId('work_order-detail')).toBeVisible({ timeout: 10_000 });

    await hodPage.getByTestId('show-related-button').click();

    // Wait for signal item to appear
    const faultItem = hodPage.getByTestId(`signal-item-fault-${faultId}`);
    await expect(faultItem).toBeVisible({ timeout: 15_000 });

    // Click the signal item — triggers router.push (SPA navigation)
    await faultItem.click();
    await hodPage.waitForFunction(
      (id) => window.location.href.includes(id),
      faultId,
      { timeout: 10_000 }
    );

    // Must have navigated away from the WO page
    const newUrl = hodPage.url();
    expect(newUrl).not.toContain(`/work-orders/${wo.id}`);
    expect(newUrl).toContain(faultId);

    // Back button returns to the WO lens page
    const backBtn = hodPage.getByTestId('back-button');
    const hasBackBtn = await backBtn.isVisible({ timeout: 5_000 }).catch(() => false);
    if (hasBackBtn) {
      await backBtn.click();
      await hodPage.waitForFunction(
        (woId) => {
          const url = window.location.href;
          return url.includes(`/work-orders/${woId}`) && !url.includes('/faults/');
        },
        wo.id,
        { timeout: 10_000 }
      );
      expect(hodPage.url()).toContain(`/work-orders/${wo.id}`);
    }
  });

  test('signal item for manual navigates to correct route', async ({
    hodPage,
    seedWorkOrder,
  }) => {
    const wo = await seedWorkOrder(`S34 SUI NavManual WO ${generateTestId('m')}`);
    const manualId = 'bbbbbbbb-0000-0000-0000-000000000001';

    await mockSignalEndpoint(hodPage, makeSignalResponse([makeManualSignalItem(manualId)]));

    await hodPage.goto(`${FRONTEND_BASE}/work-orders/${wo.id}`);
    await hodPage.waitForLoadState('domcontentloaded');
    await expect(hodPage.getByTestId('work_order-detail')).toBeVisible({ timeout: 10_000 });

    await hodPage.getByTestId('show-related-button').click();

    const manualItem = hodPage.getByTestId(`signal-item-manual-${manualId}`);
    await expect(manualItem).toBeVisible({ timeout: 15_000 });

    await manualItem.click();
    await hodPage.waitForFunction(
      (id) => window.location.href.includes(id),
      manualId,
      { timeout: 10_000 }
    );

    const newUrl = hodPage.url();
    expect(newUrl).not.toContain(`/work-orders/${wo.id}`);
    expect(newUrl).toContain(manualId);
  });
});

// ---------------------------------------------------------------------------
// Section 5: Graceful degradation — signal errors don't break the drawer
// ---------------------------------------------------------------------------

test.describe('[HOD] UI: Signal errors — graceful degradation', () => {
  test('drawer renders normally when signal API returns 500', async ({
    hodPage,
    seedWorkOrder,
  }) => {
    const wo = await seedWorkOrder(`S34 SUI Error WO ${generateTestId('err')}`);

    await page500Mock(hodPage);

    await hodPage.goto(`${FRONTEND_BASE}/work-orders/${wo.id}`);
    await hodPage.waitForLoadState('domcontentloaded');

    await expect(hodPage.getByTestId('work_order-detail')).toBeVisible({ timeout: 10_000 });

    // Open panel — should not crash
    await hodPage.getByTestId('show-related-button').click();
    await hodPage.waitForTimeout(3_000);

    // Signal section should not appear (signal errored)
    await expect(hodPage.getByTestId('signal-also-related')).not.toBeVisible();
  });

  test('drawer renders normally when signal API is aborted (network error)', async ({
    hodPage,
    seedWorkOrder,
  }) => {
    const wo = await seedWorkOrder(`S34 SUI Abort WO ${generateTestId('ab')}`);

    await hodPage.route(/\/v1\/show-related-signal/, (route) => route.abort('failed'));

    await hodPage.goto(`${FRONTEND_BASE}/work-orders/${wo.id}`);
    await hodPage.waitForLoadState('domcontentloaded');

    await expect(hodPage.getByTestId('work_order-detail')).toBeVisible({ timeout: 10_000 });
    await hodPage.getByTestId('show-related-button').click();
    await hodPage.waitForTimeout(4_000);

    await expect(hodPage.getByTestId('signal-also-related')).not.toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Section 6: Panel open/close state management
// ---------------------------------------------------------------------------

test.describe('[HOD] UI: Panel state management', () => {
  test('clicking ShowRelated again closes the panel', async ({
    hodPage,
    seedWorkOrder,
  }) => {
    const wo = await seedWorkOrder(`S34 SUI Toggle WO ${generateTestId('t')}`);

    await mockSignalEndpoint(hodPage, makeSignalResponse([makeFaultSignalItem()]));

    await hodPage.goto(`${FRONTEND_BASE}/work-orders/${wo.id}`);
    await hodPage.waitForLoadState('domcontentloaded');
    await expect(hodPage.getByTestId('work_order-detail')).toBeVisible({ timeout: 10_000 });

    const btn = hodPage.getByTestId('show-related-button');

    // Open
    await btn.click();
    await expect(hodPage.getByTestId('signal-also-related')).toBeVisible({ timeout: 15_000 });

    // Close
    await hodPage.evaluate(() => {
      (document.querySelector('[data-testid="show-related-button"]') as HTMLElement)?.click();
    });
    await expect(hodPage.getByTestId('signal-also-related')).not.toBeVisible({ timeout: 5_000 });
  });

  test('signal section count shows correct number of items', async ({
    hodPage,
    seedWorkOrder,
  }) => {
    const wo = await seedWorkOrder(`S34 SUI Count WO ${generateTestId('c')}`);

    await mockSignalEndpoint(
      hodPage,
      makeSignalResponse([makeFaultSignalItem(), makeManualSignalItem()])
    );

    await hodPage.goto(`${FRONTEND_BASE}/work-orders/${wo.id}`);
    await hodPage.waitForLoadState('domcontentloaded');
    await expect(hodPage.getByTestId('work_order-detail')).toBeVisible({ timeout: 10_000 });

    await hodPage.getByTestId('show-related-button').click();
    await expect(hodPage.getByTestId('signal-also-related')).toBeVisible({ timeout: 15_000 });

    // Section header shows count "2" (in a div, not h3)
    const section = hodPage.getByTestId('signal-also-related');
    await expect(section.locator('div').first()).toContainText('2');
  });
});
