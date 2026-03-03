'use client';

/**
 * useReceivingPermissions - Type-safe Receiving Permissions
 *
 * Derived from lens_matrix.json - DO NOT hardcode roles here.
 * Uses centralized PermissionService as single source of truth.
 *
 * Actions from lens_matrix.json receiving lens:
 * - create_receiving: role_restricted: [] (all roles)
 * - attach_receiving_image_with_comment: role_restricted: [] (all roles)
 * - extract_receiving_candidates: role_restricted: [] (all roles)
 * - update_receiving_fields: role_restricted: [] (all roles)
 * - add_receiving_item: role_restricted: [] (all roles)
 * - adjust_receiving_item: role_restricted: [] (all roles)
 * - link_invoice_document: role_restricted: [] (all roles)
 * - accept_receiving: role_restricted: [] (all roles)
 * - reject_receiving: role_restricted: [] (all roles)
 */

import { usePermissions } from '../usePermissions';

// Type-safe action IDs for receiving lens
export type ReceivingAction =
  | 'create_receiving'
  | 'attach_receiving_image_with_comment'
  | 'extract_receiving_candidates'
  | 'update_receiving_fields'
  | 'add_receiving_item'
  | 'adjust_receiving_item'
  | 'link_invoice_document'
  | 'accept_receiving'
  | 'reject_receiving';

export interface ReceivingPermissions {
  /** Can create receiving (all roles) */
  canCreateReceiving: boolean;
  /** Can attach image with comment (all roles) */
  canAttachReceivingImageWithComment: boolean;
  /** Can extract candidates (all roles) */
  canExtractReceivingCandidates: boolean;
  /** Can update fields (all roles) */
  canUpdateReceivingFields: boolean;
  /** Can add item (all roles) */
  canAddReceivingItem: boolean;
  /** Can adjust item (all roles) */
  canAdjustReceivingItem: boolean;
  /** Can link invoice document (all roles) */
  canLinkInvoiceDocument: boolean;
  /** Can accept receiving (all roles) */
  canAcceptReceiving: boolean;
  /** Can reject receiving (all roles) */
  canRejectReceiving: boolean;

  // -------------------------------------------------------------------------
  // Backward-compatible aliases (used by useReceivingActions.ts)
  // -------------------------------------------------------------------------

  /** @alias canCreateReceiving - Start receiving event */
  canStartReceivingEvent: boolean;
  /** @alias canAddReceivingItem - Add line item */
  canAddLineItem: boolean;
  /** @alias canAcceptReceiving - Complete receiving event */
  canCompleteReceivingEvent: boolean;
  /** @alias canRejectReceiving - Report discrepancy */
  canReportDiscrepancy: boolean;
  /** @alias canAdjustReceivingItem - Verify line item */
  canVerifyLineItem: boolean;

  /** Generic check for any receiving action */
  can: (action: ReceivingAction) => boolean;

  /** User's current role */
  userRole: string;

  /** Whether auth is loading */
  isLoading: boolean;
}

/**
 * Type-safe receiving permissions hook
 *
 * GENERATED from lens_matrix.json - do NOT hardcode roles here.
 */
export function useReceivingPermissions(): ReceivingPermissions {
  const { can, userRole, isLoading } = usePermissions('receiving');

  // Compute core permissions
  const canCreateReceiving = can('create_receiving');
  const canAddReceivingItem = can('add_receiving_item');
  const canAcceptReceiving = can('accept_receiving');
  const canRejectReceiving = can('reject_receiving');
  const canAdjustReceivingItem = can('adjust_receiving_item');

  return {
    canCreateReceiving,
    canAttachReceivingImageWithComment: can('attach_receiving_image_with_comment'),
    canExtractReceivingCandidates: can('extract_receiving_candidates'),
    canUpdateReceivingFields: can('update_receiving_fields'),
    canAddReceivingItem,
    canAdjustReceivingItem,
    canLinkInvoiceDocument: can('link_invoice_document'),
    canAcceptReceiving,
    canRejectReceiving,

    // Backward-compatible aliases for useReceivingActions.ts
    canStartReceivingEvent: canCreateReceiving, // Start = create
    canAddLineItem: canAddReceivingItem, // Add line = add item
    canCompleteReceivingEvent: canAcceptReceiving, // Complete = accept
    canReportDiscrepancy: canRejectReceiving, // Discrepancy leads to rejection
    canVerifyLineItem: canAdjustReceivingItem, // Verify = adjust/check

    can: can as (action: ReceivingAction) => boolean,
    userRole,
    isLoading,
  };
}
