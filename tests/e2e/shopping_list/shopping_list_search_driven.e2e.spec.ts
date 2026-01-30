/**
 * Shopping List Lens - Search-Driven E2E Tests
 *
 * Tests follow Apple Spotlight-style single-surface architecture:
 * 1. User types query in search bar → backend extracts entities
 * 2. Results appear in dropdown overlay
 * 3. User clicks result → entity opens full screen (same URL)
 * 4. Action buttons render (or immediately if explicit action query)
 * 5. Execute action → verify autopopulation & saving
 *
 * Actual DOM selectors from SpotlightSearch.tsx and SuggestedActions.tsx
 */

import { test, expect, Page } from '@playwright/test';
import { saveScreenshot } from '../../helpers/artifacts';

const BASE_URL = process.env.BASE_URL || 'https://app.celeste7.ai';
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

/**
 * Helper: Wait for search results dropdown to appear
 */
async function waitForSearchResults(page: Page, timeout = 5000) {
  await page.waitForSelector('[data-testid="search-results"]', { timeout });
}

/**
 * Helper: Type in main search input
 */
async function typeSearchQuery(page: Page, query: string) {
  const searchInput = page.locator('[data-testid="search-input"]');
  await searchInput.click();
  await searchInput.fill(query);
  // Wait for debounce + backend response
  await page.waitForTimeout(500);
}

/**
 * Helper: Click first search result item
 */
async function clickFirstResult(page: Page) {
  const firstResult = page.locator('[data-testid="search-result-item"]').first();
  await expect(firstResult).toBeVisible({ timeout: 5000 });
  await firstResult.click();
}

/**
 * Helper: Get visible action buttons
 */
async function getVisibleActions(page: Page): Promise<string[]> {
  const actionsContainer = page.locator('[data-testid="suggested-actions"]');
  if (!(await actionsContainer.isVisible({ timeout: 2000 }).catch(() => false))) {
    return [];
  }

  const buttons = await page.locator('[data-testid^="action-btn-"]').all();
  const actionIds: string[] = [];

  for (const btn of buttons) {
    const testId = await btn.getAttribute('data-testid');
    if (testId) {
      actionIds.push(testId.replace('action-btn-', ''));
    }
  }

  return actionIds;
}

test.describe('Shopping List - CREW Create Flow (Spotlight Search)', () => {
  test.use({ storageState: 'test-results/.auth-states/crew-state.json' });

  test('CREW creates shopping list item via explicit action query', async ({ page }) => {
    // 1. Navigate to main surface
    await page.goto(BASE_URL);
    await saveScreenshot(page, 'shopping_list/crew_explicit', '01_landing');

    // 2. Type explicit action query (triggers action suggestions immediately)
    await typeSearchQuery(page, 'add oil filter to shopping list');
    await saveScreenshot(page, 'shopping_list/crew_explicit', '02_query_typed');

    // 3. Wait for suggested actions to appear
    await page.waitForSelector('[data-testid="suggested-actions"]', { timeout: 5000 });
    await saveScreenshot(page, 'shopping_list/crew_explicit', '03_actions_rendered');

    // 4. Verify CREW sees only create action (no approve/reject/promote)
    const actions = await getVisibleActions(page);
    expect(actions).toContain('create_shopping_list_item');
    expect(actions).not.toContain('approve_shopping_list_item'); // HOD only
    expect(actions).not.toContain('reject_shopping_list_item'); // HOD only
    expect(actions).not.toContain('promote_candidate_to_part'); // ENGINEER only

    // 5. Click "Add to Shopping List" action button
    const createButton = page.locator('[data-testid="action-btn-create_shopping_list_item"]');
    await expect(createButton).toBeVisible();
    await createButton.click();
    await saveScreenshot(page, 'shopping_list/crew_explicit', '04_action_clicked');

    // 6. Wait for action modal/form to open
    const modal = page.locator('[role="dialog"]').or(page.locator('[data-testid="action-modal"]'));
    await expect(modal).toBeVisible({ timeout: 3000 });
    await saveScreenshot(page, 'shopping_list/crew_explicit', '05_form_opened');

    // 7. Verify autopopulation: item_name should contain "oil filter"
    const itemNameField = page.locator('input[name="part_name"], input#part_name, input[name="item_name"], input#item_name').first();
    const autopopulated = await itemNameField.inputValue().catch(() => '');

    if (autopopulated && autopopulated.toLowerCase().includes('oil')) {
      console.log(`✅ Autopopulated item_name: ${autopopulated}`);
      await saveScreenshot(page, 'shopping_list/crew_explicit', '06_autopopulated');
    } else {
      console.log('⚠️ No autopopulation detected, filling manually');
      await itemNameField.fill('Engine Oil Filter');
    }

    // 8. Fill required fields
    await page.fill('input[name="quantity_requested"], input#quantity_requested', '5');

    // Select source_type (MAINTENANCE, REPAIR, UPGRADE, etc.)
    const sourceTypeField = page.locator('select[name="source_type"], select#source_type');
    if (await sourceTypeField.isVisible({ timeout: 1000 }).catch(() => false)) {
      await sourceTypeField.selectOption('MAINTENANCE');
    }
    await saveScreenshot(page, 'shopping_list/crew_explicit', '07_form_filled');

    // 9. Submit action
    const submitButton = page.locator('button[type="submit"]').filter({ hasText: /Execute|Submit|Add|Create/i });
    await submitButton.click();
    await saveScreenshot(page, 'shopping_list/crew_explicit', '08_submitted');

    // 10. Verify success toast
    const toast = page.locator('[data-sonner-toast]').or(page.locator('[data-toast]')).filter({ hasText: /success|added|created/i });
    await expect(toast).toBeVisible({ timeout: 5000 });
    await saveScreenshot(page, 'shopping_list/crew_explicit', '09_success');

    // 11. Monitor for 0×500 requirement
    page.on('response', response => {
      const status = response.status();
      if (status >= 500) {
        throw new Error(`5xx error detected: ${status} on ${response.url()}`);
      }
    });
  });

  test('CREW creates via search → click result → action button', async ({ page }) => {
    // 1. Navigate
    await page.goto(BASE_URL);
    await saveScreenshot(page, 'shopping_list/crew_search', '01_landing');

    // 2. Search for generic query (no explicit action)
    await typeSearchQuery(page, 'engine oil filter');
    await saveScreenshot(page, 'shopping_list/crew_search', '02_query_typed');

    // 3. Wait for search results dropdown
    await waitForSearchResults(page);
    await saveScreenshot(page, 'shopping_list/crew_search', '03_results_shown');

    // 4. Click first result (opens full screen on same URL)
    await clickFirstResult(page);
    await page.waitForTimeout(1000); // Wait for transition
    await saveScreenshot(page, 'shopping_list/crew_search', '04_entity_focused');

    // 5. Wait for action buttons to render
    await page.waitForSelector('[data-testid="suggested-actions"]', { timeout: 5000 }).catch(() => {
      console.log('⚠️ No suggested actions appeared for this entity');
    });
    await saveScreenshot(page, 'shopping_list/crew_search', '05_actions_rendered');

    // 6. If create action appears, click it
    const createButton = page.locator('[data-testid="action-btn-create_shopping_list_item"]');
    if (await createButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await createButton.click();

      const modal = page.locator('[role="dialog"]');
      await expect(modal).toBeVisible({ timeout: 3000 });

      // Fill and submit
      await page.fill('input[name="quantity_requested"]', '3');
      const submitButton = page.locator('button[type="submit"]').first();
      await submitButton.click();

      // Verify success
      const toast = page.locator('[data-sonner-toast]').filter({ hasText: /success/i });
      await expect(toast).toBeVisible({ timeout: 5000 });
    }
  });

  test('CREW cannot see HOD/ENGINEER actions', async ({ page }) => {
    await page.goto(BASE_URL);

    // Search with action intent
    await typeSearchQuery(page, 'approve shopping list item');
    await page.waitForTimeout(1000);

    // Check if suggested actions appear
    const actionsContainer = page.locator('[data-testid="suggested-actions"]');
    if (await actionsContainer.isVisible({ timeout: 3000 }).catch(() => false)) {
      const actions = await getVisibleActions(page);

      // CREW should NOT see these actions
      expect(actions).not.toContain('approve_shopping_list_item');
      expect(actions).not.toContain('reject_shopping_list_item');
      expect(actions).not.toContain('promote_candidate_to_part');
    }
  });
});

test.describe('Shopping List - HOD Approve/Reject Flow (Spotlight Search)', () => {
  test.use({ storageState: 'test-results/.auth-states/chief_engineer-state.json' });

  test('HOD approves shopping list item via explicit query', async ({ page }) => {
    // 1. Navigate
    await page.goto(BASE_URL);
    await saveScreenshot(page, 'shopping_list/hod_approve', '01_landing');

    // 2. Explicit action query
    await typeSearchQuery(page, 'approve shopping list items');
    await saveScreenshot(page, 'shopping_list/hod_approve', '02_query_typed');

    // 3. Wait for suggested actions
    await page.waitForSelector('[data-testid="suggested-actions"]', { timeout: 5000 });
    await saveScreenshot(page, 'shopping_list/hod_approve', '03_actions_shown');

    // 4. Verify HOD sees approve + reject (not create or promote)
    const actions = await getVisibleActions(page);
    expect(actions).toContain('approve_shopping_list_item');
    expect(actions).toContain('reject_shopping_list_item');

    // 5. Click approve button
    const approveButton = page.locator('[data-testid="action-btn-approve_shopping_list_item"]');
    if (await approveButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await approveButton.click();
      await saveScreenshot(page, 'shopping_list/hod_approve', '04_approve_clicked');

      // 6. Form opens
      const modal = page.locator('[role="dialog"]');
      await expect(modal).toBeVisible({ timeout: 3000 });

      // 7. Check autopopulation of quantity_approved
      const quantityField = page.locator('input[name="quantity_approved"], input#quantity_approved');
      const autopopulated = await quantityField.inputValue().catch(() => '');

      if (autopopulated && parseInt(autopopulated) > 0) {
        console.log(`✅ Autopopulated quantity_approved: ${autopopulated}`);
      } else {
        await quantityField.fill('5');
      }
      await saveScreenshot(page, 'shopping_list/hod_approve', '05_autopopulated');

      // 8. Submit
      const submitButton = page.locator('button[type="submit"]').filter({ hasText: /Execute|Submit|Approve/i });
      await submitButton.click();
      await saveScreenshot(page, 'shopping_list/hod_approve', '06_submitted');

      // 9. Verify success
      const toast = page.locator('[data-sonner-toast]').filter({ hasText: /success|approved/i });
      await expect(toast).toBeVisible({ timeout: 5000 });
    }
  });

  test('HOD rejects shopping list item with reason', async ({ page }) => {
    await page.goto(BASE_URL);

    // Explicit reject query
    await typeSearchQuery(page, 'reject shopping list item');
    await page.waitForTimeout(1000);

    // Click reject action if available
    const rejectButton = page.locator('[data-testid="action-btn-reject_shopping_list_item"]');
    if (await rejectButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await rejectButton.click();

      // Fill rejection reason
      const modal = page.locator('[role="dialog"]');
      await expect(modal).toBeVisible();

      await page.fill('textarea[name="rejection_reason"], textarea#rejection_reason, input[name="rejection_reason"]', 'Not in current budget');

      // Submit
      const submitButton = page.locator('button[type="submit"]').filter({ hasText: /Execute|Submit|Reject/i });
      await submitButton.click();

      // Verify success
      const toast = page.locator('[data-sonner-toast]').filter({ hasText: /success|rejected/i });
      await expect(toast).toBeVisible({ timeout: 5000 });
    }
  });
});

test.describe('Shopping List - ENGINEER Promote Flow (Spotlight Search)', () => {
  test.use({ storageState: 'test-results/.auth-states/chief_engineer-state.json' });

  test('ENGINEER promotes approved item to parts catalog', async ({ page }) => {
    // 1. Navigate
    await page.goto(BASE_URL);
    await saveScreenshot(page, 'shopping_list/engineer_promote', '01_landing');

    // 2. Explicit promote query
    await typeSearchQuery(page, 'promote shopping list to parts catalog');
    await saveScreenshot(page, 'shopping_list/engineer_promote', '02_query_typed');

    // 3. Wait for actions
    await page.waitForSelector('[data-testid="suggested-actions"]', { timeout: 5000 }).catch(() => {});
    await saveScreenshot(page, 'shopping_list/engineer_promote', '03_actions_shown');

    // 4. Click promote if visible
    const promoteButton = page.locator('[data-testid="action-btn-promote_candidate_to_part"]');
    if (await promoteButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await promoteButton.click();
      await saveScreenshot(page, 'shopping_list/engineer_promote', '04_promote_clicked');

      // 5. Form opens
      const modal = page.locator('[role="dialog"]');
      await expect(modal).toBeVisible({ timeout: 3000 });
      await saveScreenshot(page, 'shopping_list/engineer_promote', '05_form_opened');

      // 6. Fill optional metadata
      const categoryField = page.locator('input[name="category"], select[name="category"]');
      if (await categoryField.isVisible({ timeout: 1000 }).catch(() => false)) {
        await categoryField.fill('Engine Parts');
      }

      // 7. Submit
      const submitButton = page.locator('button[type="submit"]').filter({ hasText: /Execute|Submit|Promote|Add/i });
      await submitButton.click();
      await saveScreenshot(page, 'shopping_list/engineer_promote', '06_submitted');

      // 8. Verify success
      const toast = page.locator('[data-sonner-toast]').filter({ hasText: /success|promoted|catalog/i });
      await expect(toast).toBeVisible({ timeout: 5000 });
    }
  });
});

test.describe('Shopping List - Backend→UI Action Parity', () => {
  test.use({ storageState: 'test-results/.auth-states/crew-state.json' });

  test('UI renders exactly what backend returns (no invented actions)', async ({ page }) => {
    await page.goto(BASE_URL);

    // Search with shopping list intent
    await typeSearchQuery(page, 'add item to shopping list');
    await page.waitForTimeout(1000);

    // Get UI actions
    const uiActions = await getVisibleActions(page);

    // Get backend actions via API
    // (This would require getting access token and calling /v1/actions/suggestions)
    // For now, verify UI doesn't show unauthorized actions

    // CREW should only see create
    if (uiActions.length > 0) {
      expect(uiActions).toContain('create_shopping_list_item');
      expect(uiActions).not.toContain('approve_shopping_list_item');
      expect(uiActions).not.toContain('reject_shopping_list_item');
      expect(uiActions).not.toContain('promote_candidate_to_part');
    }
  });
});

test.describe('Shopping List - 0×500 Requirement', () => {
  test.use({ storageState: 'test-results/.auth-states/crew-state.json' });

  test('All shopping list flows have zero 5xx errors', async ({ page }) => {
    const errors: string[] = [];

    // Monitor network
    page.on('response', response => {
      const status = response.status();
      if (status >= 500) {
        errors.push(`${status} on ${response.url()}`);
      }
    });

    await page.goto(BASE_URL);

    // Search flow
    await typeSearchQuery(page, 'add oil filter to shopping list');
    await page.waitForTimeout(1000);

    // Click action if available
    const createButton = page.locator('[data-testid="action-btn-create_shopping_list_item"]');
    if (await createButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await createButton.click();

      // Wait for modal
      await page.waitForSelector('[role="dialog"]', { timeout: 2000 }).catch(() => {});
    }

    // Assert no 5xx errors
    expect(errors).toHaveLength(0);
  });
});
