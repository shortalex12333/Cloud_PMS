/**
 * Centralized Permission Service Exports
 *
 * Single source of truth for RBAC permission resolution.
 * Reads from lens_matrix.json - eliminates hardcoded role arrays.
 */

export {
  // Types
  type Role,
  type Lens,
  type ActionId,
  type ActionPermission,

  // Core functions
  canPerformAction,
  getPermittedActions,
  getActionMetadata,
  getAllActions,
  requiresSignature,
  requiresConfirmation,
  getAvailableLenses,
  isValidLens,
} from './PermissionService';
