/**
 * Work Order Domain Handlers
 *
 * TypeScript handlers for work order-related microactions.
 */

import type { ActionContext, ActionResult } from '../types';
import { createClient } from '@/lib/supabaseClient';

interface WorkOrderData {
  id: string;
  yacht_id: string;
  equipment_id?: string;
  fault_id?: string;
  title: string;
  description?: string;
  status: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  due_date?: string;
  assigned_to?: string;
  completed_at?: string;
  created_at: string;
  is_overdue?: boolean;
  days_open?: number;
  allowed_transitions?: string[];
}

// Status flow for validation
const STATUS_FLOW: Record<string, string[]> = {
  draft: ['open'],
  open: ['in_progress', 'cancelled'],
  in_progress: ['pending_parts', 'completed', 'cancelled'],
  pending_parts: ['in_progress', 'cancelled'],
  completed: ['closed'],
  closed: [],
  cancelled: [],
};

/**
 * Check if work order is overdue
 */
function isOverdue(wo: WorkOrderData): boolean {
  if (['completed', 'closed', 'cancelled'].includes(wo.status)) {
    return false;
  }
  if (!wo.due_date) return false;

  try {
    const due = new Date(wo.due_date);
    return new Date() > due;
  } catch {
    return false;
  }
}

/**
 * Calculate days work order has been open
 */
function calculateDaysOpen(wo: WorkOrderData): number {
  if (!wo.created_at) return 0;

  try {
    const created = new Date(wo.created_at);
    const end = wo.completed_at ? new Date(wo.completed_at) : new Date();
    return Math.floor((end.getTime() - created.getTime()) / (1000 * 60 * 60 * 24));
  } catch {
    return 0;
  }
}

/**
 * View work order details
 */
export async function viewWorkOrder(
  context: ActionContext,
  params?: { work_order_id?: string }
): Promise<ActionResult> {
  const supabase = createClient();
  const workOrderId = params?.work_order_id || context.entity_id;

  if (!workOrderId) {
    return {
      success: false,
      action_name: 'view_work_order',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Work order ID is required' },
      confirmation_required: false,
    };
  }

  try {
    const { data: wo, error } = await supabase
      .from('pms_work_orders')
      .select('*')
      .eq('yacht_id', context.yacht_id)
      .eq('id', workOrderId)
      .single();

    if (error || !wo) {
      return {
        success: false,
        action_name: 'view_work_order',
        data: null,
        error: { code: 'NOT_FOUND', message: `Work order not found: ${workOrderId}` },
        confirmation_required: false,
      };
    }

    // Add computed fields
    const enrichedWo: WorkOrderData = {
      ...wo,
      is_overdue: isOverdue(wo),
      days_open: calculateDaysOpen(wo),
      allowed_transitions: STATUS_FLOW[wo.status] || [],
    };

    // Get checklist progress
    let checklistProgress = { completed: 0, total: 0, percent: 0 };
    try {
      const { data: items } = await supabase
        .from('checklist_items')
        .select('is_completed')
        .eq('work_order_id', workOrderId);

      if (items) {
        const completed = items.filter((i) => i.is_completed).length;
        checklistProgress = {
          completed,
          total: items.length,
          percent: items.length > 0 ? Math.round((completed / items.length) * 100) : 0,
        };
      }
    } catch {
      // Checklist table may not exist
    }

    // Get parts count
    let partsCount = 0;
    try {
      const { count } = await supabase
        .from('work_order_parts')
        .select('id', { count: 'exact', head: true })
        .eq('work_order_id', workOrderId);
      partsCount = count || 0;
    } catch {
      // Parts table may not exist
    }

    return {
      success: true,
      action_name: 'view_work_order',
      data: {
        work_order: enrichedWo,
        checklist_progress: checklistProgress,
        parts_count: partsCount,
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'view_work_order',
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
 * View work order history (audit log)
 */
export async function viewWorkOrderHistory(
  context: ActionContext,
  params?: { work_order_id?: string; offset?: number; limit?: number }
): Promise<ActionResult> {
  const supabase = createClient();
  const workOrderId = params?.work_order_id || context.entity_id;
  const offset = params?.offset || 0;
  const limit = params?.limit || 50;

  if (!workOrderId) {
    return {
      success: false,
      action_name: 'view_work_order_history',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Work order ID is required' },
      confirmation_required: false,
    };
  }

  try {
    // Try to query audit log
    let history: Array<{
      id: string;
      action: string;
      changes: Array<{ field: string; from: unknown; to: unknown }>;
      user_name: string;
      timestamp: string;
    }> = [];
    let totalCount = 0;

    try {
      const { data, count, error } = await supabase
        .from('audit_log')
        .select('id, action, old_values, new_values, created_at, user_id', {
          count: 'exact',
        })
        .eq('entity_type', 'work_order')
        .eq('entity_id', workOrderId)
        .order('created_at', { ascending: false })
        .range(offset, offset + limit - 1);

      if (!error && data) {
        history = data.map((entry) => ({
          id: entry.id,
          action: entry.action,
          changes: formatChanges(entry.old_values, entry.new_values),
          user_name: 'System', // Simplified - no FK join
          timestamp: entry.created_at,
        }));
        totalCount = count || data.length;
      }
    } catch {
      // Audit log table may not exist
    }

    return {
      success: true,
      action_name: 'view_work_order_history',
      data: {
        work_order_id: workOrderId,
        history,
        message: history.length === 0 ? 'Audit log not configured' : undefined,
        pagination: { offset, limit, total: totalCount },
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'view_work_order_history',
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
 * Format change diff for display
 */
function formatChanges(
  oldValues: Record<string, unknown> | null,
  newValues: Record<string, unknown> | null
): Array<{ field: string; from: unknown; to: unknown }> {
  const changes: Array<{ field: string; from: unknown; to: unknown }> = [];
  const old = oldValues || {};
  const newVals = newValues || {};
  const allKeys = new Set([...Object.keys(old), ...Object.keys(newVals)]);

  for (const key of allKeys) {
    if (old[key] !== newVals[key]) {
      changes.push({ field: key, from: old[key], to: newVals[key] });
    }
  }

  return changes;
}

/**
 * Create a new work order
 */
export async function createWorkOrder(
  context: ActionContext,
  params: {
    title: string;
    description?: string;
    equipment_id?: string;
    priority?: 'low' | 'medium' | 'high' | 'critical';
    due_date?: string;
    assignee_id?: string;
  }
): Promise<ActionResult> {
  const supabase = createClient();

  if (!params?.title) {
    return {
      success: false,
      action_name: 'create_work_order',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Title is required' },
      confirmation_required: false,
    };
  }

  try {
    const { data: workOrder, error } = await supabase
      .from('pms_work_orders')
      .insert({
        yacht_id: context.yacht_id,
        title: params.title,
        description: params.description,
        equipment_id: params.equipment_id,
        priority: params.priority || 'medium',
        due_date: params.due_date,
        assigned_to: params.assignee_id,
        status: 'draft',
        created_by: context.user_id,
      })
      .select()
      .single();

    if (error) {
      return {
        success: false,
        action_name: 'create_work_order',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    return {
      success: true,
      action_name: 'create_work_order',
      data: { work_order: workOrder },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'create_work_order',
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
 * Mark work order as complete
 */
export async function markWorkOrderComplete(
  context: ActionContext,
  params: {
    work_order_id: string;
    completion_notes?: string;
    parts_used?: Array<{ part_id: string; quantity: number }>;
  }
): Promise<ActionResult> {
  const supabase = createClient();

  if (!params?.work_order_id) {
    return {
      success: false,
      action_name: 'mark_work_order_complete',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Work order ID is required' },
      confirmation_required: false,
    };
  }

  try {
    // Verify work order exists and can be completed
    const { data: wo, error: fetchError } = await supabase
      .from('pms_work_orders')
      .select('id, status')
      .eq('id', params.work_order_id)
      .single();

    if (fetchError || !wo) {
      return {
        success: false,
        action_name: 'mark_work_order_complete',
        data: null,
        error: { code: 'NOT_FOUND', message: `Work order not found: ${params.work_order_id}` },
        confirmation_required: false,
      };
    }

    const allowedTransitions = STATUS_FLOW[wo.status] || [];
    if (!allowedTransitions.includes('completed')) {
      return {
        success: false,
        action_name: 'mark_work_order_complete',
        data: null,
        error: {
          code: 'VALIDATION_ERROR',
          message: `Cannot complete work order in status: ${wo.status}`,
        },
        confirmation_required: false,
      };
    }

    // Update work order
    const { data: updated, error: updateError } = await supabase
      .from('pms_work_orders')
      .update({
        status: 'completed',
        completed_at: new Date().toISOString(),
        completion_notes: params.completion_notes,
      })
      .eq('id', params.work_order_id)
      .select()
      .single();

    if (updateError) {
      return {
        success: false,
        action_name: 'mark_work_order_complete',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: updateError.message },
        confirmation_required: false,
      };
    }

    return {
      success: true,
      action_name: 'mark_work_order_complete',
      data: { work_order: updated },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'mark_work_order_complete',
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
 * Add note to work order
 */
export async function addWorkOrderNote(
  context: ActionContext,
  params: { work_order_id: string; note_text: string }
): Promise<ActionResult> {
  const supabase = createClient();

  if (!params?.work_order_id || !params?.note_text) {
    return {
      success: false,
      action_name: 'add_work_order_note',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Work order ID and note text are required' },
      confirmation_required: false,
    };
  }

  try {
    const { data, error } = await supabase
      .from('notes')
      .insert({
        entity_type: 'work_order',
        entity_id: params.work_order_id,
        content: params.note_text,
        created_by: context.user_id,
        yacht_id: context.yacht_id,
      })
      .select()
      .single();

    if (error) {
      return {
        success: false,
        action_name: 'add_work_order_note',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    return {
      success: true,
      action_name: 'add_work_order_note',
      data: { note: data },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'add_work_order_note',
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
 * Assign work order to user
 */
export async function assignWorkOrder(
  context: ActionContext,
  params: { work_order_id: string; assignee_id: string }
): Promise<ActionResult> {
  const supabase = createClient();

  if (!params?.work_order_id || !params?.assignee_id) {
    return {
      success: false,
      action_name: 'assign_work_order',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Work order ID and assignee ID are required' },
      confirmation_required: false,
    };
  }

  try {
    const { data, error } = await supabase
      .from('pms_work_orders')
      .update({ assigned_to: params.assignee_id })
      .eq('id', params.work_order_id)
      .select()
      .single();

    if (error) {
      return {
        success: false,
        action_name: 'assign_work_order',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    return {
      success: true,
      action_name: 'assign_work_order',
      data: { work_order: data },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'assign_work_order',
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
 * Get all work order handlers for registration
 */
export const workOrderHandlers = {
  view_work_order: viewWorkOrder,
  view_work_order_history: viewWorkOrderHistory,
  create_work_order: createWorkOrder,
  mark_work_order_complete: markWorkOrderComplete,
  add_work_order_note: addWorkOrderNote,
  assign_work_order: assignWorkOrder,
};
