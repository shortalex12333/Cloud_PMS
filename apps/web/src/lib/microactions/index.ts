/**
 * CelesteOS Microactions Module
 *
 * Re-exports all microaction functionality for convenient importing.
 */

// Types
export type {
  SideEffectType,
  PurposeCluster,
  CardType,
  MicroAction,
  ActionContext,
  ActionResult,
  ActionError,
  AvailableAction,
  ValidationResult,
  ValidationError,
  ConfirmationConfig,
  ActionState,
} from './types';

// Registry
export {
  MICROACTION_REGISTRY,
  TOTAL_ACTIONS,
  getActionsForCardType,
  getActionsInCluster,
  getAction,
  getReadOnlyActions,
  getMutationActions,
  getConfirmationRequiredActions,
  countBySideEffect,
  countByCluster,
} from './registry';

// Executor
export {
  registerHandler,
  hasHandler,
  getRegisteredHandlers,
  executeAction,
  executeActions,
  canExecuteAction,
  getAvailableActionsForContext,
  getConfirmationConfig,
} from './executor';

// Validator
export {
  validateContext,
  validateParams,
  validateActionName,
  validateActionRequest,
  getParamSchema,
  requiresEntityId,
} from './validator';

// Confirmation
export {
  requiresConfirmation,
  getConfirmation,
  generateConfirmationMessage,
  createConfirmationRequest,
  getVariantStyles,
  confirmationVariantStyles,
  initialConfirmationState,
} from './confirmation';
export type { ConfirmationState } from './confirmation';

// Hooks
export { useAction, useActionState, useAvailableActions } from './hooks';
