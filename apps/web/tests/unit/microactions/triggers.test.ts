/**
 * Trigger Rules Unit Tests
 *
 * Phase 12: Updated after shouldShowAction() and getVisibleActions() removal.
 *
 * The visibility decision functions have been moved to the server (Decision Engine).
 * UI now calls /v1/decisions endpoint via useActionDecisions hook.
 *
 * This test file now only tests the remaining client-side functions:
 * - shouldAutoRun(): UI behavior for auto-running actions
 * - getTriggerRule(): Registry lookup
 * - getAutoRunActions(): Filter for auto-run actions
 */

import { describe, it, expect } from 'vitest';
import {
  shouldAutoRun,
  getTriggerRule,
  getAutoRunActions,
} from '@/lib/microactions/triggers';

describe('Trigger Rules (Phase 12)', () => {
  describe('Auto-Run Behavior', () => {
    it('diagnose_fault should auto-run', () => {
      expect(shouldAutoRun('diagnose_fault')).toBe(true);
    });

    it('view_fault_history should not auto-run', () => {
      expect(shouldAutoRun('view_fault_history')).toBe(false);
    });

    it('view_equipment_details should auto-run', () => {
      expect(shouldAutoRun('view_equipment_details')).toBe(true);
    });

    it('view_part_stock should auto-run', () => {
      expect(shouldAutoRun('view_part_stock')).toBe(true);
    });

    it('unknown actions should not auto-run', () => {
      expect(shouldAutoRun('some_unknown_action')).toBe(false);
    });
  });

  describe('Helper Functions', () => {
    it('getTriggerRule should return rule for known actions', () => {
      const rule = getTriggerRule('diagnose_fault');
      expect(rule).toBeDefined();
      expect(rule?.action_name).toBe('diagnose_fault');
      expect(rule?.auto_run).toBe(true);
    });

    it('getTriggerRule should return undefined for unknown actions', () => {
      const rule = getTriggerRule('unknown_action');
      expect(rule).toBeUndefined();
    });

    it('getAutoRunActions should return only auto-run actions', () => {
      const actions = [
        'diagnose_fault',
        'view_fault_history',
        'add_fault_note',
      ];

      const autoRun = getAutoRunActions(actions);
      expect(autoRun).toContain('diagnose_fault');
      expect(autoRun).not.toContain('view_fault_history');
      expect(autoRun).not.toContain('add_fault_note');
    });

    it('getAutoRunActions should handle empty input', () => {
      expect(getAutoRunActions([])).toEqual([]);
    });

    it('getAutoRunActions should handle unknown actions', () => {
      const actions = ['unknown1', 'unknown2'];
      expect(getAutoRunActions(actions)).toEqual([]);
    });
  });

  describe('Trigger Rule Registry', () => {
    it('should have diagnose_fault with auto_run=true', () => {
      const rule = getTriggerRule('diagnose_fault');
      expect(rule?.auto_run).toBe(true);
    });

    it('should have view_equipment_details with auto_run=true', () => {
      const rule = getTriggerRule('view_equipment_details');
      expect(rule?.auto_run).toBe(true);
    });

    it('should have view_part_stock with auto_run=true', () => {
      const rule = getTriggerRule('view_part_stock');
      expect(rule?.auto_run).toBe(true);
    });

    it('should have mark_work_order_complete without auto_run', () => {
      const rule = getTriggerRule('mark_work_order_complete');
      expect(rule).toBeDefined();
      expect(rule?.auto_run).toBeFalsy();
    });
  });
});

/**
 * =============================================================================
 * REMOVED TESTS (Phase 12)
 * =============================================================================
 *
 * The following tests have been removed because the tested functions no longer
 * exist in triggers.ts:
 *
 * - shouldShowAction() - REMOVED (now server-driven via /v1/decisions)
 * - getVisibleActions() - REMOVED (now server-driven via /v1/decisions)
 *
 * The visibility logic is now tested via:
 * 1. Server-side unit tests in apps/api/tests/test_decisions_route.py
 * 2. E2E tests in tests/e2e/phase12_decision_ui.spec.ts
 *
 * Per E020: "UI renders decisions - UI does NOT make decisions."
 * =============================================================================
 */
