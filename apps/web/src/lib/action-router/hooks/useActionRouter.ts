/**
 * useActionRouter Hook
 *
 * Comprehensive hook for action routing with caching and optimistic updates.
 */

'use client';

import { useState, useCallback, useMemo } from 'react';
import { executeAction } from '../router';
import {
  ACTION_REGISTRY,
  getAction,
  actionExists,
  getActionsForRole,
} from '../action-registry';
import type {
  ActionRequest,
  ActionResponse,
  ActionResult,
  UserContext,
  ActionDefinition,
} from '../types';

// ============================================================================
// TYPES
// ============================================================================

interface ActionHistory {
  actionId: string;
  timestamp: Date;
  status: 'success' | 'error';
  result?: ActionResult;
  error?: ActionResponse;
}

interface UseActionRouterState {
  isExecuting: boolean;
  lastResult: ActionResponse | null;
  history: ActionHistory[];
  pendingActions: string[];
}

interface UseActionRouterReturn {
  /** Execute an action */
  execute: (request: ActionRequest) => Promise<ActionResponse>;
  /** Execute multiple actions sequentially */
  executeSequence: (requests: ActionRequest[]) => Promise<ActionResponse[]>;
  /** Get actions available for current user */
  availableActions: ActionDefinition[];
  /** Get actions for a specific card type */
  actionsForCard: (cardType: string) => ActionDefinition[];
  /** Check if action requires confirmation */
  requiresConfirmation: (actionId: string) => boolean;
  /** Get action label */
  getActionLabel: (actionId: string) => string | null;
  /** Current state */
  state: UseActionRouterState;
  /** Clear history */
  clearHistory: () => void;
}

// ============================================================================
// INITIAL STATE
// ============================================================================

const initialState: UseActionRouterState = {
  isExecuting: false,
  lastResult: null,
  history: [],
  pendingActions: [],
};

// ============================================================================
// HOOK IMPLEMENTATION
// ============================================================================

/**
 * Comprehensive hook for action routing
 *
 * @param userContext - User context from session
 * @returns Action router functions and state
 */
export function useActionRouter(userContext: UserContext): UseActionRouterReturn {
  const [state, setState] = useState<UseActionRouterState>(initialState);

  /**
   * Execute a single action
   */
  const execute = useCallback(
    async (request: ActionRequest): Promise<ActionResponse> => {
      const actionId = request.action;

      // Add to pending
      setState((prev) => ({
        ...prev,
        isExecuting: true,
        pendingActions: [...prev.pendingActions, actionId],
      }));

      try {
        const response = await executeAction(request, userContext);

        // Add to history
        const historyEntry: ActionHistory = {
          actionId,
          timestamp: new Date(),
          status: response.status,
          result: response.status === 'success' ? response.result : undefined,
          error: response.status === 'error' ? response : undefined,
        };

        setState((prev) => ({
          ...prev,
          isExecuting: prev.pendingActions.length > 1,
          lastResult: response,
          history: [historyEntry, ...prev.history].slice(0, 50), // Keep last 50
          pendingActions: prev.pendingActions.filter((id) => id !== actionId),
        }));

        return response;
      } catch (error) {
        const errorResponse: ActionResponse = {
          status: 'error',
          action: actionId,
          error_code: 'internal_server_error',
          message: error instanceof Error ? error.message : String(error),
        };

        setState((prev) => ({
          ...prev,
          isExecuting: prev.pendingActions.length > 1,
          lastResult: errorResponse,
          history: [
            {
              actionId,
              timestamp: new Date(),
              status: 'error',
              error: errorResponse,
            },
            ...prev.history,
          ].slice(0, 50),
          pendingActions: prev.pendingActions.filter((id) => id !== actionId),
        }));

        return errorResponse;
      }
    },
    [userContext]
  );

  /**
   * Execute multiple actions sequentially
   */
  const executeSequence = useCallback(
    async (requests: ActionRequest[]): Promise<ActionResponse[]> => {
      const results: ActionResponse[] = [];

      for (const request of requests) {
        const response = await execute(request);
        results.push(response);

        // Stop sequence on error
        if (response.status === 'error') {
          break;
        }
      }

      return results;
    },
    [execute]
  );

  /**
   * Get actions available for current user's role
   */
  const availableActions = useMemo(() => {
    const actionsMap = getActionsForRole(userContext.role);
    return Object.values(actionsMap);
  }, [userContext.role]);

  /**
   * Get actions for a specific card type
   */
  const actionsForCard = useCallback(
    (cardType: string): ActionDefinition[] => {
      // Map card types to action IDs
      const cardActionMap: Record<string, string[]> = {
        equipment: [
          'add_note',
          'add_to_handover',
          'create_work_order',
        ],
        work_order: [
          'add_note_to_work_order',
          'close_work_order',
          'add_to_handover',
        ],
        fault: [
          'create_work_order_fault',
          'add_note',
          'add_to_handover',
        ],
        document: [
          'open_document',
          'add_document_to_handover',
        ],
        part: [
          'order_part',
          'add_part_to_handover',
        ],
        handover: [
          'edit_handover_section',
          'export_handover',
        ],
        predictive: [
          'add_predictive_to_handover',
        ],
      };

      const actionIds = cardActionMap[cardType] || [];
      const actions: ActionDefinition[] = [];

      for (const actionId of actionIds) {
        if (actionExists(actionId)) {
          const actionDef = getAction(actionId);
          // Only include if user has permission
          if (actionDef.allowedRoles.includes(userContext.role)) {
            actions.push(actionDef);
          }
        }
      }

      return actions;
    },
    [userContext.role]
  );

  /**
   * Check if action requires confirmation
   */
  const requiresConfirmation = useCallback((actionId: string): boolean => {
    if (!actionExists(actionId)) {
      return false;
    }

    // Heavy mutations require confirmation
    const actionDef = getAction(actionId);
    const heavyMutationActions = [
      'create_work_order',
      'create_work_order_fault',
      'close_work_order',
      'export_handover',
      'order_part',
    ];

    return heavyMutationActions.includes(actionDef.actionId);
  }, []);

  /**
   * Get action label
   */
  const getActionLabel = useCallback((actionId: string): string | null => {
    if (!actionExists(actionId)) {
      return null;
    }
    return getAction(actionId).label;
  }, []);

  /**
   * Clear history
   */
  const clearHistory = useCallback(() => {
    setState((prev) => ({
      ...prev,
      history: [],
    }));
  }, []);

  return {
    execute,
    executeSequence,
    availableActions,
    actionsForCard,
    requiresConfirmation,
    getActionLabel,
    state,
    clearHistory,
  };
}

// ============================================================================
// EXPORTS
// ============================================================================

export type { UseActionRouterState, UseActionRouterReturn, ActionHistory };
