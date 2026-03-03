'use client';

/**
 * useFaultPermissions - Type-safe Fault Permissions
 *
 * Derived from lens_matrix.json - DO NOT hardcode roles here.
 * Uses centralized PermissionService as single source of truth.
 *
 * Actions from lens_matrix.json fault lens:
 * - report_fault: role_restricted: [] (all roles)
 * - acknowledge_fault: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - close_fault: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - update_fault: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - add_fault_photo: role_restricted: [] (all roles)
 * - add_fault_note: role_restricted: [] (all roles)
 * - diagnose_fault: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - reopen_fault: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - mark_fault_false_alarm: role_restricted: ['chief_engineer', 'captain', 'manager']
 */

import { usePermissions } from '../usePermissions';

// Type-safe action IDs for fault lens
export type FaultAction =
  | 'report_fault'
  | 'acknowledge_fault'
  | 'close_fault'
  | 'update_fault'
  | 'add_fault_photo'
  | 'add_fault_note'
  | 'diagnose_fault'
  | 'reopen_fault'
  | 'mark_fault_false_alarm';

export interface FaultPermissions {
  /** Can report a new fault (all roles) */
  canReportFault: boolean;
  /** Can acknowledge fault (chief_engineer, captain, manager) */
  canAcknowledgeFault: boolean;
  /** Can close/resolve fault (chief_engineer, captain, manager) */
  canCloseFault: boolean;
  /** Can update fault severity/description (chief_engineer, captain, manager) */
  canUpdateFault: boolean;
  /** Can add photos (all roles) */
  canAddFaultPhoto: boolean;
  /** Can add notes (all roles) */
  canAddFaultNote: boolean;
  /** Can diagnose fault (chief_engineer, captain, manager) */
  canDiagnoseFault: boolean;
  /** Can reopen a closed fault (chief_engineer, captain, manager) */
  canReopenFault: boolean;
  /** Can mark fault as false alarm (chief_engineer, captain, manager) */
  canMarkFalseAlarm: boolean;

  // -------------------------------------------------------------------------
  // Backward-compatible aliases (used by faults/[id]/page.tsx)
  // -------------------------------------------------------------------------

  /** @alias canAcknowledgeFault - Backward compatible short name */
  canAcknowledge: boolean;
  /** @alias canCloseFault - Backward compatible short name */
  canClose: boolean;
  /** @alias canUpdateFault - Backward compatible short name */
  canUpdate: boolean;
  /** @alias canReopenFault - Backward compatible short name */
  canReopen: boolean;
  /** @alias canAddFaultPhoto - Backward compatible short name */
  canAddPhoto: boolean;
  /** @alias canAddFaultNote - Backward compatible short name */
  canAddNote: boolean;
  /** @alias canDiagnoseFault - Backward compatible short name */
  canDiagnose: boolean;
  /** @alias canReportFault - Backward compatible short name */
  canReport: boolean;

  // -------------------------------------------------------------------------
  // Cross-lens permissions (used by fault detail page)
  // -------------------------------------------------------------------------

  /** Can create work order from fault (from work_order lens) */
  canCreateWorkOrder: boolean;

  /** Generic check for any fault action */
  can: (action: FaultAction) => boolean;

  /** User's current role */
  userRole: string;

  /** Whether auth is loading */
  isLoading: boolean;
}

/**
 * Type-safe fault permissions hook
 *
 * GENERATED from lens_matrix.json - do NOT hardcode roles here.
 *
 * Usage:
 * ```tsx
 * const { canUpdateFault, canCloseFault, can } = useFaultPermissions();
 * if (canUpdateFault) { // Show update button }
 * if (can('diagnose_fault')) { // Show diagnose button }
 * ```
 */
export function useFaultPermissions(): FaultPermissions {
  const { can, userRole, isLoading } = usePermissions('fault');
  const { can: canWorkOrder } = usePermissions('work_order');

  // Compute permissions once
  const canReportFault = can('report_fault');
  const canAcknowledgeFault = can('acknowledge_fault');
  const canCloseFault = can('close_fault');
  const canUpdateFault = can('update_fault');
  const canAddFaultPhoto = can('add_fault_photo');
  const canAddFaultNote = can('add_fault_note');
  const canDiagnoseFault = can('diagnose_fault');
  const canReopenFault = can('reopen_fault');
  const canMarkFalseAlarm = can('mark_fault_false_alarm');

  return {
    // Full names (preferred for new code)
    canReportFault,
    canAcknowledgeFault,
    canCloseFault,
    canUpdateFault,
    canAddFaultPhoto,
    canAddFaultNote,
    canDiagnoseFault,
    canReopenFault,
    canMarkFalseAlarm,

    // Short aliases (backward compatibility with faults/[id]/page.tsx)
    canAcknowledge: canAcknowledgeFault,
    canClose: canCloseFault,
    canUpdate: canUpdateFault,
    canReopen: canReopenFault,
    canAddPhoto: canAddFaultPhoto,
    canAddNote: canAddFaultNote,
    canDiagnose: canDiagnoseFault,
    canReport: canReportFault,

    // Cross-lens permission for creating work orders from faults
    canCreateWorkOrder: canWorkOrder('create_work_order_from_fault'),

    can: can as (action: FaultAction) => boolean,
    userRole,
    isLoading,
  };
}
