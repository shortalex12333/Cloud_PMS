'use client';

/**
 * useHoursOfRestActions - Action hook for Hours of Rest lens.
 *
 * Wires hours of rest action registry calls to typed helper methods.
 * Uses executeAction from @/lib/actionClient for all mutations.
 *
 * Action IDs:
 *   verify_hours_of_rest
 *   add_rest_period
 *   dismiss_warning
 *   acknowledge_warning
 *   sign_monthly_signoff
 *   view_compliance_status
 *   apply_crew_template
 *
 * Role-based access is enforced at the API level; visibility gates live in
 * HoursOfRestLens (hide, not disable).
 */

import { useState, useCallback } from 'react';
import { executeAction } from '@/lib/actionClient';
import type { ActionResult } from '@/types/actions';
import { useAuth } from '@/hooks/useAuth';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface HoursOfRestActionsState {
  isLoading: boolean;
  error: string | null;
}

export interface HoursOfRestPermissions {
  /** Can verify hours of rest records (HOD+) */
  canVerify: boolean;
  /** Can add rest periods to records */
  canAddPeriod: boolean;
  /** Can dismiss compliance warnings (HOD+) */
  canDismissWarning: boolean;
  /** Can acknowledge compliance warnings (all crew can acknowledge their own) */
  canAcknowledgeWarning: boolean;
  /** Can sign monthly hours of rest records (all crew sign own, HOD+ countersign) */
  canSignMonthly: boolean;
  /** Can create crew schedule templates (captain, chief_engineer, chief_officer, manager) */
  canCreateTemplate: boolean;
  /** Can view compliance status and reports (captain, chief_engineer, chief_officer, manager, purser) */
  canViewCompliance: boolean;
  /** Can apply crew schedule templates to crew members */
  canApplyTemplate: boolean;
}

export interface RestPeriod {
  /** Start time of rest period (ISO string) */
  start_time: string;
  /** End time of rest period (ISO string) */
  end_time: string;
  /** Type of rest: scheduled, unscheduled, split */
  rest_type?: 'scheduled' | 'unscheduled' | 'split';
  /** Optional notes about the rest period */
  notes?: string;
}

// ---------------------------------------------------------------------------
// Role Configuration - DELEGATED TO CENTRALIZED SERVICE
// ---------------------------------------------------------------------------

// Note: Hours of rest lens in lens_matrix.json defines role_restricted arrays.
// Permissions are now derived from the centralized service.

// ---------------------------------------------------------------------------
// useHoursOfRestActions Hook
// ---------------------------------------------------------------------------

/**
 * useHoursOfRestActions
 *
 * Returns typed action helpers for hours of rest operations.
 * Each helper calls executeAction with action name and context.
 *
 * @param recordId - UUID of the hours of rest record in scope
 */
export function useHoursOfRestActions(recordId: string) {
  const { user } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // Internal executor wrapper
  // -------------------------------------------------------------------------

  const execute = useCallback(
    async (actionName: string, payload: Record<string, unknown>): Promise<ActionResult> => {
      if (!user?.yachtId) {
        return { success: false, error: 'No yacht context available' };
      }

      setIsLoading(true);
      setError(null);

      try {
        const result = await executeAction(
          actionName,
          {
            yacht_id: user.yachtId,
            record_id: recordId,
          },
          {
            record_id: recordId,
            ...payload,
          }
        );

        return {
          success: result.status === 'success',
          data: result.result,
          error: result.message,
        };
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Unknown error';
        setError(msg);
        return { success: false, error: msg };
      } finally {
        setIsLoading(false);
      }
    },
    [user, recordId]
  );

  // -------------------------------------------------------------------------
  // Typed action helpers
  // -------------------------------------------------------------------------

  /**
   * verify_hours_of_rest - Verify/approve hours of rest record (HOD+)
   *
   * @param verificationNotes - Optional notes from verifier
   * @param signature - Optional digital signature data for compliance
   */
  const verifyRecord = useCallback(
    (verificationNotes?: string, signature?: Record<string, unknown>): Promise<ActionResult> =>
      execute('verify_hours_of_rest', {
        verification_notes: verificationNotes,
        signature,
        verified_at: new Date().toISOString(),
      }),
    [execute]
  );

  /**
   * add_rest_period - Add a new rest period entry to the record
   *
   * @param restPeriod - The rest period details (start_time, end_time, type, notes)
   */
  const addRestPeriod = useCallback(
    (restPeriod: RestPeriod): Promise<ActionResult> =>
      execute('add_rest_period', {
        start_time: restPeriod.start_time,
        end_time: restPeriod.end_time,
        rest_type: restPeriod.rest_type || 'scheduled',
        notes: restPeriod.notes,
      }),
    [execute]
  );

  /**
   * dismiss_warning - Dismiss an hours of rest warning (HOD+ only)
   *
   * @param warningId - UUID of the warning to dismiss
   * @param hodJustification - Required justification for audit trail
   */
  const dismissWarning = useCallback(
    (warningId: string, hodJustification: string): Promise<ActionResult> =>
      execute('dismiss_warning', {
        warning_id: warningId,
        hod_justification: hodJustification,
        dismissed_at: new Date().toISOString(),
      }),
    [execute]
  );

  /**
   * acknowledge_warning - Acknowledge an hours of rest compliance warning
   *
   * @param warningId - UUID of the warning to acknowledge
   * @param acknowledgmentNotes - Optional notes explaining circumstances
   */
  const acknowledgeWarning = useCallback(
    (warningId: string, acknowledgmentNotes?: string): Promise<ActionResult> =>
      execute('acknowledge_warning', {
        warning_id: warningId,
        acknowledgment_notes: acknowledgmentNotes,
        acknowledged_at: new Date().toISOString(),
      }),
    [execute]
  );

  /**
   * sign_monthly_signoff - Sign monthly hours of rest record (MLC compliance)
   *
   * @param month - Month being signed (YYYY-MM format)
   * @param signatureType - 'crew' for initial signature, 'hod' for countersignature
   * @param signature - Digital signature data
   * @param declaration - Optional declaration text acknowledged
   */
  const signMonthlySignoff = useCallback(
    (
      month: string,
      signatureType: 'crew' | 'hod',
      signature: { signature_image?: string; pin_hash?: string },
      declaration?: string
    ): Promise<ActionResult> =>
      execute('sign_monthly_signoff', {
        month,
        signature_type: signatureType,
        signature,
        declaration,
        signed_at: new Date().toISOString(),
      }),
    [execute]
  );

  /**
   * create_crew_template - Create a new crew schedule template
   *
   * @param name - Name of the template
   * @param schedule - Array of schedule entries with day, work times, and rest periods
   * @returns Promise resolving to the created template ID
   */
  const createCrewTemplate = useCallback(
    (params: {
      name: string;
      schedule: Array<{
        day: number;
        work_start: string;
        work_end: string;
        rest_periods: Array<{ start: string; end: string }>;
      }>;
    }): Promise<ActionResult> =>
      execute('create_crew_template', {
        name: params.name,
        schedule: params.schedule,
      }),
    [execute]
  );

  /**
   * view_compliance_status - View compliance status and violations for a crew member
   *
   * @param crewMemberId - Optional crew member ID (defaults to current user)
   * @param dateRange - Optional date range for compliance summary {start: ISO string, end: ISO string}
   * @returns Promise resolving to compliance summary with violations, warnings, hours worked, and rest periods
   */
  const viewComplianceStatus = useCallback(
    (params?: {
      crew_member_id?: string;
      date_range?: { start: string; end: string };
    }): Promise<ActionResult> =>
      execute('view_compliance_status', {
        crew_member_id: params?.crew_member_id,
        date_range: params?.date_range,
      }),
    [execute]
  );

  /**
   * apply_crew_template - Apply a crew schedule template to auto-fill a crew member's week schedule
   *
   * @param params - Parameters for applying the template
   *   - template_id: UUID of the template to apply
   *   - crew_member_id: UUID of the crew member receiving the schedule
   *   - week_start: ISO string date for the start of the week (YYYY-MM-DD format)
   *   - overwrite_existing: Optional boolean to overwrite existing schedule entries (default: false)
   * @returns Promise resolving to the applied schedule data
   */
  const applyCrewTemplate = useCallback(
    (params: {
      template_id: string;
      crew_member_id: string;
      week_start: string;
      overwrite_existing?: boolean;
    }): Promise<ActionResult> =>
      execute('apply_crew_template', {
        template_id: params.template_id,
        crew_member_id: params.crew_member_id,
        week_start: params.week_start,
        overwrite_existing: params.overwrite_existing ?? false,
      }),
    [execute]
  );

  // -------------------------------------------------------------------------
  // Return
  // -------------------------------------------------------------------------

  return {
    // State
    isLoading,
    error,

    // Actions
    verifyRecord,
    addRestPeriod,
    dismissWarning,
    acknowledgeWarning,
    signMonthlySignoff,
    createCrewTemplate,
    viewComplianceStatus,
    applyCrewTemplate,
  };
}

// ---------------------------------------------------------------------------
// useHoursOfRestPermissions Hook - DELEGATED TO CENTRALIZED SERVICE
// ---------------------------------------------------------------------------

import { useHoursOfRestPermissions as useCentralizedHoursOfRestPermissions } from '@/hooks/permissions/useHoursOfRestPermissions';

/**
 * useHoursOfRestPermissions
 *
 * Derives boolean capability flags from the current user's role.
 * DELEGATED TO CENTRALIZED SERVICE - reads from lens_matrix.json
 * Used to conditionally show (not disable) action buttons.
 */
export function useHoursOfRestPermissions(): HoursOfRestPermissions {
  const central = useCentralizedHoursOfRestPermissions();

  return {
    canVerify: central.canVerifyHoursOfRest,
    canAddPeriod: central.canAddRestPeriod,
    canDismissWarning: central.canDismissWarning,
    canAcknowledgeWarning: central.canAcknowledgeWarning,
    canSignMonthly: central.canSignMonthlySignoff,
    canCreateTemplate: central.canCreateCrewTemplate,
    canViewCompliance: central.canViewComplianceStatus,
    canApplyTemplate: central.canApplyCrewTemplate,
  };
}
