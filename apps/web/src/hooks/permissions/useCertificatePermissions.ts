'use client';

/**
 * useCertificatePermissions - Type-safe Certificate Permissions
 *
 * Derived from lens_matrix.json - DO NOT hardcode roles here.
 * Uses centralized PermissionService as single source of truth.
 *
 * Actions from lens_matrix.json certificate lens:
 * - create_vessel_certificate: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - create_crew_certificate: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - update_certificate: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - link_document_to_certificate: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - supersede_certificate: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - delete_certificate: role_restricted: ['manager']
 * - upload_certificate_document: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - update_certificate_metadata: role_restricted: ['chief_engineer', 'captain', 'manager']
 */

import { usePermissions } from '../usePermissions';

// Type-safe action IDs for certificate lens
export type CertificateAction =
  | 'create_vessel_certificate'
  | 'create_crew_certificate'
  | 'update_certificate'
  | 'link_document_to_certificate'
  | 'supersede_certificate'
  | 'delete_certificate'
  | 'upload_certificate_document'
  | 'update_certificate_metadata';

export interface CertificatePermissions {
  /** Can create vessel certificate (chief_engineer, captain, manager) */
  canCreateVesselCertificate: boolean;
  /** Can create crew certificate (chief_engineer, captain, manager) */
  canCreateCrewCertificate: boolean;
  /** Can update certificate (chief_engineer, captain, manager) */
  canUpdateCertificate: boolean;
  /** Can link document (chief_engineer, captain, manager) */
  canLinkDocumentToCertificate: boolean;
  /** Can supersede certificate (chief_engineer, captain, manager) */
  canSupersedeCertificate: boolean;
  /** Can delete certificate (manager only) */
  canDeleteCertificate: boolean;
  /** Can upload certificate document (chief_engineer, captain, manager) */
  canUploadCertificateDocument: boolean;
  /** Can update certificate metadata (chief_engineer, captain, manager) */
  canUpdateCertificateMetadata: boolean;

  /** Generic check for any certificate action */
  can: (action: CertificateAction) => boolean;

  /** User's current role */
  userRole: string;

  /** Whether auth is loading */
  isLoading: boolean;
}

/**
 * Type-safe certificate permissions hook
 *
 * GENERATED from lens_matrix.json - do NOT hardcode roles here.
 */
export function useCertificatePermissions(): CertificatePermissions {
  const { can, userRole, isLoading } = usePermissions('certificate');

  return {
    canCreateVesselCertificate: can('create_vessel_certificate'),
    canCreateCrewCertificate: can('create_crew_certificate'),
    canUpdateCertificate: can('update_certificate'),
    canLinkDocumentToCertificate: can('link_document_to_certificate'),
    canSupersedeCertificate: can('supersede_certificate'),
    canDeleteCertificate: can('delete_certificate'),
    canUploadCertificateDocument: can('upload_certificate_document'),
    canUpdateCertificateMetadata: can('update_certificate_metadata'),
    can: can as (action: CertificateAction) => boolean,
    userRole,
    isLoading,
  };
}
