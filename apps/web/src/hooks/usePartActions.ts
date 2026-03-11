'use client';

/**
 * usePartActions — Unified Parts/Inventory action hook
 *
 * Consolidated from usePartActions + usePartsActions into a single canonical hook.
 * Uses actionClient for standardized auth (Supabase session management).
 *
 * Action IDs map 1:1 to registry.py keys:
 *   view_part, consume_part, receive_part, transfer_part,
 *   adjust_stock_quantity, write_off_part, create_shopping_list_item,
 *   generate_part_labels, view_part_details, check_stock_level,
 *   log_part_usage, view_low_stock
 *
 * Role-based access is enforced at the API level; visibility gates live in
 * the lens components (hide, not disable — per UI_SPEC.md pattern).
 */

import { useState, useCallback } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { executeAction, type ActionResult } from '@/lib/actionClient';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PartActionResult {
  success: boolean;
  message?: string;
  data?: Record<string, unknown>;
  error?: string;
}

export interface PartActionsState {
  isLoading: boolean;
  error: string | null;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * usePartActions
 *
 * Returns typed action helpers for ALL parts/inventory operations.
 * Each helper calls POST /v1/actions/execute via actionClient.
 *
 * @param partId - UUID of the part in scope
 */
export function usePartActions(partId: string) {
  const { user } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // Internal executor — wraps every action call
  // -------------------------------------------------------------------------

  const execute = useCallback(
    async (actionName: string, payload: Record<string, unknown>): Promise<PartActionResult> => {
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
    [user, partId]
  );

  // -------------------------------------------------------------------------
  // Core part actions (from original usePartActions)
  // -------------------------------------------------------------------------

  /** view_part — fetch part details (read-only) */
  const viewPart = useCallback(
    () => execute('view_part', {}),
    [execute]
  );

  /** consume_part — record stock consumption */
  const consumePart = useCallback(
    (quantity: number, workOrderId?: string, notes?: string) =>
      execute('consume_part', {
        quantity,
        ...(workOrderId && { work_order_id: workOrderId }),
        ...(notes && { notes }),
      }),
    [execute]
  );

  /** receive_part — add incoming stock (HOD+) */
  const receivePart = useCallback(
    (quantity: number, notes?: string) =>
      execute('receive_part', { quantity, ...(notes && { notes }) }),
    [execute]
  );

  /** transfer_part — move stock between locations (HOD+) */
  const transferPart = useCallback(
    (quantity: number, fromLocation: string, toLocation: string, notes?: string) =>
      execute('transfer_part', {
        quantity,
        from_location: fromLocation,
        to_location: toLocation,
        ...(notes && { notes }),
      }),
    [execute]
  );

  /** adjust_stock_quantity — manual correction (captain, manager - SIGNED) */
  const adjustStock = useCallback(
    (newQuantity: number, reason: string, locationId?: string) =>
      execute('adjust_stock_quantity', {
        new_quantity: newQuantity,
        reason,
        ...(locationId && { location_id: locationId }),
      }),
    [execute]
  );

  /** write_off_part — write off damaged/expired stock (HOD+) */
  const writeOff = useCallback(
    (quantity: number, reason: string) =>
      execute('write_off_part', { quantity, reason }),
    [execute]
  );

  /** create_shopping_list_item — add to procurement list */
  const addToShoppingList = useCallback(
    (quantity?: number, priority?: string, notes?: string, sourceWorkOrderId?: string) =>
      execute('create_shopping_list_item', {
        ...(quantity !== undefined && { quantity_requested: quantity }),
        ...(priority && { priority }),
        ...(notes && { source_notes: notes }),
        ...(sourceWorkOrderId && { source_work_order_id: sourceWorkOrderId }),
        source_type: 'manual_add',
      }),
    [execute]
  );

  // -------------------------------------------------------------------------
  // Extended part actions (from original usePartsActions)
  // -------------------------------------------------------------------------

  /** generate_part_labels — generate printable labels (barcode/QR) */
  const generateLabels = useCallback(
    (part_ids: string[], label_format?: 'barcode' | 'qr', include_location?: boolean) =>
      execute('generate_part_labels', {
        part_ids,
        ...(label_format && { label_format }),
        ...(include_location !== undefined && { include_location }),
      }),
    [execute]
  );

  /** view_part_details — detailed specs, BOM links, location */
  const viewDetails = useCallback(
    (include_bom?: boolean, include_history?: boolean) =>
      execute('view_part_details', {
        ...(include_bom !== undefined && { include_bom }),
        ...(include_history !== undefined && { include_history }),
      }),
    [execute]
  );

  /** check_stock_level — current quantity on-hand and location */
  const checkStockLevel = useCallback(
    (part_id?: string) =>
      execute('check_stock_level', {
        ...(part_id && { part_id }),
      }),
    [execute]
  );

  /** log_part_usage — record consumption with context */
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

  /** view_low_stock — alert report for parts below threshold */
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

    // Core actions
    viewPart,
    consumePart,
    receivePart,
    transferPart,
    adjustStock,
    writeOff,
    addToShoppingList,

    // Extended actions
    generateLabels,
    viewDetails,
    checkStockLevel,
    logUsage,
    viewLowStock,
  };
}

// ---------------------------------------------------------------------------
// Re-export ActionResult for consumers that imported it from here
// ---------------------------------------------------------------------------

export type { ActionResult };

// ---------------------------------------------------------------------------
// Role permission helpers - DELEGATED TO CENTRALIZED SERVICE
// ---------------------------------------------------------------------------

import { usePartPermissions as useCentralizedPartPermissions } from '@/hooks/permissions/usePartPermissions';
import { useInventoryPermissions as useCentralizedInventoryPermissions } from '@/hooks/permissions/useInventoryPermissions';

export interface PartPermissions {
  canView: boolean;
  canConsume: boolean;
  canReceive: boolean;
  canTransfer: boolean;
  canAdjustStock: boolean;
  canWriteOff: boolean;
  canAddToShoppingList: boolean;
  canGenerateLabels: boolean;
  canViewDetails: boolean;
  canLogUsage: boolean;
  canViewLowStock: boolean;
}

/**
 * usePartPermissions
 *
 * Unified permission flags for all part actions.
 * DELEGATED TO CENTRALIZED SERVICE - reads from lens_matrix.json
 */
export function usePartPermissions(): PartPermissions {
  const partPerms = useCentralizedPartPermissions();
  const invPerms = useCentralizedInventoryPermissions();

  return {
    canView: true,
    canConsume: partPerms.canConsumePart,
    canReceive: partPerms.canReceivePart,
    canTransfer: partPerms.canTransferPart,
    canAdjustStock: partPerms.canAdjustStockQuantity,
    canWriteOff: partPerms.canWriteOffPart,
    canAddToShoppingList: partPerms.canAddToShoppingList,
    canGenerateLabels: invPerms.canGeneratePartLabels,
    canViewDetails: invPerms.canViewPartDetails,
    canLogUsage: invPerms.canLogPartUsage,
    canViewLowStock: invPerms.canViewLowStock,
  };
}

/**
 * usePartsPermissions — Backwards-compatible alias
 *
 * Maps the old usePartsPermissions interface to the unified usePartPermissions.
 * Consumers: PartsLensContent.tsx
 */
export function usePartsPermissions() {
  const perms = usePartPermissions();
  return {
    canConsume: perms.canConsume,
    canAdjust: perms.canAdjustStock,
    canAddToList: perms.canAddToShoppingList,
    canGenerateLabels: perms.canGenerateLabels,
    canViewDetails: perms.canViewDetails,
    canLogUsage: perms.canLogUsage,
    canViewLowStock: perms.canViewLowStock,
  };
}
