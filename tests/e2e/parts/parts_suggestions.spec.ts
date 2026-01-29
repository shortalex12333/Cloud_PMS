/**
 * Part Lens v2 - Suggestions E2E Test
 * =====================================
 * Tests role-based action suggestions with backend-frontend parity verification
 *
 * Validates:
 * - Crew: Only READ actions visible (no MUTATE/SIGNED)
 * - HOD: MUTATE actions visible (receive_part, consume_part)
 * - Captain: SIGNED actions visible (write_off_part, adjust_stock_quantity)
 * - Backend-frontend parity: UI shows exactly what backend returns (no invented actions)
 */

import { test, expect, Page } from '@playwright/test';
import {
  loginAsRole,
  navigateWithAuth,
  getJWTFromPage,
  type Role,
  type RoleAuthState,
} from './helpers/roles-auth';
import { ApiClient } from '../../helpers/api-client';

const TEST_YACHT_ID = process.env.TEST_USER_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';
const TEST_PART_ID = process.env.TEST_PART_ID || '8ad67e2f-2579-4d6c-afd2-0dee85f4d8b3';

/**
 * Get part suggestions from backend API
 */
async function getBackendSuggestions(jwt: string, partId: string): Promise<string[]> {
  const apiClient = new ApiClient();
  apiClient.setAccessToken(jwt);

  const response = await apiClient.get(`/v1/parts/suggestions?part_id=${partId}`);

  if (response.status !== 200) {
    throw new Error(`Backend suggestions failed: ${response.status}`);
  }

  // Extract action IDs from response
  const actions = response.data.data?.actions || response.data.actions || [];
  return actions.map((action: any) => action.action_id || action.id);
}

/**
 * Search for part in UI and extract rendered suggestions
 */
async function getUIRenderedActions(page: Page, partName: string = 'Engine Oil Filter'): Promise<string[]> {
  // Search for part
  const searchInput = page.locator('[data-testid="search-input"], input[placeholder*="Search"]').first();
  await searchInput.fill(partName);
  await searchInput.press('Enter');

  // Wait for suggestions panel
  await page.waitForSelector('[data-testid="suggestions-list"], [role="list"]', {
    timeout: 5000,
    state: 'visible',
  });

  // Extract all rendered action buttons
  const actionButtons = page.locator('[data-testid="action-button"], button[data-action-id]');
  const count = await actionButtons.count();

  const actionIds: string[] = [];
  for (let i = 0; i < count; i++) {
    const actionId = await actionButtons.nth(i).getAttribute('data-action-id');
    if (actionId) {
      actionIds.push(actionId);
    }
  }

  return actionIds;
}

/**
 * Test matrix: Role → Expected action presence
 */
const ROLE_ACTION_MATRIX = {
  crew: {
    shouldHave: ['view_part_details'],
    shouldNotHave: ['receive_part', 'consume_part', 'write_off_part', 'adjust_stock_quantity'],
  },
  hod: {
    shouldHave: ['view_part_details', 'receive_part', 'consume_part'],
    shouldNotHave: ['write_off_part', 'adjust_stock_quantity'],
  },
  captain: {
    shouldHave: [
      'view_part_details',
      'receive_part',
      'consume_part',
      'write_off_part',
      'adjust_stock_quantity',
    ],
    shouldNotHave: [],
  },
};

test.describe('Part Suggestions - Role-Based Visibility', () => {
  test.use({ baseURL: process.env.PLAYWRIGHT_BASE_URL || 'https://app.celeste7.ai' });

  for (const role of ['crew', 'hod', 'captain'] as Role[]) {
    test(`${role.toUpperCase()}: Backend-frontend parity`, async ({ page, context }) => {
      // Step 1: Login as role
      console.log(`[TEST] Logging in as ${role}...`);
      const authState = await loginAsRole(role);
      await context.addCookies([
        {
          name: 'auth-token',
          value: authState.tokens.accessToken,
          domain: new URL(process.env.PLAYWRIGHT_BASE_URL || 'https://app.celeste7.ai').hostname,
          path: '/',
        },
      ]);

      // Step 2: Navigate to app
      await navigateWithAuth(page, role);

      // Step 3: Get backend suggestions
      const jwt = await getJWTFromPage(page);
      const backendActions = await getBackendSuggestions(jwt, TEST_PART_ID);

      console.log(`[BACKEND] ${role} sees actions:`, backendActions);

      // Step 4: Get UI rendered actions
      const uiActions = await getUIRenderedActions(page);

      console.log(`[UI] ${role} sees actions:`, uiActions);

      // Step 5: Assert backend-frontend parity
      // UI should show exactly what backend returns (set equality)
      expect(new Set(uiActions)).toEqual(new Set(backendActions));

      // Step 6: Verify role-specific expectations
      const expectations = ROLE_ACTION_MATRIX[role];

      for (const action of expectations.shouldHave) {
        expect(backendActions).toContain(action);
      }

      for (const action of expectations.shouldNotHave) {
        expect(backendActions).not.toContain(action);
      }

      // Take screenshot for evidence
      await page.screenshot({
        path: `test-results/artifacts/parts-suggestions-${role}.png`,
        fullPage: true,
      });
    });
  }

  test('CREW: Cannot see MUTATE actions', async ({ page, context }) => {
    const authState = await loginAsRole('crew');
    await context.addCookies([
      {
        name: 'auth-token',
        value: authState.tokens.accessToken,
        domain: new URL(process.env.PLAYWRIGHT_BASE_URL || 'https://app.celeste7.ai').hostname,
        path: '/',
      },
    ]);

    await navigateWithAuth(page, 'crew');

    const jwt = await getJWTFromPage(page);
    const backendActions = await getBackendSuggestions(jwt, TEST_PART_ID);

    // Assert CREW sees no MUTATE actions
    const mutateActions = ['receive_part', 'consume_part', 'transfer_part'];
    for (const action of mutateActions) {
      expect(backendActions).not.toContain(action);
    }

    // Assert CREW sees no SIGNED actions
    const signedActions = ['write_off_part', 'adjust_stock_quantity'];
    for (const action of signedActions) {
      expect(backendActions).not.toContain(action);
    }
  });

  test('HOD: Can see MUTATE but not SIGNED actions', async ({ page, context }) => {
    const authState = await loginAsRole('hod');
    await context.addCookies([
      {
        name: 'auth-token',
        value: authState.tokens.accessToken,
        domain: new URL(process.env.PLAYWRIGHT_BASE_URL || 'https://app.celeste7.ai').hostname,
        path: '/',
      },
    ]);

    await navigateWithAuth(page, 'hod');

    const jwt = await getJWTFromPage(page);
    const backendActions = await getBackendSuggestions(jwt, TEST_PART_ID);

    // Assert HOD sees MUTATE actions
    expect(backendActions).toContain('receive_part');
    expect(backendActions).toContain('consume_part');

    // Assert HOD does NOT see SIGNED actions
    expect(backendActions).not.toContain('write_off_part');
    expect(backendActions).not.toContain('adjust_stock_quantity');
  });

  test('CAPTAIN: Can see SIGNED actions', async ({ page, context }) => {
    const authState = await loginAsRole('captain');
    await context.addCookies([
      {
        name: 'auth-token',
        value: authState.tokens.accessToken,
        domain: new URL(process.env.PLAYWRIGHT_BASE_URL || 'https://app.celeste7.ai').hostname,
        path: '/',
      },
    ]);

    await navigateWithAuth(page, 'captain');

    const jwt = await getJWTFromPage(page);
    const backendActions = await getBackendSuggestions(jwt, TEST_PART_ID);

    // Assert CAPTAIN sees SIGNED actions
    expect(backendActions).toContain('write_off_part');
    expect(backendActions).toContain('adjust_stock_quantity');

    // Assert CAPTAIN also sees MUTATE actions (role hierarchy)
    expect(backendActions).toContain('receive_part');
    expect(backendActions).toContain('consume_part');
  });

  test('UI does not invent actions not in backend response', async ({ page, context }) => {
    // Login as HOD
    const authState = await loginAsRole('hod');
    await context.addCookies([
      {
        name: 'auth-token',
        value: authState.tokens.accessToken,
        domain: new URL(process.env.PLAYWRIGHT_BASE_URL || 'https://app.celeste7.ai').hostname,
        path: '/',
      },
    ]);

    await navigateWithAuth(page, 'hod');

    // Intercept backend API call
    let backendResponse: string[] = [];
    await page.route('**/v1/parts/suggestions*', async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      backendResponse = (json.data?.actions || json.actions || []).map((a: any) => a.action_id || a.id);
      await route.fulfill({ response });
    });

    // Trigger search
    const searchInput = page.locator('[data-testid="search-input"], input[placeholder*="Search"]').first();
    await searchInput.fill('Engine Oil Filter');
    await searchInput.press('Enter');

    // Wait for suggestions
    await page.waitForSelector('[data-testid="suggestions-list"], [role="list"]', {
      timeout: 5000,
    });

    // Extract UI actions
    const actionButtons = page.locator('[data-testid="action-button"], button[data-action-id]');
    const count = await actionButtons.count();
    const uiActions: string[] = [];

    for (let i = 0; i < count; i++) {
      const actionId = await actionButtons.nth(i).getAttribute('data-action-id');
      if (actionId) {
        uiActions.push(actionId);
      }
    }

    // Assert UI only shows actions from backend (no extras)
    for (const uiAction of uiActions) {
      expect(backendResponse).toContain(uiAction);
    }

    // Assert backend actions are all present in UI (no missing)
    for (const backendAction of backendResponse) {
      expect(uiActions).toContain(backendAction);
    }
  });
});
