// apps/web/e2e/shard-33-lens-actions/inventory-actions.spec.ts

import { test, expect, RBAC_CONFIG } from '../rbac-fixtures';
import { BASE_URL, callAction, assertNoRenderCrash } from './helpers';

/**
 * SHARD 33: Lens Actions — Inventory (3 roles)
 *
 * check_stock_level is a READ action — all roles including "crew" are allowed.
 * No DB write occurs; the test verifies the action router and inventory
 * handler are wired correctly via the response JSON structure.
 *
 * Uses getExistingPart (read-only fixture, no insert).
 */

// ---------------------------------------------------------------------------
// HOD role
// ---------------------------------------------------------------------------
test.describe('[HOD] Inventory lens actions', () => {
  test('renders inventory detail without crash', async ({
    hodPage,
    getExistingPart,
  }) => {
    const part = await getExistingPart();

    await hodPage.goto(`${BASE_URL}/inventory/${part.id}`);
    await hodPage.waitForLoadState('domcontentloaded');

    await expect(hodPage.getByRole('heading', { name: part.name, exact: true }).first())
      .toBeVisible({ timeout: 15_000 });
    await assertNoRenderCrash(hodPage);
  });

  test('[HOD] check_stock_level → 200 + valid stock_status in JSON', async ({
    hodPage,
    getExistingPart,
  }) => {
    const part = await getExistingPart();

    // STEP 1
    await hodPage.goto(`${BASE_URL}/inventory/${part.id}`);
    await hodPage.waitForLoadState('domcontentloaded');
    await assertNoRenderCrash(hodPage);

    // STEP 2 — READ action via API (no UI button for check_stock_level)
    const result = await callAction(hodPage, 'check_stock_level', { part_id: part.id });

    // STEP 3 — frontend JSON validation
    // Response: { status:'success', action:'check_stock_level', result:{ stock:{ stock_status, ... } } }
    expect(result.status).toBe(200);
    expect((result.data as { status?: string }).status).toBe('success');

    const stockData = (result.data as { result?: { stock?: { stock_status?: string; quantity_on_hand?: number } } }).result?.stock;
    expect(stockData?.stock_status).toBeTruthy();
    expect(['IN_STOCK', 'LOW_STOCK', 'OUT_OF_STOCK', 'OVERSTOCKED']).toContain(stockData?.stock_status);
    console.log(`✅ HOD check_stock_level: part=${part.name}, status=${stockData?.stock_status}, qty=${stockData?.quantity_on_hand}`);
  });
});

// ---------------------------------------------------------------------------
// Captain role
// ---------------------------------------------------------------------------
test.describe('[Captain] Inventory lens actions', () => {
  test('renders inventory detail without crash', async ({
    captainPage,
    getExistingPart,
  }) => {
    const part = await getExistingPart();

    await captainPage.goto(`${BASE_URL}/inventory/${part.id}`);
    await captainPage.waitForLoadState('domcontentloaded');

    await expect(captainPage.getByRole('heading', { name: part.name, exact: true }).first())
      .toBeVisible({ timeout: 15_000 });
    await assertNoRenderCrash(captainPage);
  });

  test('[Captain] check_stock_level → 200 + valid stock_status', async ({
    captainPage,
    getExistingPart,
  }) => {
    const part = await getExistingPart();

    await captainPage.goto(`${BASE_URL}/inventory/${part.id}`);
    await captainPage.waitForLoadState('domcontentloaded');
    await assertNoRenderCrash(captainPage);

    const result = await callAction(captainPage, 'check_stock_level', { part_id: part.id });

    expect(result.status).toBe(200);
    expect((result.data as { status?: string }).status).toBe('success');

    const stockData2 = (result.data as { result?: { stock?: { stock_status?: string } } }).result?.stock;
    expect(['IN_STOCK', 'LOW_STOCK', 'OUT_OF_STOCK', 'OVERSTOCKED']).toContain(stockData2?.stock_status);
    console.log(`✅ Captain check_stock_level: part=${part.name}, status=${stockData2?.stock_status}`);
  });
});

// ---------------------------------------------------------------------------
// Crew role — check_stock_level is open to all roles including crew
// ---------------------------------------------------------------------------
test.describe('[Crew] Inventory lens actions', () => {
  test('renders inventory page without 500 crash', async ({
    crewPage,
    getExistingPart,
  }) => {
    const part = await getExistingPart();

    await crewPage.goto(`${BASE_URL}/inventory/${part.id}`);
    await crewPage.waitForLoadState('domcontentloaded');

    await expect(crewPage.getByText('500', { exact: true }).first()).not.toBeVisible({ timeout: 10_000 });
  });

  test('[Crew] check_stock_level → 200 (read action, all roles permitted)', async ({
    crewPage,
    getExistingPart,
  }) => {
    const part = await getExistingPart();

    await crewPage.goto(`${BASE_URL}/inventory/${part.id}`);
    await crewPage.waitForLoadState('domcontentloaded');

    // check_stock_level allows "crew" — expect 200, not 403
    const result = await callAction(crewPage, 'check_stock_level', { part_id: part.id });

    expect(result.status).toBe(200);
    expect((result.data as { status?: string }).status).toBe('success');

    const stockData3 = (result.data as { result?: { stock?: { stock_status?: string } } }).result?.stock;
    expect(['IN_STOCK', 'LOW_STOCK', 'OUT_OF_STOCK', 'OVERSTOCKED']).toContain(stockData3?.stock_status);
    console.log(`✅ Crew check_stock_level: part=${part.name}, status=${stockData3?.stock_status}`);
  });
});
