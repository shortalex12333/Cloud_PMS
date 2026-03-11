/**
 * PermissionService — Phase 16.2 Centralized RBAC
 *
 * Single source of truth for all permission checks.
 * Reads from lens_matrix.json instead of hardcoded role arrays.
 *
 * Used by usePermissions hook for React components.
 *
 * @see /docs/ON_GOING_WORK/BACKEND/LENSES/UNIFIED-ROUTE-ARCHITECTURE.md
 */

import lensMatrix from '@/lib/lens_matrix.json';

// =============================================================================
// Types
// =============================================================================

/** All supported lens types (singular form as used in the matrix) */
export type Lens =
  | 'work_order'
  | 'fault'
  | 'equipment'
  | 'part'
  | 'inventory'
  | 'receiving'
  | 'certificate'
  | 'handover'
  | 'handover_export'
  | 'hours_of_rest'
  | 'warranty'
  | 'shopping_list'
  | 'document'
  | 'worklist'
  | 'email';

/** All supported user roles */
export type UserRole = 'captain' | 'chief_engineer' | 'eto' | 'crew' | 'admin' | 'manager';

/** Action ID string type for type safety */
export type ActionId = string;

/** Action permission definition from lens_matrix.json (mutate_actions structure) */
export interface ActionPermission {
  action_id: string;
  required_fields?: string[];
  optional_fields?: string[];
  role_restricted?: string[];
  requires_signature?: boolean;
  requires_confirmation?: boolean;
  confirmation_message?: string;
}

/** Lens definition from lens_matrix.json */
export interface LensDefinition {
  lens: string;
  read_filters?: Record<string, unknown>;
  mutate_actions: Record<string, ActionPermission>;
}

/** The full lens matrix structure */
interface LensMatrix {
  version: string;
  generated_at: string;
  lenses: Record<string, LensDefinition>;
}

// =============================================================================
// Constants
// =============================================================================

/** Map common lens aliases to matrix names */
const LENS_ALIAS_MAP: Record<string, string> = {
  work_orders: 'work_order',
  faults: 'fault',
  parts: 'part',
  certificates: 'certificate',
  warranties: 'warranty',
  documents: 'document',
  // Direct mappings (singular to singular)
  work_order: 'work_order',
  fault: 'fault',
  equipment: 'equipment',
  part: 'part',
  inventory: 'part',
  receiving: 'receiving',
  certificate: 'certificate',
  handover: 'handover',
  handover_export: 'handover_export',
  hours_of_rest: 'hours_of_rest',
  warranty: 'warranty',
  shopping_list: 'shopping_list',
  document: 'document',
  worklist: 'worklist',
  email: 'email',
};

// =============================================================================
// Internal Helpers
// =============================================================================

/**
 * Get the typed lens matrix
 */
function getMatrix(): LensMatrix {
  return lensMatrix as unknown as LensMatrix;
}

/**
 * Normalize lens name to matrix format (singular)
 */
function normalizeLens(lens: string): string {
  return LENS_ALIAS_MAP[lens] || lens;
}

/**
 * Find a lens definition in the matrix
 */
function findLens(lens: string): LensDefinition | undefined {
  const normalizedLens = normalizeLens(lens);
  return getMatrix().lenses[normalizedLens];
}

/**
 * Find an action within a lens
 */
function findAction(actionId: string, lens: string): ActionPermission | undefined {
  const lensDefinition = findLens(lens);
  if (!lensDefinition) return undefined;
  return lensDefinition.mutate_actions[actionId];
}

// =============================================================================
// Public API
// =============================================================================

/**
 * Check if a user with given role can perform an action
 *
 * @param userRole - The user's role (e.g., 'captain', 'crew')
 * @param actionId - The action ID to check (e.g., 'close_work_order')
 * @param lens - The lens context (e.g., 'work_orders', 'faults')
 * @returns true if the user can perform the action
 *
 * @example
 * ```ts
 * if (canPerformAction('captain', 'close_work_order', 'work_orders')) {
 *   // Show close button
 * }
 * ```
 */
export function canPerformAction(
  userRole: string,
  actionId: ActionId,
  lens: string
): boolean {
  const action = findAction(actionId, lens);
  if (!action) return false;

  // If no role_restricted, action is available to all roles
  if (!action.role_restricted || action.role_restricted.length === 0) {
    return true;
  }

  // Check if user's role is in the allowed list
  return action.role_restricted.includes(userRole);
}

/**
 * Get all permitted action IDs for a user in a specific lens
 *
 * @param userRole - The user's role
 * @param lens - The lens context
 * @returns Array of action IDs the user can perform
 *
 * @example
 * ```ts
 * const actions = getPermittedActions('captain', 'work_order');
 * // ['create_work_order', 'update_work_order', 'close_work_order', ...]
 * ```
 */
export function getPermittedActions(userRole: string, lens: string): ActionId[] {
  const lensDefinition = findLens(lens);
  if (!lensDefinition) return [];

  return Object.values(lensDefinition.mutate_actions)
    .filter((action) => {
      // If no role_restricted, action is available to all
      if (!action.role_restricted || action.role_restricted.length === 0) {
        return true;
      }
      return action.role_restricted.includes(userRole);
    })
    .map((action) => action.action_id);
}

/**
 * Get full action metadata
 *
 * @param actionId - The action ID
 * @param lens - The lens context
 * @returns Full action definition or null if not found
 *
 * @example
 * ```ts
 * const meta = getActionMetadata('sign_handover_outgoing', 'handover');
 * if (meta?.requires_signature) {
 *   // Show signature modal
 * }
 * ```
 */
export function getActionMetadata(
  actionId: ActionId,
  lens: string
): ActionPermission | null {
  const action = findAction(actionId, lens);
  return action || null;
}

/**
 * Check if an action requires digital signature
 *
 * @param actionId - The action ID
 * @param lens - The lens context
 * @returns true if signature is required
 */
export function requiresSignature(actionId: ActionId, lens: string): boolean {
  const action = findAction(actionId, lens);
  return action?.requires_signature ?? false;
}

/**
 * Check if an action requires confirmation dialog
 *
 * @param actionId - The action ID
 * @param lens - The lens context
 * @returns true if confirmation is required
 */
export function requiresConfirmation(actionId: ActionId, lens: string): boolean {
  const action = findAction(actionId, lens);
  return action?.requires_confirmation ?? false;
}

/**
 * Get all actions for a lens (regardless of permissions)
 *
 * @param lens - The lens context
 * @returns All action definitions for the lens
 */
export function getAllActions(lens: string): ActionPermission[] {
  const lensDefinition = findLens(lens);
  if (!lensDefinition) return [];
  return Object.values(lensDefinition.mutate_actions);
}

/**
 * Get lens display name
 *
 * @param lens - The lens type
 * @returns Human-readable lens name
 */
export function getLensDisplayName(lens: string): string {
  const lensDefinition = findLens(lens);
  if (!lensDefinition) return lens;
  // Convert snake_case to Title Case
  return lensDefinition.lens
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Check if a lens exists in the matrix
 *
 * @param lens - The lens type to check
 * @returns true if lens is defined
 */
export function lensExists(lens: string): boolean {
  return findLens(lens) !== undefined;
}

/**
 * Get all available lenses
 *
 * @returns Array of all lens types
 */
export function getAllLenses(): Lens[] {
  return Object.keys(getMatrix().lenses) as Lens[];
}
