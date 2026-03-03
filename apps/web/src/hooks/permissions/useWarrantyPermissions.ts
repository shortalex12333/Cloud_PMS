'use client';

/**
 * useWarrantyPermissions - Type-safe Warranty Permissions
 *
 * Derived from lens_matrix.json - DO NOT hardcode roles here.
 * Uses centralized PermissionService as single source of truth.
 *
 * Actions from lens_matrix.json warranty lens:
 * - create_warranty: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - update_warranty: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - claim_warranty: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - void_warranty: role_restricted: ['manager']
 * - link_document_to_warranty: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - extend_warranty: role_restricted: ['chief_engineer', 'captain', 'manager']
 */

import { usePermissions } from '../usePermissions';

// Type-safe action IDs for warranty lens
export type WarrantyAction =
  | 'create_warranty'
  | 'update_warranty'
  | 'claim_warranty'
  | 'void_warranty'
  | 'link_document_to_warranty'
  | 'extend_warranty';

export interface WarrantyPermissions {
  /** Can create warranty (chief_engineer, captain, manager) */
  canCreateWarranty: boolean;
  /** Can update warranty (chief_engineer, captain, manager) */
  canUpdateWarranty: boolean;
  /** Can claim warranty (chief_engineer, captain, manager) */
  canClaimWarranty: boolean;
  /** Can void warranty (manager only) */
  canVoidWarranty: boolean;
  /** Can link document (chief_engineer, captain, manager) */
  canLinkDocumentToWarranty: boolean;
  /** Can extend warranty (chief_engineer, captain, manager) */
  canExtendWarranty: boolean;

  // -------------------------------------------------------------------------
  // Backward-compatible aliases (used by useWarrantyActions.ts)
  // -------------------------------------------------------------------------

  /** @alias canClaimWarranty - Submit warranty claim */
  canSubmitWarrantyClaim: boolean;
  /** @alias canClaimWarranty - Approve warranty claim (HOD+ action) */
  canApproveWarrantyClaim: boolean;
  /** @alias canClaimWarranty - Reject warranty claim (HOD+ action) */
  canRejectWarrantyClaim: boolean;
  /** @alias canClaimWarranty - Compose warranty email (related to claims) */
  canComposeWarrantyEmail: boolean;

  /** Generic check for any warranty action */
  can: (action: WarrantyAction) => boolean;

  /** User's current role */
  userRole: string;

  /** Whether auth is loading */
  isLoading: boolean;
}

/**
 * Type-safe warranty permissions hook
 *
 * GENERATED from lens_matrix.json - do NOT hardcode roles here.
 */
export function useWarrantyPermissions(): WarrantyPermissions {
  const { can, userRole, isLoading } = usePermissions('warranty');

  // Compute for reuse in aliases
  const canClaimWarranty = can('claim_warranty');

  return {
    canCreateWarranty: can('create_warranty'),
    canUpdateWarranty: can('update_warranty'),
    canClaimWarranty,
    canVoidWarranty: can('void_warranty'),
    canLinkDocumentToWarranty: can('link_document_to_warranty'),
    canExtendWarranty: can('extend_warranty'),

    // Backward-compatible aliases for useWarrantyActions.ts
    canSubmitWarrantyClaim: canClaimWarranty, // Submit = claim
    canApproveWarrantyClaim: canClaimWarranty, // Approve is HOD+ action like claim
    canRejectWarrantyClaim: canClaimWarranty, // Reject is HOD+ action like claim
    canComposeWarrantyEmail: canClaimWarranty, // Email related to claims

    can: can as (action: WarrantyAction) => boolean,
    userRole,
    isLoading,
  };
}
