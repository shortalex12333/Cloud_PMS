'use client';

/**
 * usePartsActions — Parts/Inventory action hook (FE-01-03)
 *
 * Wires all parts action registry calls to typed helper methods.
 * Uses the unified action API endpoint per the action router spec.
 *
 * Action IDs map 1:1 to registry.py keys:
 *   consume_part, adjust_stock_quantity, add_to_shopping_list, generate_part_labels, check_stock_level, log_part_usage
 *
 * Role-based access is enforced at the API level; visibility gates live in
 * PartsLens (hide, not disable).
 */

import { useState, useCallback } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { executeAction, ActionResult } from '@/lib/actionClient';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PartsActionResult {
  success: boolean;
  message?: string;
  data?: Record<string, unknown>;
  error?: string;
}

export interface GenerateLabelsParams {
  part_ids: string[];
  label_format?: 'barcode' | 'qr';
  include_location?: boolean;
}

export interface ViewDetailsParams {
  include_bom?: boolean;
  include_history?: boolean;
}

export interface LogUsageParams {
  quantity: number;
  work_order_id?: string;
  equipment_id?: string;
  notes?: string;
}

export interface ViewLowStockParams {
  threshold_percentage?: number;
  category_filter?: string[];
}

export interface PartsActionsState {
  isLoading: boolean;
  error: string | null;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * usePartsActions
 *
 * Returns typed action helpers for all parts/inventory operations.
 * Each helper calls POST /v1/actions/execute with action name and JWT auth.
 *
 * @param partId - UUID of the part in scope
 */
export function usePartsActions(partId: string) {
  const { user, session } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // Internal executor — wraps every action call
  // -------------------------------------------------------------------------

  const execute = useCallback(
    async (actionName: string, payload: Record<string, unknown>): Promise<PartsActionResult> => {
      if (!session?.access_token) {
        return { success: false, error: 'Not authenticated' };
      }

      if (!user?.yachtId) {
        return { success: false, error: 'No yacht context available' };
      }

      setIsLoading(true);
      setError(null);

      try {
        const result = await executeAction(
          actionName,
          {
            yacht_id: user.yachtId,
            part_id: partId,
          },
          {
            part_id: partId,
            ...payload,
          }
        );

        if (result.status === 'error') {
          const msg = result.message || result.error_code || 'Action failed';
          setError(msg);
          return { success: false, error: msg };
        }

        return { success: true, data: result.result, message: result.message };
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Unknown error';
        setError(msg);
        return { success: false, error: msg };
      } finally {
        setIsLoading(false);
      }
    },
    [session, user, partId]
  );

  // -------------------------------------------------------------------------
  // Typed action helpers — one per registry action
  // -------------------------------------------------------------------------

  /**
   * consume_part — Record consumption/usage of a part
   *
   * @param quantity - Number of units consumed
   * @param workOrderId - Optional work order this consumption is for
   * @param notes - Optional notes about the consumption
   */
  const consumePart = useCallback(
    (quantity: number, workOrderId?: string, notes?: string) =>
      execute('consume_part', {
        quantity,
        ...(workOrderId && { work_order_id: workOrderId }),
        ...(notes && { notes }),
      }),
    [execute]
  );

  /**
   * adjust_stock_quantity — Adjust inventory stock level (count/audit)
   *
   * @param newQuantity - New stock quantity after adjustment
   * @param reason - Reason for the adjustment (e.g., "Physical count", "Damage", "Found stock")
   * @param locationId - Optional location ID for location-specific adjustment
   */
  const adjustStock = useCallback(
    (newQuantity: number, reason: string, locationId?: string) =>
      execute('adjust_stock_quantity', {
        new_quantity: newQuantity,
        reason,
        ...(locationId && { location_id: locationId }),
      }),
    [execute]
  );

  /**
   * add_to_shopping_list — Add part to procurement shopping list
   *
   * @param quantity - Quantity to order
   * @param priority - Priority level (low, normal, high, urgent)
   * @param notes - Optional procurement notes
   * @param sourceWorkOrderId - Optional source work order ID
   */
  const addToShoppingList = useCallback(
    (quantity: number, priority?: string, notes?: string, sourceWorkOrderId?: string) =>
      execute('add_to_shopping_list', {
        quantity,
        ...(priority && { priority }),
        ...(notes && { notes }),
        ...(sourceWorkOrderId && { source_work_order_id: sourceWorkOrderId }),
      }),
    [execute]
  );

  /**
   * generate_part_labels — Generate printable labels (barcode/QR) for parts
   *
   * @param part_ids - Array of part IDs to generate labels for
   * @param label_format - Label format: 'barcode' or 'qr' (default: 'barcode')
   * @param include_location - Include storage location on labels (default: false)
   * @returns Download URL for the generated PDF
   */
  const generateLabels = useCallback(
    (part_ids: string[], label_format?: 'barcode' | 'qr', include_location?: boolean) =>
      execute('generate_part_labels', {
        part_ids,
        ...(label_format && { label_format }),
        ...(include_location !== undefined && { include_location }),
      }),
    [execute]
  );

  /**
   * view_part_details — Retrieve detailed specs, BOM links, and location for a part
   *
   * @param include_bom - Include bill of materials links (default: false)
   * @param include_history - Include part usage/consumption history (default: false)
   * @returns Part specifications, BOM links, and location information
   */
  const viewDetails = useCallback(
    (include_bom?: boolean, include_history?: boolean) =>
      execute('view_part_details', {
        ...(include_bom !== undefined && { include_bom }),
        ...(include_history !== undefined && { include_history }),
      }),
    [execute]
  );

  /**
   * check_stock_level — Check current quantity on-hand and storage location for a part
   *
   * @param part_id - Optional part ID (uses context part_id if not provided)
   * @returns Current quantity on-hand and storage location information
   */
  const checkStockLevel = useCallback(
    (part_id?: string) =>
      execute('check_stock_level', {
        ...(part_id && { part_id }),
      }),
    [execute]
  );

  /**
   * log_part_usage — Record consumption with context (equipment, work order, notes)
   *
   * @param quantity - Number of units consumed
   * @param workOrderId - Optional work order this usage is associated with
   * @param equipmentId - Optional equipment ID the part was used on
   * @param notes - Optional notes about the usage context
   */
  const logUsage = useCallback(
    (quantity: number, workOrderId?: string, equipmentId?: string, notes?: string) =>
      execute('log_part_usage', {
        quantity,
        ...(workOrderId && { work_order_id: workOrderId }),
        ...(equipmentId && { equipment_id: equipmentId }),
        ...(notes && { notes }),
      }),
    [execute]
  );

  /**
   * view_low_stock — Retrieve alert report for parts with stock below threshold
   *
   * @param threshold_percentage - Stock level threshold percentage (default: 20%)
   * @param category_filter - Optional array of part categories to filter by
   * @returns Alert report for reorder candidates
   */
  const viewLowStock = useCallback(
    (threshold_percentage?: number, category_filter?: string[]) =>
      execute('view_low_stock', {
        ...(threshold_percentage !== undefined && { threshold_percentage }),
        ...(category_filter && { category_filter }),
      }),
    [execute]
  );

  // -------------------------------------------------------------------------
  // Return
  // -------------------------------------------------------------------------

  return {
    // State
    isLoading,
    error,

    // Actions
    consumePart,
    adjustStock,
    addToShoppingList,
    generateLabels,
    viewDetails,
    checkStockLevel,
    logUsage,
    viewLowStock,
  };
}

// ---------------------------------------------------------------------------
// Role permission helpers - DELEGATED TO CENTRALIZED SERVICE
// ---------------------------------------------------------------------------

// Note: Parts lens in lens_matrix.json defines role_restricted arrays.
// Permissions are now derived from the centralized service.

export interface PartsPermissions {
  /** Can log part consumption/usage */
  canConsume: boolean;
  /** Can adjust stock quantities (count/audit) */
  canAdjust: boolean;
  /** Can add parts to shopping list */
  canAddToList: boolean;
  /** Can generate part labels (barcode/QR) */
  canGenerateLabels: boolean;
  /** Can view detailed part information (specs, BOM, location) */
  canViewDetails: boolean;
  /** Can log part usage with context (work order, equipment, notes) */
  canLogUsage: boolean;
  /** Can view low stock alert report */
  canViewLowStock: boolean;
}

import { usePartPermissions as useCentralizedPartPermissions } from '@/hooks/permissions/usePartPermissions';
import { useInventoryPermissions as useCentralizedInventoryPermissions } from '@/hooks/permissions/useInventoryPermissions';

/**
 * usePartsPermissions
 *
 * Derives a set of boolean capability flags from the current user's role.
 * DELEGATED TO CENTRALIZED SERVICE - reads from lens_matrix.json (part + inventory lenses)
 * These are used to conditionally show (not disable) action buttons.
 */
export function usePartsPermissions(): PartsPermissions {
  const partPerms = useCentralizedPartPermissions();
  const invPerms = useCentralizedInventoryPermissions();

  return {
    canConsume: partPerms.canConsumePart,
    canAdjust: partPerms.canAdjustStockQuantity,
    canAddToList: partPerms.canAddToShoppingList,
    canGenerateLabels: invPerms.canGeneratePartLabels,
    canViewDetails: invPerms.canViewPartDetails,
    canLogUsage: invPerms.canLogPartUsage,
    canViewLowStock: invPerms.canViewLowStock,
  };
}
