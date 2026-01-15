/**
 * useAction Hook
 *
 * React hook for executing actions through the Action Router.
 */

'use client';

import { useState, useCallback } from 'react';
import { executeAction as executeActionFn } from '../router';
import { getAction, actionExists } from '../action-registry';
import type {
  ActionRequest,
  ActionResponse,
  ActionResult,
  ActionState,
  UserContext,
  UseActionOptions,
} from '../types';

// ============================================================================
// HOOK TYPES
// ============================================================================

interface UseActionReturn {
  /** Execute an action */
  execute: (
    actionId: string,
    context: Record<string, string>,
    payload: Record<string, unknown>
  ) => Promise<ActionResponse>;
  /** Current action state */
  state: ActionState;
  /** Reset state to initial */
  reset: () => void;
  /** Check if action can be executed by user */
  canExecute: (actionId: string) => boolean;
  /** Get action definition */
  getActionDef: (actionId: string) => ReturnType<typeof getAction> | null;
}

// ============================================================================
// INITIAL STATE
// ============================================================================

const initialState: ActionState = {
  isLoading: false,
  isSuccess: false,
  isError: false,
  error: null,
  result: null,
};

// ============================================================================
// HOOK IMPLEMENTATION
// ============================================================================

/**
 * Hook for executing actions through the Action Router
 *
 * @param userContext - User context from session
 * @param options - Optional hook options
 * @returns Action execution functions and state
 */
export function useAction(
  userContext: UserContext,
  options: UseActionOptions = {}
): UseActionReturn {
  const [state, setState] = useState<ActionState>(initialState);

  /**
   * Execute an action
   */
  const execute = useCallback(
    async (
      actionId: string,
      context: Record<string, string>,
      payload: Record<string, unknown>
    ): Promise<ActionResponse> => {
      // Set loading state
      setState({
        isLoading: true,
        isSuccess: false,
        isError: false,
        error: null,
        result: null,
      });

      // Build request
      const request: ActionRequest = {
        action: actionId,
        context: { yacht_id: userContext.yacht_id, ...context },
        payload,
      };

      try {
        // Execute action
        const response = await executeActionFn(request, userContext);

        if (response.status === 'success') {
          // Success
          setState({
            isLoading: false,
            isSuccess: true,
            isError: false,
            error: null,
            result: response.result || null,
          });

          // Call success callback
          if (options.onSuccess && response.result) {
            options.onSuccess(response.result);
          }
        } else {
          // Error
          setState({
            isLoading: false,
            isSuccess: false,
            isError: true,
            error: response,
            result: null,
          });

          // Call error callback
          if (options.onError) {
            options.onError(response);
          }
        }

        return response;
      } catch (error) {
        // Unexpected error
        const errorResponse: ActionResponse = {
          status: 'error',
          action: actionId,
          error_code: 'internal_server_error',
          message: error instanceof Error ? error.message : String(error),
        };

        setState({
          isLoading: false,
          isSuccess: false,
          isError: true,
          error: errorResponse,
          result: null,
        });

        if (options.onError) {
          options.onError(errorResponse);
        }

        return errorResponse;
      }
    },
    [userContext, options]
  );

  /**
   * Reset state to initial
   */
  const reset = useCallback(() => {
    setState(initialState);
  }, []);

  /**
   * Check if action can be executed by user
   */
  const canExecute = useCallback(
    (actionId: string): boolean => {
      if (!actionExists(actionId)) {
        return false;
      }

      const actionDef = getAction(actionId);
      return actionDef.allowedRoles.includes(userContext.role);
    },
    [userContext.role]
  );

  /**
   * Get action definition
   */
  const getActionDef = useCallback(
    (actionId: string) => {
      if (!actionExists(actionId)) {
        return null;
      }
      return getAction(actionId);
    },
    []
  );

  return {
    execute,
    state,
    reset,
    canExecute,
    getActionDef,
  };
}

// ============================================================================
// CONVENIENCE HOOKS
// ============================================================================

/**
 * Hook for a specific action type
 *
 * @param actionId - Action ID to use
 * @param userContext - User context
 * @param options - Hook options
 */
export function useSpecificAction(
  actionId: string,
  userContext: UserContext,
  options: UseActionOptions = {}
) {
  const { execute, state, reset, canExecute, getActionDef } = useAction(
    userContext,
    options
  );

  const executeAction = useCallback(
    (context: Record<string, string>, payload: Record<string, unknown>) => {
      return execute(actionId, context, payload);
    },
    [execute, actionId]
  );

  return {
    execute: executeAction,
    state,
    reset,
    canExecute: () => canExecute(actionId),
    actionDef: getActionDef(actionId),
  };
}
