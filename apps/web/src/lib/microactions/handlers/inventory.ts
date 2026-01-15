/**
 * Inventory Domain Handlers
 *
 * TypeScript handlers for inventory/parts-related microactions.
 */

import type { ActionContext, ActionResult } from '../types';
import { supabase } from '@/lib/supabaseClient';

/**
 * View part stock details
 */
export async function viewPartStock(
  context: ActionContext,
  params?: { part_id?: string }
): Promise<ActionResult> {
  
  const partId = params?.part_id || context.entity_id;

  if (!partId) {
    return {
      success: false,
      action_name: 'view_part_stock',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Part ID is required' },
      confirmation_required: false,
    };
  }

  try {
    const { data: part, error } = await supabase
      .from('pms_parts')
      .select('*')
      .eq('yacht_id', context.yacht_id)
      .eq('id', partId)
      .single();

    if (error || !part) {
      return {
        success: false,
        action_name: 'view_part_stock',
        data: null,
        error: { code: 'NOT_FOUND', message: `Part not found: ${partId}` },
        confirmation_required: false,
      };
    }

    // Compute stock status
    const qty = part.quantity || 0;
    const minQty = part.min_quantity || 0;
    let stockStatus = 'IN_STOCK';
    if (qty <= 0) stockStatus = 'OUT_OF_STOCK';
    else if (qty <= minQty) stockStatus = 'LOW_STOCK';

    return {
      success: true,
      action_name: 'view_part_stock',
      data: {
        part: {
          ...part,
          stock_status: stockStatus,
          is_low_stock: ['LOW_STOCK', 'OUT_OF_STOCK'].includes(stockStatus),
        },
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'view_part_stock',
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
 * View part location
 */
export async function viewPartLocation(
  context: ActionContext,
  params?: { part_id?: string }
): Promise<ActionResult> {
  
  const partId = params?.part_id || context.entity_id;

  if (!partId) {
    return {
      success: false,
      action_name: 'view_part_location',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Part ID is required' },
      confirmation_required: false,
    };
  }

  try {
    const { data: part, error } = await supabase
      .from('pms_parts')
      .select('id, name, location, storage_location, bin_number')
      .eq('yacht_id', context.yacht_id)
      .eq('id', partId)
      .single();

    if (error || !part) {
      return {
        success: false,
        action_name: 'view_part_location',
        data: null,
        error: { code: 'NOT_FOUND', message: `Part not found: ${partId}` },
        confirmation_required: false,
      };
    }

    return {
      success: true,
      action_name: 'view_part_location',
      data: {
        part_id: partId,
        location: part.location || part.storage_location,
        bin_number: part.bin_number,
        name: part.name,
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'view_part_location',
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
 * Order part - create purchase request
 */
export async function orderPart(
  context: ActionContext,
  params: {
    part_id: string;
    quantity: number;
    urgency?: 'normal' | 'urgent' | 'critical';
    notes?: string;
  }
): Promise<ActionResult> {
  

  if (!params?.part_id || !params?.quantity) {
    return {
      success: false,
      action_name: 'order_part',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Part ID and quantity are required' },
      confirmation_required: false,
    };
  }

  try {
    // Get part details
    const { data: part, error: partError } = await supabase
      .from('pms_parts')
      .select('id, name, part_number')
      .eq('id', params.part_id)
      .single();

    if (partError || !part) {
      return {
        success: false,
        action_name: 'order_part',
        data: null,
        error: { code: 'NOT_FOUND', message: `Part not found: ${params.part_id}` },
        confirmation_required: false,
      };
    }

    // Create purchase request
    const { data: purchaseRequest, error: prError } = await supabase
      .from('purchase_requests')
      .insert({
        yacht_id: context.yacht_id,
        part_id: params.part_id,
        quantity: params.quantity,
        urgency: params.urgency || 'normal',
        notes: params.notes,
        status: 'pending',
        created_by: context.user_id,
      })
      .select()
      .single();

    if (prError) {
      return {
        success: false,
        action_name: 'order_part',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: prError.message },
        confirmation_required: false,
      };
    }

    return {
      success: true,
      action_name: 'order_part',
      data: {
        purchase_request: purchaseRequest,
        part: part,
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'order_part',
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
 * Log part usage from work order
 */
export async function logPartUsage(
  context: ActionContext,
  params: {
    part_id: string;
    work_order_id: string;
    quantity: number;
  }
): Promise<ActionResult> {
  

  if (!params?.part_id || !params?.work_order_id || !params?.quantity) {
    return {
      success: false,
      action_name: 'log_part_usage',
      data: null,
      error: {
        code: 'VALIDATION_ERROR',
        message: 'Part ID, work order ID, and quantity are required',
      },
      confirmation_required: false,
    };
  }

  try {
    // Record usage in work_order_parts
    const { data: usage, error: usageError } = await supabase
      .from('work_order_parts')
      .insert({
        work_order_id: params.work_order_id,
        part_id: params.part_id,
        quantity_used: params.quantity,
        logged_by: context.user_id,
        logged_at: new Date().toISOString(),
      })
      .select()
      .single();

    if (usageError) {
      return {
        success: false,
        action_name: 'log_part_usage',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: usageError.message },
        confirmation_required: false,
      };
    }

    // Update part quantity (decrement)
    await supabase.rpc('decrement_part_quantity', {
      p_part_id: params.part_id,
      p_quantity: params.quantity,
    });

    return {
      success: true,
      action_name: 'log_part_usage',
      data: { usage },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'log_part_usage',
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
 * Get all inventory handlers for registration
 */
export const inventoryHandlers = {
  view_part_stock: viewPartStock,
  view_part_location: viewPartLocation,
  order_part: orderPart,
  log_part_usage: logPartUsage,
};
