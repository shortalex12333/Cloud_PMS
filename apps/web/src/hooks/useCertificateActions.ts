'use client';

/**
 * useCertificateActions — Certificate action hook (FE-02-04)
 *
 * Wires all certificate action registry calls to typed helper methods.
 * Uses the unified action API endpoint per the action router spec.
 *
 * Action IDs map 1:1 to registry.py keys:
 *   view_certificate, create_certificate, update_certificate,
 *   find_expiring_certificates, link_document, supersede_certificate
 *
 * Role-based access is enforced at the API level; visibility gates live in
 * CertificateLens (hide, not disable).
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

export interface CertificateActionsState {
  isLoading: boolean;
  error: string | null;
}

// API URL — same origin Next.js API route proxied to Render backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * useCertificateActions
 *
 * Returns typed action helpers for all certificate operations.
 * Each helper calls POST /v1/certificates/{endpoint} with JWT auth.
 *
 * @param certificateId - UUID of the certificate in scope
 */
export function useCertificateActions(certificateId: string) {
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
            certificate_id: certificateId,
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
    [session, user, certificateId]
  );

  // -------------------------------------------------------------------------
  // Typed action helpers — one per registry action
  // -------------------------------------------------------------------------

  /** view_certificate — fetch full certificate data (read-only) */
  const viewCertificate = useCallback(
    () => execute('/v1/certificates/view', {}),
    [execute]
  );

  /** create_certificate — create a new certificate record (HOD+) */
  const createCertificate = useCallback(
    (fields: Record<string, unknown>) =>
      execute('/v1/certificates/create', fields),
    [execute]
  );

  /** update_certificate — update certificate fields (HOD+) */
  const updateCertificate = useCallback(
    (changes: Record<string, unknown>) =>
      execute('/v1/certificates/update', changes),
    [execute]
  );

  /** find_expiring_certificates — search for certificates expiring soon (read-only) */
  const findExpiringCertificates = useCallback(
    (daysThreshold?: number) =>
      execute('/v1/certificates/expiring', { days_threshold: daysThreshold ?? 30 }),
    [execute]
  );

  /** link_document — attach a document to the certificate */
  const linkDocument = useCallback(
    (documentUrl: string, documentName?: string) =>
      execute('/v1/certificates/link-document', {
        document_url: documentUrl,
        document_name: documentName,
      }),
    [execute]
  );

  /** supersede_certificate — mark certificate as superseded (captain/manager only) */
  const supersedeCertificate = useCallback(
    (metadata: Record<string, unknown>) =>
      execute('/v1/certificates/supersede', metadata),
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
    viewCertificate,
    findExpiringCertificates,

    // Create / update
    createCertificate,
    updateCertificate,

    // Document management
    linkDocument,

    // Privileged
    supersedeCertificate,
  };
}

// ---------------------------------------------------------------------------
// Role permission helpers
// ---------------------------------------------------------------------------

/** All roles with HOD-level or above access */
const HOD_ROLES = ['chief_engineer', 'eto', 'chief_officer', 'captain', 'manager'];

/** Roles allowed to create / update certificates */
const MANAGE_ROLES = ['chief_officer', 'captain', 'manager'];

/** Roles allowed to supersede certificates (captain/manager only) */
const SUPERSEDE_ROLES = ['captain', 'manager'];

export interface CertificatePermissions {
  /** Can view certificate (all roles) */
  canView: boolean;
  /** Can create a certificate (HOD+) */
  canCreate: boolean;
  /** Can update certificate details (MANAGE_ROLES) */
  canUpdate: boolean;
  /** Can search for expiring certificates (HOD+) */
  canFindExpiring: boolean;
  /** Can link a document to the certificate (HOD+) */
  canLinkDocument: boolean;
  /** Can supersede a certificate (captain/manager only) */
  canSupersede: boolean;
}

/**
 * useCertificatePermissions
 *
 * Derives a set of boolean capability flags from the current user's role.
 * These are used to conditionally show (not disable) action buttons.
 */
export function useCertificatePermissions(): CertificatePermissions {
  const { user } = useAuth();
  const role = user?.role ?? '';

  return {
    canView: true, // All authenticated users can view
    canCreate: HOD_ROLES.includes(role),
    canUpdate: MANAGE_ROLES.includes(role),
    canFindExpiring: HOD_ROLES.includes(role),
    canLinkDocument: HOD_ROLES.includes(role),
    canSupersede: SUPERSEDE_ROLES.includes(role),
  };
}
