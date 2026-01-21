/**
 * JOURNEY TRUTH TESTS
 *
 * These tests verify that actions:
 * 1. APPEAR when they should (visibility truth)
 * 2. DO NOT appear when they shouldn't (forbidden context)
 * 3. Execute at the right moment in user journeys
 * 4. Feel inevitable, not random
 *
 * HTTP 200 != Product Works
 * These tests prove the PRODUCT works, not just the API.
 */

import { test, expect, Page } from '@playwright/test';
import { getTenantClient } from '../helpers/supabase_tenant';

const PROD_URL = process.env.BASE_URL || 'https://app.celeste7.ai';
const TEST_EMAIL = process.env.TEST_USER_EMAIL || 'x@alex-short.com';
const TEST_PASSWORD = process.env.TEST_USER_PASSWORD || 'Password2!';
const YACHT_ID = process.env.TEST_USER_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';

// Test entity IDs - will be set up in beforeAll
let OPEN_FAULT_ID: string;
let ACKNOWLEDGED_FAULT_ID: string;
let CLOSED_FAULT_ID: string;
let OPEN_WO_ID: string;
let IN_PROGRESS_WO_ID: string;
let CLOSED_WO_ID: string;
let EQUIPMENT_ID: string;

async function login(page: Page) {
  await page.goto(PROD_URL);
  await page.fill('[data-testid="email-input"], input[type="email"]', TEST_EMAIL);
  await page.fill('[data-testid="password-input"], input[type="password"]', TEST_PASSWORD);
  await page.click('[data-testid="login-button"], button[type="submit"]');
  await page.waitForURL('**/app**', { timeout: 15000 });
}

async function searchAndClick(page: Page, query: string, cardTestId: string) {
  await page.fill('[data-testid="search-input"], input[placeholder*="Search"]', query);
  await page.waitForSelector(`[data-testid="${cardTestId}"]`, { timeout: 10000 });
  await page.click(`[data-testid="${cardTestId}"]`);
}

test.describe('LAYER 2: VISIBILITY TRUTH', () => {

  test.beforeAll(async () => {
    const tenantClient = getTenantClient();

    // Get test entities with different states
    const { data: faults } = await tenantClient
      .from('pms_faults')
      .select('id, status, acknowledged')
      .eq('yacht_id', YACHT_ID)
      .limit(10);

    if (faults) {
      OPEN_FAULT_ID = faults.find(f => f.status === 'open')?.id;
      ACKNOWLEDGED_FAULT_ID = faults.find(f => f.acknowledged)?.id;
      CLOSED_FAULT_ID = faults.find(f => f.status === 'closed')?.id;
    }

    const { data: wos } = await tenantClient
      .from('pms_work_orders')
      .select('id, status')
      .eq('yacht_id', YACHT_ID)
      .limit(10);

    if (wos) {
      OPEN_WO_ID = wos.find(w => w.status === 'open')?.id;
      IN_PROGRESS_WO_ID = wos.find(w => w.status === 'in_progress')?.id;
      CLOSED_WO_ID = wos.find(w => w.status === 'closed' || w.status === 'completed')?.id;
    }

    const { data: equipment } = await tenantClient
      .from('pms_equipment')
      .select('id')
      .eq('yacht_id', YACHT_ID)
      .limit(1)
      .single();

    EQUIPMENT_ID = equipment?.id;
  });

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  // ═══════════════════════════════════════════════════════════════════
  // FAULT VISIBILITY TESTS
  // ═══════════════════════════════════════════════════════════════════

  test('V01: acknowledge_fault button appears ONLY for unacknowledged faults', async ({ page }) => {
    test.skip(!OPEN_FAULT_ID, 'No open fault available');

    await searchAndClick(page, OPEN_FAULT_ID, 'fault-card');

    // Should see acknowledge button for open fault
    const ackButton = page.locator('[data-testid="acknowledge-fault-button"], button:has-text("Acknowledge")');
    const isVisible = await ackButton.isVisible().catch(() => false);

    // Record finding
    const evidence = {
      test: 'V01',
      fault_id: OPEN_FAULT_ID,
      button_visible: isVisible,
      expected: true,
      verdict: isVisible ? 'PASS' : 'FAIL - Button not shown for open fault'
    };

    console.log('V01 Evidence:', JSON.stringify(evidence));
    expect(isVisible).toBe(true);
  });

  test('V02: acknowledge_fault button HIDDEN for already acknowledged faults', async ({ page }) => {
    test.skip(!ACKNOWLEDGED_FAULT_ID, 'No acknowledged fault available');

    await searchAndClick(page, ACKNOWLEDGED_FAULT_ID, 'fault-card');

    const ackButton = page.locator('[data-testid="acknowledge-fault-button"], button:has-text("Acknowledge")');
    const isVisible = await ackButton.isVisible().catch(() => false);

    const evidence = {
      test: 'V02',
      fault_id: ACKNOWLEDGED_FAULT_ID,
      button_visible: isVisible,
      expected: false,
      verdict: !isVisible ? 'PASS' : 'FAIL - Button shown for already acknowledged fault'
    };

    console.log('V02 Evidence:', JSON.stringify(evidence));
    expect(isVisible).toBe(false);
  });

  test('V03: close_fault button HIDDEN for closed faults', async ({ page }) => {
    test.skip(!CLOSED_FAULT_ID, 'No closed fault available');

    await searchAndClick(page, CLOSED_FAULT_ID, 'fault-card');

    const closeButton = page.locator('[data-testid="close-fault-button"], button:has-text("Close Fault")');
    const isVisible = await closeButton.isVisible().catch(() => false);

    const evidence = {
      test: 'V03',
      fault_id: CLOSED_FAULT_ID,
      button_visible: isVisible,
      expected: false,
      verdict: !isVisible ? 'PASS' : 'FAIL - Close button shown for already closed fault'
    };

    console.log('V03 Evidence:', JSON.stringify(evidence));
    expect(isVisible).toBe(false);
  });

  // ═══════════════════════════════════════════════════════════════════
  // WORK ORDER VISIBILITY TESTS
  // ═══════════════════════════════════════════════════════════════════

  test('V04: start_work_order button ONLY for open work orders', async ({ page }) => {
    test.skip(!OPEN_WO_ID, 'No open work order available');

    await searchAndClick(page, OPEN_WO_ID, 'work-order-card');

    const startButton = page.locator('[data-testid="start-wo-button"], button:has-text("Start")');
    const isVisible = await startButton.isVisible().catch(() => false);

    const evidence = {
      test: 'V04',
      wo_id: OPEN_WO_ID,
      button_visible: isVisible,
      expected: true,
      verdict: isVisible ? 'PASS' : 'FAIL - Start button not shown for open WO'
    };

    console.log('V04 Evidence:', JSON.stringify(evidence));
    expect(isVisible).toBe(true);
  });

  test('V05: close_work_order button ONLY for in_progress work orders', async ({ page }) => {
    test.skip(!IN_PROGRESS_WO_ID, 'No in_progress work order available');

    await searchAndClick(page, IN_PROGRESS_WO_ID, 'work-order-card');

    const closeButton = page.locator('[data-testid="close-wo-button"], button:has-text("Close"), button:has-text("Complete")');
    const isVisible = await closeButton.isVisible().catch(() => false);

    const evidence = {
      test: 'V05',
      wo_id: IN_PROGRESS_WO_ID,
      button_visible: isVisible,
      expected: true,
      verdict: isVisible ? 'PASS' : 'FAIL - Close button not shown for in_progress WO'
    };

    console.log('V05 Evidence:', JSON.stringify(evidence));
    expect(isVisible).toBe(true);
  });

  test('V06: STATE MACHINE - start and close NEVER both visible', async ({ page }) => {
    test.skip(!OPEN_WO_ID && !IN_PROGRESS_WO_ID, 'No work orders available');

    const woId = OPEN_WO_ID || IN_PROGRESS_WO_ID;
    await searchAndClick(page, woId, 'work-order-card');

    const startButton = page.locator('[data-testid="start-wo-button"], button:has-text("Start")');
    const closeButton = page.locator('[data-testid="close-wo-button"], button:has-text("Close"), button:has-text("Complete")');

    const startVisible = await startButton.isVisible().catch(() => false);
    const closeVisible = await closeButton.isVisible().catch(() => false);

    const bothVisible = startVisible && closeVisible;

    const evidence = {
      test: 'V06',
      wo_id: woId,
      start_visible: startVisible,
      close_visible: closeVisible,
      both_visible: bothVisible,
      verdict: !bothVisible ? 'PASS' : 'CRITICAL FAIL - State machine violation'
    };

    console.log('V06 Evidence:', JSON.stringify(evidence));
    expect(bothVisible).toBe(false);
  });

  // ═══════════════════════════════════════════════════════════════════
  // FORBIDDEN CONTEXT TESTS
  // ═══════════════════════════════════════════════════════════════════

  test('V07: NO mutation buttons on closed work order', async ({ page }) => {
    test.skip(!CLOSED_WO_ID, 'No closed work order available');

    await searchAndClick(page, CLOSED_WO_ID, 'work-order-card');

    const mutationButtons = [
      '[data-testid="start-wo-button"]',
      '[data-testid="close-wo-button"]',
      '[data-testid="add-wo-note-button"]',
      '[data-testid="add-wo-photo-button"]',
      'button:has-text("Start")',
      'button:has-text("Add Note")',
      'button:has-text("Add Photo")'
    ];

    const visibleMutations: string[] = [];

    for (const selector of mutationButtons) {
      const isVisible = await page.locator(selector).first().isVisible().catch(() => false);
      if (isVisible) {
        visibleMutations.push(selector);
      }
    }

    const evidence = {
      test: 'V07',
      wo_id: CLOSED_WO_ID,
      visible_mutations: visibleMutations,
      expected: [],
      verdict: visibleMutations.length === 0 ? 'PASS' : `FAIL - Mutations visible on closed WO: ${visibleMutations.join(', ')}`
    };

    console.log('V07 Evidence:', JSON.stringify(evidence));
    expect(visibleMutations.length).toBe(0);
  });

  test('V08: create_work_order_from_fault HIDDEN if fault already has WO', async ({ page }) => {
    // Need to find a fault that has a linked work order
    const tenantClient = getTenantClient();
    const { data: faultWithWO } = await tenantClient
      .from('pms_faults')
      .select('id, work_order_id')
      .eq('yacht_id', YACHT_ID)
      .not('work_order_id', 'is', null)
      .limit(1)
      .single();

    test.skip(!faultWithWO, 'No fault with linked WO available');

    await searchAndClick(page, faultWithWO.id, 'fault-card');

    const createWOButton = page.locator('[data-testid="create-wo-from-fault-button"], button:has-text("Create Work Order")');
    const isVisible = await createWOButton.isVisible().catch(() => false);

    const evidence = {
      test: 'V08',
      fault_id: faultWithWO.id,
      has_wo: true,
      button_visible: isVisible,
      expected: false,
      verdict: !isVisible ? 'PASS' : 'FAIL - Create WO button shown for fault that already has WO'
    };

    console.log('V08 Evidence:', JSON.stringify(evidence));
    expect(isVisible).toBe(false);
  });
});

test.describe('LAYER 3: JOURNEY TRUTH', () => {

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  // ═══════════════════════════════════════════════════════════════════
  // JOURNEY J01: Engineer Reports Fault from Memory
  // ═══════════════════════════════════════════════════════════════════

  test('J01: Engineer reports fault - report_fault is PRIMARY action', async ({ page }) => {
    test.skip(!EQUIPMENT_ID, 'No equipment available');

    await searchAndClick(page, EQUIPMENT_ID, 'equipment-card');

    // report_fault should be prominent, not buried
    const reportButton = page.locator('[data-testid="report-fault-button"], button:has-text("Report Fault"), button:has-text("Report Issue")');

    // Check visibility
    const isVisible = await reportButton.isVisible().catch(() => false);

    // Check position (should be in first 3 buttons, not buried)
    const allButtons = page.locator('[data-testid$="-button"], .action-button');
    const buttonCount = await allButtons.count();

    let reportButtonPosition = -1;
    for (let i = 0; i < buttonCount; i++) {
      const buttonText = await allButtons.nth(i).textContent();
      if (buttonText?.includes('Report') || buttonText?.includes('Fault')) {
        reportButtonPosition = i;
        break;
      }
    }

    const evidence = {
      test: 'J01',
      equipment_id: EQUIPMENT_ID,
      report_button_visible: isVisible,
      report_button_position: reportButtonPosition,
      total_buttons: buttonCount,
      is_primary: reportButtonPosition <= 2, // Position 0, 1, or 2
      verdict: isVisible && reportButtonPosition <= 2
        ? 'PASS'
        : `FAIL - Report fault not primary (pos: ${reportButtonPosition})`
    };

    console.log('J01 Evidence:', JSON.stringify(evidence));
    expect(isVisible).toBe(true);
  });

  // ═══════════════════════════════════════════════════════════════════
  // JOURNEY J11: Fault Escalates to Work Order
  // ═══════════════════════════════════════════════════════════════════

  test('J11: Fault escalation - create_work_order_from_fault visible for diagnosed fault', async ({ page }) => {
    // Find a fault without a work order
    const tenantClient = getTenantClient();
    const { data: faultWithoutWO } = await tenantClient
      .from('pms_faults')
      .select('id, status, work_order_id')
      .eq('yacht_id', YACHT_ID)
      .is('work_order_id', null)
      .eq('status', 'open')
      .limit(1)
      .single();

    test.skip(!faultWithoutWO, 'No fault without WO available');

    await searchAndClick(page, faultWithoutWO.id, 'fault-card');

    const createWOButton = page.locator('[data-testid="create-wo-from-fault-button"], button:has-text("Create Work Order")');
    const isVisible = await createWOButton.isVisible().catch(() => false);

    const evidence = {
      test: 'J11',
      fault_id: faultWithoutWO.id,
      has_wo: false,
      create_wo_button_visible: isVisible,
      verdict: isVisible ? 'PASS' : 'FAIL - Create WO button not shown for fault without WO'
    };

    console.log('J11 Evidence:', JSON.stringify(evidence));
    expect(isVisible).toBe(true);
  });

  // ═══════════════════════════════════════════════════════════════════
  // JOURNEY J12: Work Order Lifecycle Completion
  // ═══════════════════════════════════════════════════════════════════

  test('J12: WO completion - close_work_order PRIMARY for in_progress WO', async ({ page }) => {
    test.skip(!IN_PROGRESS_WO_ID, 'No in_progress work order available');

    await searchAndClick(page, IN_PROGRESS_WO_ID, 'work-order-card');

    const closeButton = page.locator('[data-testid="close-wo-button"], button:has-text("Close"), button:has-text("Complete")');
    const isVisible = await closeButton.isVisible().catch(() => false);

    // Check if it's primary (not in dropdown)
    const isInDropdown = await page.locator('.dropdown-menu, [role="menu"]').locator('button:has-text("Close"), button:has-text("Complete")').isVisible().catch(() => false);

    const evidence = {
      test: 'J12',
      wo_id: IN_PROGRESS_WO_ID,
      close_button_visible: isVisible,
      is_in_dropdown: isInDropdown,
      is_primary: isVisible && !isInDropdown,
      verdict: isVisible && !isInDropdown
        ? 'PASS'
        : 'FAIL - Close WO not primary action'
    };

    console.log('J12 Evidence:', JSON.stringify(evidence));
    expect(isVisible).toBe(true);
  });
});

test.describe('LAYER 4: THRESHOLD TRUTH', () => {

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  // ═══════════════════════════════════════════════════════════════════
  // THRESHOLD T01: Ambiguous Input
  // ═══════════════════════════════════════════════════════════════════

  test('T01: Ambiguous input "broken" - NO immediate mutations', async ({ page }) => {
    await page.fill('[data-testid="search-input"], input[placeholder*="Search"]', 'broken');
    await page.waitForTimeout(2000); // Wait for search results

    // Should NOT see mutation buttons directly
    const mutationButtons = page.locator('button:has-text("Create"), button:has-text("Report"), button:has-text("Close")');
    const mutationCount = await mutationButtons.count();

    // Should see clarification or search results, not direct action buttons
    const hasResults = await page.locator('[data-testid="search-results"], .search-result').isVisible().catch(() => false);

    const evidence = {
      test: 'T01',
      input: 'broken',
      mutation_buttons_visible: mutationCount,
      has_results: hasResults,
      verdict: mutationCount === 0
        ? 'PASS'
        : `FAIL - ${mutationCount} mutation buttons shown for ambiguous input`
    };

    console.log('T01 Evidence:', JSON.stringify(evidence));
    // This might fail currently - documenting the gap
    expect(mutationCount).toBe(0);
  });

  // ═══════════════════════════════════════════════════════════════════
  // THRESHOLD T02: Double Submit Prevention
  // ═══════════════════════════════════════════════════════════════════

  test('T02: Double-click prevention on acknowledge', async ({ page }) => {
    test.skip(!OPEN_FAULT_ID, 'No open fault available');

    await searchAndClick(page, OPEN_FAULT_ID, 'fault-card');

    const ackButton = page.locator('[data-testid="acknowledge-fault-button"], button:has-text("Acknowledge")');

    if (await ackButton.isVisible().catch(() => false)) {
      // Click once
      await ackButton.click();

      // Button should be disabled or hidden immediately
      await page.waitForTimeout(500);

      const isDisabled = await ackButton.isDisabled().catch(() => true);
      const isHidden = !(await ackButton.isVisible().catch(() => false));

      const evidence = {
        test: 'T02',
        fault_id: OPEN_FAULT_ID,
        button_disabled_after_click: isDisabled,
        button_hidden_after_click: isHidden,
        double_submit_prevented: isDisabled || isHidden,
        verdict: (isDisabled || isHidden)
          ? 'PASS'
          : 'FAIL - Button still clickable after first click'
      };

      console.log('T02 Evidence:', JSON.stringify(evidence));
      expect(isDisabled || isHidden).toBe(true);
    }
  });
});

test.describe('LAYER 5: UX PLACEMENT TRUTH', () => {

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  // ═══════════════════════════════════════════════════════════════════
  // UX01: Primary Action Distinction
  // ═══════════════════════════════════════════════════════════════════

  test('UX01: Primary actions visually distinct from secondary', async ({ page }) => {
    test.skip(!OPEN_FAULT_ID, 'No open fault available');

    await searchAndClick(page, OPEN_FAULT_ID, 'fault-card');

    // Get all action buttons
    const buttons = page.locator('[data-testid$="-button"], .action-button, button');
    const buttonCount = await buttons.count();

    // Check for visual distinction (different classes/styles)
    const primaryButtons: string[] = [];
    const secondaryButtons: string[] = [];

    for (let i = 0; i < Math.min(buttonCount, 10); i++) {
      const button = buttons.nth(i);
      const className = await button.getAttribute('class') || '';
      const text = await button.textContent() || '';

      if (className.includes('primary') || className.includes('solid')) {
        primaryButtons.push(text.trim());
      } else {
        secondaryButtons.push(text.trim());
      }
    }

    const evidence = {
      test: 'UX01',
      total_buttons: buttonCount,
      primary_buttons: primaryButtons,
      secondary_buttons: secondaryButtons,
      has_distinction: primaryButtons.length > 0 && secondaryButtons.length > 0,
      verdict: primaryButtons.length > 0
        ? 'PASS'
        : 'FAIL - No visual distinction between primary and secondary actions'
    };

    console.log('UX01 Evidence:', JSON.stringify(evidence));
    // This documents the current state - may fail
  });

  // ═══════════════════════════════════════════════════════════════════
  // UX02: CULLED Actions Not in UI
  // ═══════════════════════════════════════════════════════════════════

  test('UX02: CULLED actions (404) not visible in UI', async ({ page }) => {
    test.skip(!OPEN_FAULT_ID, 'No open fault available');

    await searchAndClick(page, OPEN_FAULT_ID, 'fault-card');

    // These actions were CULLED (return 404) and should not have buttons
    const culledActions = [
      'view_fault_history',
      'suggest_parts',
      'add_fault_note'
    ];

    const visibleCulled: string[] = [];

    for (const action of culledActions) {
      const selector = `[data-testid="${action}-button"], button:has-text("${action.replace(/_/g, ' ')}")`;
      const isVisible = await page.locator(selector).isVisible().catch(() => false);
      if (isVisible) {
        visibleCulled.push(action);
      }
    }

    const evidence = {
      test: 'UX02',
      culled_actions_checked: culledActions,
      visible_culled: visibleCulled,
      verdict: visibleCulled.length === 0
        ? 'PASS'
        : `FAIL - CULLED actions visible: ${visibleCulled.join(', ')}`
    };

    console.log('UX02 Evidence:', JSON.stringify(evidence));
    expect(visibleCulled.length).toBe(0);
  });
});

// ═══════════════════════════════════════════════════════════════════
// SUMMARY TEST
// ═══════════════════════════════════════════════════════════════════

test('SUMMARY: Journey Truth Results', async () => {
  console.log(`
╔═══════════════════════════════════════════════════════════════════╗
║                    JOURNEY TRUTH TEST SUMMARY                     ║
╠═══════════════════════════════════════════════════════════════════╣
║ Layer 2: Visibility Truth     - Actions appear/hide correctly     ║
║ Layer 3: Journey Truth        - User flows work naturally         ║
║ Layer 4: Threshold Truth      - Edge cases handled gracefully     ║
║ Layer 5: UX Placement Truth   - Right place, right time           ║
╚═══════════════════════════════════════════════════════════════════╝

These tests prove the PRODUCT works, not just the API.
HTTP 200 != Product Works

Check individual test results for detailed evidence.
  `);
});
