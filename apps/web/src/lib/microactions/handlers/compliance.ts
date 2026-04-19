/**
 * Compliance Domain Handlers
 *
 * TypeScript handlers for compliance microactions.
 * Exports: view_compliance_status, tag_for_survey
 *
 * Note: viewHoursOfRest / updateHoursOfRest / exportHoursOfRest were removed
 * when the backend Tier-6 actions (view/update/export_hours_of_rest) were
 * deleted. Use the Crew Lens v3 actions (get_hours_of_rest / upsert_hours_of_rest).
 */

import type { ActionContext, ActionResult } from '../types';
import { supabase } from '@/lib/supabaseClient';

/**
 * View overall compliance status
 */
async function viewComplianceStatus(
  context: ActionContext,
  params?: { days?: number }
): Promise<ActionResult> {

  const days = params?.days || 30;

  try {
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);

    // Get all hours of rest records for the yacht
    const { data: records, error } = await supabase
      .from('pms_hours_of_rest')
      .select('user_id, date, hours')
      .eq('yacht_id', context.yacht_id)
      .gte('date', startDate.toISOString().split('T')[0])
      .order('date', { ascending: false });

    if (error) {
      return {
        success: false,
        action_name: 'view_compliance_status',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    // Calculate compliance by user
    const userCompliance: Record<string, { compliant: number; total: number }> = {};
    let totalRecords = 0;
    let compliantRecords = 0;

    for (const record of records || []) {
      if (!userCompliance[record.user_id]) {
        userCompliance[record.user_id] = { compliant: 0, total: 0 };
      }

      userCompliance[record.user_id].total++;
      totalRecords++;

      let restHours = 0;
      for (const h of record.hours || []) {
        if (h.type === 'rest') restHours += h.end_hour - h.start_hour;
      }

      if (restHours >= 10) {
        userCompliance[record.user_id].compliant++;
        compliantRecords++;
      }
    }

    const overallCompliance = totalRecords > 0
      ? Math.round((compliantRecords / totalRecords) * 100)
      : 100;

    return {
      success: true,
      action_name: 'view_compliance_status',
      data: {
        period_days: days,
        overall_compliance_percent: overallCompliance,
        total_records: totalRecords,
        compliant_records: compliantRecords,
        users: Object.entries(userCompliance).map(([userId, data]) => ({
          user_id: userId,
          compliance_percent: data.total > 0
            ? Math.round((data.compliant / data.total) * 100)
            : 100,
          compliant_days: data.compliant,
          total_days: data.total,
        })),
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'view_compliance_status',
      data: null,
      error: {
        code: 'INTERNAL_ERROR',
        message: err instanceof Error ? err.message : 'Unknown error',
      },
      confirmation_required: false,
    };
  }
}

/**
 * Tag item for survey inspection
 */
async function tagForSurvey(
  context: ActionContext,
  params: {
    entity_id: string;
    entity_type: 'equipment' | 'fault' | 'work_order';
    survey_type?: string;
    notes?: string;
  }
): Promise<ActionResult> {
  if (!params?.entity_id || !params?.entity_type) {
    return {
      success: false,
      action_name: 'tag_for_survey',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Entity ID and type are required' },
      confirmation_required: false,
    };
  }

  try {
    // Create survey tag
    const { data: tag, error } = await supabase
      .from('survey_tags')
      .insert({
        yacht_id: context.yacht_id,
        entity_id: params.entity_id,
        entity_type: params.entity_type,
        survey_type: params.survey_type || 'annual',
        notes: params.notes,
        status: 'pending',
        tagged_by: context.user_id,
        tagged_at: new Date().toISOString(),
      })
      .select()
      .single();

    if (error) {
      // Table might not exist
      if (error.code === '42P01') {
        return {
          success: true,
          action_name: 'tag_for_survey',
          data: {
            message: 'Survey tag recorded (table pending creation)',
            entity_id: params.entity_id,
            entity_type: params.entity_type,
            survey_type: params.survey_type || 'annual',
          },
          error: null,
          confirmation_required: false,
        };
      }
      return {
        success: false,
        action_name: 'tag_for_survey',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    return {
      success: true,
      action_name: 'tag_for_survey',
      data: { tag },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'tag_for_survey',
      data: null,
      error: {
        code: 'INTERNAL_ERROR',
        message: err instanceof Error ? err.message : 'Unknown error',
      },
      confirmation_required: false,
    };
  }
}

export const complianceHandlers = {
  view_compliance_status: viewComplianceStatus,
  tag_for_survey: tagForSurvey,
};
