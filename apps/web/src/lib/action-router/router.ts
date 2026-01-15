/**
 * Action Router - Main Router
 *
 * Central gateway for all user-initiated mutations.
 * Orchestrates validation, dispatch, and logging.
 */

import { getAction, actionExists, ACTION_REGISTRY } from './action-registry';
import { validateActionRequest } from './validators';
import { dispatch } from './dispatchers';
import { logAction } from './logger';
import type {
  ActionRequest,
  ActionResponse,
  ActionResult,
  UserContext,
  RouteOptions,
  DispatchParams,
} from './types';

// ============================================================================
// ROUTER
// ============================================================================

/**
 * Execute an action with full validation, dispatch, and logging
 *
 * Flow:
 * 1. Validate action exists
 * 2. Validate user context
 * 3. Validate yacht isolation
 * 4. Validate role permissions
 * 5. Validate required fields
 * 6. Validate schema
 * 7. Dispatch to handler
 * 8. Log execution
 * 9. Return result
 *
 * @param request - Action request
 * @param userContext - User context from session
 * @param options - Optional routing options
 * @returns Action response
 */
export async function executeAction(
  request: ActionRequest,
  userContext: UserContext,
  options: RouteOptions = {}
): Promise<ActionResponse> {
  const startTime = Date.now();
  const actionId = request.action;

  try {
    // ========================================================================
    // STEP 1: Validate action exists
    // ========================================================================
    if (!actionExists(actionId)) {
      const errorResponse: ActionResponse = {
        status: 'error',
        action: actionId,
        error_code: 'action_not_found',
        message: `Action '${actionId}' not found in registry`,
      };

      // Log failed attempt
      if (!options.skipLogging) {
        await logAction({
          actionId,
          actionLabel: actionId,
          yachtId: request.context.yacht_id || 'unknown',
          userId: userContext.user_id || 'unknown',
          payload: request.payload,
          status: 'error',
          errorMessage: errorResponse.message,
        });
      }

      return errorResponse;
    }

    const actionDef = getAction(actionId);

    // ========================================================================
    // STEP 2-6: Run all validations
    // ========================================================================
    if (!options.skipValidation) {
      const validationResult = validateActionRequest(
        actionId,
        request.context,
        request.payload,
        userContext,
        {
          allowedRoles: actionDef.allowedRoles,
          requiredFields: actionDef.requiredFields,
          schemaFile: actionDef.schemaFile,
        }
      );

      if (!validationResult.valid) {
        const errorResponse: ActionResponse = {
          status: 'error',
          action: actionId,
          error_code: validationResult.error?.error_code || 'validation_error',
          message: validationResult.error?.message || 'Validation failed',
          details: validationResult.error?.details,
        };

        // Log validation failure
        if (!options.skipLogging) {
          await logAction({
            actionId,
            actionLabel: actionDef.label,
            yachtId: request.context.yacht_id || 'unknown',
            userId: userContext.user_id || 'unknown',
            payload: request.payload,
            status: 'error',
            errorMessage: errorResponse.message,
          });
        }

        return errorResponse;
      }
    }

    // ========================================================================
    // STEP 7: Dispatch to handler
    // ========================================================================
    const params: DispatchParams = {
      ...request.context,
      ...request.payload,
      yacht_id: request.context.yacht_id,
      user_id: userContext.user_id,
      role: userContext.role,
    };

    let result: ActionResult;

    try {
      result = await dispatch(actionId, params, actionDef.handlerType);
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error);

      // Determine error code based on error type
      const isValidationError =
        error instanceof Error && error.message.includes('not found');
      const errorCode = isValidationError
        ? 'handler_validation_error'
        : 'handler_execution_error';

      const errorResponse: ActionResponse = {
        status: 'error',
        action: actionId,
        error_code: errorCode,
        message: errorMessage,
      };

      // Log dispatch failure
      if (!options.skipLogging) {
        const durationMs = Date.now() - startTime;
        await logAction({
          actionId,
          actionLabel: actionDef.label,
          yachtId: request.context.yacht_id,
          userId: userContext.user_id,
          payload: request.payload,
          status: 'error',
          errorMessage,
          durationMs,
        });
      }

      return errorResponse;
    }

    // ========================================================================
    // STEP 8: Log success
    // ========================================================================
    if (!options.skipLogging) {
      const durationMs = Date.now() - startTime;
      await logAction({
        actionId,
        actionLabel: actionDef.label,
        yachtId: request.context.yacht_id,
        userId: userContext.user_id,
        payload: request.payload,
        status: 'success',
        result,
        durationMs,
      });
    }

    // ========================================================================
    // STEP 9: Return success response
    // ========================================================================
    return {
      status: 'success',
      action: actionId,
      result,
    };
  } catch (error) {
    // Catch-all for unexpected errors
    const errorMessage =
      error instanceof Error ? error.message : String(error);

    const errorResponse: ActionResponse = {
      status: 'error',
      action: actionId,
      error_code: 'internal_server_error',
      message: `Unexpected error: ${errorMessage}`,
    };

    // Log unexpected error
    if (!options.skipLogging) {
      const durationMs = Date.now() - startTime;
      await logAction({
        actionId,
        actionLabel: actionId,
        yachtId: request.context?.yacht_id || 'unknown',
        userId: userContext?.user_id || 'unknown',
        payload: request.payload || {},
        status: 'error',
        errorMessage: errorResponse.message,
        durationMs,
      });
    }

    return errorResponse;
  }
}

// ============================================================================
// CONVENIENCE FUNCTIONS
// ============================================================================

/**
 * Execute an action by ID with simplified parameters
 *
 * @param actionId - Action to execute
 * @param yachtId - Yacht ID
 * @param payload - Action payload
 * @param userContext - User context
 * @returns Action response
 */
export async function executeActionById(
  actionId: string,
  yachtId: string,
  payload: Record<string, unknown>,
  userContext: UserContext
): Promise<ActionResponse> {
  return executeAction(
    {
      action: actionId,
      context: { yacht_id: yachtId },
      payload,
    },
    userContext
  );
}

/**
 * Check if user can execute a specific action
 *
 * @param actionId - Action to check
 * @param userRole - User's role
 * @returns true if user can execute action
 */
export function canExecuteAction(actionId: string, userRole: string): boolean {
  if (!actionExists(actionId)) {
    return false;
  }

  const actionDef = getAction(actionId);
  return actionDef.allowedRoles.includes(userRole);
}

/**
 * Get list of actions user can execute
 *
 * @param userRole - User's role
 * @returns List of action IDs
 */
export function getExecutableActions(userRole: string): string[] {
  const actions: string[] = [];

  for (const [actionId, actionDef] of Object.entries(ACTION_REGISTRY)) {
    if (actionDef.allowedRoles.includes(userRole)) {
      actions.push(actionId);
    }
  }

  return actions;
}
