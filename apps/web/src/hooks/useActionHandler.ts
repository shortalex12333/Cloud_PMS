/**
 * useActionHandler Hook
 *
 * Core infrastructure for executing all 67 micro-actions
 * Handles:
 * - Action dispatching
 * - Confirmation dialogs for mutation_heavy actions
 * - Reason prompts for audit-sensitive actions
 * - Loading states
 * - Error handling
 * - Success notifications
 * - API integration with n8n webhooks
 */

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner'; // Using sonner for toast notifications
import {
  MicroAction,
  ActionPayload,
  ActionResponse,
  ACTION_REGISTRY,
  requiresConfirmation,
  requiresReason,
  canPerformAction,
  getActionMetadata,
} from '@/types/actions';
// Removed workflow-archetypes import - using Action Router instead
import { callCelesteApi } from '@/lib/apiClient';
import { useAuth } from '@/hooks/useAuth';

// ============================================================================
// TYPES
// ============================================================================

interface ActionHandlerOptions {
  /** Auto-execute without confirmation (for read_only actions) */
  skipConfirmation?: boolean;
  /** Custom success message */
  successMessage?: string;
  /** Custom error message */
  errorMessage?: string;
  /** Callback after successful action */
  onSuccess?: (response: ActionResponse) => void;
  /** Callback after action error */
  onError?: (error: Error) => void;
  /** Refresh data after mutation */
  refreshData?: boolean;
}

interface ActionHandlerState {
  /** Is action currently executing */
  isLoading: boolean;
  /** Error from last action */
  error: Error | null;
  /** Response from last action */
  response: ActionResponse | null;
}

// ============================================================================
// HOOK
// ============================================================================

export function useActionHandler() {
  const router = useRouter();
  const { user, session } = useAuth();
  const [state, setState] = useState<ActionHandlerState>({
    isLoading: false,
    error: null,
    response: null,
  });

  /**
   * Execute a micro-action
   */
  const executeAction = useCallback(
    async (
      action: MicroAction,
      context: Record<string, any> = {},
      options: ActionHandlerOptions = {}
    ): Promise<ActionResponse | null> => {
      try {
        // Get action metadata
        const metadata = getActionMetadata(action);

        // Check user permissions
        if (!user || !session?.access_token) {
          throw new Error('User not authenticated');
        }

        if (!canPerformAction(action, user.role as 'chief_engineer' | 'eto' | 'captain' | 'manager' | 'vendor' | 'crew' | 'deck' | 'interior')) {
          toast.error('Permission Denied', {
            description: `You don't have permission to perform this action.`,
          });
          return null;
        }

        // For mutation_heavy actions, show confirmation
        if (requiresConfirmation(action) && !options.skipConfirmation) {
          // This will be handled by the ConfirmationDialog component
          // For now, we'll skip auto-confirmation in the hook
          // The UI layer will call executeAction with skipConfirmation=true after user confirms
          return null;
        }

        // For actions requiring reason, ensure reason is provided
        if (requiresReason(action) && !context.reason) {
          toast.error('Reason Required', {
            description: 'This action requires a justification reason.',
          });
          return null;
        }

        // Set loading state
        setState((prev) => ({
          ...prev,
          isLoading: true,
          error: null,
        }));

        // Build payload for Action Router
        const payload = {
          action: action,
          context: {
            yacht_id: user.yachtId,
            user_id: user.id,
            ...context,
          },
          payload: {
            ...context.parameters,
            ...(context.user_input && { user_input: context.user_input }),
          },
        };

        // Use unified Action Router endpoint (Next.js API route)
        const endpoint = '/api/v1/actions/execute';

        // Log action (for debugging)
        console.log('[useActionHandler] Executing action:', {
          action,
          endpoint,
          payload,
          metadata,
        });

        // Call Next.js API route directly (not external API)
        const apiResponse = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${session?.access_token}`,
          },
          body: JSON.stringify(payload),
        });

        if (!apiResponse.ok) {
          const errorData = await apiResponse.json().catch(() => ({}));
          throw new Error(errorData.error || `API Error: ${apiResponse.statusText}`);
        }

        const response = await apiResponse.json() as ActionResponse;

        // Original implementation used callCelesteApi, but Action Router is a Next.js API route
        // so we call it directly with fetch() instead
        /* Old code - replaced with direct fetch() above:
        const response = await callCelesteApi<ActionResponse>(
          endpoint,
          {
            method: 'POST',
            body: JSON.stringify(payload),
          }
        );
        */

        // Update state with success
        setState((prev) => ({
          ...prev,
          isLoading: false,
          response,
        }));

        // Show success toast
        const successMsg =
          options.successMessage ||
          response.message ||
          `${metadata.label} completed successfully`;

        toast.success('Success', {
          description: successMsg,
        });

        // Call success callback
        if (options.onSuccess) {
          options.onSuccess(response);
        }

        // Refresh data if needed (for mutations)
        if (options.refreshData && metadata.side_effect_type !== 'read_only') {
          router.refresh();
        }

        return response;
      } catch (error) {
        const err = error as Error;

        // Update state with error
        setState((prev) => ({
          ...prev,
          isLoading: false,
          error: err,
        }));

        // Show error toast
        const errorMsg = options.errorMessage || err.message || 'Action failed';

        toast.error('Error', {
          description: errorMsg,
        });

        // Call error callback
        if (options.onError) {
          options.onError(err);
        }

        console.error('[useActionHandler] Action failed:', {
          action,
          error: err,
        });

        return null;
      }
    },
    [user, session, router]
  );

  /**
   * Execute read-only action (no confirmation needed)
   */
  const executeReadAction = useCallback(
    (action: MicroAction, context: Record<string, any> = {}) => {
      return executeAction(action, context, {
        skipConfirmation: true,
        refreshData: false,
      });
    },
    [executeAction]
  );

  /**
   * Execute mutation action with confirmation
   */
  const executeMutationAction = useCallback(
    (
      action: MicroAction,
      context: Record<string, any> = {},
      options: Omit<ActionHandlerOptions, 'skipConfirmation'> = {}
    ) => {
      return executeAction(action, context, {
        ...options,
        skipConfirmation: false,
        refreshData: true,
      });
    },
    [executeAction]
  );

  /**
   * Reset error state
   */
  const resetError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
  }, []);

  /**
   * Reset entire state
   */
  const reset = useCallback(() => {
    setState({
      isLoading: false,
      error: null,
      response: null,
    });
  }, []);

  return {
    // State
    isLoading: state.isLoading,
    error: state.error,
    response: state.response,

    // Methods
    executeAction,
    executeReadAction,
    executeMutationAction,
    resetError,
    reset,
  };
}

// ============================================================================
// SPECIFIC ACTION HELPERS
// ============================================================================

/**
 * Helper hook for work order actions
 */
export function useWorkOrderActions() {
  const { executeAction, isLoading } = useActionHandler();

  const createWorkOrder = useCallback(
    async (payload: {
      equipment_id?: string;
      title: string;
      description: string;
      type: 'scheduled' | 'corrective' | 'unplanned';
      priority: 'routine' | 'important' | 'critical';
      due_date?: string;
      assigned_to?: string;
    }) => {
      return executeAction('create_work_order', payload, {
        successMessage: 'Work order created successfully',
        refreshData: true,
      });
    },
    [executeAction]
  );

  const markComplete = useCallback(
    async (work_order_id: string, completion_notes?: string) => {
      return executeAction(
        'mark_work_order_complete',
        { work_order_id, completion_notes },
        {
          successMessage: 'Work order marked as complete',
          refreshData: true,
        }
      );
    },
    [executeAction]
  );

  const addNote = useCallback(
    async (work_order_id: string, note_text: string) => {
      return executeAction(
        'add_work_order_note',
        { entity_type: 'work_order', entity_id: work_order_id, note_text },
        {
          successMessage: 'Note added to work order',
          refreshData: true,
        }
      );
    },
    [executeAction]
  );

  const editDetails = useCallback(
    async (
      work_order_id: string,
      changes: {
        title?: string;
        description?: string;
        priority?: 'routine' | 'important' | 'critical';
        due_date?: string;
        assigned_to?: string;
      }
    ) => {
      return executeAction(
        'edit_work_order_details',
        { work_order_id, changes },
        {
          successMessage: 'Work order updated successfully',
          refreshData: true,
        }
      );
    },
    [executeAction]
  );

  return {
    createWorkOrder,
    markComplete,
    addNote,
    editDetails,
    isLoading,
  };
}

