/**
 * Hours of Rest (HOR) Domain Handlers - PRODUCTION COMPLIANT
 *
 * Migrated from direct Supabase calls to /v1/actions/execute
 * - Enforces Row-Level Security (RLS) via user-scoped clients
 * - Follows backend authority pattern (frontend renders what backend returns)
 * - Aligns with flow-based architecture (no URL fragments, action execution only)
 *
 * MLC 2006 / STCW Compliance:
 * - All actions go through audit log with signature tracking
 * - RLS enforces owner-only access (CREW sees only own records)
 * - HOD can view department, CAPTAIN can view all yacht records
 *
 * Backend Actions (12):
 * - get_hours_of_rest, upsert_hours_of_rest (Daily records)
 * - list_monthly_signoffs, get_monthly_signoff, create_monthly_signoff, sign_monthly_signoff (Signoffs)
 * - list_crew_templates, create_crew_template, apply_crew_template (Schedule templates)
 * - list_crew_warnings, acknowledge_warning, dismiss_warning (Compliance warnings)
 */

import type { ActionContext, ActionResult } from '../types';
import { executeAction } from '@/lib/actionClient';

// ============================================================================
// DAILY HOURS OF REST
// ============================================================================

/**
 * Get hours of rest records for a user
 *
 * Backend: get_hours_of_rest
 * RLS: Owner-only (CREW sees own), HOD sees department, CAPTAIN sees all
 */
export async function getHoursOfRest(
  context: ActionContext,
  params?: {
    user_id?: string;
    start_date?: string;
    end_date?: string;
  }
): Promise<ActionResult> {
  try {
    const result = await executeAction(
      'get_hours_of_rest',
      {
        yacht_id: context.yacht_id,
        user_id: context.user_id,
        role: context.user_role,
      },
      {
        yacht_id: context.yacht_id,
        user_id: params?.user_id || context.user_id,
        start_date: params?.start_date,
        end_date: params?.end_date,
      }
    );

    return {
      success: result.status === 'success',
      action_name: 'get_hours_of_rest',
      data: result.result || null,
      error: result.status === 'error' ? {
        code: result.error_code === 'not_found' ? 'NOT_FOUND' : 'INTERNAL_ERROR',
        message: result.message || 'Failed to get hours of rest',
      } : null,
      confirmation_required: false,
    };
  } catch (err: any) {
    return {
      success: false,
      action_name: 'get_hours_of_rest',
      data: null,
      error: {
        code: 'INTERNAL_ERROR',
        message: err.message || 'Failed to get hours of rest',
      },
      confirmation_required: false,
    };
  }
}

/**
 * Create or update hours of rest record
 *
 * Backend: upsert_hours_of_rest
 * RLS: Owner-only (CREW can only upsert own records)
 * Schema: record_date (ISO date), rest_periods [{start, end, hours}], total_rest_hours
 */
export async function upsertHoursOfRest(
  context: ActionContext,
  params: {
    record_date: string;
    rest_periods: Array<{
      start: string;  // "22:00"
      end: string;    // "06:00"
      hours: number;  // 8.0
    }>;
    total_rest_hours: number;
  }
): Promise<ActionResult> {
  // Validation
  if (!params?.record_date || !params?.rest_periods || params?.total_rest_hours === undefined) {
    return {
      success: false,
      action_name: 'upsert_hours_of_rest',
      data: null,
      error: {
        code: 'VALIDATION_ERROR',
        message: 'record_date, rest_periods, and total_rest_hours are required',
      },
      confirmation_required: false,
    };
  }

  try {
    const result = await executeAction(
      'upsert_hours_of_rest',
      {
        yacht_id: context.yacht_id,
        user_id: context.user_id,
        role: context.user_role,
      },
      {
        yacht_id: context.yacht_id,
        user_id: context.user_id,
        record_date: params.record_date,
        rest_periods: params.rest_periods,
        total_rest_hours: params.total_rest_hours,
      }
    );

    return {
      success: result.status === 'success',
      action_name: 'upsert_hours_of_rest',
      data: result.result || null,
      error: result.status === 'error' ? {
        code: 'INTERNAL_ERROR',
        message: result.message || 'Failed to upsert hours of rest',
      } : null,
      confirmation_required: false,
    };
  } catch (err: any) {
    return {
      success: false,
      action_name: 'upsert_hours_of_rest',
      data: null,
      error: {
        code: 'INTERNAL_ERROR',
        message: err.message || 'Failed to upsert hours of rest',
      },
      confirmation_required: false,
    };
  }
}

// ============================================================================
// MONTHLY SIGN-OFFS
// ============================================================================

/**
 * List monthly sign-offs
 *
 * Backend: list_monthly_signoffs
 * Returns all sign-offs for the yacht (RLS-filtered by role)
 */
export async function listMonthlySignoffs(
  context: ActionContext
): Promise<ActionResult> {
  try {
    const result = await executeAction(
      'list_monthly_signoffs',
      {
        yacht_id: context.yacht_id,
        user_id: context.user_id,
        role: context.user_role,
      },
      {
        yacht_id: context.yacht_id,
      }
    );

    return {
      success: result.status === 'success',
      action_name: 'list_monthly_signoffs',
      data: result.result || null,
      error: result.status === 'error' ? {
        code: 'INTERNAL_ERROR',
        message: result.message || 'Failed to list monthly signoffs',
      } : null,
      confirmation_required: false,
    };
  } catch (err: any) {
    return {
      success: false,
      action_name: 'list_monthly_signoffs',
      data: null,
      error: {
        code: 'INTERNAL_ERROR',
        message: err.message || 'Failed to list monthly signoffs',
      },
      confirmation_required: false,
    };
  }
}

/**
 * Get monthly sign-off details
 *
 * Backend: get_monthly_signoff
 * RLS: Owner can view own, HOD can view department, CAPTAIN can view all
 */
export async function getMonthlySignoff(
  context: ActionContext,
  params: {
    signoff_id: string;
  }
): Promise<ActionResult> {
  if (!params?.signoff_id) {
    return {
      success: false,
      action_name: 'get_monthly_signoff',
      data: null,
      error: {
        code: 'VALIDATION_ERROR',
        message: 'signoff_id is required',
      },
      confirmation_required: false,
    };
  }

  try {
    const result = await executeAction(
      'get_monthly_signoff',
      {
        yacht_id: context.yacht_id,
        user_id: context.user_id,
        role: context.user_role,
      },
      {
        yacht_id: context.yacht_id,
        signoff_id: params.signoff_id,
      }
    );

    return {
      success: result.status === 'success',
      action_name: 'get_monthly_signoff',
      data: result.result || null,
      error: result.status === 'error' ? {
        code: result.error_code === 'not_found' ? 'NOT_FOUND' : 'INTERNAL_ERROR',
        message: result.message || 'Failed to get monthly signoff',
      } : null,
      confirmation_required: false,
    };
  } catch (err: any) {
    return {
      success: false,
      action_name: 'get_monthly_signoff',
      data: null,
      error: {
        code: 'INTERNAL_ERROR',
        message: err.message || 'Failed to get monthly signoff',
      },
      confirmation_required: false,
    };
  }
}

/**
 * Create monthly sign-off
 *
 * Backend: create_monthly_signoff
 * RLS: CREW can create own, HOD can create for department
 */
export async function createMonthlySignoff(
  context: ActionContext,
  params: {
    month: string;        // "2026-02"
    department: string;   // "deck", "engine", "interior"
  }
): Promise<ActionResult> {
  if (!params?.month || !params?.department) {
    return {
      success: false,
      action_name: 'create_monthly_signoff',
      data: null,
      error: {
        code: 'VALIDATION_ERROR',
        message: 'month and department are required',
      },
      confirmation_required: false,
    };
  }

  try {
    const result = await executeAction(
      'create_monthly_signoff',
      {
        yacht_id: context.yacht_id,
        user_id: context.user_id,
        role: context.user_role,
      },
      {
        yacht_id: context.yacht_id,
        user_id: context.user_id,
        month: params.month,
        department: params.department,
      }
    );

    return {
      success: result.status === 'success',
      action_name: 'create_monthly_signoff',
      data: result.result || null,
      error: result.status === 'error' ? {
        code: 'INTERNAL_ERROR',
        message: result.message || 'Failed to create monthly signoff',
      } : null,
      confirmation_required: false,
    };
  } catch (err: any) {
    return {
      success: false,
      action_name: 'create_monthly_signoff',
      data: null,
      error: {
        code: 'INTERNAL_ERROR',
        message: err.message || 'Failed to create monthly signoff',
      },
      confirmation_required: false,
    };
  }
}

/**
 * Sign monthly sign-off (SIGNED action)
 *
 * Backend: sign_monthly_signoff
 * RLS: Owner signs own, HOD signs department, CAPTAIN signs all
 * Audit: Signature written to audit log with timestamp + user + role + type
 */
export async function signMonthlySignoff(
  context: ActionContext,
  params: {
    signoff_id: string;
    signature_level: 'crew' | 'hod' | 'captain';
    signature_data: {
      signed_at: string;      // ISO timestamp
      signature_type: 'electronic' | 'wet' | 'delegated';
      signature_hash?: string;
    };
  }
): Promise<ActionResult> {
  if (!params?.signoff_id || !params?.signature_level || !params?.signature_data) {
    return {
      success: false,
      action_name: 'sign_monthly_signoff',
      data: null,
      error: {
        code: 'VALIDATION_ERROR',
        message: 'signoff_id, signature_level, and signature_data are required',
      },
      confirmation_required: false,
    };
  }

  try {
    const result = await executeAction(
      'sign_monthly_signoff',
      {
        yacht_id: context.yacht_id,
        user_id: context.user_id,
        role: context.user_role,
      },
      {
        yacht_id: context.yacht_id,
        signoff_id: params.signoff_id,
        signature_level: params.signature_level,
        signature_data: params.signature_data,
      }
    );

    return {
      success: result.status === 'success',
      action_name: 'sign_monthly_signoff',
      data: result.result || null,
      error: result.status === 'error' ? {
        code: 'INTERNAL_ERROR',
        message: result.message || 'Failed to sign monthly signoff',
      } : null,
      confirmation_required: false,
    };
  } catch (err: any) {
    return {
      success: false,
      action_name: 'sign_monthly_signoff',
      data: null,
      error: {
        code: 'INTERNAL_ERROR',
        message: err.message || 'Failed to sign monthly signoff',
      },
      confirmation_required: false,
    };
  }
}

// ============================================================================
// SCHEDULE TEMPLATES
// ============================================================================

/**
 * List schedule templates
 *
 * Backend: list_crew_templates
 * Returns all templates for the yacht
 */
export async function listCrewTemplates(
  context: ActionContext
): Promise<ActionResult> {
  try {
    const result = await executeAction(
      'list_crew_templates',
      {
        yacht_id: context.yacht_id,
        user_id: context.user_id,
        role: context.user_role,
      },
      {
        yacht_id: context.yacht_id,
      }
    );

    return {
      success: result.status === 'success',
      action_name: 'list_crew_templates',
      data: result.result || null,
      error: result.status === 'error' ? {
        code: 'INTERNAL_ERROR',
        message: result.message || 'Failed to list crew templates',
      } : null,
      confirmation_required: false,
    };
  } catch (err: any) {
    return {
      success: false,
      action_name: 'list_crew_templates',
      data: null,
      error: {
        code: 'INTERNAL_ERROR',
        message: err.message || 'Failed to list crew templates',
      },
      confirmation_required: false,
    };
  }
}

/**
 * Create schedule template
 *
 * Backend: create_crew_template
 * RLS: HOD+ can create templates
 */
export async function createCrewTemplate(
  context: ActionContext,
  params: {
    schedule_name: string;
    schedule_template: Record<string, any>;  // Template structure defined by backend
  }
): Promise<ActionResult> {
  if (!params?.schedule_name || !params?.schedule_template) {
    return {
      success: false,
      action_name: 'create_crew_template',
      data: null,
      error: {
        code: 'VALIDATION_ERROR',
        message: 'schedule_name and schedule_template are required',
      },
      confirmation_required: false,
    };
  }

  try {
    const result = await executeAction(
      'create_crew_template',
      {
        yacht_id: context.yacht_id,
        user_id: context.user_id,
        role: context.user_role,
      },
      {
        yacht_id: context.yacht_id,
        user_id: context.user_id,
        schedule_name: params.schedule_name,
        schedule_template: params.schedule_template,
      }
    );

    return {
      success: result.status === 'success',
      action_name: 'create_crew_template',
      data: result.result || null,
      error: result.status === 'error' ? {
        code: 'INTERNAL_ERROR',
        message: result.message || 'Failed to create crew template',
      } : null,
      confirmation_required: false,
    };
  } catch (err: any) {
    return {
      success: false,
      action_name: 'create_crew_template',
      data: null,
      error: {
        code: 'INTERNAL_ERROR',
        message: err.message || 'Failed to create crew template',
      },
      confirmation_required: false,
    };
  }
}

/**
 * Apply schedule template to a week
 *
 * Backend: apply_crew_template
 * RLS: HOD+ can apply templates
 */
export async function applyCrewTemplate(
  context: ActionContext,
  params: {
    week_start_date: string;  // ISO date of Monday
    template_id?: string;     // Optional template to apply
  }
): Promise<ActionResult> {
  if (!params?.week_start_date) {
    return {
      success: false,
      action_name: 'apply_crew_template',
      data: null,
      error: {
        code: 'VALIDATION_ERROR',
        message: 'week_start_date is required',
      },
      confirmation_required: false,
    };
  }

  try {
    const result = await executeAction(
      'apply_crew_template',
      {
        yacht_id: context.yacht_id,
        user_id: context.user_id,
        role: context.user_role,
      },
      {
        yacht_id: context.yacht_id,
        user_id: context.user_id,
        week_start_date: params.week_start_date,
        template_id: params.template_id,
      }
    );

    return {
      success: result.status === 'success',
      action_name: 'apply_crew_template',
      data: result.result || null,
      error: result.status === 'error' ? {
        code: 'INTERNAL_ERROR',
        message: result.message || 'Failed to apply crew template',
      } : null,
      confirmation_required: false,
    };
  } catch (err: any) {
    return {
      success: false,
      action_name: 'apply_crew_template',
      data: null,
      error: {
        code: 'INTERNAL_ERROR',
        message: err.message || 'Failed to apply crew template',
      },
      confirmation_required: false,
    };
  }
}

// ============================================================================
// COMPLIANCE WARNINGS
// ============================================================================

/**
 * List compliance warnings
 *
 * Backend: list_crew_warnings
 * RLS: CREW sees own warnings, HOD sees department, CAPTAIN sees all
 */
export async function listCrewWarnings(
  context: ActionContext
): Promise<ActionResult> {
  try {
    const result = await executeAction(
      'list_crew_warnings',
      {
        yacht_id: context.yacht_id,
        user_id: context.user_id,
        role: context.user_role,
      },
      {
        yacht_id: context.yacht_id,
      }
    );

    return {
      success: result.status === 'success',
      action_name: 'list_crew_warnings',
      data: result.result || null,
      error: result.status === 'error' ? {
        code: 'INTERNAL_ERROR',
        message: result.message || 'Failed to list crew warnings',
      } : null,
      confirmation_required: false,
    };
  } catch (err: any) {
    return {
      success: false,
      action_name: 'list_crew_warnings',
      data: null,
      error: {
        code: 'INTERNAL_ERROR',
        message: err.message || 'Failed to list crew warnings',
      },
      confirmation_required: false,
    };
  }
}

/**
 * Acknowledge warning
 *
 * Backend: acknowledge_warning
 * RLS: CREW can acknowledge own warnings
 */
export async function acknowledgeWarning(
  context: ActionContext,
  params: {
    warning_id: string;
  }
): Promise<ActionResult> {
  if (!params?.warning_id) {
    return {
      success: false,
      action_name: 'acknowledge_warning',
      data: null,
      error: {
        code: 'VALIDATION_ERROR',
        message: 'warning_id is required',
      },
      confirmation_required: false,
    };
  }

  try {
    const result = await executeAction(
      'acknowledge_warning',
      {
        yacht_id: context.yacht_id,
        user_id: context.user_id,
        role: context.user_role,
      },
      {
        yacht_id: context.yacht_id,
        user_id: context.user_id,
        warning_id: params.warning_id,
      }
    );

    return {
      success: result.status === 'success',
      action_name: 'acknowledge_warning',
      data: result.result || null,
      error: result.status === 'error' ? {
        code: 'INTERNAL_ERROR',
        message: result.message || 'Failed to acknowledge warning',
      } : null,
      confirmation_required: false,
    };
  } catch (err: any) {
    return {
      success: false,
      action_name: 'acknowledge_warning',
      data: null,
      error: {
        code: 'INTERNAL_ERROR',
        message: err.message || 'Failed to acknowledge warning',
      },
      confirmation_required: false,
    };
  }
}

/**
 * Dismiss warning (SIGNED action - HOD+ only)
 *
 * Backend: dismiss_warning
 * RLS: HOD can dismiss department warnings, CAPTAIN can dismiss all
 * Audit: Signature written to audit log
 */
export async function dismissWarning(
  context: ActionContext,
  params: {
    warning_id: string;
    hod_justification: string;
    dismissed_by_role: string;
  }
): Promise<ActionResult> {
  if (!params?.warning_id || !params?.hod_justification || !params?.dismissed_by_role) {
    return {
      success: false,
      action_name: 'dismiss_warning',
      data: null,
      error: {
        code: 'VALIDATION_ERROR',
        message: 'warning_id, hod_justification, and dismissed_by_role are required',
      },
      confirmation_required: false,
    };
  }

  try {
    const result = await executeAction(
      'dismiss_warning',
      {
        yacht_id: context.yacht_id,
        user_id: context.user_id,
        role: context.user_role,
      },
      {
        yacht_id: context.yacht_id,
        user_id: context.user_id,
        warning_id: params.warning_id,
        hod_justification: params.hod_justification,
        dismissed_by_role: params.dismissed_by_role,
      }
    );

    return {
      success: result.status === 'success',
      action_name: 'dismiss_warning',
      data: result.result || null,
      error: result.status === 'error' ? {
        code: 'INTERNAL_ERROR',
        message: result.message || 'Failed to dismiss warning',
      } : null,
      confirmation_required: false,
    };
  } catch (err: any) {
    return {
      success: false,
      action_name: 'dismiss_warning',
      data: null,
      error: {
        code: 'INTERNAL_ERROR',
        message: err.message || 'Failed to dismiss warning',
      },
      confirmation_required: false,
    };
  }
}

// ============================================================================
// HANDLER REGISTRY
// ============================================================================

/**
 * Export all HOR handlers for registration with action router
 */
export const hoursOfRestHandlers = {
  // Daily records
  get_hours_of_rest: getHoursOfRest,
  upsert_hours_of_rest: upsertHoursOfRest,

  // Monthly signoffs
  list_monthly_signoffs: listMonthlySignoffs,
  get_monthly_signoff: getMonthlySignoff,
  create_monthly_signoff: createMonthlySignoff,
  sign_monthly_signoff: signMonthlySignoff,

  // Schedule templates
  list_crew_templates: listCrewTemplates,
  create_crew_template: createCrewTemplate,
  apply_crew_template: applyCrewTemplate,

  // Compliance warnings
  list_crew_warnings: listCrewWarnings,
  acknowledge_warning: acknowledgeWarning,
  dismiss_warning: dismissWarning,
};
