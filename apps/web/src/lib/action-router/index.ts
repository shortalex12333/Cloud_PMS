/**
 * Action Router Module
 *
 * Central gateway for all user-initiated mutations in CelesteOS.
 *
 * @example
 * ```typescript
 * import { useAction } from '@/lib/action-router';
 *
 * function MyComponent() {
 *   const userContext = { user_id: '...', yacht_id: '...', role: 'Engineer' };
 *   const { execute, state } = useAction(userContext);
 *
 *   const handleClick = async () => {
 *     const response = await execute('add_note', {}, {
 *       equipment_id: '...',
 *       note_text: 'My note'
 *     });
 *     if (response.status === 'success') {
 *       // Handle success
 *     }
 *   };
 *
 *   return <button onClick={handleClick}>Add Note</button>;
 * }
 * ```
 */

// Types
export type {
  HandlerType,
  ActionDefinition,
  ActionContext,
  ActionPayload,
  ActionRequest,
  ActionStatus,
  ActionResult,
  ActionResponse,
  ValidationError,
  ValidationResult,
  UserContext,
  ValidationErrorCode,
  DispatchParams,
  DispatchResult,
  ActionLogEntry,
  RouteContext,
  RouteOptions,
  ActionState,
  UseActionOptions,
} from './types';

// Action Registry
export {
  ACTION_REGISTRY,
  getAction,
  actionExists,
  listActions,
  getActionsForRole,
  getActionsByHandler,
  getActionCount,
} from './action-registry';

// Validators
export {
  validationSuccess,
  validationFailure,
  validateJWT,
  validateUserContext,
  validateYachtIsolation,
  validateRolePermission,
  validateRequiredFields,
  validateFieldType,
  validateSchema,
  validateActionRequest,
} from './validators';

// Dispatchers
export {
  dispatchInternal,
  dispatchN8n,
  dispatch,
  INTERNAL_HANDLERS,
  N8N_WEBHOOK_PATHS,
} from './dispatchers';

// Logger
export {
  sanitizePayload,
  logAction,
  getActionStats,
  getRecentActions,
  getEntityActionHistory,
} from './logger';

// Router
export {
  executeAction,
  executeActionById,
  canExecuteAction,
  getExecutableActions,
} from './router';

// Hooks
export {
  useAction,
  useSpecificAction,
  useActionRouter,
} from './hooks';
export type {
  UseActionRouterState,
  UseActionRouterReturn,
  ActionHistory,
} from './hooks';
