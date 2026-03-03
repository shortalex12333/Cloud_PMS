'use client';

/**
 * useInventoryPermissions - Type-safe Inventory Permissions
 *
 * Derived from lens_matrix.json - DO NOT hardcode roles here.
 * Uses centralized PermissionService as single source of truth.
 *
 * Actions from lens_matrix.json inventory lens:
 * - log_part_usage: role_restricted: [] (all roles)
 * - update_stock_level: role_restricted: [] (all roles)
 * - create_purchase_request: role_restricted: [] (all roles)
 * - reserve_part: role_restricted: [] (all roles)
 * - count_inventory: role_restricted: [] (all roles)
 */

import { usePermissions } from '../usePermissions';

// Type-safe action IDs for inventory lens
export type InventoryAction =
  | 'log_part_usage'
  | 'update_stock_level'
  | 'create_purchase_request'
  | 'reserve_part'
  | 'count_inventory';

export interface InventoryPermissions {
  /** Can log part usage (all roles) */
  canLogPartUsage: boolean;
  /** Can update stock level (all roles) */
  canUpdateStockLevel: boolean;
  /** Can create purchase request (all roles) */
  canCreatePurchaseRequest: boolean;
  /** Can reserve part (all roles) */
  canReservePart: boolean;
  /** Can count inventory (all roles) */
  canCountInventory: boolean;

  // -------------------------------------------------------------------------
  // Additional permissions (not in lens_matrix, role-based fallbacks)
  // -------------------------------------------------------------------------

  /** Can generate part labels (all roles with inventory access) */
  canGeneratePartLabels: boolean;
  /** Can view detailed part information (all roles) */
  canViewPartDetails: boolean;
  /** Can view low stock alerts (all roles) */
  canViewLowStock: boolean;

  /** Generic check for any inventory action */
  can: (action: InventoryAction) => boolean;

  /** User's current role */
  userRole: string;

  /** Whether auth is loading */
  isLoading: boolean;
}

/**
 * Type-safe inventory permissions hook
 *
 * GENERATED from lens_matrix.json - do NOT hardcode roles here.
 */
export function useInventoryPermissions(): InventoryPermissions {
  const { can, userRole, isLoading } = usePermissions('inventory');

  // Core permissions from lens_matrix
  const canLogPartUsage = can('log_part_usage');

  return {
    canLogPartUsage,
    canUpdateStockLevel: can('update_stock_level'),
    canCreatePurchaseRequest: can('create_purchase_request'),
    canReservePart: can('reserve_part'),
    canCountInventory: can('count_inventory'),

    // Additional permissions - use log_part_usage as proxy (all roles have access)
    canGeneratePartLabels: canLogPartUsage, // Label generation follows usage permission
    canViewPartDetails: canLogPartUsage, // Viewing follows same access as usage
    canViewLowStock: canLogPartUsage, // Low stock alerts follow same access

    can: can as (action: InventoryAction) => boolean,
    userRole,
    isLoading,
  };
}
