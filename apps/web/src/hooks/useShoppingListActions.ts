'use client';

/**
 * useShoppingListActions - Shopping List action hook (FE-01-06)
 *
 * Wires all shopping list action registry calls to typed helper methods.
 * Uses the unified action API endpoint per the action router spec.
 *
 * Action IDs map 1:1 to registry.py keys:
 *   create_shopping_list_item, approve_shopping_list_item, reject_shopping_list_item
 *
 * State machine:
 *   candidate -> under_review -> approved -> ordered -> partially_fulfilled -> fulfilled -> installed
 *                             -> rejected (terminal)
 *
 * Role-based access is enforced at the API level; visibility gates live in
 * ShoppingListLens (hide, not disable).
 */

import { useState, useCallback } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { executeAction } from '@/lib/actionClient';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ActionResult {
  success: boolean;
  message?: string;
  data?: Record<string, unknown>;
  error?: string;
}

export interface ShoppingListActionsState {
  isLoading: boolean;
  error: string | null;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * useShoppingListActions
 *
 * Returns typed action helpers for all shopping list operations.
 * Each helper calls POST /v1/actions/execute with action name and JWT auth.
 *
 * @param itemId - UUID of the shopping list item in scope (optional for create)
 */
export function useShoppingListActions(itemId?: string) {
  const { user } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // Internal executor - wraps every action call
  // -------------------------------------------------------------------------

  const execute = useCallback(
    async (actionName: string, payload: Record<string, unknown>): Promise<ActionResult> => {
      if (!user?.yachtId) {
        return { success: false, error: 'No yacht context available' };
      }

      setIsLoading(true);
      setError(null);

      try {
        const context: Record<string, unknown> = {
          yacht_id: user.yachtId,
        };

        // Include shopping_list_item_id in context if available
        if (itemId) {
          context.shopping_list_item_id = itemId;
        }

        const result = await executeAction(actionName, context, {
          shopping_list_item_id: itemId,
          ...payload,
        });

        if (result.status === 'error') {
          const msg = result.message || `Action '${actionName}' failed`;
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
    [user, itemId]
  );

  // -------------------------------------------------------------------------
  // Typed action helpers - one per registry action
  // -------------------------------------------------------------------------

  /**
   * create_shopping_list_item - Create a new shopping list item
   *
   * Creates a candidate item that goes through approval workflow.
   *
   * @param params - Item creation parameters
   * @param params.part_id - Optional: Link to existing part catalog entry
   * @param params.description - Item description (required if no part_id)
   * @param params.quantity - Requested quantity
   * @param params.unit - Unit of measure (e.g., 'each', 'liters', 'kg')
   * @param params.priority - 'low' | 'normal' | 'high' | 'critical'
   * @param params.notes - Additional notes for procurement
   * @param params.source_work_order_id - Optional: Link to originating work order
   * @param params.estimated_cost - Optional: Estimated unit cost
   */
  const createItem = useCallback(
    (params: {
      part_id?: string;
      description?: string;
      quantity: number;
      unit?: string;
      priority?: 'low' | 'normal' | 'high' | 'critical';
      notes?: string;
      source_work_order_id?: string;
      estimated_cost?: number;
    }) =>
      execute('create_shopping_list_item', {
        part_id: params.part_id,
        description: params.description,
        quantity: params.quantity,
        unit: params.unit || 'each',
        priority: params.priority || 'normal',
        notes: params.notes,
        source_work_order_id: params.source_work_order_id,
        estimated_cost: params.estimated_cost,
      }),
    [execute]
  );

  /**
   * approve_shopping_list_item - Approve item for ordering (HOD+)
   *
   * Transitions item from under_review -> approved state.
   * Updates state history and triggers procurement workflow.
   *
   * @param approvalNotes - Optional notes explaining approval decision
   */
  const approveItem = useCallback(
    (approvalNotes?: string) =>
      execute('approve_shopping_list_item', {
        approval_notes: approvalNotes,
      }),
    [execute]
  );

  /**
   * reject_shopping_list_item - Reject item (HOD+)
   *
   * Transitions item to rejected (terminal) state.
   * Updates state history with rejection reason.
   *
   * @param reason - Required: Reason for rejection
   */
  const rejectItem = useCallback(
    (reason: string) =>
      execute('reject_shopping_list_item', {
        rejection_reason: reason,
      }),
    [execute]
  );

  /**
   * mark_shopping_list_ordered - Mark item as ordered (procurement action)
   *
   * Transitions item from approved -> ordered state.
   * Links to purchase order and updates procurement tracking.
   *
   * Note: Uses dedicated mark_shopping_list_ordered action (fixed 2026-03-02).
   * Previously tried to use approve_shopping_list_item with transition_to: 'ordered'
   * but backend ignored the parameter.
   *
   * @param params - Order tracking parameters
   * @param params.order_id - Optional: Link to purchase order
   * @param params.order_reference - Optional: External PO reference number
   * @param params.supplier - Optional: Supplier name
   * @param params.ordered_quantity - Quantity actually ordered
   * @param params.unit_price - Actual unit price
   * @param params.expected_delivery_date - Expected delivery date (ISO string)
   */
  const markOrdered = useCallback(
    (params: {
      order_id?: string;
      order_reference?: string;
      supplier?: string;
      ordered_quantity?: number;
      unit_price?: number;
      expected_delivery_date?: string;
    }) =>
      execute('mark_shopping_list_ordered', {
        order_id: params.order_id,
        order_reference: params.order_reference,
        supplier: params.supplier,
        ordered_quantity: params.ordered_quantity,
        unit_price: params.unit_price,
        expected_delivery_date: params.expected_delivery_date,
      }),
    [execute]
  );

  /**
   * promote_candidate_to_part - Promote shopping list item to parts catalog
   *
   * Adds a candidate item to the parts catalog as a permanent part entry.
   * Requires HOD+ roles. Creates a new part record linked to the original shopping list item.
   *
   * @param params - Part promotion parameters
   * @param params.part_number - Optional: Part number to assign
   * @param params.location - Optional: Default storage location
   * @param params.min_stock - Optional: Minimum stock level
   */
  const promoteTopart = useCallback(
    (params: {
      part_number?: string;
      location?: string;
      min_stock?: number;
    }) =>
      execute('promote_candidate_to_part', {
        part_number: params.part_number,
        location: params.location,
        min_stock: params.min_stock,
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
    createItem,
    approveItem,
    rejectItem,
    markOrdered,
    promoteTopart,
  };
}

// ---------------------------------------------------------------------------
// Role permission helpers - DELEGATED TO CENTRALIZED SERVICE
// ---------------------------------------------------------------------------

// Note: Shopping list lens in lens_matrix.json defines role_restricted arrays.
// Permissions are now derived from the centralized service.

export interface ShoppingListPermissions {
  /** Can create a new shopping list item (all crew) */
  canCreate: boolean;
  /** Can approve items for ordering (HOD+) */
  canApprove: boolean;
  /** Can reject items (HOD+) */
  canReject: boolean;
  /** Can mark items as ordered (procurement roles) */
  canMarkOrdered: boolean;
  /** Can promote candidate items to parts catalog (HOD+) */
  canPromoteToPart: boolean;
}

import { useShoppingListPermissions as useCentralizedShoppingListPermissions } from '@/hooks/permissions/useShoppingListPermissions';

/**
 * useShoppingListPermissions
 *
 * Derives a set of boolean capability flags from the current user's role.
 * DELEGATED TO CENTRALIZED SERVICE - reads from lens_matrix.json
 * These are used to conditionally show (not disable) action buttons.
 */
export function useShoppingListPermissions(): ShoppingListPermissions {
  const central = useCentralizedShoppingListPermissions();

  return {
    canCreate: central.canCreateShoppingListItem,
    canApprove: central.canApproveShoppingListItem,
    canReject: central.canRejectShoppingListItem,
    canMarkOrdered: central.canMarkShoppingListOrdered,
    canPromoteToPart: central.canPromoteCandidateToPart,
  };
}
