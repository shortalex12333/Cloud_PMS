'use client';

/**
 * useHandoverActions - Action hook for Handover lens.
 *
 * Wires handover action registry calls to typed helper methods.
 * Uses executeAction from @/lib/actionClient for all mutations.
 *
 * Action IDs:
 *   acknowledge_handover
 *   sign_handover_outgoing
 *
 * Role-based access is enforced at the API level; visibility gates live in
 * HandoverLens (hide, not disable).
 */

import { useState, useCallback } from 'react';
import { executeAction } from '@/lib/actionClient';
import type { ActionResult } from '@/types/actions';
import { useAuth } from '@/hooks/useAuth';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface HandoverActionsState {
  isLoading: boolean;
  error: string | null;
}

export interface HandoverPermissions {
  /** Can acknowledge handover (incoming officer) */
  canAcknowledge: boolean;
  /** Can sign handover as incoming officer */
  canSignIncoming: boolean;
  /** Can sign handover as outgoing officer */
  canSignOutgoing: boolean;
  /** Can export handover document (officers involved) */
  canExport: boolean;
}

// ---------------------------------------------------------------------------
// Role Configuration - DELEGATED TO CENTRALIZED SERVICE
// ---------------------------------------------------------------------------

// Note: Handover lens in lens_matrix.json has role_restricted: [] for all actions,
// meaning all roles have access. The permissions below use the centralized service.

// ---------------------------------------------------------------------------
// useHandoverActions Hook
// ---------------------------------------------------------------------------

/**
 * useHandoverActions
 *
 * Returns typed action helpers for handover operations.
 * Each helper calls executeAction with action name and context.
 *
 * @param handoverId - UUID of the handover in scope
 */
export function useHandoverActions(handoverId: string) {
  const { user } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // Internal executor wrapper
  // -------------------------------------------------------------------------

  const execute = useCallback(
    async (actionName: string, payload: Record<string, unknown>): Promise<ActionResult> => {
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
            handover_id: handoverId,
          },
          {
            handover_id: handoverId,
            ...payload,
          }
        );

        return {
          success: result.status === 'success',
          data: result.result,
          error: result.message,
        };
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Unknown error';
        setError(msg);
        return { success: false, error: msg };
      } finally {
        setIsLoading(false);
      }
    },
    [user, handoverId]
  );

  // -------------------------------------------------------------------------
  // Typed action helpers
  // -------------------------------------------------------------------------

  /**
   * acknowledge_handover - Acknowledge receipt of handover by incoming officer
   *
   * @param notes - Optional acknowledgment notes
   * @param signature - Optional digital signature data
   */
  const acknowledgeHandover = useCallback(
    (notes?: string, signature?: Record<string, unknown>): Promise<ActionResult> =>
      execute('acknowledge_handover', {
        acknowledgment_notes: notes,
        signature,
        acknowledged_at: new Date().toISOString(),
      }),
    [execute]
  );

  /**
   * sign_handover_incoming - Sign handover as incoming officer
   * Requires signature modal with PIN+TOTP and critical item acknowledgment
   *
   * @param signature - Digital signature data including PIN hash and TOTP
   * @param criticalItemsAcknowledged - Array of critical item IDs acknowledged
   * @param notes - Optional acknowledgment notes
   */
  const signIncoming = useCallback(
    (
      signature: { pin_hash: string; totp_code: string; signature_image?: string },
      criticalItemsAcknowledged: string[],
      notes?: string
    ): Promise<ActionResult> =>
      execute('sign_handover_incoming', {
        signature,
        critical_items_acknowledged: criticalItemsAcknowledged,
        notes,
        signed_at: new Date().toISOString(),
      }),
    [execute]
  );

  /**
   * sign_handover_outgoing - Sign handover as outgoing officer
   * Requires signature modal with PIN+TOTP verification
   *
   * @param signature - Digital signature data including PIN hash and TOTP
   * @param notes - Optional handover notes
   */
  const signOutgoing = useCallback(
    (signature: { pin_hash: string; totp_code: string; signature_image?: string }, notes?: string): Promise<ActionResult> =>
      execute('sign_handover_outgoing', {
        signature,
        notes,
        signed_at: new Date().toISOString(),
      }),
    [execute]
  );

  /**
   * export_handover - Generate PDF export of handover document
   * Returns download URL for the generated PDF
   *
   * @param format - Export format: 'pdf' | 'html'
   * @param includeSignatures - Whether to include signature images
   */
  const exportHandover = useCallback(
    (format: 'pdf' | 'html' = 'pdf', includeSignatures: boolean = true): Promise<ActionResult> =>
      execute('export_handover', {
        format,
        include_signatures: includeSignatures,
        exported_at: new Date().toISOString(),
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
    acknowledgeHandover,
    signIncoming,
    signOutgoing,
    exportHandover,
  };
}

// ---------------------------------------------------------------------------
// useHandoverPermissions Hook - DELEGATED TO CENTRALIZED SERVICE
// ---------------------------------------------------------------------------

import { useHandoverPermissions as useCentralizedHandoverPermissions } from '@/hooks/permissions/useHandoverPermissions';

/**
 * useHandoverPermissions
 *
 * Derives boolean capability flags from the current user's role.
 * DELEGATED TO CENTRALIZED SERVICE - reads from lens_matrix.json
 *
 * Note: All handover actions in lens_matrix.json have role_restricted: [],
 * meaning all roles can perform these actions.
 */
export function useHandoverPermissions(): HandoverPermissions {
  const central = useCentralizedHandoverPermissions();

  return {
    // All handover actions are available to all roles per lens_matrix.json
    canAcknowledge: central.canEditHandoverItem, // Uses same "all roles" permission
    canSignIncoming: central.canEditHandoverItem,
    canSignOutgoing: central.canEditHandoverItem,
    canExport: central.canExportHandover,
  };
}
