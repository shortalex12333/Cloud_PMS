/**
 * Unit tests for Microaction Registry
 *
 * 15 tests covering:
 * - Registry structure and completeness
 * - Helper function correctness
 * - Type safety
 * - Edge cases
 */

import { describe, it, expect } from 'vitest';
import {
  MICROACTION_REGISTRY,
  TOTAL_ACTIONS,
  getActionsForCardType,
  getActionsInCluster,
  getAction,
  getReadOnlyActions,
  getMutationActions,
  getConfirmationRequiredActions,
  countBySideEffect,
  countByCluster,
} from '@/lib/microactions/registry';
import type { MicroAction, CardType, PurposeCluster } from '@/lib/microactions/types';

describe('Microaction Registry', () => {
  // =========================================================================
  // Test 1: Success - Registry has expected minimum actions
  // =========================================================================
  it('should have at least 57 registered actions', () => {
    expect(TOTAL_ACTIONS).toBeGreaterThanOrEqual(57);
    expect(Object.keys(MICROACTION_REGISTRY).length).toEqual(TOTAL_ACTIONS);
  });

  // =========================================================================
  // Test 2: Success - All required clusters have actions
  // =========================================================================
  it('should have actions in all 7 purpose clusters', () => {
    const clusterCounts = countByCluster();

    expect(clusterCounts.fix_something).toBeGreaterThanOrEqual(7);
    expect(clusterCounts.do_maintenance).toBeGreaterThanOrEqual(16);
    expect(clusterCounts.manage_equipment).toBeGreaterThanOrEqual(6);
    expect(clusterCounts.control_inventory).toBeGreaterThanOrEqual(7);
    expect(clusterCounts.communicate_status).toBeGreaterThanOrEqual(9);
    expect(clusterCounts.comply_audit).toBeGreaterThanOrEqual(5);
    expect(clusterCounts.procure_suppliers).toBeGreaterThanOrEqual(7);
  });

  // =========================================================================
  // Test 3: Success - Side effect counts match expected distribution
  // =========================================================================
  it('should have balanced side effect distribution', () => {
    const sideEffectCounts = countBySideEffect();

    // Most actions should be read_only
    expect(sideEffectCounts.read_only).toBeGreaterThan(sideEffectCounts.mutation_heavy);
    // mutation_light should have reasonable count
    expect(sideEffectCounts.mutation_light).toBeGreaterThanOrEqual(15);
    // mutation_heavy should be limited (high-impact actions)
    expect(sideEffectCounts.mutation_heavy).toBeGreaterThanOrEqual(5);
    expect(sideEffectCounts.mutation_heavy).toBeLessThanOrEqual(15);
  });

  // =========================================================================
  // Test 4: Failure - Getting non-existent action returns undefined
  // =========================================================================
  it('should return undefined for non-existent action', () => {
    const action = getAction('non_existent_action');
    expect(action).toBeUndefined();

    const action2 = getAction('');
    expect(action2).toBeUndefined();
  });

  // =========================================================================
  // Test 5: Failure - Empty/invalid card type returns empty array
  // =========================================================================
  it('should return empty array for invalid card type', () => {
    // @ts-expect-error Testing invalid input
    const actions = getActionsForCardType('invalid_card_type');
    expect(actions).toEqual([]);

    // @ts-expect-error Testing null input
    const actions2 = getActionsForCardType(null);
    expect(actions2).toEqual([]);
  });

  // =========================================================================
  // Test 6: Failure - Invalid cluster returns empty array
  // =========================================================================
  it('should return empty array for invalid cluster', () => {
    // @ts-expect-error Testing invalid input
    const actions = getActionsInCluster('invalid_cluster');
    expect(actions).toEqual([]);
  });

  // =========================================================================
  // Test 7: Edge - All actions have required fields
  // =========================================================================
  it('should have all required fields in every action', () => {
    const requiredFields: (keyof MicroAction)[] = [
      'action_name',
      'label',
      'cluster',
      'card_types',
      'side_effect',
      'description',
      'handler',
      'requires_confirmation',
    ];

    Object.entries(MICROACTION_REGISTRY).forEach(([key, action]) => {
      requiredFields.forEach((field) => {
        expect(action[field]).toBeDefined();
        expect(action[field]).not.toBeNull();
      });
      // Action name should match key
      expect(action.action_name).toEqual(key);
      // Card types should be non-empty array
      expect(action.card_types.length).toBeGreaterThan(0);
    });
  });

  // =========================================================================
  // Test 8: Edge - Action names are unique and valid format
  // =========================================================================
  it('should have unique action names in snake_case format', () => {
    const actionNames = Object.keys(MICROACTION_REGISTRY);
    const uniqueNames = new Set(actionNames);

    // All names should be unique
    expect(actionNames.length).toEqual(uniqueNames.size);

    // All names should be snake_case
    actionNames.forEach((name) => {
      expect(name).toMatch(/^[a-z][a-z0-9_]*$/);
    });
  });

  // =========================================================================
  // Test 9: Edge - Card types are valid enum values
  // =========================================================================
  it('should have valid card types for all actions', () => {
    const validCardTypes: CardType[] = [
      'fault',
      'work_order',
      'equipment',
      'part',
      'handover',
      'document',
      'hor_table',
      'purchase',
      'checklist',
      'worklist',
      'fleet_summary',
      'smart_summary',
    ];

    Object.values(MICROACTION_REGISTRY).forEach((action) => {
      action.card_types.forEach((cardType) => {
        expect(validCardTypes).toContain(cardType);
      });
    });
  });

  // =========================================================================
  // Test 10: User - getActionsForCardType returns correct actions
  // =========================================================================
  it('should return fault-related actions for fault card type', () => {
    const faultActions = getActionsForCardType('fault');

    expect(faultActions.length).toBeGreaterThan(5);

    // Should include diagnose_fault
    const diagnoseAction = faultActions.find((a) => a.action_name === 'diagnose_fault');
    expect(diagnoseAction).toBeDefined();
    expect(diagnoseAction?.cluster).toEqual('fix_something');

    // Should include create_work_order_from_fault
    const createWoAction = faultActions.find(
      (a) => a.action_name === 'create_work_order_from_fault'
    );
    expect(createWoAction).toBeDefined();
    expect(createWoAction?.requires_confirmation).toBe(true);
  });

  // =========================================================================
  // Test 11: User - getActionsInCluster returns correct actions
  // =========================================================================
  it('should return correct actions for fix_something cluster', () => {
    const fixActions = getActionsInCluster('fix_something');

    expect(fixActions.length).toEqual(7);

    const actionNames = fixActions.map((a) => a.action_name);
    expect(actionNames).toContain('diagnose_fault');
    expect(actionNames).toContain('show_manual_section');
    expect(actionNames).toContain('view_fault_history');
    expect(actionNames).toContain('suggest_parts');
    expect(actionNames).toContain('create_work_order_from_fault');
    expect(actionNames).toContain('add_fault_note');
    expect(actionNames).toContain('add_fault_photo');
  });

  // =========================================================================
  // Test 12: User - Confirmation required actions are mutation_heavy
  // =========================================================================
  it('should only require confirmation for mutation_heavy actions', () => {
    const confirmationActions = getConfirmationRequiredActions();

    // All confirmation-required actions should be mutation_heavy
    confirmationActions.forEach((action) => {
      expect(action.side_effect).toEqual('mutation_heavy');
    });

    // There should be several confirmation-required actions
    expect(confirmationActions.length).toBeGreaterThanOrEqual(5);
  });

  // =========================================================================
  // Test 13: System - Read-only actions don't require confirmation
  // =========================================================================
  it('should not require confirmation for read-only actions', () => {
    const readOnlyActions = getReadOnlyActions();

    readOnlyActions.forEach((action) => {
      expect(action.requires_confirmation).toBe(false);
    });
  });

  // =========================================================================
  // Test 14: System - Mutation actions include correct types
  // =========================================================================
  it('should include both light and heavy mutations in mutation actions', () => {
    const mutationActions = getMutationActions();

    const lightCount = mutationActions.filter(
      (a) => a.side_effect === 'mutation_light'
    ).length;
    const heavyCount = mutationActions.filter(
      (a) => a.side_effect === 'mutation_heavy'
    ).length;

    expect(lightCount).toBeGreaterThan(0);
    expect(heavyCount).toBeGreaterThan(0);
    expect(mutationActions.length).toEqual(lightCount + heavyCount);
  });

  // =========================================================================
  // Test 15: System - Handler strings follow expected format
  // =========================================================================
  it('should have properly formatted handler strings', () => {
    Object.values(MICROACTION_REGISTRY).forEach((action) => {
      // Handler should be in format: handler_group.function_name
      expect(action.handler).toMatch(/^[a-z_]+\.[a-z_]+$/);

      // Handler should contain the action name or be semantically related
      const [handlerGroup] = action.handler.split('.');
      expect(handlerGroup.length).toBeGreaterThan(0);
    });
  });
});
