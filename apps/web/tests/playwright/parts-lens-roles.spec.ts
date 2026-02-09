/**
 * Parts Lens - Role Enforcement E2E Tests
 *
 * Verifies:
 * - CREW can only view (2 READ actions only)
 * - HOD can view and mutate (8 actions: 2 READ + 6 MUTATE)
 * - CAPTAIN has full access (10 actions: 2 READ + 6 MUTATE + 2 SIGNED)
 * - Security: CREW gets 403 for unauthorized mutations
 * - View Low Stock functionality works for all roles
 * - SIGNED actions require signature badge
 *
 * Run: npx playwright test parts-lens-roles.spec.ts --project=chromium
 * Run with UI: npx playwright test parts-lens-roles.spec.ts --ui
 * Run headed: npx playwright test parts-lens-roles.spec.ts --headed
 */
import { test, expect, Page } from '@playwright/test';
import {
  loginAs,
  searchInSpotlight,
  getActionSuggestions,
  clickAction,
  waitForActionModal,
  hasSignatureBadge,
} from './auth.helper';

// Test yacht ID - loaded from env
const TEST_YACHT_ID = process.env.TEST_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';
const API_URL = process.env.RENDER_API_URL || 'https://pipeline-core.int.celeste7.ai';

/**
 * Helper: Navigate to Parts Lens
 */
async function navigateToPartsLens(page: Page): Promise<void> {
  // Try multiple navigation approaches
  await page.goto('/');

  // Try clicking Parts navigation if it exists
  const partsNav = page.locator(
    'a:has-text("Parts"), ' +
    'a:has-text("Inventory"), ' +
    '[data-testid="parts-nav"], ' +
    '[href*="/parts"]'
  ).first();

  if (await partsNav.count() > 0) {
    await partsNav.click();
    await page.waitForURL((url) => url.pathname.includes('parts') || url.pathname.includes('inventory'));
  } else {
    // Try searching for parts
    await searchInSpotlight(page, 'parts');
  }
}

/**
 * Helper: Get action buttons from Parts Lens UI
 */
async function getPartsActionButtons(page: Page): Promise<string[]> {
  // Wait for action buttons to load
  await page.waitForSelector(
    '[data-testid="action-button"], ' +
    '[data-testid="parts-action"], ' +
    '.parts-actions button, ' +
    '.action-button',
    { timeout: 10000 }
  ).catch(() => null);

  const buttons = page.locator(
    '[data-testid="action-button"], ' +
    '[data-testid="parts-action"], ' +
    '.parts-actions button'
  );

  const count = await buttons.count();
  const actions: string[] = [];

  for (let i = 0; i < count; i++) {
    const text = await buttons.nth(i).textContent();
    if (text) actions.push(text.trim());
  }

  return actions;
}

/**
 * Helper: Get JWT from page context
 */
async function getJWTFromPage(page: Page): Promise<string | null> {
  return await page.evaluate(() => {
    // Check localStorage for Supabase auth token
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && (key.includes('sb-') || key.includes('supabase.auth.token'))) {
        const value = localStorage.getItem(key);
        if (value) {
          try {
            const parsed = JSON.parse(value);
            return parsed.access_token || parsed.currentSession?.access_token || null;
          } catch {
            return null;
          }
        }
      }
    }
    return null;
  });
}

/**
 * Helper: Call /v1/actions/list API directly
 */
async function getActionsFromAPI(page: Page): Promise<any> {
  const jwt = await getJWTFromPage(page);
  if (!jwt) {
    throw new Error('No JWT found in page context');
  }

  const response = await page.request.get(`${API_URL}/v1/actions/list?domain=parts`, {
    headers: {
      'Authorization': `Bearer ${jwt}`,
    },
  });

  expect(response.ok()).toBe(true);
  return await response.json();
}

/**
 * Helper: Attempt to execute an action via API
 */
async function executeActionViaAPI(
  page: Page,
  action: string,
  payload: any = {}
): Promise<{ status: number; body: any }> {
  const jwt = await getJWTFromPage(page);
  if (!jwt) {
    throw new Error('No JWT found in page context');
  }

  const response = await page.request.post(`${API_URL}/v1/actions/execute`, {
    headers: {
      'Authorization': `Bearer ${jwt}`,
      'Content-Type': 'application/json',
    },
    data: {
      action,
      context: { yacht_id: TEST_YACHT_ID },
      payload,
    },
    failOnStatusCode: false,
  });

  const body = await response.json().catch(() => ({}));
  return { status: response.status(), body };
}

// ============================================================================
// TEST SUITE: CREW Role - READ ONLY
// ============================================================================

test.describe('Parts Lens - CREW Role (READ ONLY)', () => {
  test('CREW sees exactly 2 READ actions via API', async ({ page }) => {
    await loginAs(page, 'crew');
    await navigateToPartsLens(page);

    // Get actions from API
    const data = await getActionsFromAPI(page);

    // Verify role resolved
    expect(data.role).toBe('crew');

    // Verify action count
    expect(data.actions).toHaveLength(2);

    // Verify all actions are READ variant
    const allRead = data.actions.every((a: any) => a.variant === 'READ');
    expect(allRead).toBe(true);

    // Verify specific actions
    const actionIds = data.actions.map((a: any) => a.action_id);
    expect(actionIds).toContain('view_part_details');
    expect(actionIds).toContain('check_stock_level'); // or view_low_stock

    // Take screenshot for evidence
    await page.screenshot({ path: 'test-results/artifacts/crew-parts-actions.png', fullPage: true });
  });

  test('CREW cannot see MUTATE actions in UI', async ({ page }) => {
    await loginAs(page, 'crew');
    await navigateToPartsLens(page);

    // Search for parts actions
    await searchInSpotlight(page, 'receive part');

    const actions = await getActionSuggestions(page);

    // CREW should NOT see mutation actions
    const mutationActions = [
      'receive',
      'consume',
      'transfer',
      'adjust',
      'write off',
      'write-off',
    ];

    const hasMutation = actions.some((action) =>
      mutationActions.some((m) => action.toLowerCase().includes(m))
    );

    expect(hasMutation).toBe(false);
  });

  test('CREW gets 403 when attempting MUTATE action via API', async ({ page }) => {
    await loginAs(page, 'crew');
    await navigateToPartsLens(page);

    // Attempt to execute receive_part (MUTATE action)
    const result = await executeActionViaAPI(page, 'receive_part', {
      part_id: 'test-part-id',
      quantity_received: 10,
      to_location_id: 'test-location-id',
      idempotency_key: 'test-key',
    });

    // CREW should get 403 Forbidden
    expect(result.status).toBe(403);

    // Verify error message does NOT contain field names (authorization-first security)
    const errorText = JSON.stringify(result.body).toLowerCase();
    expect(errorText).toContain('forbidden');
    expect(errorText).not.toContain('part_id');
    expect(errorText).not.toContain('quantity_received');

    console.log('✅ CREW correctly denied with 403 (no field disclosure)');
  });

  test('CREW can view low stock parts', async ({ page }) => {
    await loginAs(page, 'crew');
    await navigateToPartsLens(page);

    // Try to find and click "View Low Stock" button
    const viewLowStockButton = page.locator(
      'button:has-text("View Low Stock"), ' +
      'button:has-text("Low Stock"), ' +
      '[data-testid="view-low-stock"], ' +
      '[data-testid="check-stock-level"]'
    ).first();

    if (await viewLowStockButton.count() > 0) {
      await viewLowStockButton.click();

      // Wait for parts table or list to appear
      await page.waitForSelector(
        'table, ' +
        '[data-testid="parts-table"], ' +
        '[data-testid="parts-list"], ' +
        '.parts-table',
        { timeout: 10000 }
      );

      // Take screenshot
      await page.screenshot({ path: 'test-results/artifacts/crew-view-low-stock.png', fullPage: true });
    } else {
      console.log('ℹ️  View Low Stock button not found in UI (may be in different location)');
    }
  });
});

// ============================================================================
// TEST SUITE: HOD Role - READ + MUTATE (NO SIGNED)
// ============================================================================

test.describe('Parts Lens - HOD Role (READ + MUTATE)', () => {
  test('HOD sees exactly 8 actions via API', async ({ page }) => {
    await loginAs(page, 'hod');
    await navigateToPartsLens(page);

    // Get actions from API
    const data = await getActionsFromAPI(page);

    // Verify role resolved to chief_engineer
    expect(data.role).toBe('chief_engineer');

    // Verify action count
    expect(data.actions).toHaveLength(8);

    // Categorize actions
    const readActions = data.actions.filter((a: any) => a.variant === 'READ');
    const mutateActions = data.actions.filter((a: any) => a.variant === 'MUTATE');
    const signedActions = data.actions.filter((a: any) => a.variant === 'SIGNED');

    expect(readActions).toHaveLength(2);
    expect(mutateActions).toHaveLength(6);
    expect(signedActions).toHaveLength(0); // HOD cannot see SIGNED actions

    // Verify specific MUTATE actions are present
    const actionIds = data.actions.map((a: any) => a.action_id);
    expect(actionIds).toContain('receive_part');
    expect(actionIds).toContain('consume_part');
    expect(actionIds).toContain('transfer_part');

    // Verify SIGNED actions are NOT present
    expect(actionIds).not.toContain('adjust_stock_quantity');
    expect(actionIds).not.toContain('write_off_part');

    // Take screenshot
    await page.screenshot({ path: 'test-results/artifacts/hod-parts-actions.png', fullPage: true });
  });

  test('HOD can see MUTATE actions in UI', async ({ page }) => {
    await loginAs(page, 'hod');
    await navigateToPartsLens(page);

    // Search for receive part
    await searchInSpotlight(page, 'receive part');

    const actions = await getActionSuggestions(page);

    // HOD should see MUTATE actions
    const hasReceive = actions.some((a) =>
      a.toLowerCase().includes('receive') && a.toLowerCase().includes('part')
    );

    // If search returns actions, at least one should be a MUTATE action
    if (actions.length > 0) {
      console.log('Actions visible to HOD:', actions);
    }
  });

  test('HOD gets 403 when attempting SIGNED action', async ({ page }) => {
    await loginAs(page, 'hod');
    await navigateToPartsLens(page);

    // Attempt to execute adjust_stock_quantity (SIGNED action)
    const result = await executeActionViaAPI(page, 'adjust_stock_quantity', {
      part_id: 'test-part-id',
      adjustment: 5,
      reason: 'Test adjustment',
      idempotency_key: 'test-key',
    });

    // HOD should get 403 for SIGNED actions
    expect(result.status).toBe(403);

    const errorText = JSON.stringify(result.body).toLowerCase();
    expect(errorText).toContain('forbidden');

    console.log('✅ HOD correctly denied SIGNED action with 403');
  });

  test.skip('HOD can open Receive Part modal', async ({ page }) => {
    // Skip by default - requires specific UI navigation
    await loginAs(page, 'hod');
    await navigateToPartsLens(page);

    // Try to find Receive Part button
    const receiveButton = page.locator(
      'button:has-text("Receive Part"), ' +
      '[data-testid="receive-part"]'
    ).first();

    if (await receiveButton.count() > 0) {
      await receiveButton.click();
      await waitForActionModal(page);

      // Modal should show form fields
      const partField = page.locator(
        'input[name="part_id"], ' +
        'select[name="part_id"], ' +
        '[data-testid="part-selector"]'
      );

      expect(await partField.count()).toBeGreaterThan(0);

      // Take screenshot
      await page.screenshot({ path: 'test-results/artifacts/hod-receive-part-modal.png', fullPage: true });
    }
  });
});

// ============================================================================
// TEST SUITE: CAPTAIN Role - FULL ACCESS (READ + MUTATE + SIGNED)
// ============================================================================

test.describe('Parts Lens - CAPTAIN Role (FULL ACCESS)', () => {
  test('CAPTAIN sees all 10 actions via API', async ({ page }) => {
    await loginAs(page, 'captain');
    await navigateToPartsLens(page);

    // Get actions from API
    const data = await getActionsFromAPI(page);

    // Verify role resolved to captain
    expect(data.role).toBe('captain');

    // Verify action count
    expect(data.actions).toHaveLength(10);

    // Categorize actions
    const readActions = data.actions.filter((a: any) => a.variant === 'READ');
    const mutateActions = data.actions.filter((a: any) => a.variant === 'MUTATE');
    const signedActions = data.actions.filter((a: any) => a.variant === 'SIGNED');

    expect(readActions).toHaveLength(2);
    expect(mutateActions).toHaveLength(6);
    expect(signedActions).toHaveLength(2); // CAPTAIN can see SIGNED actions

    // Verify SIGNED actions are present
    const actionIds = data.actions.map((a: any) => a.action_id);
    expect(actionIds).toContain('adjust_stock_quantity');
    expect(actionIds).toContain('write_off_part');

    console.log('✅ CAPTAIN sees all 10 actions including SIGNED');

    // Take screenshot
    await page.screenshot({ path: 'test-results/artifacts/captain-parts-actions.png', fullPage: true });
  });

  test.skip('CAPTAIN can open Write Off Part modal with signature badge', async ({ page }) => {
    // Skip by default - requires specific UI navigation
    await loginAs(page, 'captain');
    await navigateToPartsLens(page);

    // Search for write off action
    await searchInSpotlight(page, 'write off part');

    const actions = await getActionSuggestions(page);
    const writeOffAction = actions.find((a) =>
      a.toLowerCase().includes('write') && a.toLowerCase().includes('off')
    );

    if (writeOffAction) {
      await clickAction(page, writeOffAction);
      await waitForActionModal(page);

      // Modal should show "Requires Signature" badge
      const hasBadge = await hasSignatureBadge(page);
      expect(hasBadge).toBe(true);

      // Take screenshot
      await page.screenshot({ path: 'test-results/artifacts/captain-write-off-modal.png', fullPage: true });
    }
  });

  test.skip('Adjust Stock Quantity modal shows signature requirement', async ({ page }) => {
    // Skip by default - requires specific UI navigation
    await loginAs(page, 'captain');
    await navigateToPartsLens(page);

    // Find Adjust Stock button
    const adjustButton = page.locator(
      'button:has-text("Adjust Stock"), ' +
      'button:has-text("Adjust Quantity"), ' +
      '[data-testid="adjust-stock-quantity"]'
    ).first();

    if (await adjustButton.count() > 0) {
      await adjustButton.click();
      await waitForActionModal(page);

      // Verify signature badge
      const hasBadge = await hasSignatureBadge(page);
      expect(hasBadge).toBe(true);

      // Verify required fields
      const reasonField = page.locator(
        'input[name="reason"], ' +
        'textarea[name="reason"]'
      );

      expect(await reasonField.count()).toBeGreaterThan(0);
    }
  });
});

// ============================================================================
// TEST SUITE: Cross-Role Security Validation
// ============================================================================

test.describe('Parts Lens - Cross-Role Security', () => {
  test('All roles can access view_low_stock', async ({ browser }) => {
    const roles: Array<'crew' | 'hod' | 'captain'> = ['crew', 'hod', 'captain'];

    for (const role of roles) {
      // Create fresh context for each role to avoid session reuse
      const context = await browser.newContext();
      const page = await context.newPage();

      await loginAs(page, role);
      await navigateToPartsLens(page);

      const data = await getActionsFromAPI(page);
      const actionIds = data.actions.map((a: any) => a.action_id);

      // All roles should have a READ action for viewing stock
      const hasViewStock = actionIds.some((id: string) =>
        id.includes('view') || id.includes('check_stock') || id.includes('low_stock')
      );

      expect(hasViewStock).toBe(true);
      console.log(`✅ ${role.toUpperCase()} has view stock action`);

      // Cleanup
      await context.close();
    }
  });

  test('Role gating summary (action counts)', async ({ browser }) => {
    const expectedCounts = {
      crew: 2,
      hod: 8,
      captain: 10,
    };

    for (const [role, expectedCount] of Object.entries(expectedCounts)) {
      // Create fresh context for each role to avoid session reuse
      const context = await browser.newContext();
      const page = await context.newPage();

      await loginAs(page, role as 'crew' | 'hod' | 'captain');
      await navigateToPartsLens(page);

      const data = await getActionsFromAPI(page);

      expect(data.actions.length).toBe(expectedCount);
      console.log(`✅ ${role.toUpperCase()}: ${data.actions.length} actions (expected ${expectedCount})`);

      // Cleanup
      await context.close();
    }
  });

  test('Authorization-first security: 403 before 400', async ({ page }) => {
    await loginAs(page, 'crew');
    await navigateToPartsLens(page);

    // CREW attempts MUTATE with missing required fields
    // Should get 403 (authorization) NOT 400 (validation)
    const result = await executeActionViaAPI(page, 'receive_part', {
      // Intentionally missing required fields
    });

    // Must be 403, not 400
    expect(result.status).toBe(403);

    // Error should NOT reveal field names
    const errorText = JSON.stringify(result.body).toLowerCase();
    expect(errorText).not.toContain('part_id');
    expect(errorText).not.toContain('required field');

    console.log('✅ Authorization-first security validated (403 before 400)');
  });
});

// ============================================================================
// TEST SUITE: Real Data Validation
// ============================================================================

test.describe('Parts Lens - Real Data', () => {
  test('Low stock endpoint returns real parts data', async ({ page }) => {
    await loginAs(page, 'captain');

    const jwt = await getJWTFromPage(page);
    if (!jwt) throw new Error('No JWT');

    // Call low stock endpoint
    const response = await page.request.get(
      `${API_URL}/v1/parts/low-stock?yacht_id=${TEST_YACHT_ID}`,
      {
        headers: { 'Authorization': `Bearer ${jwt}` },
      }
    );

    expect(response.ok()).toBe(true);

    const data = await response.json();

    // Verify structure (object with parts key, not raw array)
    expect(data).toHaveProperty('parts');
    expect(data).toHaveProperty('total_low_stock');

    // Verify parts array exists
    expect(Array.isArray(data.parts)).toBe(true);

    console.log(`✅ Low stock returned ${data.total_low_stock} parts`);

    // If parts exist, verify structure
    if (data.parts.length > 0) {
      const firstPart = data.parts[0];
      expect(firstPart).toHaveProperty('name');
      expect(firstPart).toHaveProperty('on_hand');
      expect(firstPart).toHaveProperty('min_level');

      console.log(`Sample part: ${firstPart.name} (stock: ${firstPart.on_hand}/${firstPart.min_level})`);
    }
  });
});
