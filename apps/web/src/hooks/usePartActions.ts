'use client';

/**
 * usePartActions — Parts/Inventory action hook (FE-02-03)
 *
 * Wires all parts action registry calls to typed helper methods.
 * Uses the unified action API endpoint per the action router spec.
 *
 * Action IDs map 1:1 to registry.py keys:
 *   view_part, consume_part, receive_part, transfer_part,
 *   adjust_stock, write_off, add_to_shopping_list
 *
 * Role-based access is enforced at the API level; visibility gates live in
 * PartsLens (hide, not disable — per UI_SPEC.md pattern).
 *
 * Role matrix:
 * - view_part:            all authenticated users
 * - consume_part:         crew, HOD, captain (everyone with vessel access)
 * - receive_part:         HOD+ (chief_engineer, chief_officer, captain, manager)
 * - transfer_part:        HOD+
 * - adjust_stock:         HOD+
 * - write_off:            HOD+
 * - add_to_shopping_list: crew, HOD, captain
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

export interface PartActionsState {
  isLoading: boolean;
  error: string | null;
}

// API URL — same origin Next.js API route proxied to Render backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * usePartActions
 *
 * Returns typed action helpers for all parts/inventory operations.
 * Each helper calls POST /v1/actions/execute with action name and JWT auth.
 *
 * @param partId - UUID of the part in scope
 */
export function usePartActions(partId: string) {
  const { user, session } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // Internal executor — wraps every action call
  // -------------------------------------------------------------------------

  const execute = useCallback(
    async (actionName: string, payload: Record<string, unknown>): Promise<ActionResult> => {
      if (!session?.access_token) {
        return { success: false, error: 'Not authenticated' };
      }

      setIsLoading(true);
      setError(null);

      try {
        // Use unified action router endpoint - /v1/actions/execute
        const response = await fetch(`${API_BASE}/v1/actions/execute`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${session.access_token}`,
          },
          body: JSON.stringify({
            action: actionName,
            context: {
              yacht_id: user?.yachtId,
              part_id: partId,
            },
            payload,
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
    [session, user, partId]
  );

  // -------------------------------------------------------------------------
  // Typed action helpers — one per registry action
  // -------------------------------------------------------------------------

  /** view_part — fetch part details (read-only) */
  const viewPart = useCallback(
    () => execute('view_part', {}),
    [execute]
  );

  /** consume_part — record stock consumption (crew can do this) */
  const consumePart = useCallback(
    (quantity: number, notes?: string) =>
      execute('consume_part', { quantity, notes }),
    [execute]
  );

  /** receive_part — add incoming stock (HOD+) */
  const receivePart = useCallback(
    (quantity: number, notes?: string) =>
      execute('receive_part', { quantity, notes }),
    [execute]
  );

  /** transfer_part — move stock between locations (HOD+) */
  const transferPart = useCallback(
    (quantity: number, targetLocation: string, notes?: string) =>
      execute('transfer_part', { quantity, target_location: targetLocation, notes }),
    [execute]
  );

  /** adjust_stock — manual correction of stock level (HOD+) */
  const adjustStock = useCallback(
    (newQuantity: number, reason: string) =>
      execute('adjust_stock', { new_quantity: newQuantity, reason }),
    [execute]
  );

  /** write_off — write off damaged/expired stock (HOD+) */
  const writeOff = useCallback(
    (quantity: number, reason: string) =>
      execute('write_off_part', { quantity, reason }),
    [execute]
  );

  /** add_to_shopping_list — add this part to the procurement shopping list */
  const addToShoppingList = useCallback(
    (quantity?: number, notes?: string) =>
      execute('add_part_to_shopping_list', { quantity, notes }),
    [execute]
  );

  // -------------------------------------------------------------------------
  // Return
  // -------------------------------------------------------------------------

  return {
    // State
    isLoading,
    error,

    // Read-only
    viewPart,

    // Stock movements
    consumePart,
    receivePart,
    transferPart,

    // Privileged adjustments
    adjustStock,
    writeOff,

    // Procurement
    addToShoppingList,
  };
}

// ---------------------------------------------------------------------------
// Role permission helpers
// ---------------------------------------------------------------------------

/** All roles with HOD-level or above access */
const HOD_ROLES = ['chief_engineer', 'eto', 'chief_officer', 'captain', 'manager'];

/** Roles allowed to consume parts (everyone with vessel access) */
const CONSUME_ROLES = ['crew', 'chief_engineer', 'eto', 'chief_officer', 'captain', 'manager'];

/** Roles allowed to add to shopping list */
const SHOPPING_LIST_ROLES = ['crew', 'chief_engineer', 'eto', 'chief_officer', 'captain', 'manager'];

export interface PartPermissions {
  /** Can view part details (all authenticated users) */
  canView: boolean;
  /** Can consume stock (crew can do this — everyone with vessel access) */
  canConsume: boolean;
  /** Can receive stock (HOD+) */
  canReceive: boolean;
  /** Can transfer stock between locations (HOD+) */
  canTransfer: boolean;
  /** Can manually adjust stock level (HOD+) */
  canAdjustStock: boolean;
  /** Can write off stock (HOD+) */
  canWriteOff: boolean;
  /** Can add to shopping list (crew and above) */
  canAddToShoppingList: boolean;
}

/**
 * usePartPermissions
 *
 * Derives a set of boolean capability flags from the current user's role.
 * These are used to conditionally show (not disable) action buttons.
 * Per UI_SPEC.md: hide, not disable for role gates.
 */
export function usePartPermissions(): PartPermissions {
  const { user } = useAuth();
  const role = user?.role ?? '';

  return {
    canView: true, // All authenticated users can view parts
    canConsume: CONSUME_ROLES.includes(role),
    canReceive: HOD_ROLES.includes(role),
    canTransfer: HOD_ROLES.includes(role),
    canAdjustStock: HOD_ROLES.includes(role),
    canWriteOff: HOD_ROLES.includes(role),
    canAddToShoppingList: SHOPPING_LIST_ROLES.includes(role),
  };
}
