'use client';

/**
 * useHoursOfRestPermissions - Type-safe Hours of Rest Permissions
 *
 * Derived from lens_matrix.json - DO NOT hardcode roles here.
 * Uses centralized PermissionService as single source of truth.
 *
 * Actions from lens_matrix.json hours_of_rest lens:
 * - log_hours_of_rest: role_restricted: [] (all roles)
 * - upsert_hours_of_rest: role_restricted: [] (all roles)
 * - create_monthly_signoff: role_restricted: ['chief_engineer', 'captain', 'manager']
 * - sign_monthly_signoff: role_restricted: [] (all roles)
 * - create_crew_template: role_restricted: [] (all roles)
 * - apply_crew_template: role_restricted: [] (all roles)
 * - acknowledge_warning: role_restricted: [] (all roles)
 * - dismiss_warning: role_restricted: ['chief_engineer', 'captain', 'manager']
 */

import { usePermissions } from '../usePermissions';

// Type-safe action IDs for hours_of_rest lens
export type HoursOfRestAction =
  | 'log_hours_of_rest'
  | 'upsert_hours_of_rest'
  | 'create_monthly_signoff'
  | 'sign_monthly_signoff'
  | 'create_crew_template'
  | 'apply_crew_template'
  | 'acknowledge_warning'
  | 'dismiss_warning';

export interface HoursOfRestPermissions {
  /** Can log hours of rest (all roles) */
  canLogHoursOfRest: boolean;
  /** Can upsert hours of rest (all roles) */
  canUpsertHoursOfRest: boolean;
  /** Can create monthly signoff (chief_engineer, captain, manager) */
  canCreateMonthlySignoff: boolean;
  /** Can sign monthly signoff (all roles) */
  canSignMonthlySignoff: boolean;
  /** Can create crew template (all roles) */
  canCreateCrewTemplate: boolean;
  /** Can apply crew template (all roles) */
  canApplyCrewTemplate: boolean;
  /** Can acknowledge warning (all roles) */
  canAcknowledgeWarning: boolean;
  /** Can dismiss warning (chief_engineer, captain, manager) */
  canDismissWarning: boolean;

  // -------------------------------------------------------------------------
  // Additional permissions (mapped to closest lens_matrix actions)
  // -------------------------------------------------------------------------

  /** Can verify hours of rest records (HOD+ - uses dismiss_warning permission) */
  canVerifyHoursOfRest: boolean;
  /** Can add rest period (uses log_hours_of_rest permission) */
  canAddRestPeriod: boolean;
  /** Can view compliance status (uses dismiss_warning as proxy for HOD+) */
  canViewComplianceStatus: boolean;

  /** Generic check for any hours of rest action */
  can: (action: HoursOfRestAction) => boolean;

  /** User's current role */
  userRole: string;

  /** Whether auth is loading */
  isLoading: boolean;
}

/**
 * Type-safe hours of rest permissions hook
 *
 * GENERATED from lens_matrix.json - do NOT hardcode roles here.
 */
export function useHoursOfRestPermissions(): HoursOfRestPermissions {
  const { can, userRole, isLoading } = usePermissions('hours_of_rest');

  // Compute core permissions
  const canLogHoursOfRest = can('log_hours_of_rest');
  const canDismissWarning = can('dismiss_warning');

  return {
    canLogHoursOfRest,
    canUpsertHoursOfRest: can('upsert_hours_of_rest'),
    canCreateMonthlySignoff: can('create_monthly_signoff'),
    canSignMonthlySignoff: can('sign_monthly_signoff'),
    canCreateCrewTemplate: can('create_crew_template'),
    canApplyCrewTemplate: can('apply_crew_template'),
    canAcknowledgeWarning: can('acknowledge_warning'),
    canDismissWarning,

    // Mapped permissions for backward compatibility
    canVerifyHoursOfRest: canDismissWarning, // Verify is HOD+ action, same as dismiss
    canAddRestPeriod: canLogHoursOfRest, // Adding rest period is same as logging
    canViewComplianceStatus: canDismissWarning, // View compliance is HOD+ action

    can: can as (action: HoursOfRestAction) => boolean,
    userRole,
    isLoading,
  };
}
