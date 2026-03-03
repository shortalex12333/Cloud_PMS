'use client';

/**
 * useWarrantyActions - Action hook for Warranty lens.
 *
 * Wires warranty action registry calls to typed helper methods.
 * Uses executeAction from @/lib/actionClient for all mutations.
 *
 * Action IDs (registry.py):
 *   submit_warranty_claim (not file_warranty_claim - fixed 2026-03-02)
 *   approve_warranty_claim
 *   reject_warranty_claim
 *
 * Role-based access is enforced at the API level; visibility gates live in
 * WarrantyLens (hide, not disable).
 */

import { useState, useCallback } from 'react';
import { executeAction } from '@/lib/actionClient';
import type { ActionResult } from '@/types/actions';
import { useAuth } from '@/hooks/useAuth';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface WarrantyActionsState {
  isLoading: boolean;
  error: string | null;
}

export interface WarrantyPermissions {
  /** Can file a warranty claim (HOD+) */
  canFileClaim: boolean;
  /** Can approve warranty claims (HOD+) */
  canApproveClaim: boolean;
  /** Can reject a warranty claim (HOD+) */
  canRejectClaim: boolean;
  /** Can compose warranty email (HOD+) */
  canComposeEmail: boolean;
}

export interface ComposeEmailOptions {
  /** Email template type: initial claim, follow-up, or escalation */
  template_type?: 'initial_claim' | 'follow_up' | 'escalation';
  /** Override default recipient email */
  recipient_override?: string;
}

export interface WarrantyClaimPayload {
  /** Description of the issue */
  issue_description: string;
  /** Date the issue was discovered (ISO string) */
  issue_date: string;
  /** Related equipment ID if applicable */
  equipment_id?: string;
  /** Related part ID if applicable */
  part_id?: string;
  /** Work order ID that identified the warranty issue */
  work_order_id?: string;
  /** Attached evidence/photo URLs */
  evidence_urls?: string[];
  /** Supplier/vendor contact info */
  vendor_contact?: string;
  /** Original purchase/invoice reference */
  purchase_reference?: string;
  /** Claim priority: low, medium, high, urgent */
  priority?: 'low' | 'medium' | 'high' | 'urgent';
  /** Additional notes */
  notes?: string;
}

// ---------------------------------------------------------------------------
// Role Configuration - DELEGATED TO CENTRALIZED SERVICE
// ---------------------------------------------------------------------------

// Note: Warranty lens in lens_matrix.json defines role_restricted arrays.
// Permissions are now derived from the centralized service.

// ---------------------------------------------------------------------------
// useWarrantyActions Hook
// ---------------------------------------------------------------------------

/**
 * useWarrantyActions
 *
 * Returns typed action helpers for warranty operations.
 * Each helper calls executeAction with action name and context.
 *
 * @param warrantyId - UUID of the warranty record in scope
 */
export function useWarrantyActions(warrantyId: string) {
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
            warranty_id: warrantyId,
          },
          {
            warranty_id: warrantyId,
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
    [user, warrantyId]
  );

  // -------------------------------------------------------------------------
  // Typed action helpers
  // -------------------------------------------------------------------------

  /**
   * submit_warranty_claim - Submit a warranty claim for this warranty record
   *
   * Note: Backend action is 'submit_warranty_claim', not 'file_warranty_claim'.
   * Requires HOD+ role (chief_engineer, chief_officer, captain).
   *
   * @param claim - The warranty claim details
   */
  const fileClaim = useCallback(
    (claim: WarrantyClaimPayload): Promise<ActionResult> =>
      execute('submit_warranty_claim', {
        issue_description: claim.issue_description,
        issue_date: claim.issue_date,
        equipment_id: claim.equipment_id,
        part_id: claim.part_id,
        work_order_id: claim.work_order_id,
        evidence_urls: claim.evidence_urls,
        vendor_contact: claim.vendor_contact,
        purchase_reference: claim.purchase_reference,
        priority: claim.priority || 'medium',
        notes: claim.notes,
        filed_at: new Date().toISOString(),
      }),
    [execute]
  );

  /**
   * approve_warranty_claim - Approve a warranty claim (HOD+)
   *
   * @param approvedAmount - The approved claim amount
   * @param approvalNotes - Notes from approver
   * @param vendorAction - Action to take with vendor: 'credit' | 'replacement' | 'repair'
   */
  const approveClaim = useCallback(
    (
      approvedAmount: number,
      approvalNotes?: string,
      vendorAction?: 'credit' | 'replacement' | 'repair'
    ): Promise<ActionResult> =>
      execute('approve_warranty_claim', {
        approved_amount: approvedAmount,
        approval_notes: approvalNotes,
        vendor_action: vendorAction || 'credit',
        approved_at: new Date().toISOString(),
      }),
    [execute]
  );

  /**
   * reject_warranty_claim - Reject a warranty claim (HOD+)
   *
   * @param reason - Required reason for rejection
   * @param notes - Additional notes
   */
  const rejectClaim = useCallback(
    (reason: string, notes?: string): Promise<ActionResult> =>
      execute('reject_warranty_claim', {
        rejection_reason: reason,
        rejection_notes: notes,
        rejected_at: new Date().toISOString(),
      }),
    [execute]
  );

  /**
   * compose_warranty_email - Compose a pre-filled warranty email (HOD+)
   *
   * @param options - Email composition options (template type, recipient override)
   */
  const composeEmail = useCallback(
    (options?: ComposeEmailOptions): Promise<ActionResult> =>
      execute('compose_warranty_email', {
        template_type: options?.template_type || 'initial_claim',
        recipient_override: options?.recipient_override,
        composed_at: new Date().toISOString(),
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
    fileClaim,
    approveClaim,
    rejectClaim,
    composeEmail,
  };
}

// ---------------------------------------------------------------------------
// useWarrantyPermissions Hook - DELEGATED TO CENTRALIZED SERVICE
// ---------------------------------------------------------------------------

import { useWarrantyPermissions as useCentralizedWarrantyPermissions } from '@/hooks/permissions/useWarrantyPermissions';

/**
 * useWarrantyPermissions
 *
 * Derives boolean capability flags from the current user's role.
 * DELEGATED TO CENTRALIZED SERVICE - reads from lens_matrix.json
 * Used to conditionally show (not disable) action buttons.
 */
export function useWarrantyPermissions(): WarrantyPermissions {
  const central = useCentralizedWarrantyPermissions();

  return {
    canFileClaim: central.canSubmitWarrantyClaim,
    canApproveClaim: central.canApproveWarrantyClaim,
    canRejectClaim: central.canRejectWarrantyClaim,
    canComposeEmail: central.canComposeWarrantyEmail,
  };
}
