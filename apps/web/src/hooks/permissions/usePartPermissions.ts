'use client';

/**
 * usePartPermissions - Type-safe Part Permissions
 *
 * Derived from lens_matrix.json - DO NOT hardcode roles here.
 * Uses centralized PermissionService as single source of truth.
 *
 * Actions from lens_matrix.json part lens:
 * - consume_part: role_restricted: [] (all roles)
 * - receive_part: role_restricted: [] (all roles)
 * - transfer_part: role_restricted: [] (all roles)
 * - adjust_stock_quantity: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - write_off_part: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - add_to_shopping_list: role_restricted: [] (all roles)
 * - order_part: role_restricted: ['chief_engineer', 'captain', 'manager']
 */

import { usePermissions } from '../usePermissions';

// Type-safe action IDs for part lens
export type PartAction =
  | 'consume_part'
  | 'receive_part'
  | 'transfer_part'
  | 'adjust_stock_quantity'
  | 'write_off_part'
  | 'add_to_shopping_list'
  | 'order_part';

export interface PartPermissions {
  /** Can consume part (all roles) */
  canConsumePart: boolean;
  /** Can receive part (all roles) */
  canReceivePart: boolean;
  /** Can transfer part (all roles) */
  canTransferPart: boolean;
  /** Can adjust stock quantity (chief_engineer, captain, manager) */
  canAdjustStockQuantity: boolean;
  /** Can write off part (chief_engineer, captain, manager) */
  canWriteOffPart: boolean;
  /** Can add to shopping list (all roles) */
  canAddToShoppingList: boolean;
  /** Can order part (chief_engineer, captain, manager) */
  canOrderPart: boolean;

  /** Generic check for any part action */
  can: (action: PartAction) => boolean;

  /** User's current role */
  userRole: string;

  /** Whether auth is loading */
  isLoading: boolean;
}

/**
 * Type-safe part permissions hook
 *
 * GENERATED from lens_matrix.json - do NOT hardcode roles here.
 */
export function usePartPermissions(): PartPermissions {
  const { can, userRole, isLoading } = usePermissions('part');

  return {
    canConsumePart: can('consume_part'),
    canReceivePart: can('receive_part'),
    canTransferPart: can('transfer_part'),
    canAdjustStockQuantity: can('adjust_stock_quantity'),
    canWriteOffPart: can('write_off_part'),
    canAddToShoppingList: can('add_to_shopping_list'),
    canOrderPart: can('order_part'),
    can: can as (action: PartAction) => boolean,
    userRole,
    isLoading,
  };
}
