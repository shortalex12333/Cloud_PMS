/**
 * Procurement Domain Handlers
 *
 * TypeScript handlers for procurement/purchasing related microactions.
 */

import type { ActionContext, ActionResult } from '../types';
import { supabase } from '@/lib/supabaseClient';

/**
 * Create purchase request
 */
async function createPurchaseRequest(
  context: ActionContext,
  params: {
    title: string;
    description?: string;
    urgency?: 'normal' | 'urgent' | 'critical';
    requested_by?: string;
  }
): Promise<ActionResult> {
  if (!params?.title) {
    return {
      success: false,
      action_name: 'create_purchase_request',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Title is required' },
      confirmation_required: false,
    };
  }

  try {
    // Generate PR number
    const prNumber = `PR-${Date.now().toString(36).toUpperCase()}`;

    const { data: pr, error } = await supabase
      .from('pms_purchase_orders')
      .insert({
        yacht_id: context.yacht_id,
        pr_number: prNumber,
        title: params.title,
        description: params.description,
        urgency: params.urgency || 'normal',
        status: 'draft',
        requested_by: params.requested_by || context.user_id,
        created_by: context.user_id,
        created_at: new Date().toISOString(),
      })
      .select()
      .single();

    if (error) {
      return {
        success: false,
        action_name: 'create_purchase_request',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    return {
      success: true,
      action_name: 'create_purchase_request',
      data: { purchase_request: pr },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'create_purchase_request',
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
 * Add item to purchase request
 */
async function addItemToPurchase(
  context: ActionContext,
  params: {
    purchase_request_id: string;
    part_id?: string;
    item_name: string;
    quantity: number;
    unit_price?: number;
    notes?: string;
  }
): Promise<ActionResult> {
  if (!params?.purchase_request_id || !params?.item_name || !params?.quantity) {
    return {
      success: false,
      action_name: 'add_item_to_purchase',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Purchase request ID, item name, and quantity are required' },
      confirmation_required: false,
    };
  }

  try {
    // Verify PR exists and is not approved
    const { data: pr, error: prError } = await supabase
      .from('pms_purchase_orders')
      .select('id, status')
      .eq('id', params.purchase_request_id)
      .eq('yacht_id', context.yacht_id)
      .single();

    if (prError || !pr) {
      return {
        success: false,
        action_name: 'add_item_to_purchase',
        data: null,
        error: { code: 'NOT_FOUND', message: `Purchase request not found: ${params.purchase_request_id}` },
        confirmation_required: false,
      };
    }

    if (['approved', 'completed', 'cancelled'].includes(pr.status)) {
      return {
        success: false,
        action_name: 'add_item_to_purchase',
        data: null,
        error: { code: 'VALIDATION_ERROR', message: 'Cannot add items to approved/completed purchase request' },
        confirmation_required: false,
      };
    }

    // Add item
    const { data: item, error } = await supabase
      .from('purchase_request_items')
      .insert({
        purchase_request_id: params.purchase_request_id,
        part_id: params.part_id,
        item_name: params.item_name,
        quantity: params.quantity,
        unit_price: params.unit_price,
        notes: params.notes,
        created_at: new Date().toISOString(),
      })
      .select()
      .single();

    if (error) {
      return {
        success: false,
        action_name: 'add_item_to_purchase',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    return {
      success: true,
      action_name: 'add_item_to_purchase',
      data: { item },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'add_item_to_purchase',
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
 * Approve purchase request
 */
async function approvePurchase(
  context: ActionContext,
  params: { purchase_request_id: string; notes?: string }
): Promise<ActionResult> {
  if (!params?.purchase_request_id) {
    return {
      success: false,
      action_name: 'approve_purchase',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Purchase request ID is required' },
      confirmation_required: false,
    };
  }

  try {
    // Verify PR exists and is pending
    const { data: pr, error: prError } = await supabase
      .from('pms_purchase_orders')
      .select('id, status')
      .eq('id', params.purchase_request_id)
      .eq('yacht_id', context.yacht_id)
      .single();

    if (prError || !pr) {
      return {
        success: false,
        action_name: 'approve_purchase',
        data: null,
        error: { code: 'NOT_FOUND', message: `Purchase request not found: ${params.purchase_request_id}` },
        confirmation_required: false,
      };
    }

    if (pr.status !== 'pending' && pr.status !== 'draft') {
      return {
        success: false,
        action_name: 'approve_purchase',
        data: null,
        error: { code: 'VALIDATION_ERROR', message: `Cannot approve purchase request with status: ${pr.status}` },
        confirmation_required: false,
      };
    }

    // Update status to approved
    const { data: updatedPr, error } = await supabase
      .from('pms_purchase_orders')
      .update({
        status: 'approved',
        approved_by: context.user_id,
        approved_at: new Date().toISOString(),
        approval_notes: params.notes,
        updated_at: new Date().toISOString(),
      })
      .eq('id', params.purchase_request_id)
      .select()
      .single();

    if (error) {
      return {
        success: false,
        action_name: 'approve_purchase',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    return {
      success: true,
      action_name: 'approve_purchase',
      data: { purchase_request: updatedPr },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'approve_purchase',
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
 * Upload invoice for purchase
 */
async function uploadInvoice(
  context: ActionContext,
  params: {
    purchase_request_id: string;
    invoice_number: string;
    invoice_url: string;
    total_amount?: number;
    currency?: string;
  }
): Promise<ActionResult> {
  if (!params?.purchase_request_id || !params?.invoice_number || !params?.invoice_url) {
    return {
      success: false,
      action_name: 'upload_invoice',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Purchase request ID, invoice number, and invoice URL are required' },
      confirmation_required: false,
    };
  }

  try {
    // Create invoice record
    const { data: invoice, error } = await supabase
      .from('invoices')
      .insert({
        yacht_id: context.yacht_id,
        purchase_request_id: params.purchase_request_id,
        invoice_number: params.invoice_number,
        storage_path: params.invoice_url,
        total_amount: params.total_amount,
        currency: params.currency || 'USD',
        status: 'pending',
        uploaded_by: context.user_id,
        uploaded_at: new Date().toISOString(),
      })
      .select()
      .single();

    if (error) {
      return {
        success: false,
        action_name: 'upload_invoice',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    // Update purchase request status
    await supabase
      .from('pms_purchase_orders')
      .update({
        status: 'invoiced',
        updated_at: new Date().toISOString(),
      })
      .eq('id', params.purchase_request_id);

    return {
      success: true,
      action_name: 'upload_invoice',
      data: { invoice },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'upload_invoice',
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
 * Track delivery status
 */
async function trackDelivery(
  context: ActionContext,
  params: { purchase_request_id: string }
): Promise<ActionResult> {
  if (!params?.purchase_request_id) {
    return {
      success: false,
      action_name: 'track_delivery',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Purchase request ID is required' },
      confirmation_required: false,
    };
  }

  try {
    // Get purchase request with items and delivery info
    const { data: pr, error: prError } = await supabase
      .from('pms_purchase_orders')
      .select(`
        *,
        purchase_request_items (*),
        deliveries (*)
      `)
      .eq('id', params.purchase_request_id)
      .eq('yacht_id', context.yacht_id)
      .single();

    if (prError || !pr) {
      return {
        success: false,
        action_name: 'track_delivery',
        data: null,
        error: { code: 'NOT_FOUND', message: `Purchase request not found: ${params.purchase_request_id}` },
        confirmation_required: false,
      };
    }

    // Calculate delivery status
    const items = pr.purchase_request_items || [];
    const deliveries = pr.deliveries || [];

    const totalItems = items.reduce((sum: number, item: { quantity: number }) => sum + (item.quantity || 0), 0);
    const deliveredItems = deliveries
      .filter((d: { status: string }) => d.status === 'received')
      .reduce((sum: number, d: { quantity_received: number }) => sum + (d.quantity_received || 0), 0);

    const deliveryStatus = deliveredItems === 0
      ? 'NOT_SHIPPED'
      : deliveredItems >= totalItems
        ? 'DELIVERED'
        : 'PARTIAL';

    return {
      success: true,
      action_name: 'track_delivery',
      data: {
        purchase_request_id: params.purchase_request_id,
        status: pr.status,
        delivery_status: deliveryStatus,
        items: items.length,
        deliveries: deliveries.length,
        total_ordered: totalItems,
        total_received: deliveredItems,
        tracking_numbers: deliveries
          .filter((d: { tracking_number?: string }) => d.tracking_number)
          .map((d: { tracking_number: string }) => d.tracking_number),
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'track_delivery',
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
 * Log delivery received
 */
async function logDeliveryReceived(
  context: ActionContext,
  params: {
    purchase_request_id: string;
    items_received: Array<{
      item_id: string;
      quantity_received: number;
      condition?: 'good' | 'damaged' | 'partial';
      notes?: string;
    }>;
    received_date?: string;
  }
): Promise<ActionResult> {
  if (!params?.purchase_request_id || !params?.items_received?.length) {
    return {
      success: false,
      action_name: 'log_delivery_received',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Purchase request ID and items received are required' },
      confirmation_required: false,
    };
  }

  try {
    // Create delivery record
    const { data: delivery, error } = await supabase
      .from('deliveries')
      .insert({
        yacht_id: context.yacht_id,
        purchase_request_id: params.purchase_request_id,
        received_by: context.user_id,
        received_at: params.received_date || new Date().toISOString(),
        items: params.items_received,
        status: 'received',
        quantity_received: params.items_received.reduce((sum, item) => sum + (item.quantity_received || 0), 0),
      })
      .select()
      .single();

    if (error) {
      return {
        success: false,
        action_name: 'log_delivery_received',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    // Update purchase request status
    await supabase
      .from('pms_purchase_orders')
      .update({
        status: 'delivered',
        updated_at: new Date().toISOString(),
      })
      .eq('id', params.purchase_request_id);

    // Update part quantities if part_id is linked
    for (const item of params.items_received) {
      const { data: prItem } = await supabase
        .from('purchase_request_items')
        .select('part_id')
        .eq('id', item.item_id)
        .single();

      if (prItem?.part_id) {
        await supabase.rpc('increment_part_quantity', {
          p_part_id: prItem.part_id,
          p_quantity: item.quantity_received,
        });
      }
    }

    return {
      success: true,
      action_name: 'log_delivery_received',
      data: { delivery },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'log_delivery_received',
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
 * Update purchase request status
 */
async function updatePurchaseStatus(
  context: ActionContext,
  params: {
    purchase_request_id: string;
    status: 'draft' | 'pending' | 'approved' | 'ordered' | 'shipped' | 'delivered' | 'completed' | 'cancelled';
    notes?: string;
  }
): Promise<ActionResult> {
  if (!params?.purchase_request_id || !params?.status) {
    return {
      success: false,
      action_name: 'update_purchase_status',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Purchase request ID and status are required' },
      confirmation_required: false,
    };
  }

  try {
    const updateData: Record<string, unknown> = {
      status: params.status,
      updated_at: new Date().toISOString(),
      updated_by: context.user_id,
    };

    if (params.notes) {
      updateData.status_notes = params.notes;
    }

    if (params.status === 'completed') {
      updateData.completed_at = new Date().toISOString();
    } else if (params.status === 'cancelled') {
      updateData.cancelled_at = new Date().toISOString();
      updateData.cancelled_by = context.user_id;
    }

    const { data: pr, error } = await supabase
      .from('pms_purchase_orders')
      .update(updateData)
      .eq('id', params.purchase_request_id)
      .eq('yacht_id', context.yacht_id)
      .select()
      .single();

    if (error) {
      return {
        success: false,
        action_name: 'update_purchase_status',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    return {
      success: true,
      action_name: 'update_purchase_status',
      data: { purchase_request: pr },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'update_purchase_status',
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
 * Get all procurement handlers for registration
 */
export const procurementHandlers = {
  create_purchase_request: createPurchaseRequest,
  add_item_to_purchase: addItemToPurchase,
  approve_purchase: approvePurchase,
  upload_invoice: uploadInvoice,
  track_delivery: trackDelivery,
  log_delivery_received: logDeliveryReceived,
  update_purchase_status: updatePurchaseStatus,
};
