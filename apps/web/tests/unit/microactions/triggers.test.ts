/**
 * Trigger Rules Unit Tests
 *
 * Tests the conditional visibility logic for microactions.
 */

import { describe, it, expect } from 'vitest';
import {
  shouldShowAction,
  shouldAutoRun,
  getTriggerRule,
  getVisibleActions,
  getAutoRunActions,
} from '@/lib/microactions/triggers';
import type { TriggerContext } from '@/lib/microactions/types';

describe('Trigger Rules', () => {
  describe('Fault Actions (Cluster 1)', () => {
    it('diagnose_fault should always show when fault exists', () => {
      const ctx: TriggerContext = {
        fault: { id: 'fault-123' },
      };
      expect(shouldShowAction('diagnose_fault', ctx)).toBe(true);
    });

    it('diagnose_fault should not show without fault', () => {
      const ctx: TriggerContext = {};
      expect(shouldShowAction('diagnose_fault', ctx)).toBe(false);
    });

    it('diagnose_fault should auto-run', () => {
      expect(shouldAutoRun('diagnose_fault')).toBe(true);
    });

    it('suggest_parts should show only when fault is known', () => {
      const unknownFault: TriggerContext = {
        fault: {
          id: 'fault-123',
          ai_diagnosis: { is_known: false },
        },
      };
      expect(shouldShowAction('suggest_parts', unknownFault)).toBe(false);

      const knownFault: TriggerContext = {
        fault: {
          id: 'fault-123',
          ai_diagnosis: { is_known: true },
        },
      };
      expect(shouldShowAction('suggest_parts', knownFault)).toBe(true);
    });

    it('create_work_order_from_fault should hide when WO exists', () => {
      const noWO: TriggerContext = {
        fault: { id: 'fault-123', has_work_order: false },
      };
      expect(shouldShowAction('create_work_order_from_fault', noWO)).toBe(true);

      const hasWO: TriggerContext = {
        fault: { id: 'fault-123', has_work_order: true },
      };
      expect(shouldShowAction('create_work_order_from_fault', hasWO)).toBe(false);
    });

    it('show_manual_section should require equipment_id', () => {
      const noEquipment: TriggerContext = {
        fault: { id: 'fault-123' },
      };
      expect(shouldShowAction('show_manual_section', noEquipment)).toBe(false);

      const withEquipment: TriggerContext = {
        fault: { id: 'fault-123', equipment_id: 'equip-456' },
      };
      expect(shouldShowAction('show_manual_section', withEquipment)).toBe(true);
    });

    it('view_fault_history should always show for faults', () => {
      const ctx: TriggerContext = {
        fault: { id: 'fault-123' },
      };
      expect(shouldShowAction('view_fault_history', ctx)).toBe(true);
    });

    it('add_fault_note and add_fault_photo should always show', () => {
      const ctx: TriggerContext = {
        fault: { id: 'fault-123' },
      };
      expect(shouldShowAction('add_fault_note', ctx)).toBe(true);
      expect(shouldShowAction('add_fault_photo', ctx)).toBe(true);
    });
  });

  describe('Work Order Actions (Cluster 2)', () => {
    it('mark_work_order_complete should only show for open/in_progress', () => {
      const openWO: TriggerContext = {
        work_order: { id: 'wo-123', status: 'open' },
      };
      expect(shouldShowAction('mark_work_order_complete', openWO)).toBe(true);

      const inProgressWO: TriggerContext = {
        work_order: { id: 'wo-123', status: 'in_progress' },
      };
      expect(shouldShowAction('mark_work_order_complete', inProgressWO)).toBe(true);

      const completedWO: TriggerContext = {
        work_order: { id: 'wo-123', status: 'completed' },
      };
      expect(shouldShowAction('mark_work_order_complete', completedWO)).toBe(false);
    });

    it('assign_work_order should require HOD role', () => {
      const crewUser: TriggerContext = {
        work_order: { id: 'wo-123' },
        user_role: 'deckhand',
      };
      expect(shouldShowAction('assign_work_order', crewUser)).toBe(false);

      const hodUser: TriggerContext = {
        work_order: { id: 'wo-123' },
        user_role: 'chief_engineer',
      };
      expect(shouldShowAction('assign_work_order', hodUser)).toBe(true);
    });

    it('view_work_order_checklist should require has_checklist', () => {
      const noChecklist: TriggerContext = {
        work_order: { id: 'wo-123', has_checklist: false },
      };
      expect(shouldShowAction('view_work_order_checklist', noChecklist)).toBe(false);

      const hasChecklist: TriggerContext = {
        work_order: { id: 'wo-123', has_checklist: true },
      };
      expect(shouldShowAction('view_work_order_checklist', hasChecklist)).toBe(true);
    });
  });

  describe('Inventory Actions (Cluster 4)', () => {
    it('order_part should show when stock is low', () => {
      const inStock: TriggerContext = {
        part: { id: 'part-123', stock_level: 10, reorder_threshold: 5 },
      };
      expect(shouldShowAction('order_part', inStock)).toBe(false);

      const lowStock: TriggerContext = {
        part: { id: 'part-123', stock_level: 3, reorder_threshold: 5 },
      };
      expect(shouldShowAction('order_part', lowStock)).toBe(true);

      const outOfStock: TriggerContext = {
        part: { id: 'part-123', is_out_of_stock: true },
      };
      expect(shouldShowAction('order_part', outOfStock)).toBe(true);
    });
  });

  describe('Compliance Actions (Cluster 6)', () => {
    it('export_hours_of_rest should require HOD role', () => {
      const crewUser: TriggerContext = {
        user_role: 'deckhand',
      };
      expect(shouldShowAction('export_hours_of_rest', crewUser)).toBe(false);

      const hodUser: TriggerContext = {
        user_role: 'captain',
      };
      expect(shouldShowAction('export_hours_of_rest', hodUser)).toBe(true);
    });

    it('tag_for_survey should require HOD and entity', () => {
      const noEntity: TriggerContext = {
        user_role: 'chief_engineer',
      };
      expect(shouldShowAction('tag_for_survey', noEntity)).toBe(false);

      const hodWithEntity: TriggerContext = {
        user_role: 'chief_engineer',
        equipment: { id: 'equip-123' },
      };
      expect(shouldShowAction('tag_for_survey', hodWithEntity)).toBe(true);
    });
  });

  describe('Procurement Actions (Cluster 7)', () => {
    it('approve_purchase should require HOD and pending_approval status', () => {
      const crewUser: TriggerContext = {
        purchase: { id: 'po-123', status: 'pending_approval' },
        user_role: 'deckhand',
      };
      expect(shouldShowAction('approve_purchase', crewUser)).toBe(false);

      const hodDraft: TriggerContext = {
        purchase: { id: 'po-123', status: 'draft' },
        user_role: 'captain',
      };
      expect(shouldShowAction('approve_purchase', hodDraft)).toBe(false);

      const hodPending: TriggerContext = {
        purchase: { id: 'po-123', status: 'pending_approval' },
        user_role: 'captain',
      };
      expect(shouldShowAction('approve_purchase', hodPending)).toBe(true);
    });

    it('log_delivery_received should require in_transit status', () => {
      const ordered: TriggerContext = {
        purchase: { id: 'po-123', status: 'ordered' },
      };
      expect(shouldShowAction('log_delivery_received', ordered)).toBe(false);

      const inTransit: TriggerContext = {
        purchase: { id: 'po-123', status: 'in_transit' },
      };
      expect(shouldShowAction('log_delivery_received', inTransit)).toBe(true);
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

    it('getVisibleActions should filter based on context', () => {
      const actions = [
        'diagnose_fault',
        'suggest_parts',
        'create_work_order_from_fault',
      ];
      const ctx: TriggerContext = {
        fault: { id: 'fault-123', ai_diagnosis: { is_known: false } },
      };

      const visible = getVisibleActions(actions, ctx);
      expect(visible).toContain('diagnose_fault');
      expect(visible).toContain('create_work_order_from_fault');
      expect(visible).not.toContain('suggest_parts'); // Not known
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
  });

  describe('Default Behavior', () => {
    it('unknown actions should show by default (backward compatibility)', () => {
      const ctx: TriggerContext = {};
      expect(shouldShowAction('some_unknown_action', ctx)).toBe(true);
    });

    it('unknown actions should not auto-run', () => {
      expect(shouldAutoRun('some_unknown_action')).toBe(false);
    });
  });
});
