'use client';

/**
 * useCertificateActions — Certificate action hook (FE-01-03)
 *
 * Wires all certificate action registry calls to typed helper methods.
 * Uses the unified action API endpoint per the action router spec.
 *
 * Supports both vessel and crew certificates via certType parameter.
 *
 * Action IDs map 1:1 to registry.py keys:
 *   update_certificate (renew), link_document_to_certificate, supersede_certificate
 *
 * Role-based access is enforced at the API level; visibility gates live in
 * CertificatesLens (hide, not disable).
 */

import { useState, useCallback } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { executeAction, ActionResult } from '@/lib/actionClient';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type CertificateType = 'vessel' | 'crew';

export interface CertificateActionResult {
  success: boolean;
  message?: string;
  data?: Record<string, unknown>;
  error?: string;
}

export interface CertificateActionsState {
  isLoading: boolean;
  error: string | null;
}

export interface RenewalPayload {
  /** New expiry date (ISO 8601 format) */
  new_expiry_date: string;
  /** New issue date (ISO 8601 format) */
  issue_date?: string;
  /** Issuing authority */
  issuing_authority?: string;
  /** Certificate number */
  certificate_number?: string;
  /** Notes about the renewal */
  notes?: string;
}

/** Certificate status for state validation */
export type CertificateStatus = 'draft' | 'active' | 'expired' | 'superseded' | 'revoked';

/** Options for certificate state validation */
export interface CertificateStateOptions {
  /** Current certificate status */
  currentStatus?: CertificateStatus;
  /** Current expiry date (ISO 8601 format) */
  currentExpiryDate?: string;
}

export interface LinkDocumentPayload {
  /** UUID of the document to link */
  document_id: string;
  /** Relationship type (e.g., 'supporting', 'scan', 'attachment') */
  relationship_type?: string;
}

export interface CreateVesselCertificatePayload {
  /** Type of certificate (e.g., 'imo', 'class', 'flag') */
  certificate_type: string;
  /** Authority that issued the certificate */
  issuing_authority: string;
  /** Issue date (ISO 8601 format) */
  issue_date: string;
  /** Expiry date (ISO 8601 format) */
  expiry_date: string;
  /** Certificate number */
  certificate_number: string;
  /** Optional UUID of linked document */
  document_id?: string;
}

export interface SupersedeCertificatePayload {
  /** UUID of the new certificate that supersedes this one */
  new_certificate_id: string;
  /** Optional reason for superseding */
  reason?: string;
  /** Signature required: PIN hash (base64 encoded) and TOTP code */
  signature: {
    pin_hash: string;
    totp_code: string;
  };
}

export interface CreateCrewCertificatePayload {
  /** Crew member ID */
  crew_member_id: string;
  /** Certificate type (e.g., 'STCW', 'training', 'medical') */
  certificate_type: string;
  /** Issuing authority */
  issuing_authority: string;
  /** Issue date (ISO 8601 format) */
  issue_date: string;
  /** Expiry date (ISO 8601 format) */
  expiry_date: string;
  /** Certificate number */
  certificate_number: string;
  /** Optional document ID to link upon creation */
  document_id?: string;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * useCertificateActions
 *
 * Returns typed action helpers for all certificate operations.
 * Each helper calls POST /v1/actions/execute with action name and JWT auth.
 *
 * @param certId - UUID of the certificate in scope
 * @param certType - Type of certificate: 'vessel' or 'crew'
 * @param stateOptions - Optional certificate state for validation (status, expiry date)
 */
export function useCertificateActions(
  certId: string,
  certType: CertificateType,
  stateOptions?: CertificateStateOptions
) {
  const { user, session } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // State validation helpers (MEDIUM-1 fix: prevent updates to expired certs)
  // -------------------------------------------------------------------------

  /**
   * Check if certificate is expired based on expiry date
   */
  const isExpired = useCallback((expiryDate?: string): boolean => {
    if (!expiryDate) return false;
    try {
      const expiry = new Date(expiryDate);
      return expiry < new Date();
    } catch {
      return false;
    }
  }, []);

  /**
   * Check if a date is in the future
   */
  const isFutureDate = useCallback((dateStr: string): boolean => {
    try {
      const date = new Date(dateStr);
      return date > new Date();
    } catch {
      return false;
    }
  }, []);

  /**
   * Validate state transition for certificate updates
   * Returns error message if invalid, null if valid
   */
  const validateStateForUpdate = useCallback(
    (newExpiryDate?: string): string | null => {
      const currentStatus = stateOptions?.currentStatus;
      const currentExpiryDate = stateOptions?.currentExpiryDate;

      // Terminal states cannot be updated
      if (currentStatus === 'superseded') {
        return 'Cannot update a superseded certificate';
      }
      if (currentStatus === 'revoked') {
        return 'Cannot update a revoked certificate';
      }

      // Expired certificates require a new future expiry date (renewal)
      const certIsExpired = currentStatus === 'expired' || isExpired(currentExpiryDate);
      if (certIsExpired) {
        if (!newExpiryDate) {
          return 'Expired certificate requires a new expiry date for renewal';
        }
        if (!isFutureDate(newExpiryDate)) {
          return 'New expiry date must be in the future to renew an expired certificate';
        }
      }

      return null;
    },
    [stateOptions, isExpired, isFutureDate]
  );

  // -------------------------------------------------------------------------
  // Internal executor — wraps every action call
  // -------------------------------------------------------------------------

  const execute = useCallback(
    async (actionName: string, payload: Record<string, unknown>): Promise<CertificateActionResult> => {
      if (!session?.access_token) {
        return { success: false, error: 'Not authenticated' };
      }

      if (!user?.yachtId) {
        return { success: false, error: 'No yacht context available' };
      }

      setIsLoading(true);
      setError(null);

      // Build context with certificate type for proper table routing
      const contextKey = certType === 'vessel' ? 'vessel_certificate_id' : 'crew_certificate_id';

      try {
        const result = await executeAction(
          actionName,
          {
            yacht_id: user.yachtId,
            certificate_type: certType,
            [contextKey]: certId,
          },
          {
            certificate_id: certId,
            certificate_type: certType,
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
    [session, user, certId, certType]
  );

  // -------------------------------------------------------------------------
  // Typed action helpers — one per registry action
  // -------------------------------------------------------------------------

  /**
   * update_certificate — Renew/update a certificate
   *
   * Updates certificate details including expiry date, issue date, and authority.
   * Used for both initial setup and renewal workflows.
   *
   * Includes state validation (MEDIUM-1 fix):
   * - Cannot update superseded/revoked certificates
   * - Expired certificates require a future expiry date (renewal action)
   *
   * @param renewal - Renewal payload with new dates and optional metadata
   */
  const renewCertificate = useCallback(
    (renewal: RenewalPayload): Promise<CertificateActionResult> => {
      // Client-side state validation before API call
      const validationError = validateStateForUpdate(renewal.new_expiry_date);
      if (validationError) {
        setError(validationError);
        return Promise.resolve({ success: false, error: validationError });
      }

      return execute('update_certificate', {
        new_expiry_date: renewal.new_expiry_date,
        expiry_date: renewal.new_expiry_date, // Backend expects expiry_date
        ...(renewal.issue_date && { issue_date: renewal.issue_date }),
        ...(renewal.issuing_authority && { issuing_authority: renewal.issuing_authority }),
        ...(renewal.certificate_number && { certificate_number: renewal.certificate_number }),
        ...(renewal.notes && { notes: renewal.notes }),
      });
    },
    [execute, validateStateForUpdate]
  );

  /**
   * link_document_to_certificate — Link a document to this certificate
   *
   * Associates an existing document (scan, supporting doc) with the certificate.
   *
   * @param documentId - UUID of the document to link
   * @param relationshipType - Optional relationship type (defaults to 'supporting')
   */
  const linkDocument = useCallback(
    (documentId: string, relationshipType?: string) =>
      execute('link_document_to_certificate', {
        document_id: documentId,
        ...(relationshipType && { relationship_type: relationshipType }),
      }),
    [execute]
  );

  /**
   * create_vessel_certificate — Create a new vessel certificate
   *
   * Creates a new vessel certificate (IMO, class, or flag) with the provided details.
   *
   * @param payload - Certificate creation payload with type, authority, dates, and number
   */
  const createVesselCertificate = useCallback(
    (payload: CreateVesselCertificatePayload) =>
      execute('create_vessel_certificate', {
        certificate_type: payload.certificate_type,
        issuing_authority: payload.issuing_authority,
        issue_date: payload.issue_date,
        expiry_date: payload.expiry_date,
        certificate_number: payload.certificate_number,
        ...(payload.document_id && { document_id: payload.document_id }),
      }),
    [execute]
  );

  /**
   * create_crew_certificate — Create a new crew certificate
   *
   * Creates a new crew certificate (STCW, training, medical, etc.) with the provided details.
   *
   * @param payload - Certificate creation payload with crew member ID, type, authority, dates, and number
   */
  const createCrewCertificate = useCallback(
    (payload: CreateCrewCertificatePayload) =>
      execute('create_crew_certificate', {
        crew_member_id: payload.crew_member_id,
        certificate_type: payload.certificate_type,
        issuing_authority: payload.issuing_authority,
        issue_date: payload.issue_date,
        expiry_date: payload.expiry_date,
        certificate_number: payload.certificate_number,
        ...(payload.document_id && { document_id: payload.document_id }),
      }),
    [execute]
  );

  /**
   * supersede_certificate — Mark certificate as superseded
   *
   * Marks the current certificate as superseded by a new one.
   * Links the old certificate to the new one and records the reason.
   * Requires PIN and TOTP signature for audit trail.
   *
   * @param payload - Supersede payload with new certificate ID and required signature
   */
  const supersedeCertificate = useCallback(
    (payload: SupersedeCertificatePayload) =>
      execute('supersede_certificate', {
        new_certificate_id: payload.new_certificate_id,
        ...(payload.reason && { reason: payload.reason }),
        signature: {
          pin_hash: payload.signature.pin_hash,
          totp_code: payload.signature.totp_code,
        },
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
    renewCertificate,
    linkDocument,
    createVesselCertificate,
    supersedeCertificate,
    createCrewCertificate,

    // State validation helpers (MEDIUM-1 fix)
    /** Check if certificate is expired based on current state */
    isExpired: isExpired(stateOptions?.currentExpiryDate),
    /** Validate if update is allowed with the given new expiry date */
    validateStateForUpdate,
    /** Check if certificate is in a terminal state (cannot be updated) */
    isTerminalState: stateOptions?.currentStatus === 'superseded' || stateOptions?.currentStatus === 'revoked',
  };
}

// ---------------------------------------------------------------------------
// Role permission helpers - DELEGATED TO CENTRALIZED SERVICE
// ---------------------------------------------------------------------------

import { useCertificatePermissions as useCentralizedCertificatePermissions } from '@/hooks/permissions/useCertificatePermissions';

export interface CertificatePermissions {
  /** Can renew/update certificate details (chief_engineer, captain, manager) */
  canRenew: boolean;
  /** Can link documents to certificate (chief_engineer, captain, manager) */
  canLink: boolean;
  /** Can create vessel certificates (chief_engineer, captain, manager) */
  canCreateVesselCert: boolean;
  /** Can supersede a certificate (chief_engineer, captain, manager) */
  canSupersede: boolean;
  /** Can create crew certificates (chief_engineer, captain, manager) */
  canCreateCrewCert: boolean;
}

/**
 * useCertificatePermissions
 *
 * Derives a set of boolean capability flags from the current user's role.
 * DELEGATED TO CENTRALIZED SERVICE - reads from lens_matrix.json
 */
export function useCertificatePermissions(): CertificatePermissions {
  const central = useCentralizedCertificatePermissions();

  return {
    canRenew: central.canUpdateCertificate,
    canLink: central.canLinkDocumentToCertificate,
    canCreateVesselCert: central.canCreateVesselCertificate,
    canSupersede: central.canSupersedeCertificate,
    canCreateCrewCert: central.canCreateCrewCertificate,
  };
}
