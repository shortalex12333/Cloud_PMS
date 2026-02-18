'use client';

/**
 * useHoursOfRestActions — Hours of Rest action hook (FE-03-03)
 *
 * Wires all HOR action registry calls to typed helper methods.
 * Uses the unified action API endpoint per the action router spec.
 *
 * Action IDs map 1:1 to registry.py keys:
 *   log_hours, upsert_hours, get_hours, create_signoff, sign_monthly,
 *   list_warnings, acknowledge_warning, create_template, apply_template
 *
 * Role-based access:
 *   - CREW: logs own hours, acknowledges own warnings, signs own monthly
 *   - HOD: can view department records, dismiss warnings, create signoffs
 *   - CAPTAIN: full access + can countersign all monthly sign-offs
 *
 * Role enforcement is at API level; visibility gates live in HoursOfRestLens
 * (hide, not disable — per UI_SPEC.md).
 */

import { useState, useCallback } from 'react';
import { useAuth } from '@/hooks/useAuth';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ActionResult {
  success: boolean;
  message?: string;
  data?: Record<string, unknown>;
  error?: string;
}

export interface HoursOfRestActionsState {
  isLoading: boolean;
  error: string | null;
}

// API URL — same origin Next.js API route proxied to Render backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * useHoursOfRestActions
 *
 * Returns typed action helpers for all hours-of-rest operations.
 * Each helper calls POST /v1/hours-of-rest/{endpoint} with JWT auth.
 *
 * @param userId - UUID of the crew member whose HOR records are in scope
 */
export function useHoursOfRestActions(userId: string) {
  const { user, session } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // Internal executor — wraps every action call
  // Injects yacht_id + user_id automatically (no repetition at call site)
  // -------------------------------------------------------------------------

  const execute = useCallback(
    async (endpoint: string, payload: Record<string, unknown>): Promise<ActionResult> => {
      if (!session?.access_token) {
        return { success: false, error: 'Not authenticated' };
      }

      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${session.access_token}`,
          },
          body: JSON.stringify({
            yacht_id: user?.yachtId,
            user_id: userId,
            ...payload,
          }),
        });

        const json = await response.json().catch(() => ({}));

        if (!response.ok) {
          const msg =
            (json as { error?: string; detail?: string }).error ||
            (json as { error?: string; detail?: string }).detail ||
            `Request failed (${response.status})`;
          setError(msg);
          return { success: false, error: msg };
        }

        return { success: true, ...(json as object) };
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Unknown error';
        setError(msg);
        return { success: false, error: msg };
      } finally {
        setIsLoading(false);
      }
    },
    [session, user, userId]
  );

  // -------------------------------------------------------------------------
  // Typed action helpers — one per registry action
  // -------------------------------------------------------------------------

  /**
   * log_hours — Crew member logs rest hours for a specific date.
   * Creates a new record if none exists for the date.
   */
  const logHours = useCallback(
    (
      recordDate: string,
      restPeriods: Array<{ start: string; end: string; hours: number }>,
      totalRestHours: number
    ) =>
      execute('/v1/hours-of-rest/log', {
        record_date: recordDate,
        rest_periods: restPeriods,
        total_rest_hours: totalRestHours,
      }),
    [execute]
  );

  /**
   * upsert_hours — Create or update rest hours for a date.
   * Idempotent — safe to call if record already exists.
   */
  const upsertHours = useCallback(
    (
      recordDate: string,
      restPeriods: Array<{ start: string; end: string; hours: number }>,
      totalRestHours: number
    ) =>
      execute('/v1/hours-of-rest/upsert', {
        record_date: recordDate,
        rest_periods: restPeriods,
        total_rest_hours: totalRestHours,
      }),
    [execute]
  );

  /**
   * get_hours — Fetch hours of rest records for a date range.
   */
  const getHours = useCallback(
    (startDate?: string, endDate?: string) =>
      execute('/v1/hours-of-rest/get', {
        start_date: startDate,
        end_date: endDate,
      }),
    [execute]
  );

  /**
   * create_signoff — HOD creates a monthly sign-off record for their department.
   */
  const createSignoff = useCallback(
    (month: string, department: string) =>
      execute('/v1/hours-of-rest/create-signoff', {
        month,
        department,
      }),
    [execute]
  );

  /**
   * sign_monthly — Sign the monthly sign-off record.
   * signature_level: 'crew' | 'hod' | 'captain'
   */
  const signMonthly = useCallback(
    (signoffId: string, signatureLevel: 'crew' | 'hod' | 'captain') =>
      execute('/v1/hours-of-rest/sign-monthly', {
        signoff_id: signoffId,
        signature_level: signatureLevel,
        signature_data: {
          signed_at: new Date().toISOString(),
          signature_type: 'electronic',
        },
      }),
    [execute]
  );

  /**
   * list_warnings — List STCW compliance warnings.
   * CREW sees own, HOD sees department, CAPTAIN sees all.
   */
  const listWarnings = useCallback(
    () => execute('/v1/hours-of-rest/list-warnings', {}),
    [execute]
  );

  /**
   * acknowledge_warning — Crew member acknowledges an STCW violation warning.
   * Required for compliance record — unacknowledged violations remain flagged.
   */
  const acknowledgeWarning = useCallback(
    (warningId: string) =>
      execute('/v1/hours-of-rest/acknowledge-warning', {
        warning_id: warningId,
      }),
    [execute]
  );

  /**
   * create_template — HOD+ creates a schedule template for repeated patterns.
   */
  const createTemplate = useCallback(
    (scheduleName: string, scheduleTemplate: Record<string, unknown>) =>
      execute('/v1/hours-of-rest/create-template', {
        schedule_name: scheduleName,
        schedule_template: scheduleTemplate,
      }),
    [execute]
  );

  /**
   * apply_template — HOD+ applies a schedule template to a week.
   */
  const applyTemplate = useCallback(
    (weekStartDate: string, templateId?: string) =>
      execute('/v1/hours-of-rest/apply-template', {
        week_start_date: weekStartDate,
        template_id: templateId,
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

    // Daily hours
    logHours,
    upsertHours,
    getHours,

    // Monthly sign-off
    createSignoff,
    signMonthly,

    // Warnings
    listWarnings,
    acknowledgeWarning,

    // Templates
    createTemplate,
    applyTemplate,
  };
}

// ---------------------------------------------------------------------------
// Role permission helpers
// ---------------------------------------------------------------------------

/** Roles with HOD-level or above access */
const HOD_ROLES = ['chief_engineer', 'eto', 'chief_officer', 'captain', 'manager'];

/** Roles allowed to sign off (captain-level — countersigns all) */
const CAPTAIN_ROLES = ['captain'];

/** Roles allowed to sign off as HOD */
const HOD_SIGNOFF_ROLES = ['chief_engineer', 'chief_officer', 'captain', 'manager'];

/** Roles that can log and acknowledge their own hours */
const LOG_ROLES = ['crew', 'chief_engineer', 'eto', 'chief_officer', 'captain', 'manager'];

/** Roles that can create/apply templates (HOD+) */
const TEMPLATE_ROLES = ['chief_engineer', 'chief_officer', 'captain', 'manager'];

export interface HoursOfRestPermissions {
  /** Can log hours (all authenticated crew) */
  canLogHours: boolean;
  /** Can acknowledge own STCW violation warnings */
  canAcknowledgeWarning: boolean;
  /** Can sign off the monthly sign-off record */
  canSignOff: boolean;
  /** Can create a monthly sign-off (HOD+) */
  canCreateSignoff: boolean;
  /** Can dismiss warnings (HOD+) */
  canDismissWarning: boolean;
  /** Can create/apply schedule templates (HOD+) */
  canManageTemplates: boolean;
  /** Can countersign as captain */
  canCaptainSign: boolean;
}

/**
 * useHoursOfRestPermissions
 *
 * Derives boolean capability flags from the current user's role.
 * Used to conditionally show (not disable) action buttons in HoursOfRestLens.
 */
export function useHoursOfRestPermissions(): HoursOfRestPermissions {
  const { user } = useAuth();
  const role = user?.role ?? '';

  return {
    canLogHours: LOG_ROLES.includes(role),
    canAcknowledgeWarning: LOG_ROLES.includes(role), // crew can acknowledge own
    canSignOff: LOG_ROLES.includes(role), // crew signs own monthly
    canCreateSignoff: HOD_SIGNOFF_ROLES.includes(role), // HOD creates signoff records
    canDismissWarning: HOD_ROLES.includes(role),
    canManageTemplates: TEMPLATE_ROLES.includes(role),
    canCaptainSign: CAPTAIN_ROLES.includes(role),
  };
}
