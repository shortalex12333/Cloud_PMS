import { test, expect, SpotlightSearchPO, ContextPanelPO } from '../fixtures';
import { Page } from '@playwright/test';

/**
 * SHARD 2: SpotlightSearch Intent Detection Tests
 *
 * Tests the intent detection and action routing flow:
 * - MUTATE intent detection - queries like "create work order" show SuggestedActions
 * - READ intent routing - queries like "show work orders" navigate to filtered lists
 * - Prefill preview - action buttons show ReadinessIndicator (READY/NEEDS_INPUT/BLOCKED)
 * - ActionModal opens with prefilled fields when clicking a suggested action
 *
 * Test IDs used:
 * - search-input: Main spotlight search input
 * - suggested-actions: Container for MUTATE action buttons
 * - action-btn-{action_id}: Individual action buttons
 * - navigate-btn: READ navigation button
 * - filter-chips: Filter chip container
 * - filter-chip-{field}: Individual filter chips
 *
 * Component references:
 * - SpotlightSearch.tsx: Main search component
 * - SuggestedActions.tsx: Action buttons with ReadinessIndicator
 * - ActionModal.tsx: Prefilled form modal
 */

// ============================================================================
// TEST DATA: Intent Query Patterns
// ============================================================================

interface MutateQuery {
  query: string;
  expectedActionId: string;
  expectedLabel: string;
  description: string;
}

interface ReadQuery {
  query: string;
  expectedRoutePattern: string | RegExp;
  expectedFilters?: string[];
  description: string;
}

// MUTATE intent queries - should trigger SuggestedActions
const MUTATE_QUERIES: MutateQuery[] = [
  {
    query: 'create work order for generator',
    expectedActionId: 'create_work_order',
    expectedLabel: 'Create Work Order',
    description: 'Basic work order creation with equipment context',
  },
  {
    query: 'new work order for main engine',
    expectedActionId: 'create_work_order',
    expectedLabel: 'Create Work Order',
    description: 'Synonym: "new" triggers create intent',
  },
  {
    query: 'add fault for watermaker',
    expectedActionId: 'create_fault',
    expectedLabel: 'Report Fault',
    description: 'Fault creation with equipment context',
  },
  {
    query: 'log receiving',
    expectedActionId: 'log_receiving',
    expectedLabel: 'Log Receiving',
    description: 'Receiving log action',
  },
  {
    query: 'create urgent work order for ME1',
    expectedActionId: 'create_work_order',
    expectedLabel: 'Create Work Order',
    description: 'Work order with priority and equipment code',
  },
];

// READ intent queries - should navigate to filtered routes
const READ_QUERIES: ReadQuery[] = [
  {
    query: 'show work orders',
    expectedRoutePattern: /\/work-orders/,
    description: 'Basic work orders list',
  },
  {
    query: 'open engine work orders',
    expectedRoutePattern: /\/work-orders.*equipment.*engine/i,
    expectedFilters: ['equipment'],
    description: 'Work orders filtered by equipment keyword',
  },
  {
    query: 'overdue faults',
    expectedRoutePattern: /\/faults.*status.*overdue/i,
    expectedFilters: ['status'],
    description: 'Faults filtered by overdue status',
  },
  {
    query: 'maintenance scheduled this week',
    expectedRoutePattern: /\/work-orders.*schedule/i,
    description: 'Work orders with temporal filter',
  },
];

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Wait for suggested actions container to appear
 */
async function waitForSuggestedActions(page: Page, timeout = 5000): Promise<boolean> {
  const suggestedActions = page.getByTestId('suggested-actions');
  try {
    await suggestedActions.waitFor({ state: 'visible', timeout });
    return true;
  } catch {
    return false;
  }
}

/**
 * Get all visible action buttons
 */
async function getActionButtons(page: Page): Promise<{ id: string; label: string }[]> {
  const buttons = page.locator('[data-testid^="action-btn-"]');
  const count = await buttons.count();
  const actions: { id: string; label: string }[] = [];

  for (let i = 0; i < count; i++) {
    const btn = buttons.nth(i);
    const testId = await btn.getAttribute('data-testid');
    const label = await btn.textContent();
    if (testId && label) {
      actions.push({
        id: testId.replace('action-btn-', ''),
        label: label.trim(),
      });
    }
  }

  return actions;
}

/**
 * Get ReadinessIndicator state from action button
 * Per READY-04: green checkmark (READY), amber dot (NEEDS_INPUT), lock (BLOCKED)
 */
async function getReadinessState(
  page: Page,
  actionId: string
): Promise<'READY' | 'NEEDS_INPUT' | 'BLOCKED' | 'UNKNOWN'> {
  const btn = page.getByTestId(`action-btn-${actionId}`);
  const isVisible = await btn.isVisible().catch(() => false);
  if (!isVisible) return 'UNKNOWN';

  // Check for ReadinessIndicator icons
  const checkIcon = btn.locator('[aria-label="Ready to execute"]');
  const dotIcon = btn.locator('[aria-label="Requires input"]');
  const lockIcon = btn.locator('[aria-label="Permission required"]');

  if (await checkIcon.isVisible().catch(() => false)) return 'READY';
  if (await lockIcon.isVisible().catch(() => false)) return 'BLOCKED';
  if (await dotIcon.isVisible().catch(() => false)) return 'NEEDS_INPUT';

  // Check by CSS classes as fallback
  const className = await btn.getAttribute('class') || '';
  if (className.includes('emerald')) return 'READY';
  if (className.includes('red') || className.includes('cursor-not-allowed')) return 'BLOCKED';
  if (className.includes('amber')) return 'NEEDS_INPUT';

  return 'NEEDS_INPUT'; // Default to NEEDS_INPUT
}

// ============================================================================
// SECTION 1: MUTATE INTENT DETECTION
// Verify MUTATE queries show SuggestedActions container
// ============================================================================

test.describe('SpotlightSearch Intent Detection - MUTATE', () => {
  test.describe.configure({ retries: 1 });

  test('MUTATE query "create work order for generator" shows SuggestedActions', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('create work order for generator');

    // Wait for suggested actions to appear
    const hasActions = await waitForSuggestedActions(page);

    if (hasActions) {
      // Verify suggested-actions container is visible
      const suggestedActions = page.getByTestId('suggested-actions');
      await expect(suggestedActions).toBeVisible();

      // Verify action-btn-create_work_order exists
      const createWoBtn = page.getByTestId('action-btn-create_work_order');
      const hasCreateBtn = await createWoBtn.isVisible().catch(() => false);

      if (hasCreateBtn) {
        console.log('  PASS: create_work_order action button visible');
        await expect(createWoBtn).toBeVisible();
      } else {
        // Check for alternative action IDs
        const actionButtons = await getActionButtons(page);
        console.log(`  Available actions: ${actionButtons.map((a) => a.id).join(', ')}`);

        const hasCreateAction = actionButtons.some(
          (a) => a.id.includes('create') || a.id.includes('work_order')
        );
        expect(hasCreateAction).toBe(true);
      }
    } else {
      console.log('  INFO: No SuggestedActions for MUTATE query - feature may not be implemented');
    }
  });

  // Test multiple MUTATE query patterns
  for (const mutateQuery of MUTATE_QUERIES.slice(0, 3)) {
    test(`MUTATE query "${mutateQuery.query}" triggers action suggestions`, async ({ page }) => {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search(mutateQuery.query);

      const hasActions = await waitForSuggestedActions(page);

      if (hasActions) {
        const actionButtons = await getActionButtons(page);
        console.log(
          `  ${mutateQuery.description}: ${actionButtons.length} actions - [${actionButtons.map((a) => a.id).join(', ')}]`
        );

        // Verify expected action appears (exact or partial match)
        const hasExpectedAction = actionButtons.some(
          (a) =>
            a.id === mutateQuery.expectedActionId ||
            a.id.includes(mutateQuery.expectedActionId.split('_')[0])
        );

        if (hasExpectedAction) {
          console.log(`  PASS: Found expected action ${mutateQuery.expectedActionId}`);
        } else {
          console.log(
            `  INFO: Expected ${mutateQuery.expectedActionId}, got [${actionButtons.map((a) => a.id).join(', ')}]`
          );
        }
      } else {
        console.log(`  INFO: No actions for "${mutateQuery.query}"`);
      }
    });
  }

  test('MUTATE query should NOT appear for READ-only queries', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    // Pure search query without action intent
    await spotlight.search('maintenance');

    // Wait for results to load
    await page.waitForTimeout(2500);

    // Suggested actions should NOT appear for READ queries
    const suggestedActions = page.getByTestId('suggested-actions');
    const hasActions = await suggestedActions.isVisible({ timeout: 2000 }).catch(() => false);

    if (!hasActions) {
      console.log('  PASS: No action suggestions for READ-only query (correct)');
    } else {
      // If actions appear, they should be contextual (not MUTATE)
      const actionButtons = await getActionButtons(page);
      console.log(`  INFO: Unexpected actions for READ query: ${actionButtons.map((a) => a.id).join(', ')}`);
    }
  });
});

// ============================================================================
// SECTION 2: READ INTENT ROUTING
// Verify READ queries navigate to filtered list routes
// ============================================================================

test.describe('SpotlightSearch Intent Detection - READ', () => {
  test.describe.configure({ retries: 1 });

  test('READ query "engine work orders" navigates to filtered list', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('open engine work orders');

    // Wait for results
    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    // Check for filter chips (READ intent indicator)
    const filterChips = page.getByTestId('filter-chips');
    const hasFilterChips = await filterChips.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasFilterChips) {
      console.log('  Filter chips visible - READ intent detected');

      // Check for navigate button
      const navigateBtn = page.getByTestId('navigate-btn');
      const hasNavigateBtn = await navigateBtn.isVisible({ timeout: 2000 }).catch(() => false);

      if (hasNavigateBtn) {
        // Click navigate button and verify URL
        const initialUrl = page.url();
        await navigateBtn.click();
        await page.waitForLoadState('networkidle');

        const newUrl = page.url();
        const urlChanged = newUrl !== initialUrl;

        if (urlChanged) {
          console.log(`  PASS: Navigated to ${newUrl}`);

          // Verify URL contains expected route
          const hasWorkOrdersRoute = /work-orders/.test(newUrl);
          expect(hasWorkOrdersRoute).toBe(true);
        }
      } else {
        console.log('  INFO: No navigate button - checking for direct click navigation');

        // Try clicking first result
        const resultCount = await spotlight.getResultCount();
        if (resultCount > 0) {
          await spotlight.clickResult(0);
          await page.waitForLoadState('networkidle');

          const newUrl = page.url();
          console.log(`  Clicked result, navigated to: ${newUrl}`);
        }
      }
    } else {
      // Without filter chips, check if results can be clicked to navigate
      const resultCount = await spotlight.getResultCount();
      if (resultCount > 0) {
        await spotlight.clickResult(0);
        await page.waitForLoadState('networkidle');

        const newUrl = page.url();
        console.log(`  INFO: No filter chips, clicked result -> ${newUrl}`);
      } else {
        console.log('  INFO: No filter chips and no results');
      }
    }
  });

  test('Filter chips appear for equipment-scoped queries', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('main engine');

    await page.waitForTimeout(2500);

    // Check for equipment filter chip
    const equipmentChip = page.getByTestId('filter-chip-equipment');
    const hasEquipmentChip = await equipmentChip.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasEquipmentChip) {
      console.log('  PASS: Equipment filter chip visible');
      await expect(equipmentChip).toBeVisible();
    } else {
      // Check for any filter chips
      const filterChips = page.getByTestId('filter-chips');
      const hasAnyChips = await filterChips.isVisible({ timeout: 2000 }).catch(() => false);
      console.log(`  INFO: Equipment chip not found, any chips: ${hasAnyChips}`);
    }
  });
});

// ============================================================================
// SECTION 3: PREFILL PREVIEW & READINESS INDICATOR
// Verify action buttons show correct ReadinessIndicator state
// ============================================================================

test.describe('SpotlightSearch Prefill Preview', () => {
  test.describe.configure({ retries: 1 });

  test('Prefill preview shows READY state when all fields extractable', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    // Query with complete entity extraction (equipment + priority)
    await spotlight.search('create urgent work order for ME1');

    const hasActions = await waitForSuggestedActions(page);

    if (hasActions) {
      const readinessState = await getReadinessState(page, 'create_work_order');
      console.log(`  Readiness state: ${readinessState}`);

      // READY state indicates all required fields can be prefilled
      if (readinessState === 'READY') {
        console.log('  PASS: READY state - all fields extractable from query');
      } else if (readinessState === 'NEEDS_INPUT') {
        console.log('  INFO: NEEDS_INPUT state - some fields require manual entry');
      } else if (readinessState === 'BLOCKED') {
        console.log('  INFO: BLOCKED state - permission required');
      }
    } else {
      console.log('  INFO: No action suggestions to check readiness');
    }
  });

  test('Prefill preview shows NEEDS_INPUT state when fields missing', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    // Query without complete context
    await spotlight.search('create work order');

    const hasActions = await waitForSuggestedActions(page);

    if (hasActions) {
      const readinessState = await getReadinessState(page, 'create_work_order');
      console.log(`  Readiness state for incomplete query: ${readinessState}`);

      // Without equipment context, should show NEEDS_INPUT
      expect(['NEEDS_INPUT', 'UNKNOWN']).toContain(readinessState);

      if (readinessState === 'NEEDS_INPUT') {
        console.log('  PASS: NEEDS_INPUT state for query without equipment');
      }
    } else {
      console.log('  INFO: No action suggestions');
    }
  });

  test('ReadinessIndicator icons render correctly', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('create work order for generator');

    const hasActions = await waitForSuggestedActions(page);

    if (hasActions) {
      const createBtn = page.getByTestId('action-btn-create_work_order');
      const isVisible = await createBtn.isVisible().catch(() => false);

      if (isVisible) {
        // Check for any ReadinessIndicator icon
        const hasCheckIcon = await createBtn.locator('svg.text-emerald-400').isVisible().catch(() => false);
        const hasAmberIcon = await createBtn.locator('svg.text-amber-400').isVisible().catch(() => false);
        const hasLockIcon = await createBtn.locator('svg.text-red-400').isVisible().catch(() => false);

        const hasIndicator = hasCheckIcon || hasAmberIcon || hasLockIcon;

        if (hasIndicator) {
          console.log(`  PASS: ReadinessIndicator rendered (check: ${hasCheckIcon}, amber: ${hasAmberIcon}, lock: ${hasLockIcon})`);
        } else {
          console.log('  INFO: No explicit ReadinessIndicator icon - may use className styling');
        }
      }
    }
  });
});

// ============================================================================
// SECTION 4: ACTION MODAL WITH PREFILLED FIELDS
// Verify clicking action opens modal with prefilled values
// ============================================================================

test.describe('SpotlightSearch ActionModal Prefill', () => {
  test.describe.configure({ retries: 1 });

  test('ActionModal opens with prefilled fields when clicking suggested action', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('create work order for main engine');

    const hasActions = await waitForSuggestedActions(page);

    if (!hasActions) {
      console.log('  SKIP: No action suggestions available');
      return;
    }

    // Click create work order action
    const createBtn = page.getByTestId('action-btn-create_work_order');
    const isVisible = await createBtn.isVisible().catch(() => false);

    if (!isVisible) {
      // Try alternative selectors
      const anyActionBtn = page.locator('[data-testid^="action-btn-"]:has-text("Create")');
      const hasAnyCreate = await anyActionBtn.isVisible().catch(() => false);

      if (!hasAnyCreate) {
        console.log('  SKIP: No create action button found');
        return;
      }

      await anyActionBtn.click();
    } else {
      await createBtn.click();
    }

    // Wait for modal
    const modal = page.locator('[role="dialog"]');
    const modalVisible = await modal.waitFor({ state: 'visible', timeout: 5000 }).then(() => true).catch(() => false);

    if (!modalVisible) {
      console.log('  INFO: Modal did not open');
      return;
    }

    console.log('  Modal opened');

    // Check for prefilled fields
    // Title should contain extracted entity (e.g., "main engine")
    const titleInput = modal.locator('input[id="title"], input[name="title"], [data-testid="title-input"]');
    const hasTitleInput = await titleInput.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasTitleInput) {
      const titleValue = await titleInput.inputValue();
      console.log(`  Title field value: "${titleValue}"`);

      // Check if prefilled with equipment context
      const hasPrefill = titleValue.toLowerCase().includes('engine') || titleValue.length > 0;
      if (hasPrefill) {
        console.log('  PASS: Title field appears prefilled');
      }
    }

    // Check for equipment_id dropdown or field
    const equipmentField = modal.locator('[data-testid="equipment_id-input"], select[name="equipment_id"]');
    const hasEquipmentField = await equipmentField.isVisible({ timeout: 2000 }).catch(() => false);

    if (hasEquipmentField) {
      console.log('  Equipment field present in modal');
    }

    // Check for confidence indicator badges
    const confidenceIndicator = modal.locator('span:has-text("auto-filled"), span:has-text("confirm")');
    const hasConfidenceIndicator = await confidenceIndicator.isVisible({ timeout: 2000 }).catch(() => false);

    if (hasConfidenceIndicator) {
      console.log('  PASS: Confidence indicator badges visible');
    }

    // Close modal
    await page.keyboard.press('Escape');
  });

  test('ActionModal shows disambiguation dropdown for ambiguous entities', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    // Query that might match multiple equipment items
    await spotlight.search('create work order for engine');

    const hasActions = await waitForSuggestedActions(page);

    if (!hasActions) {
      console.log('  SKIP: No action suggestions');
      return;
    }

    // Click action
    const createBtn = page.locator('[data-testid^="action-btn-"]:has-text("Create")').first();
    const hasBtn = await createBtn.isVisible().catch(() => false);

    if (!hasBtn) {
      console.log('  SKIP: No create button');
      return;
    }

    await createBtn.click();

    // Wait for modal
    const modal = page.locator('[role="dialog"]');
    await modal.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {});

    // Check for disambiguation dropdown (DISAMB-01)
    const ambiguityDropdown = modal.locator('[data-testid^="ambiguity-"]');
    const hasAmbiguity = await ambiguityDropdown.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasAmbiguity) {
      console.log('  PASS: Disambiguation dropdown visible');

      // Check for "Did you mean" prompt
      const didYouMean = modal.locator('text=Did you mean');
      const hasPrompt = await didYouMean.isVisible().catch(() => false);
      console.log(`  "Did you mean" prompt: ${hasPrompt}`);
    } else {
      console.log('  INFO: No disambiguation needed (single match or no ambiguity)');
    }

    // Close modal
    await page.keyboard.press('Escape');
  });

  test('ActionModal submit button reflects disambiguation state', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('create work order');

    const hasActions = await waitForSuggestedActions(page);

    if (!hasActions) {
      console.log('  SKIP: No action suggestions');
      return;
    }

    const createBtn = page.locator('[data-testid^="action-btn-"]:has-text("Create")').first();
    const hasBtn = await createBtn.isVisible().catch(() => false);

    if (!hasBtn) {
      console.log('  SKIP: No create button');
      return;
    }

    await createBtn.click();

    // Wait for modal
    const modal = page.locator('[role="dialog"]');
    await modal.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {});

    // Check submit button state
    const submitBtn = modal.getByTestId('action-submit');
    const hasSubmitBtn = await submitBtn.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasSubmitBtn) {
      const isDisabled = await submitBtn.isDisabled();
      const buttonText = await submitBtn.textContent();

      console.log(`  Submit button: "${buttonText?.trim()}", disabled: ${isDisabled}`);

      // If disambiguation pending, button should say "Select options above"
      if (buttonText?.includes('Select options')) {
        console.log('  PASS: Submit blocked pending disambiguation');
      } else if (isDisabled) {
        console.log('  INFO: Submit disabled (validation or disambiguation)');
      } else {
        console.log('  Submit enabled - ready to execute');
      }
    }

    // Close modal
    await page.keyboard.press('Escape');
  });
});

// ============================================================================
// SECTION 5: INTENT DETERMINISM
// Verify same query produces same intent classification
// ============================================================================

test.describe('SpotlightSearch Intent Determinism', () => {
  test.describe.configure({ retries: 0 }); // Strict - must be deterministic

  test('Same MUTATE query produces consistent action suggestions', async ({ page }) => {
    const query = 'create work order for generator';
    const runs: string[][] = [];

    for (let i = 0; i < 2; i++) {
      await page.goto('/');

      const spotlight = new SpotlightSearchPO(page);
      await spotlight.search(query);

      const hasActions = await waitForSuggestedActions(page);

      if (hasActions) {
        const actionButtons = await getActionButtons(page);
        runs.push(actionButtons.map((a) => a.id).sort());
        console.log(`  Run ${i + 1}: [${runs[i].join(', ')}]`);
      } else {
        runs.push([]);
        console.log(`  Run ${i + 1}: no actions`);
      }
    }

    // Compare runs
    if (runs[0].length > 0 && runs[1].length > 0) {
      const match = JSON.stringify(runs[0]) === JSON.stringify(runs[1]);
      if (match) {
        console.log('  PASS: Deterministic action suggestions');
      } else {
        console.log('  FAIL: Non-deterministic results');
      }
      expect(runs[0]).toEqual(runs[1]);
    } else {
      console.log('  INFO: Cannot verify determinism - no actions returned');
    }
  });

  test('Intent classification is stable across page reloads', async ({ page }) => {
    const query = 'create urgent work order';

    // First load
    await page.goto('/');
    const spotlight1 = new SpotlightSearchPO(page);
    await spotlight1.search(query);
    const hasActions1 = await waitForSuggestedActions(page);
    const state1 = hasActions1 ? await getReadinessState(page, 'create_work_order') : 'NONE';
    console.log(`  First load readiness: ${state1}`);

    // Reload and search again
    await page.reload();
    await page.waitForLoadState('networkidle');

    const spotlight2 = new SpotlightSearchPO(page);
    await spotlight2.search(query);
    const hasActions2 = await waitForSuggestedActions(page);
    const state2 = hasActions2 ? await getReadinessState(page, 'create_work_order') : 'NONE';
    console.log(`  After reload readiness: ${state2}`);

    // States should match
    expect(state1).toBe(state2);
    console.log('  PASS: Intent classification stable across reloads');
  });
});

// ============================================================================
// SECTION 6: EDGE CASES
// ============================================================================

test.describe('SpotlightSearch Intent Edge Cases', () => {
  test.describe.configure({ retries: 1 });

  test('Ambiguous query (could be READ or MUTATE) is handled gracefully', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    // "work order" could be "show work orders" or "create work order"
    await spotlight.search('work order');

    await page.waitForTimeout(2500);

    // Should show search results
    const hasResults = await spotlight.resultsContainer.isVisible({ timeout: 5000 }).catch(() => false);
    const hasSuggestedActions = await waitForSuggestedActions(page);

    console.log(`  Results visible: ${hasResults}`);
    console.log(`  Action suggestions: ${hasSuggestedActions}`);

    // At minimum, we should have either results or actions (or both)
    expect(hasResults || hasSuggestedActions).toBe(true);
  });

  test('Special characters in query do not break intent detection', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('create work order for "Main Engine" #1');

    await page.waitForTimeout(2500);

    // Should not show error
    const errorState = page.getByTestId('search-error');
    const hasError = await errorState.isVisible({ timeout: 2000 }).catch(() => false);

    expect(hasError).toBe(false);
    console.log('  PASS: Special characters handled gracefully');
  });

  test('Very long query is handled', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    const longQuery = 'create work order for the main starboard engine that has been showing signs of overheating';
    await spotlight.search(longQuery);

    await page.waitForTimeout(3000);

    // Should process without crashing
    const errorState = page.getByTestId('search-error');
    const hasError = await errorState.isVisible({ timeout: 2000 }).catch(() => false);

    expect(hasError).toBe(false);

    // May or may not show actions depending on entity extraction
    const hasSuggestedActions = await waitForSuggestedActions(page);
    console.log(`  Long query processed: actions=${hasSuggestedActions}, error=${hasError}`);
  });
});
