'use client';

/**
 * useHandoverActions — Handover action hook (FE-03-02)
 *
 * Wires all handover action registry calls to typed helper methods.
 * Uses the unified action API endpoint per the action router spec.
 *
 * Action IDs map 1:1 to registry.py keys:
 *   add_handover_item, edit_handover_item, validate_handover,
 *   finalize_handover, sign_outgoing, sign_incoming, export_handover
 *
 * Role-based access is enforced at the API level; visibility gates live in
 * HandoverLens (hide, not disable — per UI_SPEC.md).
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

export interface HandoverActionsState {
  isLoading: boolean;
  error: string | null;
}

// API URL — same origin Next.js API route proxied to Render backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * useHandoverActions
 *
 * Returns typed action helpers for all handover operations.
 * Each helper calls POST /v1/handover/{endpoint} with JWT auth.
 *
 * @param handoverId - UUID of the handover in scope
 */
export function useHandoverActions(handoverId: string) {
  const { user, session } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // Internal executor — wraps every action call
  // Injects yacht_id + handover_id automatically (no repetition at call site)
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
            handover_id: handoverId,
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
    [session, user, handoverId]
  );

  // -------------------------------------------------------------------------
  // Typed action helpers — one per registry action
  // -------------------------------------------------------------------------

  /**
   * add_handover_item — crew+ adds an item to the handover (draft state only)
   */
  const addHandoverItem = useCallback(
    (params: {
      entity_id: string;
      entity_type: string;
      summary?: string;
      category?: string;
      is_critical?: boolean;
      requires_action?: boolean;
      action_summary?: string;
      section?: string;
    }) => execute('/v1/handover/add-item', params),
    [execute]
  );

  /**
   * edit_handover_item — crew+ edits a handover item (draft state only)
   */
  const editHandoverItem = useCallback(
    (params: {
      item_id: string;
      content?: string;
      category?: string;
      is_critical?: boolean;
      requires_action?: boolean;
      action_summary?: string;
    }) => execute('/v1/handover/edit-item', params),
    [execute]
  );

  /**
   * validate_handover — HOD+ validates the handover before finalization
   */
  const validateHandover = useCallback(
    () => execute('/v1/handover/validate', {}),
    [execute]
  );

  /**
   * finalize_handover — HOD+ finalizes and locks the handover for signatures
   *
   * After finalization:
   * - No more item edits
   * - Status changes to pending_signatures
   * - Outgoing crew can then sign
   */
  const finalizeHandover = useCallback(
    () =>
      execute('/v1/handover/finalize', {
        signature: {
          signed_by: user?.id,
          signed_at: new Date().toISOString(),
          signature_type: 'finalize',
        },
      }),
    [execute, user]
  );

  /**
   * sign_outgoing — outgoing crew member signs the handover
   *
   * Called when status = pending_signatures and outgoing has not yet signed.
   * This is the first signature in the dual-signature flow.
   */
  const signOutgoing = useCallback(
    () =>
      execute('/v1/handover/sign-outgoing', {
        signature: {
          signed_by: user?.id,
          signed_at: new Date().toISOString(),
          signature_type: 'outgoing',
        },
      }),
    [execute, user]
  );

  /**
   * sign_incoming — incoming crew member signs the handover
   *
   * Called when status = pending_signatures and outgoing has already signed.
   * Both signatures being present transitions status to complete.
   */
  const signIncoming = useCallback(
    () =>
      execute('/v1/handover/sign-incoming', {
        signature: {
          signed_by: user?.id,
          signed_at: new Date().toISOString(),
          signature_type: 'incoming',
        },
      }),
    [execute, user]
  );

  /**
   * export_handover — captain+ exports the complete handover to PDF
   *
   * Only available when status = complete (both signatures collected).
   */
  const exportHandover = useCallback(
    (format: 'pdf' | 'docx' = 'pdf', department?: string) =>
      execute('/v1/handover/export', { format, department }),
    [execute]
  );

  /**
   * acknowledge_item — any crew member acknowledges a handover item
   */
  const acknowledgeItem = useCallback(
    (itemId: string) =>
      execute('/v1/handover/acknowledge-item', { item_id: itemId }),
    [execute]
  );

  // -------------------------------------------------------------------------
  // Return
  // -------------------------------------------------------------------------

  return {
    // State
    isLoading,
    error,

    // Item management (draft only)
    addHandoverItem,
    editHandoverItem,

    // Workflow transitions
    validateHandover,
    finalizeHandover,

    // Dual signature flow
    signOutgoing,
    signIncoming,

    // Export
    exportHandover,

    // Acknowledgement
    acknowledgeItem,
  };
}

// ---------------------------------------------------------------------------
// Role permission helpers
// ---------------------------------------------------------------------------

/** Roles with HOD-level or above access */
const HOD_ROLES = ['chief_engineer', 'eto', 'chief_officer', 'captain', 'manager'];

/** Roles who can finalize handovers (HOD+) */
const FINALIZE_ROLES = ['chief_engineer', 'chief_officer', 'captain', 'manager'];

/** Roles who can export handovers (captain/manager) */
const EXPORT_ROLES = ['captain', 'manager'];

/** All crew can add items and sign */
const CREW_ROLES = ['crew', 'chief_engineer', 'eto', 'chief_officer', 'captain', 'manager'];

export interface HandoverPermissions {
  /** Can add items to the handover (crew+, draft state) */
  canAddItem: boolean;
  /** Can edit handover items (crew+, draft state) */
  canEditItem: boolean;
  /** Can finalize the handover (HOD+) */
  canFinalize: boolean;
  /** Can sign as outgoing crew (determined by outgoing_crew_id match or role) */
  canSignOutgoing: boolean;
  /** Can sign as incoming crew (determined by incoming_crew_id match or role) */
  canSignIncoming: boolean;
  /** Can export to PDF (captain+, after complete) */
  canExport: boolean;
  /** Can acknowledge handover items (crew+) */
  canAcknowledge: boolean;
}

/**
 * useHandoverPermissions
 *
 * Derives boolean capability flags from the current user's role.
 * Used to conditionally show (not disable) action buttons in HandoverLens.
 *
 * Note: For outgoing/incoming signing, role alone is not sufficient —
 * the lens also checks if the user matches the outgoing/incoming crew ID.
 * This hook grants the base capability; HandoverLens applies the additional
 * crew-ID check in the canSignOutgoing/canSignIncoming derivation.
 */
export function useHandoverPermissions(): HandoverPermissions {
  const { user } = useAuth();
  const role = user?.role ?? '';

  return {
    canAddItem: CREW_ROLES.includes(role),
    canEditItem: CREW_ROLES.includes(role),
    canFinalize: FINALIZE_ROLES.includes(role),
    // Any crew member can be outgoing or incoming — actual gate is crew_id match
    // and status check, applied in HandoverLens
    canSignOutgoing: CREW_ROLES.includes(role),
    canSignIncoming: CREW_ROLES.includes(role),
    canExport: EXPORT_ROLES.includes(role) || HOD_ROLES.includes(role),
    canAcknowledge: CREW_ROLES.includes(role),
  };
}
