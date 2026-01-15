/**
 * Executor Unit Tests
 *
 * Tests for the microaction execution engine including handler registration,
 * execution flow, confirmation handling, and error cases.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  registerHandler,
  hasHandler,
  getRegisteredHandlers,
  executeAction,
  executeActions,
  canExecuteAction,
  getAvailableActionsForContext,
  getConfirmationConfig,
} from '@/lib/microactions/executor';
import { getAction } from '@/lib/microactions/registry';
import type { ActionContext, ActionResult } from '@/lib/microactions/types';

describe('Executor Module', () => {
  // Valid context for testing
  const validContext: ActionContext = {
    yacht_id: '123e4567-e89b-12d3-a456-426614174000',
    user_id: '123e4567-e89b-12d3-a456-426614174001',
    user_role: 'captain',
    source_card: 'fault',
  };

  // Mock handler that returns success
  const successHandler = vi.fn(async () => ({
    success: true,
    action_name: 'diagnose_fault',
    data: { diagnosis: 'Engine overheating' },
    error: null,
    confirmation_required: false,
  }));

  // Mock handler that returns failure
  const failureHandler = vi.fn(async () => ({
    success: false,
    action_name: 'diagnose_fault',
    data: null,
    error: { code: 'VALIDATION_ERROR' as const, message: 'Invalid fault ID' },
    confirmation_required: false,
  }));

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================================================
  // Handler Registration Tests
  // ============================================================================

  describe('Handler Registration', () => {
    it('should register a handler for a valid action', () => {
      registerHandler('diagnose_fault', successHandler);
      expect(hasHandler('diagnose_fault')).toBe(true);
    });

    it('should return false for unregistered handlers', () => {
      expect(hasHandler('nonexistent_action')).toBe(false);
    });

    it('should list all registered handlers', () => {
      registerHandler('diagnose_fault', successHandler);
      registerHandler('view_fault_history', successHandler);
      const handlers = getRegisteredHandlers();
      expect(handlers).toContain('diagnose_fault');
      expect(handlers).toContain('view_fault_history');
    });

    it('should warn when registering handler for unknown action', () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      registerHandler('completely_unknown_action', successHandler);
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('unknown action')
      );
      consoleSpy.mockRestore();
    });
  });

  // ============================================================================
  // Action Execution Tests
  // ============================================================================

  describe('Action Execution', () => {
    beforeEach(() => {
      registerHandler('diagnose_fault', successHandler);
    });

    it('should execute a registered action successfully', async () => {
      const result = await executeAction('diagnose_fault', validContext);
      expect(result.success).toBe(true);
      expect(result.data).toEqual({ diagnosis: 'Engine overheating' });
      expect(successHandler).toHaveBeenCalledWith(validContext, undefined);
    });

    it('should return NOT_FOUND error for unknown action', async () => {
      const result = await executeAction('nonexistent_action', validContext);
      expect(result.success).toBe(false);
      expect(result.error?.code).toBe('NOT_FOUND');
    });

    it('should return INTERNAL_ERROR when no handler is registered', async () => {
      // Use show_manual_section which is unlikely to have a handler registered
      const result = await executeAction('show_manual_section', validContext);
      expect(result.success).toBe(false);
      expect(result.error?.code).toBe('INTERNAL_ERROR');
      expect(result.error?.message).toContain('No handler registered');
    });

    it('should pass params to handler', async () => {
      const params = { fault_id: '123e4567-e89b-12d3-a456-426614174002' };
      await executeAction('diagnose_fault', validContext, params);
      expect(successHandler).toHaveBeenCalledWith(validContext, params);
    });

    it('should catch handler exceptions and return error result', async () => {
      const throwingHandler = vi.fn(async () => {
        throw new Error('Database connection failed');
      });
      registerHandler('add_fault_note', throwingHandler);

      const result = await executeAction('add_fault_note', validContext);
      expect(result.success).toBe(false);
      expect(result.error?.code).toBe('INTERNAL_ERROR');
      expect(result.error?.message).toBe('Database connection failed');
    });
  });

  // ============================================================================
  // Confirmation Tests
  // ============================================================================

  describe('Confirmation Handling', () => {
    it('should return confirmation_required for unconfirmed mutation_heavy actions', async () => {
      registerHandler('create_work_order', successHandler);
      const workOrderContext = { ...validContext, source_card: 'work_order' as const };

      const result = await executeAction('create_work_order', workOrderContext, undefined, false);
      expect(result.confirmation_required).toBe(true);
      expect(result.success).toBe(false);
      expect(result.confirmation_message).toBeDefined();
    });

    it('should execute action when confirmed=true', async () => {
      registerHandler('create_work_order', successHandler);
      const workOrderContext = { ...validContext, source_card: 'work_order' as const };

      const result = await executeAction('create_work_order', workOrderContext, undefined, true);
      expect(result.confirmation_required).toBe(false);
      expect(successHandler).toHaveBeenCalled();
    });

    it('should generate confirmation config for actions', () => {
      const action = getAction('mark_work_order_complete');
      if (action) {
        const config = getConfirmationConfig(action);
        expect(config.title).toBe('Complete Work Order');
        expect(config.variant).toBe('warning');
        expect(config.confirm_label).toBeDefined();
        expect(config.cancel_label).toBeDefined();
      }
    });

    it('should use default config for actions without specific config', () => {
      const action = getAction('diagnose_fault');
      if (action) {
        const config = getConfirmationConfig(action);
        expect(config.confirm_label).toBe('Confirm');
        expect(config.cancel_label).toBe('Cancel');
      }
    });
  });

  // ============================================================================
  // Batch Execution Tests
  // ============================================================================

  describe('Batch Execution', () => {
    beforeEach(() => {
      registerHandler('diagnose_fault', successHandler);
      registerHandler('add_fault_note', failureHandler);
    });

    it('should execute multiple actions in sequence', async () => {
      const actions = [
        { actionName: 'diagnose_fault' },
        { actionName: 'diagnose_fault' },
      ];
      const results = await executeActions(actions, validContext);
      expect(results).toHaveLength(2);
      expect(results[0].success).toBe(true);
      expect(results[1].success).toBe(true);
    });

    it('should stop on first failure', async () => {
      const actions = [
        { actionName: 'add_fault_note' }, // Will fail
        { actionName: 'diagnose_fault' }, // Should not execute
      ];
      const results = await executeActions(actions, validContext);
      expect(results).toHaveLength(1);
      expect(results[0].success).toBe(false);
    });
  });

  // ============================================================================
  // Permission & Availability Tests
  // ============================================================================

  describe('Permission Checks', () => {
    beforeEach(() => {
      registerHandler('diagnose_fault', successHandler);
    });

    it('should allow action with valid context', () => {
      const result = canExecuteAction('diagnose_fault', validContext);
      expect(result.allowed).toBe(true);
    });

    it('should deny unknown action', () => {
      const result = canExecuteAction('nonexistent_action', validContext);
      expect(result.allowed).toBe(false);
      expect(result.reason).toBe('Unknown action');
    });

    it('should deny action for wrong card type', () => {
      const wrongContext = { ...validContext, source_card: 'hor_table' as const };
      const result = canExecuteAction('diagnose_fault', wrongContext);
      expect(result.allowed).toBe(false);
      expect(result.reason).toContain('not available');
    });

    it('should deny action without registered handler', () => {
      // Use suggest_parts which is unlikely to have a handler registered
      const result = canExecuteAction('suggest_parts', validContext);
      expect(result.allowed).toBe(false);
      expect(result.reason).toBe('Handler not implemented');
    });

    it('should return available actions for context', () => {
      const actions = getAvailableActionsForContext(validContext);
      expect(Array.isArray(actions)).toBe(true);
      // Should include diagnose_fault since handler is registered and context matches
      const actionNames = actions.map((a) => a.action_name);
      expect(actionNames).toContain('diagnose_fault');
    });

    it('should return empty array for context without source_card', () => {
      const noCardContext = { ...validContext, source_card: undefined };
      const actions = getAvailableActionsForContext(noCardContext);
      expect(actions).toHaveLength(0);
    });
  });
});
