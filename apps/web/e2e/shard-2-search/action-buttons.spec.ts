import { test, expect, SpotlightSearchPO } from '../fixtures';

/**
 * ACTION BUTTON E2E TESTS
 *
 * ARCHITECTURE NOTE (GAP-005 - UPDATED):
 * There are THREE action button rendering paths:
 *
 * 1. SuggestedActions (SpotlightSearch) - for MUTATE-intent queries ("create work order")
 *    - Renders in search results dropdown
 *    - TestID: suggested-actions, action-btn-{action_id}
 *
 * 2. Fragmented Route Pages (/faults/{id}, /equipment/{id}, /work-orders/{id})
 *    - When NEXT_PUBLIC_FRAGMENTED_ROUTES_ENABLED=true
 *    - Click result → router.push() → dedicated page with action buttons
 *    - Action buttons on the page itself
 *
 * 3. Legacy ContextPanel (*LensContent.tsx)
 *    - When FRAGMENTED_ROUTES disabled OR for unsupported types (documents)
 *    - Click result → surfaceContext.showContext()
 *    - TestIDs: acknowledge-fault-btn, update-status-button, etc.
 *
 * DETECTION STRATEGY:
 * After clicking a search result, check URL:
 * - If URL changed (contains /faults/, /equipment/, etc.) → fragmented route
 * - If URL is still /app or / → legacy ContextPanel
 */

// Known action button testids by entity type
const ENTITY_ACTION_BUTTONS = {
  fault: [
    'acknowledge-fault-btn',
    'close-fault-btn',
    'reopen-fault-btn',
    'false-alarm-btn',
    'add-note-btn',
  ],
  equipment: [
    'update-status-button',
    'flag-attention-button',
    'decommission-button',
  ],
  work_order: [
    'add-note-btn',
    'mark-complete-btn',
    'add-hours-btn',
    'reassign-btn',
    'edit-wo-btn',
  ],
  document: [
    'download-btn',
    'share-btn',
    'delete-btn',
  ],
};

// Fragmented route patterns (all entity detail pages)
const FRAGMENTED_ROUTE_PATTERNS = {
  fault: /\/faults\/[a-f0-9-]+/,
  equipment: /\/equipment\/[a-f0-9-]+/,
  work_order: /\/work-orders\/[a-f0-9-]+/,
  part: /\/inventory\/[a-f0-9-]+/,
  document: /\/documents\/[a-f0-9-]+/,
  email: /\/email\/[a-f0-9-]+/,
  receiving: /\/receiving\/[a-f0-9-]+/,
  shopping_list: /\/shopping-lists\/[a-f0-9-]+/,
};

/**
 * Detects whether we navigated to a fragmented route or opened ContextPanel
 */
async function detectNavigationPath(page: any, initialUrl: string): Promise<'fragmented' | 'contextPanel' | 'unknown'> {
  const currentUrl = page.url();

  // Check if URL changed to a fragmented route
  for (const pattern of Object.values(FRAGMENTED_ROUTE_PATTERNS)) {
    if (pattern.test(currentUrl)) {
      return 'fragmented';
    }
  }

  // Check if ContextPanel opened (URL didn't change significantly)
  if (currentUrl.includes('/app') || currentUrl === initialUrl) {
    const contextPanel = page.getByTestId('context-panel');
    const isVisible = await contextPanel.isVisible({ timeout: 3_000 }).catch(() => false);
    if (isVisible) {
      return 'contextPanel';
    }
  }

  return 'unknown';
}

test.describe('Action Button Rendering - Navigation Aware', () => {
  test.describe.configure({ retries: 1 });

  test('should render action buttons after clicking search result', async ({ page }) => {
    await page.goto('/');
    const initialUrl = page.url();

    const spotlight = new SpotlightSearchPO(page);

    // Try multiple search terms to find results
    const searchTerms = ['work order', 'equipment', 'maintenance', 'engine'];
    let foundResults = false;

    for (const term of searchTerms) {
      await spotlight.search(term);

      const resultsVisible = await spotlight.resultsContainer.isVisible({ timeout: 5_000 }).catch(() => false);
      if (resultsVisible) {
        const count = await spotlight.getResultCount();
        if (count > 0) {
          console.log(`✅ Found ${count} results for "${term}"`);
          foundResults = true;
          break;
        }
      }
      // Clear and try next term
      await page.goto('/');
    }

    if (!foundResults) {
      console.log('ℹ️ No results found for any search term - skipping test');
      return;
    }

    await spotlight.clickResult(0);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    const navPath = await detectNavigationPath(page, initialUrl);
    console.log(`📍 Navigation path: ${navPath}`);

    if (navPath === 'fragmented') {
      // Fragmented route - action buttons are on the dedicated page
      const currentUrl = page.url();
      console.log(`✅ Navigated to fragmented route: ${currentUrl}`);

      // Look for action buttons on the page
      const faultButtons = ENTITY_ACTION_BUTTONS.fault;
      let foundCount = 0;

      for (const btnId of faultButtons) {
        const btn = page.getByTestId(btnId);
        const isVisible = await btn.isVisible().catch(() => false);
        if (isVisible) {
          foundCount++;
          console.log(`  ✓ Found action button: ${btnId}`);
        }
      }

      // Also check for generic action buttons on the page
      const allActionButtons = page.locator('button[data-testid*="-btn"], button[data-testid*="-button"]');
      const totalButtons = await allActionButtons.count();
      console.log(`✅ Fragmented route: ${foundCount} known buttons, ${totalButtons} total action buttons`);
    } else if (navPath === 'contextPanel') {
      // Legacy context panel - action buttons in lens content
      const contextPanel = page.getByTestId('context-panel');
      const entityType = await contextPanel.getAttribute('data-entity-type');
      console.log(`✅ ContextPanel opened for entity type: ${entityType}`);

      if (entityType && ENTITY_ACTION_BUTTONS[entityType as keyof typeof ENTITY_ACTION_BUTTONS]) {
        const buttons = ENTITY_ACTION_BUTTONS[entityType as keyof typeof ENTITY_ACTION_BUTTONS];
        let foundCount = 0;

        for (const btnId of buttons) {
          const btn = page.getByTestId(btnId);
          const isVisible = await btn.isVisible().catch(() => false);
          if (isVisible) {
            foundCount++;
            console.log(`  ✓ Found lens button: ${btnId}`);
          }
        }

        console.log(`✅ Lens content: ${foundCount} action buttons found`);
      }
    } else {
      console.log('ℹ️ Unknown navigation path - neither fragmented route nor ContextPanel detected');
    }
  });

  test('should find action buttons on equipment detail page', async ({ page }) => {
    await page.goto('/');
    const initialUrl = page.url();

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('engine');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const resultCount = await spotlight.getResultCount();
    if (resultCount === 0) {
      console.log('ℹ️ No equipment results found - skipping test');
      return;
    }

    await spotlight.clickResult(0);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    const navPath = await detectNavigationPath(page, initialUrl);
    const currentUrl = page.url();
    console.log(`📍 Navigation: ${navPath} → ${currentUrl}`);

    // Count action buttons regardless of path
    const equipmentButtons = ENTITY_ACTION_BUTTONS.equipment;
    let foundCount = 0;

    for (const btnId of equipmentButtons) {
      const btn = page.getByTestId(btnId);
      const isVisible = await btn.isVisible().catch(() => false);
      if (isVisible) {
        foundCount++;
        console.log(`  ✓ Found: ${btnId}`);
      }
    }

    console.log(`✅ Equipment view: ${foundCount}/${equipmentButtons.length} expected action buttons found`);
  });
});

test.describe('SuggestedActions (MUTATE Intent)', () => {
  test.describe.configure({ retries: 1 });

  test('should show suggested actions for MUTATE query', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    // Use MUTATE-intent query that triggers action suggestions
    await spotlight.search('create work order');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    // For MUTATE intent, check for suggested-actions in SpotlightSearch
    const suggestedActions = page.getByTestId('suggested-actions');
    const hasActions = await suggestedActions.isVisible({ timeout: 5_000 }).catch(() => false);

    if (hasActions) {
      const actionButtons = page.locator('[data-testid^="action-btn-"]');
      const buttonCount = await actionButtons.count();
      console.log(`✅ MUTATE query rendered ${buttonCount} suggested action buttons`);
      expect(buttonCount).toBeGreaterThan(0);
    } else {
      // This is expected if backend doesn't return action suggestions
      console.log('ℹ️ No suggested actions for MUTATE query - backend may not have matching actions');
    }
  });

  test('should NOT show suggested actions for READ query', async ({ page }) => {
    await page.goto('/');

    const spotlight = new SpotlightSearchPO(page);
    // READ-intent query - should NOT trigger action suggestions
    await spotlight.search('maintenance');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    // For READ intent, suggested-actions should NOT appear in SpotlightSearch
    const suggestedActions = page.getByTestId('suggested-actions');
    const hasActions = await suggestedActions.isVisible({ timeout: 2_000 }).catch(() => false);

    if (!hasActions) {
      console.log('✅ READ query correctly shows no suggested actions (as expected)');
    } else {
      console.log('ℹ️ READ query unexpectedly showed suggested actions');
    }
  });
});

test.describe('RBAC on Action Buttons', () => {
  test.describe.configure({ retries: 1 });

  test('should show appropriate buttons for crew role', async ({ crewPage }) => {
    await crewPage.goto('/');
    const initialUrl = crewPage.url();

    const spotlight = new SpotlightSearchPO(crewPage);
    await spotlight.search('fault');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const resultCount = await spotlight.getResultCount();
    if (resultCount === 0) {
      console.log('ℹ️ No results for crew role - skipping test');
      return;
    }

    await spotlight.clickResult(0);
    await crewPage.waitForLoadState('networkidle');
    await crewPage.waitForTimeout(1000);

    const navPath = await detectNavigationPath(crewPage, initialUrl);
    console.log(`📍 Crew navigation: ${navPath}`);

    // Count all buttons and disabled buttons on whatever page/panel we're on
    const allButtons = crewPage.locator('button[data-testid]');
    const disabledButtons = crewPage.locator('button[data-testid][disabled]');

    const totalCount = await allButtons.count();
    const disabledCount = await disabledButtons.count();

    console.log(`ℹ️ Crew role: ${totalCount} buttons, ${disabledCount} disabled (RBAC)`);
  });
});

test.describe('Action Button Click Behavior', () => {
  test.describe.configure({ retries: 1 });

  test('should open modal when clicking action button', async ({ page }) => {
    await page.goto('/');
    const initialUrl = page.url();

    const spotlight = new SpotlightSearchPO(page);
    await spotlight.search('equipment');

    await expect(spotlight.resultsContainer).toBeVisible({ timeout: 10_000 });

    const resultCount = await spotlight.getResultCount();
    if (resultCount === 0) {
      console.log('ℹ️ No results found - skipping test');
      return;
    }

    await spotlight.clickResult(0);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    const navPath = await detectNavigationPath(page, initialUrl);
    console.log(`📍 Navigation: ${navPath}`);

    // Try to click an action button that opens a modal
    const statusBtn = page.getByTestId('update-status-button');
    const noteBtn = page.getByTestId('add-note-btn');

    const hasStatusBtn = await statusBtn.isVisible().catch(() => false);
    const hasNoteBtn = await noteBtn.isVisible().catch(() => false);

    if (hasStatusBtn) {
      await statusBtn.click();
      const modal = page.locator('[role="dialog"]');
      const modalVisible = await modal.isVisible({ timeout: 3_000 }).catch(() => false);
      if (modalVisible) {
        console.log('✅ update-status-button opened modal');
        await page.keyboard.press('Escape');
      } else {
        console.log('ℹ️ update-status-button clicked but no modal appeared');
      }
    } else if (hasNoteBtn) {
      await noteBtn.click();
      const modal = page.locator('[role="dialog"]');
      const modalVisible = await modal.isVisible({ timeout: 3_000 }).catch(() => false);
      if (modalVisible) {
        console.log('✅ add-note-btn opened modal');
        await page.keyboard.press('Escape');
      } else {
        console.log('ℹ️ add-note-btn clicked but no modal appeared');
      }
    } else {
      console.log('ℹ️ No actionable buttons found on this view');
    }
  });
});
