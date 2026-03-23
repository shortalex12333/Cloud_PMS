import { test, expect, RBAC_CONFIG } from '../rbac-fixtures';

/**
 * SHARD 48: Attention System + Filtered List Views
 *
 * Tests the SmartPointers two-phase rendering, FilterBar on list pages,
 * and direct Supabase data loading (no Python backend dependency).
 *
 * Uses captain (x@alex-short.com) which sees all domains.
 */

const ROUTES = {
  home: '/',
  faults: '/faults',
  workOrders: '/work-orders',
  equipment: '/equipment',
  inventory: '/inventory',
  receiving: '/receiving',
  shoppingList: '/shopping-list',
  certificates: '/certificates',
};

// ─── SmartPointers: Two-Phase Rendering ───────────────────────────────────────

test.describe('SmartPointers — Attention System', () => {
  test('homepage loads with attention items (collapsed view)', async ({ captainPage }) => {
    await captainPage.goto(ROUTES.home);
    await captainPage.waitForLoadState('networkidle');

    // "Needs your attention" header should be visible
    const header = captainPage.locator('text=Needs your attention');
    await expect(header).toBeVisible({ timeout: 15_000 });

    // Should show max 5 deduped items in collapsed mode
    const rows = captainPage.locator('[role="button"]').filter({ has: captainPage.locator('svg') });
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);
    expect(count).toBeLessThanOrEqual(6); // 5 items + possible "View all" button
  });

  test('View all expands to full list, Show less collapses', async ({ captainPage }) => {
    await captainPage.goto(ROUTES.home);
    await captainPage.waitForLoadState('networkidle');

    const viewAll = captainPage.locator('text=/View all \\(\\d+\\)/');
    const showLess = captainPage.locator('text=Show less');

    // If "View all" exists, there are more items than the deduped summary
    if (await viewAll.isVisible({ timeout: 10_000 }).catch(() => false)) {
      await viewAll.click();

      // After expanding, "Show less" should appear
      await expect(showLess).toBeVisible({ timeout: 5_000 });

      // Click "Show less" to collapse
      await showLess.click();
      await expect(viewAll).toBeVisible({ timeout: 5_000 });
    }
  });

  test('clicking attention item navigates to detail page', async ({ captainPage }) => {
    await captainPage.goto(ROUTES.home);
    await captainPage.waitForLoadState('networkidle');

    // Wait for attention items
    const header = captainPage.locator('text=Needs your attention');
    await expect(header).toBeVisible({ timeout: 15_000 });

    // Find the first clickable attention item (has role="button" and contains entity info)
    const firstItem = captainPage.locator('[role="button"]').filter({
      has: captainPage.locator('div[style*="fontSize"]'),
    }).first();

    if (await firstItem.isVisible({ timeout: 5_000 }).catch(() => false)) {
      const initialUrl = captainPage.url();
      await firstItem.click();

      // Should navigate away from homepage
      await captainPage.waitForURL((url) => url.pathname !== '/', { timeout: 10_000 });
      const newUrl = captainPage.url();
      expect(newUrl).not.toBe(initialUrl);
    }
  });
});

// ─── Filtered List Pages: Data Loading ────────────────────────────────────────

test.describe('Filtered List Pages — Direct Supabase Loading', () => {
  test.describe.configure({ retries: 1 });

  test('faults list loads with filter bar', async ({ captainPage }) => {
    await captainPage.goto(ROUTES.faults);
    await captainPage.waitForLoadState('networkidle');

    // Filter bar should be present with Status and Severity dropdowns
    const statusFilter = captainPage.locator('button', { hasText: 'Status' }).first();
    await expect(statusFilter).toBeVisible({ timeout: 15_000 });

    const severityFilter = captainPage.locator('button', { hasText: 'Severity' }).first();
    await expect(severityFilter).toBeVisible({ timeout: 5_000 });

    // Wait for loading spinner to disappear (data loaded or errored)
    await captainPage.waitForTimeout(3_000);

    // Should not still be loading
    const loading = captainPage.locator('text=Loading...');
    await expect(loading).not.toBeVisible({ timeout: 10_000 });
  });

  test('work orders list loads with filter bar', async ({ captainPage }) => {
    await captainPage.goto(ROUTES.workOrders);
    await captainPage.waitForLoadState('networkidle');

    await expect(captainPage.locator('text=Failed to load items')).not.toBeVisible({ timeout: 10_000 });

    // Filter bar with Priority dropdown
    const priorityFilter = captainPage.locator('text=Priority').first();
    await expect(priorityFilter).toBeVisible({ timeout: 10_000 });
  });

  test('equipment list loads with filter bar', async ({ captainPage }) => {
    await captainPage.goto(ROUTES.equipment);
    await captainPage.waitForLoadState('networkidle');

    await expect(captainPage.locator('text=Failed to load items')).not.toBeVisible({ timeout: 10_000 });

    // Filter bar with Criticality dropdown
    const critFilter = captainPage.locator('text=Criticality').first();
    await expect(critFilter).toBeVisible({ timeout: 10_000 });
  });

  test('inventory list loads with filter bar', async ({ captainPage }) => {
    await captainPage.goto(ROUTES.inventory);
    await captainPage.waitForLoadState('networkidle');

    await expect(captainPage.locator('text=Failed to load items')).not.toBeVisible({ timeout: 10_000 });

    // Filter bar with Stock dropdown
    const stockFilter = captainPage.locator('text=Stock').first();
    await expect(stockFilter).toBeVisible({ timeout: 10_000 });
  });

  test('receiving list loads with filter bar', async ({ captainPage }) => {
    await captainPage.goto(ROUTES.receiving);
    await captainPage.waitForLoadState('networkidle');

    await expect(captainPage.locator('text=Failed to load items')).not.toBeVisible({ timeout: 10_000 });
  });

  test('shopping list loads with filter bar', async ({ captainPage }) => {
    await captainPage.goto(ROUTES.shoppingList);
    await captainPage.waitForLoadState('networkidle');

    await expect(captainPage.locator('text=Failed to load items')).not.toBeVisible({ timeout: 10_000 });

    // Urgency filter
    const urgencyFilter = captainPage.locator('text=Urgency').first();
    await expect(urgencyFilter).toBeVisible({ timeout: 10_000 });
  });

  test('certificates list loads (already Supabase-direct)', async ({ captainPage }) => {
    await captainPage.goto(ROUTES.certificates);
    await captainPage.waitForLoadState('networkidle');

    await expect(captainPage.locator('text=Failed to load')).not.toBeVisible({ timeout: 10_000 });
  });
});

// ─── Filter Interactions ──────────────────────────────────────────────────────

test.describe('Filter Bar — Interactions', () => {
  test('faults: status filter works', async ({ captainPage }) => {
    await captainPage.goto(ROUTES.faults);
    await captainPage.waitForLoadState('networkidle');

    // Click the Status dropdown
    const statusBtn = captainPage.locator('button', { hasText: 'Status' }).first();
    await expect(statusBtn).toBeVisible({ timeout: 10_000 });
    await statusBtn.click();

    // Select "Open" from dropdown
    const openOption = captainPage.locator('button', { hasText: 'Open' }).first();
    await expect(openOption).toBeVisible({ timeout: 5_000 });
    await openOption.click();

    // Active filter pill should appear
    const pill = captainPage.locator('text=Status: Open');
    await expect(pill).toBeVisible({ timeout: 5_000 });

    // Items should reflect the filter (no error state)
    await expect(captainPage.locator('text=Failed to load items')).not.toBeVisible({ timeout: 5_000 });
  });

  test('work orders: priority filter works', async ({ captainPage }) => {
    await captainPage.goto(ROUTES.workOrders);
    await captainPage.waitForLoadState('networkidle');

    // Click Priority dropdown
    const priorityBtn = captainPage.locator('button', { hasText: 'Priority' }).first();
    await expect(priorityBtn).toBeVisible({ timeout: 10_000 });
    await priorityBtn.click();

    // Select "Critical"
    const criticalOption = captainPage.locator('button', { hasText: 'Critical' }).first();
    await expect(criticalOption).toBeVisible({ timeout: 5_000 });
    await criticalOption.click();

    // Active filter pill
    const pill = captainPage.locator('text=Priority: Critical');
    await expect(pill).toBeVisible({ timeout: 5_000 });
  });

  test('clear all filters resets the view', async ({ captainPage }) => {
    await captainPage.goto(ROUTES.faults);
    await captainPage.waitForLoadState('networkidle');

    // Apply a filter first
    const statusBtn = captainPage.locator('button', { hasText: 'Status' }).first();
    await expect(statusBtn).toBeVisible({ timeout: 10_000 });
    await statusBtn.click();
    const closedOption = captainPage.locator('button', { hasText: 'Closed' }).first();
    await expect(closedOption).toBeVisible({ timeout: 5_000 });
    await closedOption.click();

    // "Clear all" button should appear
    const clearAll = captainPage.locator('text=Clear all');
    await expect(clearAll).toBeVisible({ timeout: 5_000 });

    // Click clear all
    await clearAll.click();

    // Filter pill should disappear
    await expect(captainPage.locator('text=Status: Closed')).not.toBeVisible({ timeout: 5_000 });
  });
});

// ─── Item Count Display ───────────────────────────────────────────────────────

test.describe('Item Count Display', () => {
  test('work orders page shows item count after load', async ({ captainPage }) => {
    await captainPage.goto(ROUTES.workOrders);
    await captainPage.waitForLoadState('networkidle');

    // Wait for data to load (spinner disappears)
    const loading = captainPage.locator('text=Loading...');
    await expect(loading).not.toBeVisible({ timeout: 15_000 });

    // The filter bar should show "N item(s)" count if there are items
    const countLabel = captainPage.locator('span', { hasText: /^\d+ items?$/ }).first();
    const noItems = captainPage.locator('text=No work orders found');

    const hasCount = await countLabel.isVisible({ timeout: 5_000 }).catch(() => false);
    const hasEmpty = await noItems.isVisible({ timeout: 2_000 }).catch(() => false);
    // One of these should be true
    expect(hasCount || hasEmpty).toBe(true);
  });
});

// ─── Navigation from Attention to List ────────────────────────────────────────

test.describe('Pill Strip Navigation', () => {
  test('pill strip navigates to list page', async ({ captainPage }) => {
    await captainPage.goto(ROUTES.home);
    await captainPage.waitForLoadState('networkidle');

    // LensPillStrip renders below SmartPointers — look for pill buttons
    // The pills have routes like /work-orders, /faults, etc.
    const woButton = captainPage.locator('text=/Work Orders|W\\/O/i').first();

    if (await woButton.isVisible({ timeout: 10_000 }).catch(() => false)) {
      await woButton.click();
      await captainPage.waitForURL('**/work-orders**', { timeout: 10_000 });
      expect(captainPage.url()).toContain('/work-orders');

      // Should load with filter bar (not error)
      await expect(captainPage.locator('text=Failed to load items')).not.toBeVisible({ timeout: 10_000 });
    }
  });
});
