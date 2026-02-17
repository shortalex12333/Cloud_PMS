'use client';

/**
 * useShoppingListActions — Shopping List action hook (FE-03-05)
 *
 * Wires all shopping list action registry calls to typed helper methods.
 * Uses the unified action API endpoint per the action router spec.
 *
 * Action IDs map 1:1 to registry.py keys:
 *   create_shopping_list_item, update_shopping_list_item,
 *   remove_shopping_list_item, approve_shopping_list_item (HOD+),
 *   reject_shopping_list_item (HOD+ with reason),
 *   mark_ordered
 *
 * Role-based access is enforced at the API level; visibility gates live in
 * ShoppingListLens (hide, not disable).
 *
 * State transitions tracked in pms_audit_log (SHOP-03 requirement).
 */

import { useState, useCallback } from 'react';
import { useAuth } from '@/hooks/useAuth';

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

// API URL — same origin Next.js API route proxied to Render backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * useShoppingListActions
 *
 * Returns typed action helpers for all shopping list operations.
 * Each helper calls POST to the backend action endpoint with JWT auth.
 *
 * @param shoppingListId - UUID of the shopping list in scope
 */
export function useShoppingListActions(shoppingListId: string) {
  const { user, session } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // Internal executor — wraps every action call
  // -------------------------------------------------------------------------

  const execute = useCallback(
    async (endpoint: string, payload: Record<string, unknown>): Promise<ActionResult> => {
      if (!session?.access_token) {
        return { success: false, error: 'Not authenticated' };
      }

      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${session.access_token}`,
          },
          body: JSON.stringify({
            yacht_id: user?.yachtId,
            shopping_list_id: shoppingListId,
            ...payload,
          }),
        });

        const json = await response.json().catch(() => ({}));

        if (!response.ok) {
          const msg =
            (json as { error?: string; detail?: string }).error ||
            (json as { error?: string; detail?: string }).detail ||
            `Request failed (${response.status})`;
          setError(msg);
          return { success: false, error: msg };
        }

        return { success: true, ...(json as object) };
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Unknown error';
        setError(msg);
        return { success: false, error: msg };
      } finally {
        setIsLoading(false);
      }
    },
    [session, user, shoppingListId]
  );

  // -------------------------------------------------------------------------
  // Typed action helpers — one per registry action
  // -------------------------------------------------------------------------

  /**
   * create_item — crew adds a new item to the shopping list.
   * Any authenticated crew member can request items.
   */
  const createItem = useCallback(
    (params: {
      part_name: string;
      quantity_requested: number;
      unit?: string;
      urgency?: 'low' | 'normal' | 'high' | 'critical';
      source_type?: string;
      source_notes?: string;
      part_id?: string;
      part_number?: string;
      manufacturer?: string;
      preferred_supplier?: string;
      estimated_unit_price?: number;
    }) =>
      execute('/v1/shopping-list/create-item', params),
    [execute]
  );

  /**
   * update_item — edit an existing item (crew can edit own items,
   * HOD+ can edit any item).
   */
  const updateItem = useCallback(
    (
      itemId: string,
      changes: {
        part_name?: string;
        quantity_requested?: number;
        unit?: string;
        urgency?: string;
        source_notes?: string;
      }
    ) =>
      execute('/v1/shopping-list/update-item', {
        shopping_list_item_id: itemId,
        ...changes,
      }),
    [execute]
  );

  /**
   * remove_item — remove an item from the list.
   * Crew can remove their own items; HOD+ can remove any.
   */
  const removeItem = useCallback(
    (itemId: string) =>
      execute('/v1/shopping-list/remove-item', {
        shopping_list_item_id: itemId,
      }),
    [execute]
  );

  /**
   * approve_item — HOD+ approves a single item for ordering.
   * Logs to pms_audit_log with approved_by, approved_at, quantity_approved.
   */
  const approveItem = useCallback(
    (
      itemId: string,
      params: {
        quantity_approved: number;
        approval_notes?: string;
        signature?: {
          signed_by?: string;
          signed_at?: string;
          signature_type?: string;
        };
      }
    ) =>
      execute('/v1/shopping-list/approve-item', {
        shopping_list_item_id: itemId,
        ...params,
      }),
    [execute]
  );

  /**
   * reject_item — HOD+ rejects a single item with a required reason.
   * Logs to pms_audit_log with rejected_by, rejected_at, rejection_reason.
   */
  const rejectItem = useCallback(
    (
      itemId: string,
      params: {
        rejection_reason: string;
        rejection_notes?: string;
      }
    ) =>
      execute('/v1/shopping-list/reject-item', {
        shopping_list_item_id: itemId,
        ...params,
      }),
    [execute]
  );

  /**
   * mark_ordered — marks an approved item as ordered (HOD+).
   * Updates item status from 'approved' → 'ordered'.
   * Logs to pms_audit_log.
   */
  const markOrdered = useCallback(
    (itemId: string) =>
      execute('/v1/shopping-list/mark-ordered', {
        shopping_list_item_id: itemId,
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

    // Crew actions
    createItem,
    updateItem,
    removeItem,

    // HOD+ approval workflow
    approveItem,
    rejectItem,
    markOrdered,
  };
}

// ---------------------------------------------------------------------------
// Role permission helpers
// ---------------------------------------------------------------------------

/** All authenticated crew (can request items) */
const CREW_ROLES = [
  'crew',
  'engineer',
  'eto',
  'chief_engineer',
  'chief_officer',
  'captain',
  'manager',
];

/** HOD-level and above (can approve/reject per item) */
const HOD_ROLES = [
  'chief_engineer',
  'eto',
  'chief_officer',
  'captain',
  'manager',
];

/** Roles that can mark approved items as ordered */
const ORDER_ROLES = [
  'chief_engineer',
  'chief_officer',
  'captain',
  'manager',
];

export interface ShoppingListPermissions {
  /** Can add new items (all crew) */
  canCreateItem: boolean;
  /** Can edit items (all crew for own; HOD+ for any) */
  canUpdateItem: boolean;
  /** Can remove items (all crew for own; HOD+ for any) */
  canRemoveItem: boolean;
  /** Can approve individual items (HOD+) */
  canApproveItem: boolean;
  /** Can reject individual items (HOD+) */
  canRejectItem: boolean;
  /** Can mark approved items as ordered (HOD+) */
  canMarkOrdered: boolean;
}

/**
 * useShoppingListPermissions
 *
 * Derives a set of boolean capability flags from the current user's role.
 * These are used to conditionally show (not disable) action buttons in ShoppingListLens.
 */
export function useShoppingListPermissions(): ShoppingListPermissions {
  const { user } = useAuth();
  const role = user?.role ?? '';

  return {
    canCreateItem: CREW_ROLES.includes(role),
    canUpdateItem: CREW_ROLES.includes(role),
    canRemoveItem: CREW_ROLES.includes(role),
    canApproveItem: HOD_ROLES.includes(role),
    canRejectItem: HOD_ROLES.includes(role),
    canMarkOrdered: ORDER_ROLES.includes(role),
  };
}
