'use client';

/**
 * useEquipmentPermissions - Type-safe Equipment Permissions
 *
 * Derived from lens_matrix.json - DO NOT hardcode roles here.
 * Uses centralized PermissionService as single source of truth.
 *
 * Actions from lens_matrix.json equipment lens:
 * - update_equipment: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - set_equipment_status: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - link_document_to_equipment: role_restricted: [] (all roles)
 * - update_running_hours: role_restricted: [] (all roles)
 * - log_contractor_work: role_restricted: [] (all roles)
 */

import { usePermissions } from '../usePermissions';

// Type-safe action IDs for equipment lens
export type EquipmentAction =
  | 'update_equipment'
  | 'set_equipment_status'
  | 'link_document_to_equipment'
  | 'update_running_hours'
  | 'log_contractor_work';

export interface EquipmentPermissions {
  /** Can update equipment fields (chief_engineer, captain, manager) */
  canUpdateEquipment: boolean;
  /** Can set equipment status (chief_engineer, captain, manager) */
  canSetEquipmentStatus: boolean;
  /** Can link documents (all roles) */
  canLinkDocumentToEquipment: boolean;
  /** Can update running hours (all roles) */
  canUpdateRunningHours: boolean;
  /** Can log contractor work (all roles) */
  canLogContractorWork: boolean;

  /** Generic check for any equipment action */
  can: (action: EquipmentAction) => boolean;

  /** User's current role */
  userRole: string;

  /** Whether auth is loading */
  isLoading: boolean;
}

/**
 * Type-safe equipment permissions hook
 *
 * GENERATED from lens_matrix.json - do NOT hardcode roles here.
 */
export function useEquipmentPermissions(): EquipmentPermissions {
  const { can, userRole, isLoading } = usePermissions('equipment');

  return {
    canUpdateEquipment: can('update_equipment'),
    canSetEquipmentStatus: can('set_equipment_status'),
    canLinkDocumentToEquipment: can('link_document_to_equipment'),
    canUpdateRunningHours: can('update_running_hours'),
    canLogContractorWork: can('log_contractor_work'),
    can: can as (action: EquipmentAction) => boolean,
    userRole,
    isLoading,
  };
}
