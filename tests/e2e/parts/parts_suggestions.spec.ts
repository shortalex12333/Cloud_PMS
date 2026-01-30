/**
 * Part Lens v2 - Suggestions E2E Test
 * =====================================
 * Tests role-based action suggestions with backend-frontend parity verification
 *
 * Validates:
 * - Crew: Only READ actions visible (no MUTATE/SIGNED)
 * - Chief Engineer: MUTATE actions visible (receive_part, consume_part)
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

  // TODO: TEMPORARY WORKAROUND - Deployed API (main branch) requires yacht_id as query param
  // This branch has the correct implementation (yacht_id from JWT only), but it's not deployed yet
  // Once the fix is merged to main and deployed, remove yacht_id from this URL
  const yachtId = TEST_YACHT_ID;
  const response = await apiClient.get(`/v1/parts/suggestions?part_id=${partId}&yacht_id=${yachtId}`);

  if (response.status !== 200) {
    // Capture full error details for debugging
    console.error('=== Backend Suggestions Error ===');
    console.error('Status:', response.status);
    console.error('Status Text:', response.statusText);
    console.error('Response Data:', JSON.stringify(response.data, null, 2));
    console.error('Request URL:', response.request.url);
    console.error('Request Headers:', JSON.stringify(response.request.headers, null, 2));

    const errorDetail = typeof response.data === 'object'
      ? JSON.stringify(response.data)
      : response.data;
    throw new Error(`Backend suggestions failed: ${response.status} - ${errorDetail}`);
  }

  // Extract action IDs from response
  const actions = response.data.data?.actions || response.data.actions || [];
  return actions.map((action: any) => action.action_id || action.id);
}

/**
 * Search for part in UI and extract rendered suggestions
 *
 * ARCHITECTURE: Search-first, entity extraction, action surfacing
 * - Query triggers entity extraction
 * - Part entity card appears with focused state
 * - Actions surface based on entity type + user role
 */
async function getUIRenderedActions(page: Page, partName: string = 'Engine Oil Filter'): Promise<string[]> {
  // Search for part
  const searchInput = page.locator('[data-testid="search-input"], input[placeholder*="Search"]').first();
  await searchInput.fill(partName);
  await searchInput.press('Enter');

  // Wait for entity extraction and card rendering
  await page.waitForSelector('[data-entity-type="part"], [data-testid="part-card"]', {
    timeout: 5000,
    state: 'visible',
  });

  // Wait for action buttons to appear (based on focused entity + role)
  await page.waitForSelector('[data-testid="action-button"], button[data-action-id]', {
    timeout: 3000,
    state: 'visible',
  }).catch(() => {
    // No actions visible (expected for crew role)
    console.log('No action buttons visible (may be expected for role)');
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
  chief_engineer: {
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

// Backend-Frontend Parity: CREW
test.describe('Part Suggestions - CREW Role', () => {
  test.use({
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'https://app.celeste7.ai',
    storageState: './test-results/.auth-states/crew-state.json',
  });

  test('CREW: Backend-frontend parity', async ({ page }) => {
    // Navigate to app (already authenticated via storage state)
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    // Get backend suggestions
    const jwt = await getJWTFromPage(page);
    const backendActions = await getBackendSuggestions(jwt, TEST_PART_ID);

    console.log(`[BACKEND] crew sees actions:`, backendActions);

    // Get UI rendered actions
    const uiActions = await getUIRenderedActions(page);

    console.log(`[UI] crew sees actions:`, uiActions);

    // Assert backend-frontend parity
    expect(new Set(uiActions)).toEqual(new Set(backendActions));

    // Verify role-specific expectations
    const expectations = ROLE_ACTION_MATRIX['crew'];
    for (const action of expectations.shouldHave) {
      expect(backendActions).toContain(action);
    }
    for (const action of expectations.shouldNotHave) {
      expect(backendActions).not.toContain(action);
    }

    // Take screenshot
    await page.screenshot({
      path: `test-results/artifacts/parts-suggestions-crew.png`,
      fullPage: true,
    });
  });
});

// Backend-Frontend Parity: HOD
test.describe('Part Suggestions - Chief Engineer Role', () => {
  test.use({
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'https://app.celeste7.ai',
    storageState: './test-results/.auth-states/chief_engineer-state.json',
  });

  test('Chief Engineer: Backend-frontend parity', async ({ page }) => {
    // Navigate to app (already authenticated via storage state)
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    // Get backend suggestions
    const jwt = await getJWTFromPage(page);
    const backendActions = await getBackendSuggestions(jwt, TEST_PART_ID);

    console.log(`[BACKEND] chief_engineer sees actions:`, backendActions);

    // Get UI rendered actions
    const uiActions = await getUIRenderedActions(page);

    console.log(`[UI] chief_engineer sees actions:`, uiActions);

    // Assert backend-frontend parity
    expect(new Set(uiActions)).toEqual(new Set(backendActions));

    // Verify role-specific expectations
    const expectations = ROLE_ACTION_MATRIX['chief_engineer'];
    for (const action of expectations.shouldHave) {
      expect(backendActions).toContain(action);
    }
    for (const action of expectations.shouldNotHave) {
      expect(backendActions).not.toContain(action);
    }

    // Take screenshot
    await page.screenshot({
      path: `test-results/artifacts/parts-suggestions-hod.png`,
      fullPage: true,
    });
  });
});

// Backend-Frontend Parity: CAPTAIN
test.describe('Part Suggestions - CAPTAIN Role', () => {
  test.use({
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'https://app.celeste7.ai',
    storageState: './test-results/.auth-states/captain-state.json',
  });

  test('CAPTAIN: Backend-frontend parity', async ({ page }) => {
    // Navigate to app (already authenticated via storage state)
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    // Get backend suggestions
    const jwt = await getJWTFromPage(page);
    const backendActions = await getBackendSuggestions(jwt, TEST_PART_ID);

    console.log(`[BACKEND] captain sees actions:`, backendActions);

    // Get UI rendered actions
    const uiActions = await getUIRenderedActions(page);

    console.log(`[UI] captain sees actions:`, uiActions);

    // Assert backend-frontend parity
    expect(new Set(uiActions)).toEqual(new Set(backendActions));

    // Verify role-specific expectations
    const expectations = ROLE_ACTION_MATRIX['captain'];
    for (const action of expectations.shouldHave) {
      expect(backendActions).toContain(action);
    }
    for (const action of expectations.shouldNotHave) {
      expect(backendActions).not.toContain(action);
    }

    // Take screenshot
    await page.screenshot({
      path: `test-results/artifacts/parts-suggestions-captain.png`,
      fullPage: true,
    });
  });
});

// Role-Specific Action Tests: CREW
test.describe('Part Suggestions - CREW Action Restrictions', () => {
  test.use({
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'https://app.celeste7.ai',
    storageState: './test-results/.auth-states/crew-state.json',
  });

  test('CREW: Cannot see MUTATE actions', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

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
});

// Role-Specific Action Tests: HOD
test.describe('Part Suggestions - Chief Engineer Action Permissions', () => {
  test.use({
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'https://app.celeste7.ai',
    storageState: './test-results/.auth-states/chief_engineer-state.json',
  });

  test('Chief Engineer: Can see MUTATE but not SIGNED actions', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    const jwt = await getJWTFromPage(page);
    const backendActions = await getBackendSuggestions(jwt, TEST_PART_ID);

    // Assert Chief Engineer sees MUTATE actions
    expect(backendActions).toContain('receive_part');
    expect(backendActions).toContain('consume_part');

    // Assert Chief Engineer does NOT see SIGNED actions
    expect(backendActions).not.toContain('write_off_part');
    expect(backendActions).not.toContain('adjust_stock_quantity');
  });

  test('UI does not invent actions not in backend response', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

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

// Role-Specific Action Tests: CAPTAIN
test.describe('Part Suggestions - CAPTAIN Action Permissions', () => {
  test.use({
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'https://app.celeste7.ai',
    storageState: './test-results/.auth-states/captain-state.json',
  });

  test('CAPTAIN: Can see SIGNED actions', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    const jwt = await getJWTFromPage(page);
    const backendActions = await getBackendSuggestions(jwt, TEST_PART_ID);

    // Assert CAPTAIN sees SIGNED actions
    expect(backendActions).toContain('write_off_part');
    expect(backendActions).toContain('adjust_stock_quantity');

    // Assert CAPTAIN also sees MUTATE actions (role hierarchy)
    expect(backendActions).toContain('receive_part');
    expect(backendActions).toContain('consume_part');
  });
});
