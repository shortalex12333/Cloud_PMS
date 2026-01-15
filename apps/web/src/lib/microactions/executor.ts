/**
 * Microaction Executor
 *
 * Executes microactions by routing to the appropriate handler,
 * managing confirmation dialogs, and returning structured results.
 */

import { MICROACTION_REGISTRY, getAction } from './registry';
import type {
  MicroAction,
  ActionContext,
  ActionResult,
  ActionError,
  ConfirmationConfig,
} from './types';

// Handler function type
type HandlerFunction = (
  context: ActionContext,
  params?: Record<string, unknown>
) => Promise<ActionResult>;

// Handler registry - populated at runtime
const handlerRegistry: Record<string, HandlerFunction> = {};

/**
 * Register a handler function for an action
 */
export function registerHandler(actionName: string, handler: HandlerFunction): void {
  if (!getAction(actionName)) {
    console.warn(`Warning: Registering handler for unknown action: ${actionName}`);
  }
  handlerRegistry[actionName] = handler;
}

/**
 * Check if a handler is registered for an action
 */
export function hasHandler(actionName: string): boolean {
  return actionName in handlerRegistry;
}

/**
 * Get all registered handler names
 */
export function getRegisteredHandlers(): string[] {
  return Object.keys(handlerRegistry);
}

/**
 * Create an error result
 */
function createErrorResult(
  actionName: string,
  code: ActionError['code'],
  message: string,
  details?: Record<string, unknown>
): ActionResult {
  return {
    success: false,
    action_name: actionName,
    data: null,
    error: { code, message, details },
    confirmation_required: false,
  };
}

/**
 * Create a confirmation-required result
 */
function createConfirmationResult(
  actionName: string,
  config: ConfirmationConfig
): ActionResult {
  return {
    success: false,
    action_name: actionName,
    data: null,
    error: null,
    confirmation_required: true,
    confirmation_message: config.message,
  };
}

/**
 * Get confirmation configuration for an action
 */
export function getConfirmationConfig(action: MicroAction): ConfirmationConfig {
  // Default configurations based on side effect type
  const configs: Record<string, ConfirmationConfig> = {
    create_work_order_from_fault: {
      title: 'Create Work Order',
      message: 'This will create a new work order from the fault. Continue?',
      confirm_label: 'Create',
      cancel_label: 'Cancel',
      variant: 'default',
    },
    create_work_order: {
      title: 'Create Work Order',
      message: 'This will create a new work order. Continue?',
      confirm_label: 'Create',
      cancel_label: 'Cancel',
      variant: 'default',
    },
    mark_work_order_complete: {
      title: 'Complete Work Order',
      message: 'This will mark the work order as complete. This action cannot be undone.',
      confirm_label: 'Complete',
      cancel_label: 'Cancel',
      variant: 'warning',
    },
    order_part: {
      title: 'Order Part',
      message: 'This will create a purchase request for this part. Continue?',
      confirm_label: 'Order',
      cancel_label: 'Cancel',
      variant: 'default',
    },
    approve_purchase: {
      title: 'Approve Purchase',
      message: 'This will approve the purchase request. Continue?',
      confirm_label: 'Approve',
      cancel_label: 'Cancel',
      variant: 'default',
    },
    log_delivery_received: {
      title: 'Log Delivery',
      message: 'This will mark items as received and update inventory. Continue?',
      confirm_label: 'Confirm Receipt',
      cancel_label: 'Cancel',
      variant: 'default',
    },
    update_hours_of_rest: {
      title: 'Update Hours of Rest',
      message: 'This will modify hours of rest records. Continue?',
      confirm_label: 'Update',
      cancel_label: 'Cancel',
      variant: 'warning',
    },
    add_worklist_task: {
      title: 'Add Worklist Task',
      message: 'This will create a new shipyard work item. Continue?',
      confirm_label: 'Add Task',
      cancel_label: 'Cancel',
      variant: 'default',
    },
  };

  return (
    configs[action.action_name] || {
      title: action.label,
      message: `Are you sure you want to ${action.label.toLowerCase()}?`,
      confirm_label: 'Confirm',
      cancel_label: 'Cancel',
      variant: action.side_effect === 'mutation_heavy' ? 'warning' : 'default',
    }
  );
}

/**
 * Execute a microaction
 *
 * @param actionName - Name of the action to execute
 * @param context - Execution context (yacht_id, user_id, etc.)
 * @param params - Optional parameters for the action
 * @param confirmed - Whether the user has confirmed (for confirmation-required actions)
 * @returns ActionResult with success/failure and data
 */
export async function executeAction(
  actionName: string,
  context: ActionContext,
  params?: Record<string, unknown>,
  confirmed: boolean = false
): Promise<ActionResult> {
  // Get action definition
  const action = getAction(actionName);
  if (!action) {
    return createErrorResult(
      actionName,
      'NOT_FOUND',
      `Unknown action: ${actionName}`
    );
  }

  // Check if confirmation is required but not provided
  if (action.requires_confirmation && !confirmed) {
    const config = getConfirmationConfig(action);
    return createConfirmationResult(actionName, config);
  }

  // Check if handler is registered
  const handler = handlerRegistry[actionName];
  if (!handler) {
    return createErrorResult(
      actionName,
      'INTERNAL_ERROR',
      `No handler registered for action: ${actionName}`
    );
  }

  // Execute the handler
  try {
    const startTime = Date.now();
    const result = await handler(context, params);
    const duration = Date.now() - startTime;

    // Log execution for audit trail
    await logExecution(actionName, context, params, result, duration);

    return result;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return createErrorResult(actionName, 'INTERNAL_ERROR', message);
  }
}

/**
 * Execute multiple actions in sequence
 */
export async function executeActions(
  actions: Array<{
    actionName: string;
    params?: Record<string, unknown>;
    confirmed?: boolean;
  }>,
  context: ActionContext
): Promise<ActionResult[]> {
  const results: ActionResult[] = [];

  for (const action of actions) {
    const result = await executeAction(
      action.actionName,
      context,
      action.params,
      action.confirmed
    );
    results.push(result);

    // Stop on first failure
    if (!result.success && !result.confirmation_required) {
      break;
    }
  }

  return results;
}

/**
 * Log action execution for audit trail
 * This will be implemented with Supabase when database tables are created
 */
async function logExecution(
  actionName: string,
  context: ActionContext,
  params: Record<string, unknown> | undefined,
  result: ActionResult,
  durationMs: number
): Promise<void> {
  // TODO: Implement with Supabase when action_executions table exists
  // For now, just log to console in development
  if (process.env.NODE_ENV === 'development') {
    console.log('[Action Execution]', {
      action_name: actionName,
      yacht_id: context.yacht_id,
      user_id: context.user_id,
      success: result.success,
      duration_ms: durationMs,
    });
  }
}

/**
 * Validate that an action can be executed in the given context
 */
export function canExecuteAction(
  actionName: string,
  context: ActionContext
): { allowed: boolean; reason?: string } {
  const action = getAction(actionName);

  if (!action) {
    return { allowed: false, reason: 'Unknown action' };
  }

  // Check if source card type matches action's allowed card types
  if (context.source_card && !action.card_types.includes(context.source_card)) {
    return {
      allowed: false,
      reason: `Action not available for ${context.source_card} card type`,
    };
  }

  // Check if handler is registered
  if (!hasHandler(actionName)) {
    return { allowed: false, reason: 'Handler not implemented' };
  }

  return { allowed: true };
}

/**
 * Get available actions for a given context
 */
export function getAvailableActionsForContext(
  context: ActionContext
): MicroAction[] {
  if (!context.source_card) {
    return [];
  }

  return Object.values(MICROACTION_REGISTRY).filter((action) => {
    // Must be available for the card type
    if (!action.card_types.includes(context.source_card!)) {
      return false;
    }

    // Must have a registered handler
    if (!hasHandler(action.action_name)) {
      return false;
    }

    return true;
  });
}
