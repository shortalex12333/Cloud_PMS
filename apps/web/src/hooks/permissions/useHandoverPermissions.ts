'use client';

/**
 * useHandoverPermissions - Type-safe Handover Permissions
 *
 * Derived from lens_matrix.json - DO NOT hardcode roles here.
 * Uses centralized PermissionService as single source of truth.
 *
 * Actions from lens_matrix.json handover lens:
 * - add_to_handover: role_restricted: [] (all roles)
 * - edit_handover_item: role_restricted: [] (all roles)
 * - attach_document_to_handover: role_restricted: [] (all roles)
 * - export_handover: role_restricted: [] (all roles)
 * - regenerate_handover_summary: role_restricted: [] (all roles)
 * - edit_handover_section: role_restricted: [] (all roles)
 */

import { usePermissions } from '../usePermissions';

// Type-safe action IDs for handover lens
export type HandoverAction =
  | 'add_to_handover'
  | 'edit_handover_item'
  | 'attach_document_to_handover'
  | 'export_handover'
  | 'regenerate_handover_summary'
  | 'edit_handover_section';

export interface HandoverPermissions {
  /** Can add to handover (all roles) */
  canAddToHandover: boolean;
  /** Can edit handover item (all roles) */
  canEditHandoverItem: boolean;
  /** Can attach document (all roles) */
  canAttachDocumentToHandover: boolean;
  /** Can export handover (all roles) */
  canExportHandover: boolean;
  /** Can regenerate summary (all roles) */
  canRegenerateHandoverSummary: boolean;
  /** Can edit section (all roles) */
  canEditHandoverSection: boolean;

  /** Generic check for any handover action */
  can: (action: HandoverAction) => boolean;

  /** User's current role */
  userRole: string;

  /** Whether auth is loading */
  isLoading: boolean;
}

/**
 * Type-safe handover permissions hook
 *
 * GENERATED from lens_matrix.json - do NOT hardcode roles here.
 */
export function useHandoverPermissions(): HandoverPermissions {
  const { can, userRole, isLoading } = usePermissions('handover');

  return {
    canAddToHandover: can('add_to_handover'),
    canEditHandoverItem: can('edit_handover_item'),
    canAttachDocumentToHandover: can('attach_document_to_handover'),
    canExportHandover: can('export_handover'),
    canRegenerateHandoverSummary: can('regenerate_handover_summary'),
    canEditHandoverSection: can('edit_handover_section'),
    can: can as (action: HandoverAction) => boolean,
    userRole,
    isLoading,
  };
}
