'use client';

/**
 * useWarrantyActions — Warranty Claim action hook (FE-03-04)
 *
 * Wires all warranty claim action registry calls to typed helper methods.
 * Uses the unified action API endpoint per the action router spec.
 *
 * Action IDs map 1:1 to registry.py keys:
 *   draft_claim, submit_claim, approve_claim, reject_claim,
 *   add_document, update_claim
 *
 * Role-based access is enforced at the API level; visibility gates live in
 * WarrantyLens (hide, not disable).
 *
 * Follows useWorkOrderActions pattern exactly.
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

export interface WarrantyActionsState {
  isLoading: boolean;
  error: string | null;
}

// API URL — same origin Next.js API route proxied to Render backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * useWarrantyActions
 *
 * Returns typed action helpers for all warranty claim operations.
 * Each helper calls POST /v1/warranty/{endpoint} with JWT auth.
 *
 * @param claimId - UUID of the warranty claim in scope
 */
export function useWarrantyActions(claimId: string) {
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
            claim_id: claimId,
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
    [session, user, claimId]
  );

  // -------------------------------------------------------------------------
  // Typed action helpers — one per registry action
  // -------------------------------------------------------------------------

  /** draft_claim — create or save a draft warranty claim */
  const draftClaim = useCallback(
    (changes: Record<string, unknown>) =>
      execute('/v1/warranty/draft', changes),
    [execute]
  );

  /** submit_claim — submit draft for HOD approval (transitions draft → submitted) */
  const submitClaim = useCallback(
    () => execute('/v1/warranty/submit', {}),
    [execute]
  );

  /** approve_claim — HOD+ approves a submitted claim (transitions submitted → approved) */
  const approveClaim = useCallback(
    (approvedAmount?: number, notes?: string) =>
      execute('/v1/warranty/approve', {
        approved_amount: approvedAmount,
        notes,
      }),
    [execute]
  );

  /** reject_claim — HOD+ rejects a submitted claim with reason (transitions submitted → rejected) */
  const rejectClaim = useCallback(
    (reason: string) =>
      execute('/v1/warranty/reject', { rejection_reason: reason }),
    [execute]
  );

  /** add_document — attach a document to the claim */
  const addDocument = useCallback(
    (documentUrl: string, documentName: string, documentType: string) =>
      execute('/v1/warranty/add-document', {
        document_url: documentUrl,
        document_name: documentName,
        document_type: documentType,
      }),
    [execute]
  );

  /** update_claim — update editable claim fields */
  const updateClaim = useCallback(
    (changes: Record<string, unknown>) =>
      execute('/v1/warranty/update', changes),
    [execute]
  );

  // -------------------------------------------------------------------------
  // Return
  // -------------------------------------------------------------------------

  return {
    // State
    isLoading,
    error,

    // Workflow transitions
    draftClaim,
    submitClaim,
    approveClaim,
    rejectClaim,

    // Documents
    addDocument,

    // Updates
    updateClaim,
  };
}

// ---------------------------------------------------------------------------
// Role permission helpers
// ---------------------------------------------------------------------------

/** All roles with HOD-level or above access */
const HOD_ROLES = ['chief_engineer', 'eto', 'chief_officer', 'captain', 'manager'];

/** Roles that can approve or reject claims */
const APPROVE_ROLES = ['chief_engineer', 'chief_officer', 'captain', 'manager'];

/** All crew roles (including junior crew) */
const CREW_ROLES = [
  'captain',
  'chief_officer',
  'chief_engineer',
  'eto',
  'manager',
  'bosun',
  'engineer',
  'steward',
  'deckhand',
  'crew',
  'member',
];

export interface WarrantyPermissions {
  /** Can submit a draft claim for approval (any crew) */
  canSubmit: boolean;
  /** Can approve or reject submitted claims (HOD+) */
  canApprove: boolean;
  /** Can update claim details (HOD+) */
  canUpdate: boolean;
  /** Can add documents (any crew) */
  canAddDocument: boolean;
}

/**
 * useWarrantyPermissions
 *
 * Derives boolean capability flags from the current user's role.
 * Used to conditionally show (not disable) action buttons per UI_SPEC.md.
 */
export function useWarrantyPermissions(): WarrantyPermissions {
  const { user } = useAuth();
  const role = user?.role ?? '';

  return {
    canSubmit: CREW_ROLES.includes(role),
    canApprove: APPROVE_ROLES.includes(role),
    canUpdate: HOD_ROLES.includes(role),
    canAddDocument: CREW_ROLES.includes(role),
  };
}
