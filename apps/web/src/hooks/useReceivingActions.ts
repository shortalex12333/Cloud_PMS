'use client';

/**
 * useReceivingActions — Receiving action hook (FE-03-01)
 *
 * Wires all receiving action registry calls to typed helper methods.
 * Uses the unified action API endpoint per the action router spec.
 *
 * Action IDs map 1:1 to registry.py keys:
 *   create_receiving, add_receiving_item, update_receiving_fields,
 *   accept_receiving, reject_receiving, view_receiving_history
 *
 * Role-based access:
 * - All crew: create_receiving
 * - Crew (draft only): add_receiving_item, update_receiving_fields
 * - HOD+ (chief_engineer, chief_officer, captain, manager): accept_receiving, reject_receiving
 *
 * Role-based visibility is enforced at the API level; gates live in
 * ReceivingLens (hide, not disable).
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

export interface ReceivingActionsState {
  isLoading: boolean;
  error: string | null;
}

// API URL — same origin Next.js API route proxied to Render backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * useReceivingActions
 *
 * Returns typed action helpers for all receiving operations.
 * Each helper calls POST /v1/receiving/{endpoint} with JWT auth.
 *
 * @param receivingId - UUID of the receiving record in scope
 */
export function useReceivingActions(receivingId: string) {
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
            receiving_id: receivingId,
            ...payload,
          }),
        });

        const json = await response.json().catch(() => ({}));

        if (!response.ok) {
          const msg = (json as { error?: string; detail?: string }).error
            || (json as { error?: string; detail?: string }).detail
            || `Request failed (${response.status})`;
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
    [session, user, receivingId]
  );

  // -------------------------------------------------------------------------
  // Typed action helpers — one per registry action
  // -------------------------------------------------------------------------

  /** create_receiving — create a new receiving record (all crew) */
  const createReceiving = useCallback(
    (supplierName: string, poNumber?: string, notes?: string) =>
      execute('/v1/receiving/create', { supplier_name: supplierName, po_number: poNumber, notes }),
    [execute]
  );

  /** add_receiving_item — add a line item to the receiving record (crew, draft only) */
  const addReceivingItem = useCallback(
    (params: {
      description: string;
      quantity_received: number;
      quantity_expected?: number;
      unit_price?: number;
      currency?: string;
      part_id?: string;
    }) => execute('/v1/receiving/add-item', params),
    [execute]
  );

  /** update_receiving_fields — update editable fields (crew, draft only) */
  const updateReceivingFields = useCallback(
    (changes: Record<string, unknown>) =>
      execute('/v1/receiving/update', changes),
    [execute]
  );

  /** accept_receiving — accept the delivery (HOD+ with signature) */
  const acceptReceiving = useCallback(
    (signature: Record<string, unknown>) =>
      execute('/v1/receiving/accept', { signature }),
    [execute]
  );

  /** reject_receiving — reject the delivery with reason (HOD+ with reason) */
  const rejectReceiving = useCallback(
    (reason: string, signature: Record<string, unknown>) =>
      execute('/v1/receiving/reject', { rejection_reason: reason, signature }),
    [execute]
  );

  /** view_receiving_history — fetch history entries (read-only) */
  const viewReceivingHistory = useCallback(
    () => execute('/v1/receiving/history', {}),
    [execute]
  );

  // -------------------------------------------------------------------------
  // Return
  // -------------------------------------------------------------------------

  return {
    // State
    isLoading,
    error,

    // CRUD
    createReceiving,
    addReceivingItem,
    updateReceivingFields,

    // Status transitions (HOD+)
    acceptReceiving,
    rejectReceiving,

    // Read-only
    viewReceivingHistory,
  };
}

// ---------------------------------------------------------------------------
// Role permission helpers
// ---------------------------------------------------------------------------

/** All roles with HOD-level or above access */
const HOD_ROLES = ['chief_engineer', 'eto', 'chief_officer', 'captain', 'manager'];

export interface ReceivingPermissions {
  /** Can create a new receiving record (all crew) */
  canCreate: boolean;
  /** Can add items to a draft receiving record (all crew) */
  canAddItem: boolean;
  /** Can update receiving fields when in draft (all crew) */
  canUpdate: boolean;
  /** Can accept a receiving record (HOD+) */
  canAccept: boolean;
  /** Can reject a receiving record with reason (HOD+) */
  canReject: boolean;
  /** Can view receiving history (all crew) */
  canViewHistory: boolean;
}

/**
 * useReceivingPermissions
 *
 * Derives a set of boolean capability flags from the current user's role.
 * These are used to conditionally show (not disable) action buttons.
 */
export function useReceivingPermissions(): ReceivingPermissions {
  const { user } = useAuth();
  const role = user?.role ?? '';

  const isHod = HOD_ROLES.includes(role);

  return {
    canCreate: true, // All authenticated crew
    canAddItem: true, // All authenticated crew (backend gates on draft status)
    canUpdate: true, // All authenticated crew (backend gates on draft status)
    canAccept: isHod,
    canReject: isHod,
    canViewHistory: true, // All authenticated crew
  };
}
