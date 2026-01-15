'use client';

/**
 * useActionState Hook
 *
 * React hook for managing action execution state
 * with support for optimistic updates and rollback.
 */

import { useState, useCallback, useMemo } from 'react';
import type { ActionResult, ActionError } from '../types';

interface ActionHistoryEntry {
  id: string;
  actionName: string;
  timestamp: Date;
  result: ActionResult | null;
  status: 'pending' | 'success' | 'error' | 'rolled_back';
}

interface UseActionStateOptions {
  /** Maximum history entries to keep */
  maxHistory?: number;
  /** Enable optimistic updates */
  optimisticUpdates?: boolean;
}

interface UseActionStateReturn {
  /** All action executions in progress */
  pending: string[];
  /** Whether any action is in progress */
  isLoading: boolean;
  /** Current error if any */
  error: ActionError | null;
  /** Last successful result */
  lastResult: ActionResult | null;
  /** Execution history */
  history: ActionHistoryEntry[];
  /** Start tracking an action */
  startAction: (actionName: string) => string;
  /** Complete an action */
  completeAction: (id: string, result: ActionResult) => void;
  /** Fail an action */
  failAction: (id: string, error: ActionError) => void;
  /** Rollback an action */
  rollbackAction: (id: string) => void;
  /** Clear all state */
  clearState: () => void;
  /** Clear error */
  clearError: () => void;
  /** Get action by ID */
  getAction: (id: string) => ActionHistoryEntry | undefined;
}

export function useActionState(
  options: UseActionStateOptions = {}
): UseActionStateReturn {
  const { maxHistory = 50, optimisticUpdates = false } = options;

  const [pending, setPending] = useState<string[]>([]);
  const [error, setError] = useState<ActionError | null>(null);
  const [lastResult, setLastResult] = useState<ActionResult | null>(null);
  const [history, setHistory] = useState<ActionHistoryEntry[]>([]);

  const isLoading = useMemo(() => pending.length > 0, [pending]);

  const generateId = useCallback(() => {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  const startAction = useCallback(
    (actionName: string): string => {
      const id = generateId();
      const entry: ActionHistoryEntry = {
        id,
        actionName,
        timestamp: new Date(),
        result: null,
        status: 'pending',
      };

      setPending((prev) => [...prev, id]);
      setError(null);
      setHistory((prev) => {
        const updated = [entry, ...prev];
        return updated.slice(0, maxHistory);
      });

      return id;
    },
    [generateId, maxHistory]
  );

  const completeAction = useCallback(
    (id: string, result: ActionResult) => {
      setPending((prev) => prev.filter((p) => p !== id));
      setLastResult(result);
      setHistory((prev) =>
        prev.map((entry) =>
          entry.id === id ? { ...entry, result, status: 'success' } : entry
        )
      );
    },
    []
  );

  const failAction = useCallback((id: string, actionError: ActionError) => {
    setPending((prev) => prev.filter((p) => p !== id));
    setError(actionError);
    setHistory((prev) =>
      prev.map((entry) =>
        entry.id === id
          ? {
              ...entry,
              result: {
                success: false,
                action_name: entry.actionName,
                data: null,
                error: actionError,
                confirmation_required: false,
              },
              status: 'error',
            }
          : entry
      )
    );
  }, []);

  const rollbackAction = useCallback((id: string) => {
    setPending((prev) => prev.filter((p) => p !== id));
    setHistory((prev) =>
      prev.map((entry) =>
        entry.id === id ? { ...entry, status: 'rolled_back' } : entry
      )
    );
  }, []);

  const clearState = useCallback(() => {
    setPending([]);
    setError(null);
    setLastResult(null);
    setHistory([]);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const getAction = useCallback(
    (id: string): ActionHistoryEntry | undefined => {
      return history.find((entry) => entry.id === id);
    },
    [history]
  );

  return {
    pending,
    isLoading,
    error,
    lastResult,
    history,
    startAction,
    completeAction,
    failAction,
    rollbackAction,
    clearState,
    clearError,
    getAction,
  };
}

export default useActionState;
