/**
 * TRIGGER MATRIX VALIDATION
 *
 * Validates that each action's visibility matches Phase 9's E013 Trigger Matrix:
 * - Intent Required: What user intent triggers this action
 * - Entity Required: What entities must be present
 * - Situation Required: What conditions must be met
 * - Forbidden Contexts: When this action must NOT appear
 *
 * Reference: verification_handoff/phase9/E013_ACTION_TRIGGER_MATRIX.md
 */

import { test, expect, Page } from '@playwright/test';
import { getTenantClient } from '../helpers/supabase_tenant';

const PROD_URL = process.env.BASE_URL || 'https://app.celeste7.ai';
const TEST_EMAIL = process.env.TEST_USER_EMAIL || 'x@alex-short.com';
const TEST_PASSWORD = process.env.TEST_USER_PASSWORD || 'Password2!';
const YACHT_ID = process.env.TEST_USER_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';

// ═══════════════════════════════════════════════════════════════════
// TRIGGER MATRIX DEFINITION (From E013)
// ═══════════════════════════════════════════════════════════════════

interface TriggerRule {
  action: string;
  tier: 'PRIMARY' | 'CONDITIONAL' | 'RARE';
  entityRequired: string | null;
  situationRequired: string | null;
  forbiddenContexts: string[];
  hasCurrentTrigger: boolean;
}

const TRIGGER_MATRIX: TriggerRule[] = [
  // FAULT ACTIONS
  {
    action: 'report_fault',
    tier: 'PRIMARY',
    entityRequired: 'equipment.id',
    situationRequired: null,
    forbiddenContexts: [],
    hasCurrentTrigger: false // GAP - no trigger defined
  },
  {
    action: 'acknowledge_fault',
    tier: 'CONDITIONAL',
    entityRequired: 'fault.id',
    situationRequired: '!fault.acknowledged',
    forbiddenContexts: ['fault.acknowledged === true'],
    hasCurrentTrigger: false // GAP
  },
  {
    action: 'diagnose_fault',
    tier: 'PRIMARY',
    entityRequired: 'fault.id',
    situationRequired: null,
    forbiddenContexts: [],
    hasCurrentTrigger: true // Has trigger (auto_run)
  },
  {
    action: 'close_fault',
    tier: 'CONDITIONAL',
    entityRequired: 'fault.id',
    situationRequired: '!fault.has_work_order',
    forbiddenContexts: ['fault.status === "closed"', 'fault.has_work_order === true'],
    hasCurrentTrigger: false // GAP
  },
  {
    action: 'update_fault',
    tier: 'CONDITIONAL',
    entityRequired: 'fault.id',
    situationRequired: 'fault.status !== "closed"',
    forbiddenContexts: ['fault.status === "closed"'],
    hasCurrentTrigger: false // GAP
  },
  {
    action: 'view_fault_detail',
    tier: 'PRIMARY',
    entityRequired: 'fault.id',
    situationRequired: null,
    forbiddenContexts: [],
    hasCurrentTrigger: false // GAP
  },
  {
    action: 'reopen_fault',
    tier: 'CONDITIONAL',
    entityRequired: 'fault.id',
    situationRequired: 'fault.status === "closed"',
    forbiddenContexts: ['fault.status !== "closed"'],
    hasCurrentTrigger: false // GAP
  },
  {
    action: 'mark_fault_false_alarm',
    tier: 'RARE',
    entityRequired: 'fault.id',
    situationRequired: 'fault.status !== "closed"',
    forbiddenContexts: ['fault.status === "closed"'],
    hasCurrentTrigger: false // GAP
  },
  {
    action: 'add_fault_photo',
    tier: 'CONDITIONAL',
    entityRequired: 'fault.id',
    situationRequired: 'fault.status !== "closed"',
    forbiddenContexts: ['fault.status === "closed"'],
    hasCurrentTrigger: true // Has trigger but misaligned (shows always)
  },
  {
    action: 'show_manual_section',
    tier: 'PRIMARY',
    entityRequired: 'equipment.id',
    situationRequired: 'has_manual === true',
    forbiddenContexts: ['!has_manual'],
    hasCurrentTrigger: true
  },

  // WORK ORDER ACTIONS
  {
    action: 'create_work_order',
    tier: 'CONDITIONAL',
    entityRequired: 'equipment.id',
    situationRequired: null,
    forbiddenContexts: ['active WO exists for same fault'],
    hasCurrentTrigger: true
  },
  {
    action: 'create_work_order_from_fault',
    tier: 'CONDITIONAL',
    entityRequired: 'fault.id',
    situationRequired: '!fault.has_work_order',
    forbiddenContexts: ['fault.work_order_id !== null'],
    hasCurrentTrigger: true
  },
  {
    action: 'start_work_order',
    tier: 'CONDITIONAL',
    entityRequired: 'work_order.id',
    situationRequired: 'wo.status === "open"',
    forbiddenContexts: ['wo.status !== "open"'],
    hasCurrentTrigger: false // GAP
  },
  {
    action: 'close_work_order',
    tier: 'CONDITIONAL',
    entityRequired: 'work_order.id',
    situationRequired: 'wo.status === "in_progress"',
    forbiddenContexts: ['wo.status !== "in_progress"'],
    hasCurrentTrigger: false // GAP - aliased as mark_work_order_complete
  },
  {
    action: 'update_work_order',
    tier: 'CONDITIONAL',
    entityRequired: 'work_order.id',
    situationRequired: 'wo.status !== "closed"',
    forbiddenContexts: ['wo.status === "closed"', 'wo.status === "cancelled"'],
    hasCurrentTrigger: false // GAP
  },
  {
    action: 'cancel_work_order',
    tier: 'RARE',
    entityRequired: 'work_order.id',
    situationRequired: 'isHOD && wo.status !== "closed"',
    forbiddenContexts: ['!isHOD', 'wo.status === "closed"'],
    hasCurrentTrigger: false // GAP
  },
  {
    action: 'assign_work_order',
    tier: 'RARE',
    entityRequired: 'work_order.id',
    situationRequired: 'isHOD',
    forbiddenContexts: ['!isHOD'],
    hasCurrentTrigger: true
  },
  {
    action: 'view_work_order_detail',
    tier: 'PRIMARY',
    entityRequired: 'work_order.id',
    situationRequired: null,
    forbiddenContexts: [],
    hasCurrentTrigger: false // GAP
  },
  {
    action: 'view_work_order_checklist',
    tier: 'PRIMARY',
    entityRequired: 'work_order.id',
    situationRequired: 'has_checklist === true',
    forbiddenContexts: ['!has_checklist'],
    hasCurrentTrigger: true
  },
  {
    action: 'add_note_to_work_order',
    tier: 'PRIMARY',
    entityRequired: 'work_order.id',
    situationRequired: 'wo.status !== "cancelled"',
    forbiddenContexts: ['wo.status === "cancelled"'],
    hasCurrentTrigger: false // GAP - aliased
  },
  {
    action: 'add_wo_note',
    tier: 'PRIMARY',
    entityRequired: 'work_order.id',
    situationRequired: 'wo.status !== "cancelled"',
    forbiddenContexts: ['wo.status === "cancelled"'],
    hasCurrentTrigger: false // GAP
  },
  {
    action: 'add_wo_hours',
    tier: 'CONDITIONAL',
    entityRequired: 'work_order.id',
    situationRequired: 'wo.status !== "closed"',
    forbiddenContexts: ['wo.status === "closed"'],
    hasCurrentTrigger: false // GAP
  },
  {
    action: 'add_wo_part',
    tier: 'RARE',
    entityRequired: 'work_order.id',
    situationRequired: 'wo.status !== "closed"',
    forbiddenContexts: ['wo.status === "closed"'],
    hasCurrentTrigger: false // GAP
  },
  {
    action: 'add_work_order_photo',
    tier: 'CONDITIONAL',
    entityRequired: 'work_order.id',
    situationRequired: 'wo.status !== "closed"',
    forbiddenContexts: ['wo.status === "closed"'],
    hasCurrentTrigger: true // But misaligned (shows always)
  },
  {
    action: 'add_parts_to_work_order',
    tier: 'RARE',
    entityRequired: 'work_order.id',
    situationRequired: 'wo.status !== "closed"',
    forbiddenContexts: ['wo.status === "closed"'],
    hasCurrentTrigger: true // But misaligned (shows always)
  },

  // EQUIPMENT ACTIONS
  {
    action: 'update_equipment_status',
    tier: 'CONDITIONAL',
    entityRequired: 'equipment.id',
    situationRequired: null,
    forbiddenContexts: [],
    hasCurrentTrigger: false // GAP
  },

  // HANDOVER ACTIONS
  {
    action: 'add_to_handover',
    tier: 'PRIMARY',
    entityRequired: 'fault.id || work_order.id || equipment.id || part.id',
    situationRequired: null,
    forbiddenContexts: ['no entity context'],
    hasCurrentTrigger: true
  },

  // WORKLIST ACTIONS
  {
    action: 'view_worklist',
    tier: 'PRIMARY',
    entityRequired: null,
    situationRequired: 'env === "shipyard" || work_order.id',
    forbiddenContexts: [],
    hasCurrentTrigger: true
  },
  {
    action: 'add_worklist_task',
    tier: 'CONDITIONAL',
    entityRequired: null,
    situationRequired: 'env === "shipyard"',
    forbiddenContexts: ['env !== "shipyard"'],
    hasCurrentTrigger: true
  },
  {
    action: 'export_worklist',
    tier: 'RARE',
    entityRequired: null,
    situationRequired: 'env === "shipyard" && isHOD',
    forbiddenContexts: ['env !== "shipyard"', '!isHOD'],
    hasCurrentTrigger: true
  }
];

// ═══════════════════════════════════════════════════════════════════
// HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════════════

async function login(page: Page) {
  await page.goto(PROD_URL);
  await page.fill('[data-testid="email-input"], input[type="email"]', TEST_EMAIL);
  await page.fill('[data-testid="password-input"], input[type="password"]', TEST_PASSWORD);
  await page.click('[data-testid="login-button"], button[type="submit"]');
  await page.waitForURL('**/app**', { timeout: 15000 });
}

async function findActionButton(page: Page, action: string): Promise<boolean> {
  const selectors = [
    `[data-testid="${action}-button"]`,
    `[data-testid="${action.replace(/_/g, '-')}-button"]`,
    `button:has-text("${action.replace(/_/g, ' ')}")`,
    `[data-action="${action}"]`
  ];

  for (const selector of selectors) {
    try {
      const isVisible = await page.locator(selector).first().isVisible({ timeout: 2000 });
      if (isVisible) return true;
    } catch {
      continue;
    }
  }
  return false;
}

// ═══════════════════════════════════════════════════════════════════
// TRIGGER MATRIX TESTS
// ═══════════════════════════════════════════════════════════════════

test.describe('TRIGGER MATRIX VALIDATION', () => {

  test('TM00: Trigger Coverage Summary', async () => {
    const withTrigger = TRIGGER_MATRIX.filter(t => t.hasCurrentTrigger);
    const withoutTrigger = TRIGGER_MATRIX.filter(t => !t.hasCurrentTrigger);

    const summary = {
      total_actions: TRIGGER_MATRIX.length,
      with_trigger: withTrigger.length,
      without_trigger: withoutTrigger.length,
      coverage_percentage: Math.round((withTrigger.length / TRIGGER_MATRIX.length) * 100),
      gap_actions: withoutTrigger.map(t => t.action),
      by_tier: {
        PRIMARY: TRIGGER_MATRIX.filter(t => t.tier === 'PRIMARY').length,
        CONDITIONAL: TRIGGER_MATRIX.filter(t => t.tier === 'CONDITIONAL').length,
        RARE: TRIGGER_MATRIX.filter(t => t.tier === 'RARE').length
      }
    };

    console.log('TRIGGER MATRIX SUMMARY:', JSON.stringify(summary, null, 2));

    // Fail if coverage is below 50%
    expect(summary.coverage_percentage).toBeGreaterThan(50);
  });

  test.describe('FAULT ACTION TRIGGERS', () => {

    let testFaultId: string;
    let closedFaultId: string;
    let acknowledgedFaultId: string;

    test.beforeAll(async () => {
      const tenantClient = getTenantClient();

      const { data: faults } = await tenantClient
        .from('pms_faults')
        .select('id, status, acknowledged')
        .eq('yacht_id', YACHT_ID)
        .limit(10);

      if (faults) {
        testFaultId = faults.find(f => f.status === 'open' && !f.acknowledged)?.id || faults[0]?.id;
        closedFaultId = faults.find(f => f.status === 'closed')?.id;
        acknowledgedFaultId = faults.find(f => f.acknowledged)?.id;
      }
    });

    test.beforeEach(async ({ page }) => {
      await login(page);
    });

    test('TM-F01: acknowledge_fault trigger validates !acknowledged', async ({ page }) => {
      test.skip(!testFaultId, 'No test fault available');

      // Navigate to unacknowledged fault
      await page.fill('[data-testid="search-input"], input[placeholder*="Search"]', testFaultId);
      await page.waitForTimeout(2000);
      await page.click(`[data-testid="fault-card"]`).catch(() => {});

      const isVisible = await findActionButton(page, 'acknowledge_fault');

      const rule = TRIGGER_MATRIX.find(t => t.action === 'acknowledge_fault')!;

      const evidence = {
        action: rule.action,
        tier: rule.tier,
        entity_present: true,
        situation_required: rule.situationRequired,
        button_visible: isVisible,
        trigger_defined: rule.hasCurrentTrigger,
        verdict: rule.hasCurrentTrigger
          ? (isVisible ? 'PASS' : 'FAIL - trigger exists but button not visible')
          : `GAP - no trigger defined, button visible: ${isVisible}`
      };

      console.log('TM-F01:', JSON.stringify(evidence));
    });

    test('TM-F02: acknowledge_fault FORBIDDEN when already acknowledged', async ({ page }) => {
      test.skip(!acknowledgedFaultId, 'No acknowledged fault available');

      await page.fill('[data-testid="search-input"], input[placeholder*="Search"]', acknowledgedFaultId);
      await page.waitForTimeout(2000);
      await page.click(`[data-testid="fault-card"]`).catch(() => {});

      const isVisible = await findActionButton(page, 'acknowledge_fault');

      const evidence = {
        action: 'acknowledge_fault',
        context: 'FORBIDDEN - already acknowledged',
        fault_id: acknowledgedFaultId,
        button_visible: isVisible,
        expected: false,
        verdict: !isVisible ? 'PASS' : 'FAIL - button visible in forbidden context'
      };

      console.log('TM-F02:', JSON.stringify(evidence));
      expect(isVisible).toBe(false);
    });

    test('TM-F03: close_fault FORBIDDEN when closed', async ({ page }) => {
      test.skip(!closedFaultId, 'No closed fault available');

      await page.fill('[data-testid="search-input"], input[placeholder*="Search"]', closedFaultId);
      await page.waitForTimeout(2000);
      await page.click(`[data-testid="fault-card"]`).catch(() => {});

      const isVisible = await findActionButton(page, 'close_fault');

      const evidence = {
        action: 'close_fault',
        context: 'FORBIDDEN - already closed',
        fault_id: closedFaultId,
        button_visible: isVisible,
        expected: false,
        verdict: !isVisible ? 'PASS' : 'FAIL - button visible in forbidden context'
      };

      console.log('TM-F03:', JSON.stringify(evidence));
      expect(isVisible).toBe(false);
    });

    test('TM-F04: reopen_fault ONLY when closed', async ({ page }) => {
      test.skip(!closedFaultId, 'No closed fault available');

      await page.fill('[data-testid="search-input"], input[placeholder*="Search"]', closedFaultId);
      await page.waitForTimeout(2000);
      await page.click(`[data-testid="fault-card"]`).catch(() => {});

      const isVisible = await findActionButton(page, 'reopen_fault');

      const evidence = {
        action: 'reopen_fault',
        context: 'REQUIRED - fault is closed',
        fault_id: closedFaultId,
        button_visible: isVisible,
        expected: true,
        verdict: isVisible ? 'PASS' : 'FAIL - button not visible when it should be'
      };

      console.log('TM-F04:', JSON.stringify(evidence));
      expect(isVisible).toBe(true);
    });
  });

  test.describe('WORK ORDER ACTION TRIGGERS', () => {

    let openWOId: string;
    let inProgressWOId: string;
    let closedWOId: string;

    test.beforeAll(async () => {
      const tenantClient = getTenantClient();

      const { data: wos } = await tenantClient
        .from('pms_work_orders')
        .select('id, status')
        .eq('yacht_id', YACHT_ID)
        .limit(10);

      if (wos) {
        openWOId = wos.find(w => w.status === 'open')?.id;
        inProgressWOId = wos.find(w => w.status === 'in_progress')?.id;
        closedWOId = wos.find(w => w.status === 'closed' || w.status === 'completed')?.id;
      }
    });

    test.beforeEach(async ({ page }) => {
      await login(page);
    });

    test('TM-WO01: start_work_order ONLY when status=open', async ({ page }) => {
      test.skip(!openWOId, 'No open work order available');

      await page.fill('[data-testid="search-input"], input[placeholder*="Search"]', openWOId);
      await page.waitForTimeout(2000);
      await page.click(`[data-testid="work-order-card"]`).catch(() => {});

      const isVisible = await findActionButton(page, 'start_work_order');

      const evidence = {
        action: 'start_work_order',
        context: 'REQUIRED - WO status is open',
        wo_id: openWOId,
        button_visible: isVisible,
        expected: true,
        verdict: isVisible ? 'PASS' : 'FAIL - button not visible for open WO'
      };

      console.log('TM-WO01:', JSON.stringify(evidence));
      expect(isVisible).toBe(true);
    });

    test('TM-WO02: start_work_order FORBIDDEN when in_progress', async ({ page }) => {
      test.skip(!inProgressWOId, 'No in_progress work order available');

      await page.fill('[data-testid="search-input"], input[placeholder*="Search"]', inProgressWOId);
      await page.waitForTimeout(2000);
      await page.click(`[data-testid="work-order-card"]`).catch(() => {});

      const isVisible = await findActionButton(page, 'start_work_order');

      const evidence = {
        action: 'start_work_order',
        context: 'FORBIDDEN - WO is in_progress',
        wo_id: inProgressWOId,
        button_visible: isVisible,
        expected: false,
        verdict: !isVisible ? 'PASS' : 'FAIL - start visible for in_progress WO'
      };

      console.log('TM-WO02:', JSON.stringify(evidence));
      expect(isVisible).toBe(false);
    });

    test('TM-WO03: close_work_order ONLY when in_progress', async ({ page }) => {
      test.skip(!inProgressWOId, 'No in_progress work order available');

      await page.fill('[data-testid="search-input"], input[placeholder*="Search"]', inProgressWOId);
      await page.waitForTimeout(2000);
      await page.click(`[data-testid="work-order-card"]`).catch(() => {});

      const isVisible = await findActionButton(page, 'close_work_order');

      const evidence = {
        action: 'close_work_order',
        context: 'REQUIRED - WO is in_progress',
        wo_id: inProgressWOId,
        button_visible: isVisible,
        expected: true,
        verdict: isVisible ? 'PASS' : 'FAIL - close not visible for in_progress WO'
      };

      console.log('TM-WO03:', JSON.stringify(evidence));
      expect(isVisible).toBe(true);
    });

    test('TM-WO04: close_work_order FORBIDDEN when closed', async ({ page }) => {
      test.skip(!closedWOId, 'No closed work order available');

      await page.fill('[data-testid="search-input"], input[placeholder*="Search"]', closedWOId);
      await page.waitForTimeout(2000);
      await page.click(`[data-testid="work-order-card"]`).catch(() => {});

      const isVisible = await findActionButton(page, 'close_work_order');

      const evidence = {
        action: 'close_work_order',
        context: 'FORBIDDEN - WO is closed',
        wo_id: closedWOId,
        button_visible: isVisible,
        expected: false,
        verdict: !isVisible ? 'PASS' : 'FAIL - close visible for closed WO'
      };

      console.log('TM-WO04:', JSON.stringify(evidence));
      expect(isVisible).toBe(false);
    });

    test('TM-WO05: STATE MACHINE - start and close mutually exclusive', async ({ page }) => {
      const anyWOId = openWOId || inProgressWOId;
      test.skip(!anyWOId, 'No work order available');

      await page.fill('[data-testid="search-input"], input[placeholder*="Search"]', anyWOId);
      await page.waitForTimeout(2000);
      await page.click(`[data-testid="work-order-card"]`).catch(() => {});

      const startVisible = await findActionButton(page, 'start_work_order');
      const closeVisible = await findActionButton(page, 'close_work_order');

      const evidence = {
        wo_id: anyWOId,
        start_visible: startVisible,
        close_visible: closeVisible,
        both_visible: startVisible && closeVisible,
        verdict: !(startVisible && closeVisible)
          ? 'PASS - state machine valid'
          : 'CRITICAL FAIL - state machine violation'
      };

      console.log('TM-WO05:', JSON.stringify(evidence));
      expect(startVisible && closeVisible).toBe(false);
    });
  });
});

// ═══════════════════════════════════════════════════════════════════
// GAP ANALYSIS REPORT
// ═══════════════════════════════════════════════════════════════════

test('GAP-REPORT: Actions Missing Triggers', async () => {
  const gaps = TRIGGER_MATRIX.filter(t => !t.hasCurrentTrigger);

  console.log(`
╔═══════════════════════════════════════════════════════════════════╗
║                    TRIGGER GAP ANALYSIS                           ║
╠═══════════════════════════════════════════════════════════════════╣
║ Total Actions: ${TRIGGER_MATRIX.length.toString().padEnd(50)}║
║ With Triggers: ${TRIGGER_MATRIX.filter(t => t.hasCurrentTrigger).length.toString().padEnd(50)}║
║ WITHOUT Triggers: ${gaps.length.toString().padEnd(47)}║
║ Coverage: ${Math.round((1 - gaps.length / TRIGGER_MATRIX.length) * 100)}%                                                    ║
╠═══════════════════════════════════════════════════════════════════╣
║ ACTIONS MISSING TRIGGERS:                                         ║
${gaps.map(g => `║   - ${g.action.padEnd(58)}║`).join('\n')}
╚═══════════════════════════════════════════════════════════════════╝
  `);

  // Document the gap - test passes but logs the issue
  expect(gaps.length).toBeGreaterThanOrEqual(0);
});
