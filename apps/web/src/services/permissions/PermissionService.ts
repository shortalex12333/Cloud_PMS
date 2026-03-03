/**
 * PermissionService - Centralized RBAC Permission Resolution
 *
 * Single source of truth for role-based access control.
 * Reads from lens_matrix.json to determine who can perform what actions.
 *
 * SEMANTICS (critical):
 * - role_restricted: [] -> ALL roles can perform action
 * - role_restricted: ['captain', 'manager'] -> ONLY those roles
 *
 * This eliminates 76 hardcoded role arrays scattered across 13 hooks.
 */

// Import lens_matrix.json at build time
import lensMatrix from '../../../../../.planning/agents/lens-matrix/lens_matrix.json';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * Roles defined in the system
 * Note: lens_matrix.json uses these specific roles for restrictions:
 * - chief_engineer, captain, manager (restricted actions)
 * - Empty array means ALL roles have access
 */
export type Role =
  | 'crew'
  | 'deckhand'
  | 'steward'
  | 'chef'
  | 'eto'
  | 'engineer'
  | 'chief_engineer'
  | 'chief_officer'
  | 'captain'
  | 'manager'
  | 'bosun'
  | 'purser'
  | 'member'; // default role from AuthContext

/**
 * All lenses defined in lens_matrix.json
 */
export type Lens = keyof typeof lensMatrix.lenses;

/**
 * Action ID string
 */
export type ActionId = string;

/**
 * Permission metadata for an action
 */
export interface ActionPermission {
  actionId: string;
  roleRestricted: string[];
  requiredFields: string[];
  optionalFields: string[];
  requiresSignature?: boolean;
  requiresConfirmation?: boolean;
}

/**
 * Lens configuration
 */
interface LensConfig {
  lens: string;
  read_filters: Record<string, unknown>;
  mutate_actions: Record<string, ActionConfig>;
}

/**
 * Action configuration from lens_matrix.json
 */
interface ActionConfig {
  action_id: string;
  required_fields: string[];
  optional_fields: string[];
  role_restricted: string[];
  requires_signature?: boolean;
  requires_confirmation?: boolean;
  confirmation_message?: string;
}

// ---------------------------------------------------------------------------
// Type-safe access to lens matrix
// ---------------------------------------------------------------------------

const lenses = lensMatrix.lenses as Record<string, LensConfig>;

// ---------------------------------------------------------------------------
// Core Permission Functions
// ---------------------------------------------------------------------------

/**
 * Check if a user with given role can perform an action in a lens
 *
 * @param userRole - The user's role (from AuthContext)
 * @param actionId - The action to check (e.g., 'update_fault')
 * @param lens - The lens context (e.g., 'fault')
 * @returns true if the user can perform the action
 *
 * SEMANTICS:
 * - Empty role_restricted array = ALL roles can access
 * - Non-empty array = ONLY listed roles can access
 */
export function canPerformAction(userRole: Role | string, actionId: ActionId, lens: Lens): boolean {
  const lensConfig = lenses[lens];
  if (!lensConfig) {
    console.warn(`[PermissionService] Unknown lens: ${lens}`);
    return false;
  }

  const action = lensConfig.mutate_actions[actionId];
  if (!action) {
    // Action not found in this lens - might be a read action or custom action
    // Return true to allow (backend will enforce)
    return true;
  }

  const restricted = action.role_restricted;

  // Empty array = no restriction = everyone can do it
  if (!restricted || restricted.length === 0) {
    return true;
  }

  // Non-empty array = only listed roles
  return restricted.includes(userRole);
}

/**
 * Get all permitted actions for a role in a lens
 *
 * @param userRole - The user's role
 * @param lens - The lens to check
 * @returns Array of action IDs the user can perform
 */
export function getPermittedActions(userRole: Role | string, lens: Lens): ActionId[] {
  const lensConfig = lenses[lens];
  if (!lensConfig) {
    console.warn(`[PermissionService] Unknown lens: ${lens}`);
    return [];
  }

  return Object.keys(lensConfig.mutate_actions).filter(
    actionId => canPerformAction(userRole, actionId, lens)
  );
}

/**
 * Get action metadata (for UI hints like confirmation dialogs)
 *
 * @param actionId - The action to get metadata for
 * @param lens - The lens context
 * @returns Action permission metadata or null if not found
 */
export function getActionMetadata(actionId: ActionId, lens: Lens): ActionPermission | null {
  const lensConfig = lenses[lens];
  if (!lensConfig) return null;

  const action = lensConfig.mutate_actions[actionId];
  if (!action) return null;

  return {
    actionId: action.action_id,
    roleRestricted: action.role_restricted,
    requiredFields: action.required_fields,
    optionalFields: action.optional_fields,
    requiresSignature: action.requires_signature,
    requiresConfirmation: action.requires_confirmation,
  };
}

/**
 * Get all actions in a lens
 *
 * @param lens - The lens to get actions for
 * @returns Array of all action IDs in the lens
 */
export function getAllActions(lens: Lens): ActionId[] {
  const lensConfig = lenses[lens];
  if (!lensConfig) return [];

  return Object.keys(lensConfig.mutate_actions);
}

/**
 * Check if an action requires a signature
 *
 * @param actionId - The action to check
 * @param lens - The lens context
 * @returns true if signature is required
 */
export function requiresSignature(actionId: ActionId, lens: Lens): boolean {
  const metadata = getActionMetadata(actionId, lens);
  return metadata?.requiresSignature ?? false;
}

/**
 * Check if an action requires confirmation
 *
 * @param actionId - The action to check
 * @param lens - The lens context
 * @returns true if confirmation is required
 */
export function requiresConfirmation(actionId: ActionId, lens: Lens): boolean {
  const metadata = getActionMetadata(actionId, lens);
  return metadata?.requiresConfirmation ?? false;
}

/**
 * Get list of available lenses
 */
export function getAvailableLenses(): Lens[] {
  return Object.keys(lenses) as Lens[];
}

/**
 * Check if a lens exists
 */
export function isValidLens(lens: string): lens is Lens {
  return lens in lenses;
}
