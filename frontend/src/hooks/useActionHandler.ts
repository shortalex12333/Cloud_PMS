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
import { getWorkflowEndpoint, getWorkflowArchetype } from '@/types/workflow-archetypes';
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
  const { user } = useAuth();
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
        if (!user) {
          throw new Error('User not authenticated');
        }

        if (!canPerformAction(action, user.role)) {
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

        // Build unified payload (matches workflow_plan.md specification)
        const payload = {
          action_name: action,
          context: {
            ...context,
            user_id: user.id,
            yacht_id: user.yachtId || (user as any).yacht_id,
          },
          parameters: {
            user_input: context.user_input || null,
            ...context.parameters,
          },
          session: {
            user_id: user.id,
            yacht_id: user.yachtId || (user as any).yacht_id,
            timestamp: new Date().toISOString(),
          },
        };

        // Get workflow archetype endpoint
        const archetype = getWorkflowArchetype(action);
        const endpoint = getWorkflowEndpoint(action);

        // Log action (for debugging)
        console.log('[useActionHandler] Executing action:', {
          action,
          archetype,
          endpoint,
          payload,
          metadata,
        });

        // Call backend API using unified workflow archetype endpoint
        // Route: /workflows/{archetype} (e.g., /workflows/create)
        const response = await callCelesteApi<ActionResponse>(
          endpoint,
          {
            method: 'POST',
            body: JSON.stringify(payload),
          }
        );

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
    [user, router]
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

/**
 * Helper hook for handover actions
 */
export function useHandoverActions() {
  const { executeAction, isLoading } = useActionHandler();

  const addToHandover = useCallback(
    async (
      source_type: 'fault' | 'work_order' | 'equipment' | 'part' | 'document',
      source_id: string,
      summary?: string
    ) => {
      return executeAction(
        'add_to_handover',
        { source_type, source_id, summary },
        {
          successMessage: 'Added to handover',
          refreshData: true,
        }
      );
    },
    [executeAction]
  );

  const exportHandover = useCallback(
    async (handover_id: string) => {
      return executeAction('export_handover', { handover_id }, {
        successMessage: 'Handover exported successfully',
      });
    },
    [executeAction]
  );

  return {
    addToHandover,
    exportHandover,
    isLoading,
  };
}

/**
 * Helper hook for part/inventory actions
 */
export function usePartActions() {
  const { executeAction, isLoading } = useActionHandler();

  const orderPart = useCallback(
    async (
      part_id: string,
      quantity: number,
      supplier?: string,
      notes?: string
    ) => {
      return executeAction(
        'order_part',
        { part_id, quantity, supplier, notes },
        {
          successMessage: `Order created for ${quantity} units`,
          refreshData: true,
        }
      );
    },
    [executeAction]
  );

  const logUsage = useCallback(
    async (part_id: string, work_order_id: string, quantity: number) => {
      return executeAction(
        'log_part_usage',
        { part_id, work_order_id, quantity },
        {
          successMessage: 'Part usage logged',
          refreshData: true,
        }
      );
    },
    [executeAction]
  );

  return {
    orderPart,
    logUsage,
    isLoading,
  };
}

/**
 * Helper hook for edit actions (audit-sensitive)
 */
export function useEditActions() {
  const { executeAction, isLoading } = useActionHandler();

  const editInvoiceAmount = useCallback(
    async (
      purchase_id: string,
      invoice_id: string,
      old_amount: number,
      new_amount: number,
      reason: string
    ) => {
      return executeAction(
        'edit_invoice_amount',
        { purchase_id, invoice_id, old_amount, new_amount, reason },
        {
          successMessage: 'Invoice amount updated (audit log created)',
          refreshData: true,
        }
      );
    },
    [executeAction]
  );

  const editEquipment = useCallback(
    async (
      equipment_id: string,
      changes: {
        name?: string;
        model?: string;
        serial_number?: string;
        location?: string;
        manufacturer?: string;
      }
    ) => {
      return executeAction(
        'edit_equipment_details',
        { equipment_id, changes },
        {
          successMessage: 'Equipment details updated',
          refreshData: true,
        }
      );
    },
    [executeAction]
  );

  return {
    editInvoiceAmount,
    editEquipment,
    isLoading,
  };
}
