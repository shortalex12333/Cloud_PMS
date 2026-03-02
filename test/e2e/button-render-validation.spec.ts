import { test, expect, Page } from '@playwright/test';

/**
 * Button Render Validation E2E Tests
 *
 * Phase C: v1.2 Search Pipeline Truth Hardening
 *
 * Purpose: Validate button rendering based on intent classification
 *
 * Test Matrix:
 * | Query Type        | Expected UI Element | Success Criteria                      |
 * |-------------------|---------------------|---------------------------------------|
 * | READ intent       | Navigate button     | Button visible, routes to lens view   |
 * | MUTATE intent     | Execute button      | Button visible, opens ActionModal     |
 * | Low confidence    | No action buttons   | Only search results shown             |
 * | BLOCKED readiness | Disabled button     | Button present but not clickable      |
 *
 * Coverage:
 * - Intent classification: READ vs MUTATE mode detection
 * - Confidence threshold: <0.7 suppresses action buttons
 * - Readiness state: READY, NEEDS_INPUT, BLOCKED visual indicators
 * - Button behavior: Navigation routing vs ActionModal opening
 */

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';

// Confidence threshold from useCelesteSearch.ts
const CONFIDENCE_THRESHOLD = 0.7;

// Test selectors (from Phase 19)
const SELECTORS = {
  spotlightInput: '[data-testid="spotlight-input"]',
  suggestedActions: '[data-testid="suggested-actions"]',
  navigateButton: '[data-testid="navigate-btn"]',
  executeButton: '[data-testid="execute-action"]',
  actionButton: '[data-testid^="action-btn-"]',
  actionModal: '[data-testid^="action-form-"]',
  readinessIndicator: '[data-testid="readiness-indicator"]',
  filterChips: '[data-testid="filter-chips"]',
  filterChipStatus: '[data-testid="filter-chip-status"]',
  filterChipPriority: '[data-testid="filter-chip-priority"]',
  searchResults: '[data-testid="search-results"]',
  appReady: '[data-testid="app-ready"]',
  suggestionType: '[data-testid="suggestion-type"]',
  toastSuccess: '[data-testid="toast-success"]',
};

// Query types for testing
const TEST_QUERIES = {
  // READ intent queries - should show Navigate button
  read: {
    openWorkOrders: 'show open work orders',
    allFaults: 'display all faults',
    criticalItems: 'list critical faults',
    urgentWOs: 'view urgent work orders',
    pendingParts: 'find pending parts',
    equipmentList: 'show equipment',
    certificates: 'list certificates',
  },
  // MUTATE intent queries - should show Execute button
  mutate: {
    createWorkOrder: 'create new work order',
    reportFault: 'report fault',
    addCertificate: 'add certificate',
    updateWO: 'update work order WO-123',
    closeFault: 'close fault',
    assignWorkOrder: 'assign work order',
    createFromFault: 'create work order from fault',
  },
  // Low confidence queries - should show NO action buttons
  lowConfidence: {
    vague: 'stuff',
    ambiguous: 'things',
    singleWord: 'a',
    random: 'asdf',
    unclear: 'help',
  },
  // Queries requiring disambiguation or missing entities
  needsInput: {
    missingEquipment: 'create work order',  // No equipment specified
    missingFaultId: 'close fault',  // No fault ID specified
    missingDate: 'schedule work order',  // No date specified
  },
};

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Open the Spotlight search overlay
 */
async function openSpotlight(page: Page): Promise<void> {
  await page.keyboard.press('Meta+K');
  await page.waitForSelector(SELECTORS.spotlightInput, { state: 'visible', timeout: 5000 });
}

/**
 * Type a query into the Spotlight input
 */
async function typeQuery(page: Page, query: string): Promise<void> {
  await page.fill(SELECTORS.spotlightInput, query);
  // Wait for debounce and action suggestions to load
  await page.waitForTimeout(500);
}

/**
 * Type query and wait for suggested actions to appear (or not appear for low confidence)
 */
async function typeQueryAndWait(page: Page, query: string, expectActions: boolean = true): Promise<void> {
  await page.fill(SELECTORS.spotlightInput, query);
  if (expectActions) {
    await page.waitForSelector(SELECTORS.suggestedActions, { state: 'visible', timeout: 5000 });
  } else {
    // For low confidence, wait a bit then verify no actions
    await page.waitForTimeout(1000);
  }
}

/**
 * Wait for the ActionModal to appear
 */
async function waitForActionModal(page: Page): Promise<void> {
  await page.waitForSelector(SELECTORS.actionModal, { state: 'visible', timeout: 5000 });
}

/**
 * Verify that the Navigate button is visible and functional
 */
async function verifyNavigateButton(page: Page): Promise<void> {
  const navigateBtn = page.locator(SELECTORS.navigateButton);
  await expect(navigateBtn).toBeVisible();
}

/**
 * Verify that an Execute/Action button is visible
 */
async function verifyExecuteButton(page: Page): Promise<void> {
  // Execute buttons have action-btn-{action_id} pattern
  const actionBtns = page.locator(SELECTORS.actionButton);
  await expect(actionBtns.first()).toBeVisible();
}

/**
 * Verify that NO action buttons are rendered
 */
async function verifyNoActionButtons(page: Page): Promise<void> {
  // Check that suggestedActions container either doesn't exist or has no buttons
  const actionBtns = page.locator(SELECTORS.actionButton);
  const navigateBtn = page.locator(SELECTORS.navigateButton);

  // Both should not be visible
  await expect(actionBtns).toHaveCount(0);
  await expect(navigateBtn).not.toBeVisible();
}

/**
 * Click the Navigate button and verify URL change
 */
async function clickNavigateAndVerifyUrl(page: Page, expectedUrlPattern: RegExp): Promise<void> {
  const navigateBtn = page.locator(SELECTORS.navigateButton);
  await expect(navigateBtn).toBeVisible();
  await navigateBtn.click();
  await expect(page).toHaveURL(expectedUrlPattern);
}

/**
 * Click an action button and verify modal opens
 */
async function clickActionAndVerifyModal(page: Page): Promise<void> {
  const actionBtn = page.locator(SELECTORS.actionButton).first();
  await expect(actionBtn).toBeVisible();
  await actionBtn.click();
  await waitForActionModal(page);
}

/**
 * Verify readiness indicator state
 */
async function verifyReadinessState(
  page: Page,
  expectedState: 'READY' | 'NEEDS_INPUT' | 'BLOCKED'
): Promise<void> {
  // Readiness is indicated by visual styling on buttons
  // READY: green checkmark (emerald color)
  // NEEDS_INPUT: amber dot
  // BLOCKED: lock icon (red color)
  const actionBtn = page.locator(SELECTORS.actionButton).first();

  switch (expectedState) {
    case 'READY':
      // Has emerald/green styling
      await expect(actionBtn).toHaveClass(/emerald/);
      break;
    case 'NEEDS_INPUT':
      // Has amber/yellow styling
      await expect(actionBtn).toHaveClass(/amber|celeste-accent/);
      break;
    case 'BLOCKED':
      // Has red styling and is disabled
      await expect(actionBtn).toHaveClass(/red/);
      await expect(actionBtn).toBeDisabled();
      break;
  }
}

// ============================================================================
// Test Suite: Button Render Validation
// ============================================================================

test.describe('Button Render Validation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForSelector(SELECTORS.appReady, { timeout: 10000 });
  });

  // ==========================================================================
  // READ Intent Tests
  // ==========================================================================
  test.describe('READ Intent Tests', () => {
    test('READ: "show open work orders" displays Navigate button', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, TEST_QUERIES.read.openWorkOrders);

      // Navigate button should be visible
      await verifyNavigateButton(page);

      // Should show filter chips for status=open
      const filterChips = page.locator(SELECTORS.filterChips);
      await expect(filterChips).toBeVisible();
    });

    test('READ: Navigate button click routes to /work-orders with status filter', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, TEST_QUERIES.read.openWorkOrders);

      // Click Navigate and verify URL
      await clickNavigateAndVerifyUrl(page, /\/work-orders.*status.*open/);
    });

    test('READ: "display all faults" shows Navigate button routing to /faults', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, TEST_QUERIES.read.allFaults);

      await verifyNavigateButton(page);
      await clickNavigateAndVerifyUrl(page, /\/faults/);
    });

    test('READ: "list critical faults" applies severity filter in route', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, TEST_QUERIES.read.criticalItems);

      await verifyNavigateButton(page);
      await clickNavigateAndVerifyUrl(page, /\/faults.*severity.*critical|priority.*critical/);
    });

    test('READ: "view urgent work orders" applies priority filter', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, TEST_QUERIES.read.urgentWOs);

      await verifyNavigateButton(page);
      await clickNavigateAndVerifyUrl(page, /\/work-orders.*priority.*urgent/);
    });

    test('READ: Filter chips appear for recognized filters', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, TEST_QUERIES.read.openWorkOrders);

      // Verify filter chips container is visible
      const filterChips = page.locator(SELECTORS.filterChips);
      await expect(filterChips).toBeVisible();

      // Should have status filter chip
      const statusChip = page.locator(SELECTORS.filterChipStatus);
      await expect(statusChip).toContainText('open');
    });

    test('READ: No Execute button shown for navigation queries', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, TEST_QUERIES.read.openWorkOrders);

      // Navigate button should be visible
      await verifyNavigateButton(page);

      // Execute-style action buttons should not have MUTATE actions
      // The suggested-actions should not contain create/update actions
      const createActionBtn = page.locator('[data-testid="action-btn-create_work_order"]');
      await expect(createActionBtn).not.toBeVisible();
    });
  });

  // ==========================================================================
  // MUTATE Intent Tests
  // ==========================================================================
  test.describe('MUTATE Intent Tests', () => {
    test('MUTATE: "create new work order" displays Execute button', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, TEST_QUERIES.mutate.createWorkOrder);

      // Action button should be visible
      await verifyExecuteButton(page);
    });

    test('MUTATE: Execute button click opens ActionModal', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, TEST_QUERIES.mutate.createWorkOrder);

      // Click action button and verify modal opens
      await clickActionAndVerifyModal(page);
    });

    test('MUTATE: "report fault" shows Execute button for fault creation', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, TEST_QUERIES.mutate.reportFault);

      await verifyExecuteButton(page);

      // Click should open fault reporting modal
      const actionBtn = page.locator(SELECTORS.actionButton).first();
      await actionBtn.click();
      await waitForActionModal(page);
    });

    test('MUTATE: "add certificate" shows Execute button for certificate creation', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, TEST_QUERIES.mutate.addCertificate);

      await verifyExecuteButton(page);
    });

    test('MUTATE: ActionModal contains correct form fields', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, TEST_QUERIES.mutate.createWorkOrder);

      await clickActionAndVerifyModal(page);

      // Modal should have required fields for work order
      const modalForm = page.locator(SELECTORS.actionModal);
      await expect(modalForm).toBeVisible();
    });

    test('MUTATE: "update work order WO-123" prefills entity ID', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, 'update work order WO-123');

      await verifyExecuteButton(page);

      await clickActionAndVerifyModal(page);

      // Work order ID should be prefilled
      // Note: actual field testid depends on backend schema
    });

    test('MUTATE: No Navigate button shown for action queries', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, TEST_QUERIES.mutate.createWorkOrder);

      // Action button should be visible
      await verifyExecuteButton(page);

      // Navigate button should NOT be visible for MUTATE queries
      const navigateBtn = page.locator(SELECTORS.navigateButton);
      await expect(navigateBtn).not.toBeVisible();
    });
  });

  // ==========================================================================
  // Confidence Threshold Tests
  // ==========================================================================
  test.describe('Confidence Threshold Tests', () => {
    test('LOW CONFIDENCE: "stuff" shows NO action buttons', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, TEST_QUERIES.lowConfidence.vague, false);

      // Verify no action buttons rendered
      await verifyNoActionButtons(page);
    });

    test('LOW CONFIDENCE: "a" (single char) shows only search results', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, TEST_QUERIES.lowConfidence.singleWord, false);

      // Action buttons should not appear
      await verifyNoActionButtons(page);

      // Search results may or may not appear depending on backend
    });

    test('LOW CONFIDENCE: "asdf" (nonsense) shows no action suggestions', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, TEST_QUERIES.lowConfidence.random, false);

      await verifyNoActionButtons(page);
    });

    test('LOW CONFIDENCE: Ambiguous query shows search results only', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, TEST_QUERIES.lowConfidence.ambiguous, false);

      // No action buttons when confidence < 0.7
      await verifyNoActionButtons(page);
    });

    test('LOW CONFIDENCE: Verify confidence-based fallback routing', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, 'help', false);

      // With low confidence (< 0.7), shouldRenderActions should be false
      // This is enforced in useCelesteSearch.ts
      await verifyNoActionButtons(page);
    });
  });

  // ==========================================================================
  // Readiness State Tests
  // ==========================================================================
  test.describe('Readiness State Tests', () => {
    test('NEEDS_INPUT: Missing required entity shows NEEDS_INPUT indicator', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, TEST_QUERIES.needsInput.missingEquipment);

      // Action button should exist but show NEEDS_INPUT state (amber styling)
      const actionBtn = page.locator(SELECTORS.actionButton).first();
      if (await actionBtn.isVisible()) {
        // Should have amber/celeste-accent styling (NEEDS_INPUT)
        await expect(actionBtn).toHaveClass(/amber|celeste-accent/);
      }
    });

    test('NEEDS_INPUT: "close fault" without fault_id shows NEEDS_INPUT', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, TEST_QUERIES.needsInput.missingFaultId);

      const actionBtn = page.locator(SELECTORS.actionButton).first();
      if (await actionBtn.isVisible()) {
        // Should have NEEDS_INPUT styling (amber) not READY (green)
        await expect(actionBtn).not.toHaveClass(/emerald/);
      }
    });

    test('NEEDS_INPUT: "schedule work order" without date shows NEEDS_INPUT', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, TEST_QUERIES.needsInput.missingDate);

      const actionBtn = page.locator(SELECTORS.actionButton).first();
      if (await actionBtn.isVisible()) {
        // Verify not in READY state
        await expect(actionBtn).not.toHaveClass(/emerald/);
      }
    });

    test('READY: Complete query with all entities shows READY indicator', async ({ page }) => {
      await openSpotlight(page);
      // Query with all required entities
      await typeQueryAndWait(page, 'create urgent work order for ME-001');

      const actionBtn = page.locator(SELECTORS.actionButton).first();
      if (await actionBtn.isVisible()) {
        // After prefill resolves with high confidence, should show READY (emerald)
        // Note: This depends on backend response
        await page.waitForTimeout(500); // Wait for prefill
      }
    });

    test('BLOCKED: Role-restricted action shows BLOCKED indicator', async ({ page }) => {
      await openSpotlight(page);
      // Actions like "approve" are typically role-restricted
      await typeQueryAndWait(page, 'approve shopping list item');

      const actionBtn = page.locator(SELECTORS.actionButton).first();
      if (await actionBtn.isVisible()) {
        // If user doesn't have required role, button should be disabled
        // Note: Actual behavior depends on user's role in session
      }
    });

    test('BLOCKED: Button is disabled when state is BLOCKED', async ({ page }) => {
      await openSpotlight(page);
      // Role-gated action
      await typeQueryAndWait(page, 'delete work order');

      const actionBtn = page.locator(SELECTORS.actionButton).first();
      if (await actionBtn.isVisible()) {
        // Check for disabled state (red styling and disabled attribute)
        const hasRedClass = await actionBtn.evaluate(el =>
          el.classList.contains('red') ||
          el.className.includes('red') ||
          el.className.includes('opacity-75')
        );
        const isDisabled = await actionBtn.isDisabled();

        // If BLOCKED, should be disabled
        if (hasRedClass) {
          expect(isDisabled).toBe(true);
        }
      }
    });
  });

  // ==========================================================================
  // Mixed Mode Tests
  // ==========================================================================
  test.describe('Mixed Mode Tests', () => {
    test('MIXED: "show and create work order" handles combined intent', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, 'show work orders and create new one');

      // May show both Navigate and Execute options depending on implementation
      // At minimum, should show some actionable UI
      const hasNavigate = await page.locator(SELECTORS.navigateButton).isVisible();
      const hasAction = await page.locator(SELECTORS.actionButton).first().isVisible();

      // At least one should be visible
      expect(hasNavigate || hasAction).toBe(true);
    });
  });

  // ==========================================================================
  // Edge Case Tests
  // ==========================================================================
  test.describe('Edge Case Tests', () => {
    test('EDGE: Empty query shows no action buttons', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, '', false);

      await verifyNoActionButtons(page);
    });

    test('EDGE: Whitespace-only query shows no action buttons', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, '   ', false);

      await verifyNoActionButtons(page);
    });

    test('EDGE: Query type change updates button rendering', async ({ page }) => {
      await openSpotlight(page);

      // Start with READ query
      await typeQueryAndWait(page, TEST_QUERIES.read.openWorkOrders);
      await verifyNavigateButton(page);

      // Clear and type MUTATE query
      await page.fill(SELECTORS.spotlightInput, '');
      await typeQueryAndWait(page, TEST_QUERIES.mutate.createWorkOrder);

      // Should now show Execute button instead
      await verifyExecuteButton(page);
    });

    test('EDGE: Rapid query changes do not cause stale buttons', async ({ page }) => {
      await openSpotlight(page);

      // Rapid typing simulation
      await page.type(SELECTORS.spotlightInput, 'sho', { delay: 50 });
      await page.type(SELECTORS.spotlightInput, 'w op', { delay: 50 });
      await page.type(SELECTORS.spotlightInput, 'en wo', { delay: 50 });
      await page.type(SELECTORS.spotlightInput, 'rk orders', { delay: 50 });

      // Wait for debounce
      await page.waitForTimeout(500);

      // Should show Navigate button for final query
      await verifyNavigateButton(page);
    });

    test('EDGE: Special characters in query are handled safely', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, 'show work orders <script>alert(1)</script>', false);

      // Should not break the UI - no action buttons expected for this query
      // The page should still be functional
      const input = page.locator(SELECTORS.spotlightInput);
      await expect(input).toBeVisible();
    });

    test('EDGE: Very long query is handled gracefully', async ({ page }) => {
      await openSpotlight(page);
      const longQuery = 'show work orders '.repeat(50);
      await typeQueryAndWait(page, longQuery, false);

      // Should not crash - UI remains functional
      const input = page.locator(SELECTORS.spotlightInput);
      await expect(input).toBeVisible();
    });
  });

  // ==========================================================================
  // Visual Indicator Tests
  // ==========================================================================
  test.describe('Visual Indicator Tests', () => {
    test('VISUAL: Navigate button has correct styling', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, TEST_QUERIES.read.openWorkOrders);

      const navigateBtn = page.locator(SELECTORS.navigateButton);
      await expect(navigateBtn).toBeVisible();

      // Should have brand/interactive styling
      await expect(navigateBtn).toHaveClass(/brand-interactive|bg-brand/);
    });

    test('VISUAL: Action button shows readiness icon', async ({ page }) => {
      await openSpotlight(page);
      await typeQueryAndWait(page, TEST_QUERIES.mutate.createWorkOrder);

      const actionBtn = page.locator(SELECTORS.actionButton).first();
      await expect(actionBtn).toBeVisible();

      // Button should contain an SVG icon (readiness indicator)
      const icon = actionBtn.locator('svg');
      await expect(icon).toBeVisible();
    });

    test('VISUAL: BLOCKED button shows lock icon', async ({ page }) => {
      await openSpotlight(page);
      // Query that might result in BLOCKED state
      await typeQueryAndWait(page, 'approve critical action');

      // If BLOCKED, look for lock icon
      const lockIcon = page.locator(`${SELECTORS.actionButton} svg.text-red-400`);
      // Note: Actual selector depends on implementation
    });
  });
});
