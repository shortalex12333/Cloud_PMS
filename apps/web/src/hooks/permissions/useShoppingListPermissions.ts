'use client';

/**
 * useShoppingListPermissions - Type-safe Shopping List Permissions
 *
 * Derived from lens_matrix.json - DO NOT hardcode roles here.
 * Uses centralized PermissionService as single source of truth.
 *
 * Actions from lens_matrix.json shopping_list lens:
 * - create_shopping_list_item: role_restricted: [] (all roles)
 * - approve_shopping_list_item: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - reject_shopping_list_item: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - promote_candidate_to_part: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - update_shopping_list_item: role_restricted: [] (all roles)
 * - mark_item_ordered: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - mark_item_received: role_restricted: [] (all roles)
 */

import { usePermissions } from '../usePermissions';

// Type-safe action IDs for shopping_list lens
export type ShoppingListAction =
  | 'create_shopping_list_item'
  | 'approve_shopping_list_item'
  | 'reject_shopping_list_item'
  | 'promote_candidate_to_part'
  | 'update_shopping_list_item'
  | 'mark_item_ordered'
  | 'mark_item_received';

export interface ShoppingListPermissions {
  /** Can create shopping list item (all roles) */
  canCreateShoppingListItem: boolean;
  /** Can approve item (chief_engineer, captain, manager) */
  canApproveShoppingListItem: boolean;
  /** Can reject item (chief_engineer, captain, manager) */
  canRejectShoppingListItem: boolean;
  /** Can promote candidate to part (chief_engineer, captain, manager) */
  canPromoteCandidateToPart: boolean;
  /** Can update item (all roles) */
  canUpdateShoppingListItem: boolean;
  /** Can mark as ordered (chief_engineer, captain, manager) */
  canMarkItemOrdered: boolean;
  /** Can mark as received (all roles) */
  canMarkItemReceived: boolean;

  // -------------------------------------------------------------------------
  // Backward-compatible aliases (used by useShoppingListActions.ts)
  // -------------------------------------------------------------------------

  /** @alias canMarkItemOrdered - Mark shopping list item as ordered */
  canMarkShoppingListOrdered: boolean;

  /** Generic check for any shopping list action */
  can: (action: ShoppingListAction) => boolean;

  /** User's current role */
  userRole: string;

  /** Whether auth is loading */
  isLoading: boolean;
}

/**
 * Type-safe shopping list permissions hook
 *
 * GENERATED from lens_matrix.json - do NOT hardcode roles here.
 */
export function useShoppingListPermissions(): ShoppingListPermissions {
  const { can, userRole, isLoading } = usePermissions('shopping_list');

  // Compute for reuse in aliases
  const canMarkItemOrdered = can('mark_item_ordered');

  return {
    canCreateShoppingListItem: can('create_shopping_list_item'),
    canApproveShoppingListItem: can('approve_shopping_list_item'),
    canRejectShoppingListItem: can('reject_shopping_list_item'),
    canPromoteCandidateToPart: can('promote_candidate_to_part'),
    canUpdateShoppingListItem: can('update_shopping_list_item'),
    canMarkItemOrdered,
    canMarkItemReceived: can('mark_item_received'),

    // Backward-compatible alias for useShoppingListActions.ts
    canMarkShoppingListOrdered: canMarkItemOrdered,

    can: can as (action: ShoppingListAction) => boolean,
    userRole,
    isLoading,
  };
}
