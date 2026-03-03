'use client';

/**
 * useWorkOrderPermissions - Type-safe Work Order Permissions
 *
 * Derived from lens_matrix.json - DO NOT hardcode roles here.
 * Uses centralized PermissionService as single source of truth.
 *
 * Actions from lens_matrix.json work_order lens:
 * - create_work_order: role_restricted: [] (all roles)
 * - create_work_order_from_fault: role_restricted: [] (all roles)
 * - update_work_order: role_restricted: [] (all roles)
 * - add_note_to_work_order: role_restricted: [] (all roles)
 * - add_part_to_work_order: role_restricted: [] (all roles)
 * - mark_work_order_complete: role_restricted: [] (all roles)
 * - assign_work_order: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - close_work_order: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - schedule_work_order: role_restricted: [] (all roles)
 * - set_priority_on_work_order: role_restricted: [] (all roles)
 * - attach_photo_to_work_order: role_restricted: [] (all roles)
 * - attach_document_to_work_order: role_restricted: [] (all roles)
 */

import { usePermissions } from '../usePermissions';

// Type-safe action IDs for work_order lens
export type WorkOrderAction =
  | 'create_work_order'
  | 'create_work_order_from_fault'
  | 'update_work_order'
  | 'add_note_to_work_order'
  | 'add_part_to_work_order'
  | 'mark_work_order_complete'
  | 'assign_work_order'
  | 'close_work_order'
  | 'schedule_work_order'
  | 'set_priority_on_work_order'
  | 'attach_photo_to_work_order'
  | 'attach_document_to_work_order';

export interface WorkOrderPermissions {
  /** Can create a new work order (all roles) */
  canCreateWorkOrder: boolean;
  /** Can create work order from fault (all roles) */
  canCreateWorkOrderFromFault: boolean;
  /** Can update work order (all roles) */
  canUpdateWorkOrder: boolean;
  /** Can add notes (all roles) */
  canAddNoteToWorkOrder: boolean;
  /** Can add parts (all roles) */
  canAddPartToWorkOrder: boolean;
  /** Can mark as complete (all roles) */
  canMarkWorkOrderComplete: boolean;
  /** Can assign work order (chief_engineer, captain, manager) */
  canAssignWorkOrder: boolean;
  /** Can close work order (chief_engineer, captain, manager) */
  canCloseWorkOrder: boolean;
  /** Can schedule work order (all roles) */
  canScheduleWorkOrder: boolean;
  /** Can set priority (all roles) */
  canSetPriorityOnWorkOrder: boolean;
  /** Can attach photos (all roles) */
  canAttachPhotoToWorkOrder: boolean;
  /** Can attach documents (all roles) */
  canAttachDocumentToWorkOrder: boolean;

  // -------------------------------------------------------------------------
  // Additional permissions (not in lens_matrix, derived from other actions)
  // -------------------------------------------------------------------------

  /** Can view related entities (uses add_note as proxy - read action available to all) */
  canViewRelatedEntities: boolean;

  /** Generic check for any work order action */
  can: (action: WorkOrderAction) => boolean;

  /** User's current role */
  userRole: string;

  /** Whether auth is loading */
  isLoading: boolean;
}

/**
 * Type-safe work order permissions hook
 *
 * GENERATED from lens_matrix.json - do NOT hardcode roles here.
 */
export function useWorkOrderPermissions(): WorkOrderPermissions {
  const { can, userRole, isLoading } = usePermissions('work_order');

  // Compute for reuse
  const canAddNoteToWorkOrder = can('add_note_to_work_order');

  return {
    canCreateWorkOrder: can('create_work_order'),
    canCreateWorkOrderFromFault: can('create_work_order_from_fault'),
    canUpdateWorkOrder: can('update_work_order'),
    canAddNoteToWorkOrder,
    canAddPartToWorkOrder: can('add_part_to_work_order'),
    canMarkWorkOrderComplete: can('mark_work_order_complete'),
    canAssignWorkOrder: can('assign_work_order'),
    canCloseWorkOrder: can('close_work_order'),
    canScheduleWorkOrder: can('schedule_work_order'),
    canSetPriorityOnWorkOrder: can('set_priority_on_work_order'),
    canAttachPhotoToWorkOrder: can('attach_photo_to_work_order'),
    canAttachDocumentToWorkOrder: can('attach_document_to_work_order'),

    // Additional permissions - view is a read operation, broadly available
    canViewRelatedEntities: canAddNoteToWorkOrder, // Use add_note as proxy (all roles)

    can: can as (action: WorkOrderAction) => boolean,
    userRole,
    isLoading,
  };
}
