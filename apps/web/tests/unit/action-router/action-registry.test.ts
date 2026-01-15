/**
 * Action Registry Unit Tests
 *
 * Tests for action registry functions and data.
 */

import { describe, it, expect } from 'vitest';
import {
  ACTION_REGISTRY,
  getAction,
  actionExists,
  listActions,
  getActionsForRole,
  getActionsByHandler,
  getActionCount,
} from '@/lib/action-router/action-registry';

describe('Action Registry', () => {
  // ============================================================================
  // Registry Data Tests
  // ============================================================================

  describe('ACTION_REGISTRY', () => {
    it('should have exactly 13 actions', () => {
      expect(getActionCount()).toBe(13);
    });

    it('should include all required action IDs', () => {
      const requiredActions = [
        'add_note',
        'add_note_to_work_order',
        'create_work_order',
        'create_work_order_fault',
        'close_work_order',
        'add_to_handover',
        'add_document_to_handover',
        'add_part_to_handover',
        'add_predictive_to_handover',
        'edit_handover_section',
        'export_handover',
        'open_document',
        'order_part',
      ];

      for (const actionId of requiredActions) {
        expect(actionExists(actionId)).toBe(true);
      }
    });

    it('should have valid handler types for all actions', () => {
      for (const action of Object.values(ACTION_REGISTRY)) {
        expect(['internal', 'n8n']).toContain(action.handlerType);
      }
    });

    it('should have non-empty allowedRoles for all actions', () => {
      for (const action of Object.values(ACTION_REGISTRY)) {
        expect(action.allowedRoles.length).toBeGreaterThan(0);
      }
    });

    it('should have POST method for all mutation actions', () => {
      for (const action of Object.values(ACTION_REGISTRY)) {
        expect(action.method).toBe('POST');
      }
    });
  });

  // ============================================================================
  // getAction Tests
  // ============================================================================

  describe('getAction', () => {
    it('should return action definition for valid ID', () => {
      const action = getAction('add_note');
      expect(action).toBeDefined();
      expect(action.actionId).toBe('add_note');
      expect(action.label).toBe('Add Note');
    });

    it('should throw for invalid action ID', () => {
      expect(() => getAction('invalid_action')).toThrow(
        "Action 'invalid_action' not found in registry"
      );
    });

    it('should return complete action definition', () => {
      const action = getAction('create_work_order');
      expect(action.actionId).toBe('create_work_order');
      expect(action.label).toBe('Create Work Order');
      expect(action.endpoint).toBe('/v1/work-orders/create');
      expect(action.handlerType).toBe('n8n');
      expect(action.method).toBe('POST');
      expect(action.allowedRoles).toContain('Engineer');
      expect(action.requiredFields).toContain('yacht_id');
      expect(action.schemaFile).toBe('create_work_order.json');
    });
  });

  // ============================================================================
  // actionExists Tests
  // ============================================================================

  describe('actionExists', () => {
    it('should return true for existing action', () => {
      expect(actionExists('add_note')).toBe(true);
      expect(actionExists('order_part')).toBe(true);
    });

    it('should return false for non-existing action', () => {
      expect(actionExists('fake_action')).toBe(false);
      expect(actionExists('')).toBe(false);
    });
  });

  // ============================================================================
  // listActions Tests
  // ============================================================================

  describe('listActions', () => {
    it('should return all actions', () => {
      const actions = listActions();
      expect(Object.keys(actions).length).toBe(13);
    });

    it('should return a copy (not modify original)', () => {
      const actions = listActions();
      actions['test_action'] = {} as any;
      expect(actionExists('test_action')).toBe(false);
    });
  });

  // ============================================================================
  // getActionsForRole Tests
  // ============================================================================

  describe('getActionsForRole', () => {
    it('should return actions for Engineer role', () => {
      const actions = getActionsForRole('Engineer');
      expect(Object.keys(actions).length).toBeGreaterThan(0);
      expect(actions['add_note']).toBeDefined();
      expect(actions['create_work_order']).toBeDefined();
    });

    it('should return actions for Manager role', () => {
      const actions = getActionsForRole('Manager');
      expect(Object.keys(actions).length).toBeGreaterThan(0);
      expect(actions['close_work_order']).toBeDefined();
      expect(actions['export_handover']).toBeDefined();
    });

    it('should return limited actions for Crew role', () => {
      const actions = getActionsForRole('Crew');
      expect(Object.keys(actions).length).toBeLessThan(13);
      expect(actions['open_document']).toBeDefined();
      expect(actions['close_work_order']).toBeUndefined();
    });

    it('should return empty for unknown role', () => {
      const actions = getActionsForRole('Unknown');
      expect(Object.keys(actions).length).toBe(0);
    });
  });

  // ============================================================================
  // getActionsByHandler Tests
  // ============================================================================

  describe('getActionsByHandler', () => {
    it('should return internal actions', () => {
      const actions = getActionsByHandler('internal');
      expect(Object.keys(actions).length).toBeGreaterThan(0);
      expect(actions['add_note']).toBeDefined();
      expect(actions['close_work_order']).toBeDefined();
    });

    it('should return n8n actions', () => {
      const actions = getActionsByHandler('n8n');
      expect(Object.keys(actions).length).toBeGreaterThan(0);
      expect(actions['create_work_order']).toBeDefined();
      expect(actions['export_handover']).toBeDefined();
    });

    it('should partition all actions', () => {
      const internal = getActionsByHandler('internal');
      const n8n = getActionsByHandler('n8n');
      const total = Object.keys(internal).length + Object.keys(n8n).length;
      expect(total).toBe(13);
    });
  });

  // ============================================================================
  // Action Definition Tests
  // ============================================================================

  describe('Action Definitions', () => {
    it('add_note should have correct required fields', () => {
      const action = getAction('add_note');
      expect(action.requiredFields).toContain('yacht_id');
      expect(action.requiredFields).toContain('equipment_id');
      expect(action.requiredFields).toContain('note_text');
    });

    it('close_work_order should only allow HOD and Manager', () => {
      const action = getAction('close_work_order');
      expect(action.allowedRoles).toContain('HOD');
      expect(action.allowedRoles).toContain('Manager');
      expect(action.allowedRoles).not.toContain('Engineer');
    });

    it('open_document should allow all roles including Crew', () => {
      const action = getAction('open_document');
      expect(action.allowedRoles).toContain('Crew');
      expect(action.allowedRoles).toContain('Engineer');
      expect(action.allowedRoles).toContain('Manager');
    });
  });
});
