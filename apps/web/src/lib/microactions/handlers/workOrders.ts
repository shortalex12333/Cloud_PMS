/**
 * Work Order Domain Handlers
 *
 * TypeScript handlers for work order-related microactions.
 */

import type { ActionContext, ActionResult } from '../types';
import { supabase } from '@/lib/supabaseClient';

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
        .from('pms_checklist_items')
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
        .from('pms_work_order_parts')
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
        .from('pms_audit_log')
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
      .from('pms_notes')
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
 * Add photo to work order
 */
export async function addWorkOrderPhoto(
  context: ActionContext,
  params: { work_order_id: string; photo_url: string; caption?: string }
): Promise<ActionResult> {
  if (!params?.work_order_id || !params?.photo_url) {
    return {
      success: false,
      action_name: 'add_work_order_photo',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Work order ID and photo URL are required' },
      confirmation_required: false,
    };
  }

  try {
    // Verify work order exists and is not closed
    const { data: wo, error: woError } = await supabase
      .from('pms_work_orders')
      .select('id, status')
      .eq('id', params.work_order_id)
      .eq('yacht_id', context.yacht_id)
      .single();

    if (woError || !wo) {
      return {
        success: false,
        action_name: 'add_work_order_photo',
        data: null,
        error: { code: 'NOT_FOUND', message: `Work order not found: ${params.work_order_id}` },
        confirmation_required: false,
      };
    }

    if (['completed', 'closed', 'cancelled'].includes(wo.status)) {
      return {
        success: false,
        action_name: 'add_work_order_photo',
        data: null,
        error: { code: 'VALIDATION_ERROR', message: 'Cannot add photo to closed work order' },
        confirmation_required: false,
      };
    }

    // Add photo attachment
    const { data, error } = await supabase
      .from('pms_attachments')
      .insert({
        entity_type: 'work_order',
        entity_id: params.work_order_id,
        storage_path: params.photo_url,
        filename: params.caption || 'work_order_photo.jpg',
        mime_type: 'image/jpeg',
        category: 'photo',
        uploaded_by: context.user_id,
        yacht_id: context.yacht_id,
      })
      .select()
      .single();

    if (error) {
      return {
        success: false,
        action_name: 'add_work_order_photo',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    return {
      success: true,
      action_name: 'add_work_order_photo',
      data: { attachment: data },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'add_work_order_photo',
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
 * Add parts to work order
 */
export async function addPartsToWorkOrder(
  context: ActionContext,
  params: { work_order_id: string; part_id: string; quantity: number; notes?: string }
): Promise<ActionResult> {
  if (!params?.work_order_id || !params?.part_id || !params?.quantity) {
    return {
      success: false,
      action_name: 'add_parts_to_work_order',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Work order ID, part ID, and quantity are required' },
      confirmation_required: false,
    };
  }

  if (params.quantity <= 0) {
    return {
      success: false,
      action_name: 'add_parts_to_work_order',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Quantity must be positive' },
      confirmation_required: false,
    };
  }

  try {
    // Verify work order exists and is not closed
    const { data: wo, error: woError } = await supabase
      .from('pms_work_orders')
      .select('id, wo_number, status')
      .eq('id', params.work_order_id)
      .eq('yacht_id', context.yacht_id)
      .single();

    if (woError || !wo) {
      return {
        success: false,
        action_name: 'add_parts_to_work_order',
        data: null,
        error: { code: 'NOT_FOUND', message: `Work order not found: ${params.work_order_id}` },
        confirmation_required: false,
      };
    }

    if (['completed', 'closed', 'cancelled'].includes(wo.status)) {
      return {
        success: false,
        action_name: 'add_parts_to_work_order',
        data: null,
        error: { code: 'VALIDATION_ERROR', message: 'Cannot add parts to closed work order' },
        confirmation_required: false,
      };
    }

    // Verify part exists
    const { data: part, error: partError } = await supabase
      .from('pms_parts')
      .select('id, name, part_number, quantity_on_hand, minimum_quantity')
      .eq('id', params.part_id)
      .eq('yacht_id', context.yacht_id)
      .single();

    if (partError || !part) {
      return {
        success: false,
        action_name: 'add_parts_to_work_order',
        data: null,
        error: { code: 'NOT_FOUND', message: `Part not found: ${params.part_id}` },
        confirmation_required: false,
      };
    }

    // Check if part already exists on this WO
    const { data: existing } = await supabase
      .from('pms_work_order_parts')
      .select('id, quantity')
      .eq('work_order_id', params.work_order_id)
      .eq('part_id', params.part_id)
      .single();

    let woPart;
    if (existing) {
      // Update existing entry
      const { data, error } = await supabase
        .from('pms_work_order_parts')
        .update({
          quantity: existing.quantity + params.quantity,
          notes: params.notes,
          updated_at: new Date().toISOString(),
        })
        .eq('id', existing.id)
        .select()
        .single();

      if (error) {
        return {
          success: false,
          action_name: 'add_parts_to_work_order',
          data: null,
          error: { code: 'INTERNAL_ERROR', message: error.message },
          confirmation_required: false,
        };
      }
      woPart = data;
    } else {
      // Create new entry
      const { data, error } = await supabase
        .from('pms_work_order_parts')
        .insert({
          work_order_id: params.work_order_id,
          part_id: params.part_id,
          quantity: params.quantity,
          notes: params.notes,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        })
        .select()
        .single();

      if (error) {
        return {
          success: false,
          action_name: 'add_parts_to_work_order',
          data: null,
          error: { code: 'INTERNAL_ERROR', message: error.message },
          confirmation_required: false,
        };
      }
      woPart = data;
    }

    // Check stock warning
    const stockAvailable = part.quantity_on_hand || 0;
    const minQty = part.minimum_quantity || 0;
    const stockWarning = stockAvailable <= minQty || stockAvailable < params.quantity;

    return {
      success: true,
      action_name: 'add_parts_to_work_order',
      data: {
        work_order_part: {
          ...woPart,
          part_name: part.name,
          part_number: part.part_number,
        },
        stock_warning: stockWarning,
        stock_available: stockAvailable,
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'add_parts_to_work_order',
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
 * View work order checklist
 */
export async function viewWorkOrderChecklist(
  context: ActionContext,
  params?: { work_order_id?: string }
): Promise<ActionResult> {
  const workOrderId = params?.work_order_id || context.entity_id;

  if (!workOrderId) {
    return {
      success: false,
      action_name: 'view_work_order_checklist',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Work order ID is required' },
      confirmation_required: false,
    };
  }

  try {
    // Get checklist items
    let items: Array<{
      id: string;
      description: string;
      is_completed: boolean;
      completed_at?: string;
      completed_by?: string;
      notes?: string;
      sequence: number;
    }> = [];

    try {
      const { data } = await supabase
        .from('pms_checklist_items')
        .select('id, description, is_completed, completed_at, completed_by, notes, sequence')
        .eq('work_order_id', workOrderId)
        .order('sequence');

      items = data || [];
    } catch {
      // Table may not exist
    }

    const completed = items.filter((i) => i.is_completed).length;
    const total = items.length;

    return {
      success: true,
      action_name: 'view_work_order_checklist',
      data: {
        work_order_id: workOrderId,
        checklist: items,
        progress: {
          completed,
          total,
          percent: total > 0 ? Math.round((completed / total) * 100) : 0,
        },
        message: items.length === 0 ? 'No checklist items configured' : undefined,
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'view_work_order_checklist',
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
 * Mark checklist item complete
 */
export async function markChecklistItemComplete(
  context: ActionContext,
  params: { checklist_item_id: string; notes?: string }
): Promise<ActionResult> {
  if (!params?.checklist_item_id) {
    return {
      success: false,
      action_name: 'mark_checklist_item_complete',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Checklist item ID is required' },
      confirmation_required: false,
    };
  }

  try {
    const { data, error } = await supabase
      .from('pms_checklist_items')
      .update({
        is_completed: true,
        completed_at: new Date().toISOString(),
        completed_by: context.user_id,
        notes: params.notes,
      })
      .eq('id', params.checklist_item_id)
      .select()
      .single();

    if (error) {
      return {
        success: false,
        action_name: 'mark_checklist_item_complete',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    return {
      success: true,
      action_name: 'mark_checklist_item_complete',
      data: { checklist_item: data },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'mark_checklist_item_complete',
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
 * Add note to checklist item
 */
export async function addChecklistNote(
  context: ActionContext,
  params: { checklist_item_id: string; note_text: string }
): Promise<ActionResult> {
  if (!params?.checklist_item_id || !params?.note_text) {
    return {
      success: false,
      action_name: 'add_checklist_note',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Checklist item ID and note text are required' },
      confirmation_required: false,
    };
  }

  try {
    const { data, error } = await supabase
      .from('pms_notes')
      .insert({
        entity_type: 'checklist_item',
        entity_id: params.checklist_item_id,
        content: params.note_text,
        created_by: context.user_id,
        yacht_id: context.yacht_id,
      })
      .select()
      .single();

    if (error) {
      return {
        success: false,
        action_name: 'add_checklist_note',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    return {
      success: true,
      action_name: 'add_checklist_note',
      data: { note: data },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'add_checklist_note',
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
 * Add photo to checklist item
 */
export async function addChecklistPhoto(
  context: ActionContext,
  params: { checklist_item_id: string; photo_url: string; caption?: string }
): Promise<ActionResult> {
  if (!params?.checklist_item_id || !params?.photo_url) {
    return {
      success: false,
      action_name: 'add_checklist_photo',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Checklist item ID and photo URL are required' },
      confirmation_required: false,
    };
  }

  try {
    const { data, error } = await supabase
      .from('pms_attachments')
      .insert({
        entity_type: 'checklist_item',
        entity_id: params.checklist_item_id,
        storage_path: params.photo_url,
        filename: params.caption || 'checklist_photo.jpg',
        mime_type: 'image/jpeg',
        category: 'photo',
        uploaded_by: context.user_id,
        yacht_id: context.yacht_id,
      })
      .select()
      .single();

    if (error) {
      return {
        success: false,
        action_name: 'add_checklist_photo',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    return {
      success: true,
      action_name: 'add_checklist_photo',
      data: { attachment: data },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'add_checklist_photo',
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
 * View worklist (shipyard work items)
 */
export async function viewWorklist(
  context: ActionContext,
  params?: { worklist_id?: string }
): Promise<ActionResult> {
  const worklistId = params?.worklist_id || context.entity_id;

  try {
    // Get worklist items
    let items: Array<{
      id: string;
      title: string;
      description?: string;
      status: string;
      priority: string;
      progress_percent: number;
      assigned_to?: string;
      due_date?: string;
      created_at: string;
    }> = [];

    try {
      let query = supabase
        .from('pms_worklist_tasks')
        .select('*')
        .eq('yacht_id', context.yacht_id)
        .order('created_at', { ascending: false });

      if (worklistId) {
        query = query.eq('worklist_id', worklistId);
      }

      const { data } = await query;
      items = data || [];
    } catch {
      // Table may not exist
    }

    const totalItems = items.length;
    const completedItems = items.filter((i) => i.status === 'completed').length;
    const inProgressItems = items.filter((i) => i.status === 'in_progress').length;

    return {
      success: true,
      action_name: 'view_worklist',
      data: {
        worklist_id: worklistId,
        items,
        summary: {
          total: totalItems,
          completed: completedItems,
          in_progress: inProgressItems,
          pending: totalItems - completedItems - inProgressItems,
        },
        message: items.length === 0 ? 'No worklist items found' : undefined,
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'view_worklist',
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
 * Add task to worklist
 */
export async function addWorklistTask(
  context: ActionContext,
  params: {
    worklist_id?: string;
    title: string;
    description?: string;
    priority?: string;
    due_date?: string;
  }
): Promise<ActionResult> {
  if (!params?.title) {
    return {
      success: false,
      action_name: 'add_worklist_task',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Task title is required' },
      confirmation_required: false,
    };
  }

  try {
    const { data, error } = await supabase
      .from('pms_worklist_tasks')
      .insert({
        yacht_id: context.yacht_id,
        worklist_id: params.worklist_id,
        title: params.title,
        description: params.description,
        priority: params.priority || 'medium',
        status: 'pending',
        progress_percent: 0,
        due_date: params.due_date,
        created_by: context.user_id,
        created_at: new Date().toISOString(),
      })
      .select()
      .single();

    if (error) {
      return {
        success: false,
        action_name: 'add_worklist_task',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    return {
      success: true,
      action_name: 'add_worklist_task',
      data: { worklist_item: data },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'add_worklist_task',
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
 * Update worklist progress
 */
export async function updateWorklistProgress(
  context: ActionContext,
  params: { worklist_item_id: string; progress_percent: number; status?: string; notes?: string }
): Promise<ActionResult> {
  if (!params?.worklist_item_id || params?.progress_percent === undefined) {
    return {
      success: false,
      action_name: 'update_worklist_progress',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Worklist item ID and progress percent are required' },
      confirmation_required: false,
    };
  }

  if (params.progress_percent < 0 || params.progress_percent > 100) {
    return {
      success: false,
      action_name: 'update_worklist_progress',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Progress must be between 0 and 100' },
      confirmation_required: false,
    };
  }

  try {
    // Determine status based on progress
    let status = params.status;
    if (!status) {
      if (params.progress_percent === 100) {
        status = 'completed';
      } else if (params.progress_percent > 0) {
        status = 'in_progress';
      } else {
        status = 'pending';
      }
    }

    const updateData: Record<string, unknown> = {
      progress_percent: params.progress_percent,
      status,
      updated_at: new Date().toISOString(),
    };

    if (status === 'completed') {
      updateData.completed_at = new Date().toISOString();
      updateData.completed_by = context.user_id;
    }

    const { data, error } = await supabase
      .from('pms_worklist_tasks')
      .update(updateData)
      .eq('id', params.worklist_item_id)
      .select()
      .single();

    if (error) {
      return {
        success: false,
        action_name: 'update_worklist_progress',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    // Add note if provided
    if (params.notes) {
      await supabase.from('pms_notes').insert({
        entity_type: 'worklist_item',
        entity_id: params.worklist_item_id,
        content: params.notes,
        created_by: context.user_id,
        yacht_id: context.yacht_id,
      });
    }

    return {
      success: true,
      action_name: 'update_worklist_progress',
      data: { worklist_item: data },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'update_worklist_progress',
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
 * Export worklist
 */
export async function exportWorklist(
  context: ActionContext,
  params?: { worklist_id?: string; format?: 'json' | 'csv' }
): Promise<ActionResult> {
  const worklistId = params?.worklist_id || context.entity_id;
  const format = params?.format || 'json';

  try {
    // Get worklist items
    let items: Array<Record<string, unknown>> = [];

    try {
      let query = supabase
        .from('pms_worklist_tasks')
        .select('*')
        .eq('yacht_id', context.yacht_id)
        .order('created_at', { ascending: false });

      if (worklistId) {
        query = query.eq('worklist_id', worklistId);
      }

      const { data } = await query;
      items = data || [];
    } catch {
      // Table may not exist
    }

    if (format === 'csv') {
      // Generate CSV
      const headers = ['ID', 'Title', 'Description', 'Status', 'Priority', 'Progress', 'Due Date', 'Created At'];
      const rows = items.map((item) => [
        item.id,
        item.title,
        item.description || '',
        item.status,
        item.priority,
        `${item.progress_percent}%`,
        item.due_date || '',
        item.created_at,
      ]);

      const csv = [headers.join(','), ...rows.map((row) => row.map((cell) => `"${cell}"`).join(','))].join('\n');

      return {
        success: true,
        action_name: 'export_worklist',
        data: {
          format: 'csv',
          content: csv,
          filename: `worklist_export_${new Date().toISOString().split('T')[0]}.csv`,
          item_count: items.length,
        },
        error: null,
        confirmation_required: false,
      };
    }

    // JSON format
    return {
      success: true,
      action_name: 'export_worklist',
      data: {
        format: 'json',
        items,
        item_count: items.length,
        exported_at: new Date().toISOString(),
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'export_worklist',
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
  add_work_order_photo: addWorkOrderPhoto,
  add_parts_to_work_order: addPartsToWorkOrder,
  view_work_order_checklist: viewWorkOrderChecklist,
  mark_checklist_item_complete: markChecklistItemComplete,
  add_checklist_note: addChecklistNote,
  add_checklist_photo: addChecklistPhoto,
  view_worklist: viewWorklist,
  add_worklist_task: addWorklistTask,
  update_worklist_progress: updateWorklistProgress,
  export_worklist: exportWorklist,
};
