/**
 * Compliance Domain Handlers
 *
 * TypeScript handlers for compliance and hours of rest related microactions.
 */

import type { ActionContext, ActionResult } from '../types';
import { createClient } from '@/lib/supabaseClient';

/**
 * View hours of rest for a crew member
 */
export async function viewHoursOfRest(
  context: ActionContext,
  params?: { user_id?: string; date?: string }
): Promise<ActionResult> {
  const supabase = createClient();
  const userId = params?.user_id || context.user_id;
  const date = params?.date || new Date().toISOString().split('T')[0];

  try {
    // Get hours of rest record for the date
    const { data: horRecord, error } = await supabase
      .from('hours_of_rest')
      .select('*')
      .eq('yacht_id', context.yacht_id)
      .eq('user_id', userId)
      .eq('date', date)
      .single();

    if (error && error.code !== 'PGRST116') {
      // PGRST116 is "no rows returned"
      return {
        success: false,
        action_name: 'view_hours_of_rest',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    // Calculate compliance status
    let complianceStatus = 'COMPLIANT';
    let restHours = 0;
    let workHours = 0;

    if (horRecord?.hours) {
      for (const h of horRecord.hours) {
        if (h.type === 'rest') restHours += h.end_hour - h.start_hour;
        else workHours += h.end_hour - h.start_hour;
      }

      // MLC requirements: minimum 10 hours rest in 24-hour period
      if (restHours < 10) complianceStatus = 'NON_COMPLIANT';
      else if (restHours < 11) complianceStatus = 'WARNING';
    }

    return {
      success: true,
      action_name: 'view_hours_of_rest',
      data: {
        user_id: userId,
        date,
        record: horRecord,
        summary: {
          rest_hours: restHours,
          work_hours: workHours,
          compliance_status: complianceStatus,
        },
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'view_hours_of_rest',
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
 * Update hours of rest
 */
export async function updateHoursOfRest(
  context: ActionContext,
  params: {
    user_id: string;
    date: string;
    hours: Array<{
      start_hour: number;
      end_hour: number;
      type: 'work' | 'rest';
    }>;
  }
): Promise<ActionResult> {
  const supabase = createClient();

  if (!params?.user_id || !params?.date || !params?.hours) {
    return {
      success: false,
      action_name: 'update_hours_of_rest',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'User ID, date, and hours are required' },
      confirmation_required: false,
    };
  }

  try {
    // Upsert hours of rest record
    const { data: record, error } = await supabase
      .from('hours_of_rest')
      .upsert({
        yacht_id: context.yacht_id,
        user_id: params.user_id,
        date: params.date,
        hours: params.hours,
        updated_by: context.user_id,
        updated_at: new Date().toISOString(),
      })
      .select()
      .single();

    if (error) {
      return {
        success: false,
        action_name: 'update_hours_of_rest',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    return {
      success: true,
      action_name: 'update_hours_of_rest',
      data: { record },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'update_hours_of_rest',
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
 * Export hours of rest report
 */
export async function exportHoursOfRest(
  context: ActionContext,
  params?: {
    user_id?: string;
    start_date?: string;
    end_date?: string;
    format?: 'pdf' | 'csv' | 'xlsx';
  }
): Promise<ActionResult> {
  const supabase = createClient();
  const userId = params?.user_id || context.user_id;
  const format = params?.format || 'pdf';

  // Default to last 7 days
  const endDate = params?.end_date || new Date().toISOString().split('T')[0];
  const startDateObj = new Date();
  startDateObj.setDate(startDateObj.getDate() - 7);
  const startDate = params?.start_date || startDateObj.toISOString().split('T')[0];

  try {
    // Get hours of rest records for date range
    const { data: records, error } = await supabase
      .from('hours_of_rest')
      .select('*')
      .eq('yacht_id', context.yacht_id)
      .eq('user_id', userId)
      .gte('date', startDate)
      .lte('date', endDate)
      .order('date', { ascending: true });

    if (error) {
      return {
        success: false,
        action_name: 'export_hours_of_rest',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    // Calculate summary statistics
    let totalRestHours = 0;
    let totalWorkHours = 0;
    let nonCompliantDays = 0;

    for (const record of records || []) {
      let dayRest = 0;
      for (const h of record.hours || []) {
        const duration = h.end_hour - h.start_hour;
        if (h.type === 'rest') {
          totalRestHours += duration;
          dayRest += duration;
        } else {
          totalWorkHours += duration;
        }
      }
      if (dayRest < 10) nonCompliantDays++;
    }

    return {
      success: true,
      action_name: 'export_hours_of_rest',
      data: {
        user_id: userId,
        start_date: startDate,
        end_date: endDate,
        format,
        records: records || [],
        summary: {
          total_days: records?.length || 0,
          total_rest_hours: totalRestHours,
          total_work_hours: totalWorkHours,
          non_compliant_days: nonCompliantDays,
          average_rest_per_day: records?.length
            ? Math.round(totalRestHours / records.length * 10) / 10
            : 0,
        },
        export_url: `https://handover-export.onrender.com/api/v1/hor/export?yacht_id=${context.yacht_id}&user_id=${userId}&start=${startDate}&end=${endDate}&format=${format}`,
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'export_hours_of_rest',
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
 * View overall compliance status
 */
export async function viewComplianceStatus(
  context: ActionContext,
  params?: { days?: number }
): Promise<ActionResult> {
  const supabase = createClient();
  const days = params?.days || 30;

  try {
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);

    // Get all hours of rest records for the yacht
    const { data: records, error } = await supabase
      .from('hours_of_rest')
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
 * Get all compliance handlers for registration
 */
export const complianceHandlers = {
  view_hours_of_rest: viewHoursOfRest,
  update_hours_of_rest: updateHoursOfRest,
  export_hours_of_rest: exportHoursOfRest,
  view_compliance_status: viewComplianceStatus,
};
