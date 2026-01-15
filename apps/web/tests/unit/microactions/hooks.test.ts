/**
 * Hooks Unit Tests
 *
 * Tests for the React hooks including useAction, useActionState,
 * and useAvailableActions.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAction } from '@/lib/microactions/hooks/useAction';
import { useActionState } from '@/lib/microactions/hooks/useActionState';
import { useAvailableActions } from '@/lib/microactions/hooks/useAvailableActions';
import { registerHandler } from '@/lib/microactions/executor';
import type { ActionContext, ActionResult } from '@/lib/microactions/types';

describe('Hooks Module', () => {
  // Valid context for testing
  const validContext: ActionContext = {
    yacht_id: '123e4567-e89b-12d3-a456-426614174000',
    user_id: '123e4567-e89b-12d3-a456-426614174001',
    user_role: 'captain',
    source_card: 'fault',
  };

  // Mock success result
  const successResult: ActionResult = {
    success: true,
    action_name: 'diagnose_fault',
    data: { diagnosis: 'Engine overheating' },
    error: null,
    confirmation_required: false,
  };

  // Register handlers for tests
  beforeEach(() => {
    registerHandler('diagnose_fault', async () => successResult);
    registerHandler('view_fault_history', async () => ({
      success: true,
      action_name: 'view_fault_history',
      data: { history: [] },
      error: null,
      confirmation_required: false,
    }));
  });

  // ============================================================================
  // useAction Tests
  // ============================================================================

  describe('useAction', () => {
    it('should initialize with idle state', () => {
      const { result } = renderHook(() => useAction());
      expect(result.current.state.loading).toBe(false);
      expect(result.current.state.error).toBeNull();
      expect(result.current.state.result).toBeNull();
    });

    it('should execute action successfully', async () => {
      const onSuccess = vi.fn();
      const { result } = renderHook(() => useAction({ onSuccess }));

      const params = { fault_id: '123e4567-e89b-12d3-a456-426614174002' };
      await act(async () => {
        await result.current.execute('diagnose_fault', validContext, params);
      });

      expect(result.current.state.result?.success).toBe(true);
      expect(onSuccess).toHaveBeenCalled();
    });

    it('should set error on validation failure', async () => {
      const onError = vi.fn();
      const { result } = renderHook(() => useAction({ onError }));

      const invalidContext = { ...validContext, yacht_id: 'not-a-uuid' };
      await act(async () => {
        await result.current.execute('diagnose_fault', invalidContext);
      });

      expect(result.current.state.error).not.toBeNull();
      expect(onError).toHaveBeenCalled();
    });

    it('should handle unknown action', async () => {
      const { result } = renderHook(() => useAction());

      await act(async () => {
        await result.current.execute('nonexistent_action', validContext);
      });

      expect(result.current.state.error?.code).toBe('VALIDATION_ERROR');
    });

    it('should reset state', async () => {
      const { result } = renderHook(() => useAction());

      const params = { fault_id: '123e4567-e89b-12d3-a456-426614174002' };
      await act(async () => {
        await result.current.execute('diagnose_fault', validContext, params);
      });

      expect(result.current.state.result).not.toBeNull();

      act(() => {
        result.current.reset();
      });

      expect(result.current.state.result).toBeNull();
      expect(result.current.state.error).toBeNull();
    });

    it('should cancel pending confirmation', async () => {
      const { result } = renderHook(() => useAction());

      act(() => {
        result.current.cancel();
      });

      expect(result.current.state.confirmation_pending).toBe(false);
    });
  });

  // ============================================================================
  // useActionState Tests
  // ============================================================================

  describe('useActionState', () => {
    it('should initialize with empty state', () => {
      const { result } = renderHook(() => useActionState());
      expect(result.current.pending).toHaveLength(0);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.history).toHaveLength(0);
    });

    it('should track action start', () => {
      const { result } = renderHook(() => useActionState());

      let actionId: string = '';
      act(() => {
        actionId = result.current.startAction('diagnose_fault');
      });

      expect(result.current.pending).toContain(actionId);
      expect(result.current.isLoading).toBe(true);
      expect(result.current.history).toHaveLength(1);
    });

    it('should complete action', () => {
      const { result } = renderHook(() => useActionState());

      let actionId: string = '';
      act(() => {
        actionId = result.current.startAction('diagnose_fault');
      });

      act(() => {
        result.current.completeAction(actionId, successResult);
      });

      expect(result.current.pending).not.toContain(actionId);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.lastResult).toEqual(successResult);
    });

    it('should fail action', () => {
      const { result } = renderHook(() => useActionState());

      let actionId: string = '';
      act(() => {
        actionId = result.current.startAction('diagnose_fault');
      });

      const error = { code: 'INTERNAL_ERROR' as const, message: 'Failed' };
      act(() => {
        result.current.failAction(actionId, error);
      });

      expect(result.current.error).toEqual(error);
      expect(result.current.history[0].status).toBe('error');
    });

    it('should rollback action', () => {
      const { result } = renderHook(() => useActionState());

      let actionId: string = '';
      act(() => {
        actionId = result.current.startAction('diagnose_fault');
      });

      act(() => {
        result.current.rollbackAction(actionId);
      });

      expect(result.current.history[0].status).toBe('rolled_back');
    });

    it('should clear all state', () => {
      const { result } = renderHook(() => useActionState());

      act(() => {
        result.current.startAction('diagnose_fault');
      });

      act(() => {
        result.current.clearState();
      });

      expect(result.current.pending).toHaveLength(0);
      expect(result.current.history).toHaveLength(0);
    });

    it('should limit history entries', () => {
      const { result } = renderHook(() => useActionState({ maxHistory: 2 }));

      act(() => {
        result.current.startAction('action1');
        result.current.startAction('action2');
        result.current.startAction('action3');
      });

      expect(result.current.history).toHaveLength(2);
    });
  });

  // ============================================================================
  // useAvailableActions Tests
  // ============================================================================

  describe('useAvailableActions', () => {
    it('should return actions for card type', () => {
      const { result } = renderHook(() =>
        useAvailableActions({
          cardType: 'fault',
          requireHandler: false,
        })
      );

      expect(result.current.actions.length).toBeGreaterThan(0);
    });

    it('should filter by side effect', () => {
      const { result } = renderHook(() =>
        useAvailableActions({
          cardType: 'fault',
          sideEffectFilter: ['read_only'],
          requireHandler: false,
        })
      );

      const allReadOnly = result.current.actions.every(
        (a) => a.side_effect === 'read_only'
      );
      expect(allReadOnly).toBe(true);
    });

    it('should identify primary action', () => {
      const { result } = renderHook(() =>
        useAvailableActions({
          cardType: 'fault',
          requireHandler: false,
        })
      );

      expect(result.current.primaryAction).not.toBeNull();
    });

    it('should separate read and mutation actions', () => {
      const { result } = renderHook(() =>
        useAvailableActions({
          cardType: 'fault',
          requireHandler: false,
        })
      );

      const readOnly = result.current.readActions.every(
        (a) => a.side_effect === 'read_only'
      );
      const mutations = result.current.mutationActions.every(
        (a) => a.side_effect !== 'read_only'
      );

      expect(readOnly).toBe(true);
      expect(mutations).toBe(true);
    });

    it('should check action availability', () => {
      const { result } = renderHook(() =>
        useAvailableActions({
          cardType: 'fault',
          requireHandler: false,
        })
      );

      expect(result.current.isActionAvailable('diagnose_fault')).toBe(true);
      expect(result.current.isActionAvailable('nonexistent')).toBe(false);
    });

    it('should apply limit', () => {
      const { result } = renderHook(() =>
        useAvailableActions({
          cardType: 'fault',
          limit: 3,
          requireHandler: false,
        })
      );

      expect(result.current.actions.length).toBeLessThanOrEqual(3);
    });

    it('should format actions for UI', () => {
      const { result } = renderHook(() =>
        useAvailableActions({
          cardType: 'fault',
          requireHandler: false,
        })
      );

      expect(result.current.formattedActions.length).toBeGreaterThan(0);
      const formatted = result.current.formattedActions[0];
      expect(formatted).toHaveProperty('action_name');
      expect(formatted).toHaveProperty('label');
      expect(formatted).toHaveProperty('icon');
      expect(formatted).toHaveProperty('variant');
    });
  });
});
