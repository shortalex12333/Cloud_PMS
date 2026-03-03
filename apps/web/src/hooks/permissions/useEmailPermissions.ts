'use client';

/**
 * useEmailPermissions - Type-safe Email Permissions
 *
 * Derived from lens_matrix.json - DO NOT hardcode roles here.
 * Uses centralized PermissionService as single source of truth.
 *
 * Actions from lens_matrix.json email lens:
 * - link_email_to_entity: role_restricted: [] (all roles)
 * - unlink_email_from_entity: role_restricted: [] (all roles)
 * - create_work_order_from_email: role_restricted: [] (all roles)
 * - create_fault_from_email: role_restricted: [] (all roles)
 * - mark_thread_read: role_restricted: [] (all roles)
 * - archive_thread: role_restricted: [] (all roles)
 * - download_attachment: role_restricted: [] (all roles)
 */

import { usePermissions } from '../usePermissions';

// Type-safe action IDs for email lens
export type EmailAction =
  | 'link_email_to_entity'
  | 'unlink_email_from_entity'
  | 'create_work_order_from_email'
  | 'create_fault_from_email'
  | 'mark_thread_read'
  | 'archive_thread'
  | 'download_attachment';

export interface EmailPermissions {
  /** Can link email to entity (all roles) */
  canLinkEmailToEntity: boolean;
  /** Can unlink email from entity (all roles) */
  canUnlinkEmailFromEntity: boolean;
  /** Can create work order from email (all roles) */
  canCreateWorkOrderFromEmail: boolean;
  /** Can create fault from email (all roles) */
  canCreateFaultFromEmail: boolean;
  /** Can mark thread read (all roles) */
  canMarkThreadRead: boolean;
  /** Can archive thread (all roles) */
  canArchiveThread: boolean;
  /** Can download attachment (all roles) */
  canDownloadAttachment: boolean;

  // -------------------------------------------------------------------------
  // Document permissions (no dedicated document lens in lens_matrix.json)
  // These permissions use role-based logic since documents are cross-cutting
  // -------------------------------------------------------------------------

  /** Can get document signed URL (most roles) */
  canGetDocumentUrl: boolean;
  /** Can add tags to documents (most roles) */
  canAddDocumentTags: boolean;
  /** Can upload documents (HOD+) */
  canUploadDocument: boolean;
  /** Can update document metadata (HOD+) */
  canUpdateDocument: boolean;

  /** Generic check for any email action */
  can: (action: EmailAction) => boolean;

  /** User's current role */
  userRole: string;

  /** Whether auth is loading */
  isLoading: boolean;
}

/**
 * Type-safe email permissions hook
 *
 * GENERATED from lens_matrix.json - do NOT hardcode roles here.
 */
// Document-related roles (no dedicated document lens in lens_matrix.json)
const GET_URL_ROLES = ['captain', 'chief_engineer', 'chief_officer', 'manager', 'purser', 'bosun', 'crew'];
const ADD_TAGS_ROLES = ['captain', 'chief_engineer', 'chief_officer', 'manager', 'purser', 'bosun', 'crew'];
const UPLOAD_ROLES = ['captain', 'chief_engineer', 'chief_officer', 'manager', 'purser', 'bosun'];
const UPDATE_DOC_ROLES = ['captain', 'chief_engineer', 'chief_officer', 'manager', 'purser'];

export function useEmailPermissions(): EmailPermissions {
  const { can, userRole, isLoading } = usePermissions('email');

  return {
    canLinkEmailToEntity: can('link_email_to_entity'),
    canUnlinkEmailFromEntity: can('unlink_email_from_entity'),
    canCreateWorkOrderFromEmail: can('create_work_order_from_email'),
    canCreateFaultFromEmail: can('create_fault_from_email'),
    canMarkThreadRead: can('mark_thread_read'),
    canArchiveThread: can('archive_thread'),
    canDownloadAttachment: can('download_attachment'),

    // Document permissions (role-based, no lens_matrix entry)
    canGetDocumentUrl: GET_URL_ROLES.includes(userRole),
    canAddDocumentTags: ADD_TAGS_ROLES.includes(userRole),
    canUploadDocument: UPLOAD_ROLES.includes(userRole),
    canUpdateDocument: UPDATE_DOC_ROLES.includes(userRole),

    can: can as (action: EmailAction) => boolean,
    userRole,
    isLoading,
  };
}
