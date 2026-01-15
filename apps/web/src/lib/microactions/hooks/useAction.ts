'use client';

/**
 * useAction Hook
 *
 * React hook for executing microactions with loading states,
 * error handling, and confirmation dialogs.
 */

import { useState, useCallback } from 'react';
import { executeAction, getConfirmationConfig } from '../executor';
import { validateActionRequest } from '../validator';
import { getAction } from '../registry';
import type {
  ActionContext,
  ActionResult,
  ActionError,
  ActionState,
  ConfirmationConfig,
} from '../types';

interface UseActionOptions {
  /** Callback when action succeeds */
  onSuccess?: (result: ActionResult) => void;
  /** Callback when action fails */
  onError?: (error: ActionError) => void;
  /** Callback when confirmation is required */
  onConfirmationRequired?: (config: ConfirmationConfig) => void;
  /** Auto-retry on network errors */
  retryOnNetworkError?: boolean;
  /** Maximum retry attempts */
  maxRetries?: number;
}

interface UseActionReturn {
  /** Current action state */
  state: ActionState;
  /** Execute the action */
  execute: (
    actionName: string,
    context: ActionContext,
    params?: Record<string, unknown>
  ) => Promise<ActionResult>;
  /** Confirm a pending action */
  confirm: () => Promise<ActionResult>;
  /** Cancel a pending confirmation */
  cancel: () => void;
  /** Reset state */
  reset: () => void;
}

const initialState: ActionState = {
  loading: false,
  error: null,
  result: null,
  confirmation_pending: false,
};

export function useAction(options: UseActionOptions = {}): UseActionReturn {
  const [state, setState] = useState<ActionState>(initialState);
  const [pendingAction, setPendingAction] = useState<{
    actionName: string;
    context: ActionContext;
    params?: Record<string, unknown>;
  } | null>(null);

  const {
    onSuccess,
    onError,
    onConfirmationRequired,
    retryOnNetworkError = true,
    maxRetries = 3,
  } = options;

  const execute = useCallback(
    async (
      actionName: string,
      context: ActionContext,
      params?: Record<string, unknown>
    ): Promise<ActionResult> => {
      // Validate request
      const validation = validateActionRequest(actionName, context, params);
      if (!validation.valid) {
        const error: ActionError = {
          code: 'VALIDATION_ERROR',
          message: 'Invalid request',
          details: { errors: validation.errors },
        };
        setState({ ...initialState, error });
        onError?.(error);
        return {
          success: false,
          action_name: actionName,
          data: null,
          error,
          confirmation_required: false,
        };
      }

      setState({ ...initialState, loading: true });

      let attempts = 0;
      let lastError: ActionError | null = null;

      while (attempts < maxRetries) {
        attempts++;

        try {
          const result = await executeAction(actionName, context, params, false);

          // Handle confirmation required
          if (result.confirmation_required) {
            const action = getAction(actionName);
            if (action) {
              const config = getConfirmationConfig(action);
              setPendingAction({ actionName, context, params });
              setState({
                loading: false,
                error: null,
                result: null,
                confirmation_pending: true,
              });
              onConfirmationRequired?.(config);
            }
            return result;
          }

          // Handle success
          if (result.success) {
            setState({
              loading: false,
              error: null,
              result,
              confirmation_pending: false,
            });
            onSuccess?.(result);
            return result;
          }

          // Handle error
          setState({
            loading: false,
            error: result.error,
            result: null,
            confirmation_pending: false,
          });
          if (result.error) {
            onError?.(result.error);
          }
          return result;
        } catch (error) {
          lastError = {
            code: 'INTERNAL_ERROR',
            message: error instanceof Error ? error.message : String(error),
          };

          // Only retry on network errors
          if (
            !retryOnNetworkError ||
            !(error instanceof Error && error.message.includes('network'))
          ) {
            break;
          }

          // Wait before retry with exponential backoff
          await new Promise((resolve) =>
            setTimeout(resolve, Math.pow(2, attempts) * 100)
          );
        }
      }

      // All retries failed
      const error = lastError || {
        code: 'INTERNAL_ERROR' as const,
        message: 'Unknown error',
      };
      setState({
        loading: false,
        error,
        result: null,
        confirmation_pending: false,
      });
      onError?.(error);
      return {
        success: false,
        action_name: actionName,
        data: null,
        error,
        confirmation_required: false,
      };
    },
    [maxRetries, onConfirmationRequired, onError, onSuccess, retryOnNetworkError]
  );

  const confirm = useCallback(async (): Promise<ActionResult> => {
    if (!pendingAction) {
      const error: ActionError = {
        code: 'VALIDATION_ERROR',
        message: 'No pending action to confirm',
      };
      return {
        success: false,
        action_name: '',
        data: null,
        error,
        confirmation_required: false,
      };
    }

    const { actionName, context, params } = pendingAction;
    setState({ ...state, loading: true, confirmation_pending: false });
    setPendingAction(null);

    try {
      const result = await executeAction(actionName, context, params, true);

      if (result.success) {
        setState({
          loading: false,
          error: null,
          result,
          confirmation_pending: false,
        });
        onSuccess?.(result);
      } else {
        setState({
          loading: false,
          error: result.error,
          result: null,
          confirmation_pending: false,
        });
        if (result.error) {
          onError?.(result.error);
        }
      }

      return result;
    } catch (error) {
      const actionError: ActionError = {
        code: 'INTERNAL_ERROR',
        message: error instanceof Error ? error.message : String(error),
      };
      setState({
        loading: false,
        error: actionError,
        result: null,
        confirmation_pending: false,
      });
      onError?.(actionError);
      return {
        success: false,
        action_name: actionName,
        data: null,
        error: actionError,
        confirmation_required: false,
      };
    }
  }, [pendingAction, state, onSuccess, onError]);

  const cancel = useCallback(() => {
    setPendingAction(null);
    setState(initialState);
  }, []);

  const reset = useCallback(() => {
    setPendingAction(null);
    setState(initialState);
  }, []);

  return {
    state,
    execute,
    confirm,
    cancel,
    reset,
  };
}

export default useAction;
