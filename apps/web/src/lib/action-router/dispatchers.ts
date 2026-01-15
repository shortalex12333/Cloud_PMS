/**
 * Action Router - Dispatchers
 *
 * Dispatch action execution to appropriate handlers:
 * - Internal: Direct Supabase operations
 * - n8n: External workflow automation
 */

import { createClient } from '@/lib/supabaseClient';
import type { DispatchParams, DispatchResult, HandlerType } from './types';

// ============================================================================
// INTERNAL HANDLERS
// ============================================================================

/**
 * Add a note to equipment
 */
async function addNote(params: DispatchParams): Promise<DispatchResult> {
  const supabase = createClient();

  const { data, error } = await supabase
    .from('pms_equipment_notes')
    .insert({
      yacht_id: params.yacht_id,
      equipment_id: params.equipment_id,
      note_text: params.note_text,
      created_by: params.user_id,
    })
    .select('id, created_at')
    .single();

  if (error) throw new Error(`Failed to create note: ${error.message}`);

  return {
    note_id: data.id,
    created_at: data.created_at,
  };
}

/**
 * Add a note to a work order
 */
async function addNoteToWorkOrder(params: DispatchParams): Promise<DispatchResult> {
  const supabase = createClient();

  // Verify work order exists and belongs to yacht
  const { data: woData, error: woError } = await supabase
    .from('pms_work_orders')
    .select('id')
    .eq('id', params.work_order_id)
    .eq('yacht_id', params.yacht_id)
    .single();

  if (woError || !woData) {
    throw new Error(
      `Work order ${params.work_order_id} not found or access denied`
    );
  }

  // Insert note
  const { data, error } = await supabase
    .from('pms_work_order_notes')
    .insert({
      work_order_id: params.work_order_id,
      note_text: params.note_text,
      created_by: params.user_id,
    })
    .select('id, created_at')
    .single();

  if (error) throw new Error(`Failed to create work order note: ${error.message}`);

  return {
    note_id: data.id,
    created_at: data.created_at,
  };
}

/**
 * Close a work order
 */
async function closeWorkOrder(params: DispatchParams): Promise<DispatchResult> {
  const supabase = createClient();

  const { data, error } = await supabase
    .from('pms_work_orders')
    .update({
      status: 'completed',
      completed_at: new Date().toISOString(),
      completed_by: params.user_id,
    })
    .eq('id', params.work_order_id)
    .eq('yacht_id', params.yacht_id)
    .select('id, status, completed_at')
    .single();

  if (error || !data) {
    throw new Error(
      `Work order ${params.work_order_id} not found or access denied`
    );
  }

  return {
    work_order_id: data.id,
    status: data.status,
    completed_at: data.completed_at,
  };
}

/**
 * Open a document (get signed URL)
 */
async function openDocument(params: DispatchParams): Promise<DispatchResult> {
  const supabase = createClient();

  const { data, error } = await supabase.storage
    .from('documents')
    .createSignedUrl(params.storage_path as string, 3600);

  if (error) {
    throw new Error(`Failed to generate document URL: ${error.message}`);
  }

  return {
    signed_url: data.signedUrl,
    expires_in: 3600,
  };
}

/**
 * Edit a handover section
 */
async function editHandoverSection(params: DispatchParams): Promise<DispatchResult> {
  const supabase = createClient();

  // Get current handover
  const { data: handoverData, error: handoverError } = await supabase
    .from('handovers')
    .select('*')
    .eq('id', params.handover_id)
    .eq('yacht_id', params.yacht_id)
    .single();

  if (handoverError || !handoverData) {
    throw new Error(
      `Handover ${params.handover_id} not found or access denied`
    );
  }

  // Update section content
  const content = (handoverData.content as Record<string, unknown>) || {};
  content[params.section_name as string] = params.new_text;

  // Update handover
  const { data, error } = await supabase
    .from('handovers')
    .update({
      content,
      updated_at: new Date().toISOString(),
      updated_by: params.user_id,
    })
    .eq('id', params.handover_id)
    .select('id, updated_at')
    .single();

  if (error) throw new Error(`Failed to update handover section: ${error.message}`);

  return {
    handover_id: data.id,
    section_name: params.section_name,
    updated_at: data.updated_at,
  };
}

// ============================================================================
// INTERNAL HANDLER REGISTRY
// ============================================================================

type InternalHandler = (params: DispatchParams) => Promise<DispatchResult>;

const INTERNAL_HANDLERS: Record<string, InternalHandler> = {
  add_note: addNote,
  add_note_to_work_order: addNoteToWorkOrder,
  close_work_order: closeWorkOrder,
  open_document: openDocument,
  edit_handover_section: editHandoverSection,
};

// ============================================================================
// N8N WEBHOOK PATHS
// ============================================================================

const N8N_WEBHOOK_PATHS: Record<string, string> = {
  create_work_order: '/webhook/work-order/create',
  create_work_order_fault: '/webhook/work-order/create-from-fault',
  add_to_handover: '/webhook/handover/add-item',
  add_document_to_handover: '/webhook/handover/add-document',
  add_part_to_handover: '/webhook/handover/add-part',
  add_predictive_to_handover: '/webhook/handover/add-predictive',
  export_handover: '/webhook/handover/export',
  order_part: '/webhook/inventory/order-part',
};

// ============================================================================
// INTERNAL DISPATCHER
// ============================================================================

/**
 * Dispatch action to internal handler (Supabase)
 *
 * @param actionId - Action to execute
 * @param params - Action parameters
 * @returns Dispatch result
 */
export async function dispatchInternal(
  actionId: string,
  params: DispatchParams
): Promise<DispatchResult> {
  const handler = INTERNAL_HANDLERS[actionId];

  if (!handler) {
    throw new Error(`No internal handler found for action '${actionId}'`);
  }

  try {
    return await handler(params);
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error(`Internal handler failed: ${String(error)}`);
  }
}

// ============================================================================
// N8N DISPATCHER
// ============================================================================

/**
 * Dispatch action to n8n webhook
 *
 * @param actionId - Action to execute
 * @param params - Action parameters
 * @returns Dispatch result
 */
export async function dispatchN8n(
  actionId: string,
  params: DispatchParams
): Promise<DispatchResult> {
  const webhookPath = N8N_WEBHOOK_PATHS[actionId];

  if (!webhookPath) {
    throw new Error(`No n8n webhook found for action '${actionId}'`);
  }

  const n8nBaseUrl = process.env.NEXT_PUBLIC_N8N_BASE_URL;
  const n8nAuthToken = process.env.N8N_AUTH_TOKEN;

  if (!n8nBaseUrl) {
    throw new Error('N8N_BASE_URL is not configured');
  }

  const url = `${n8nBaseUrl}${webhookPath}`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(n8nAuthToken ? { Authorization: `Bearer ${n8nAuthToken}` } : {}),
      },
      body: JSON.stringify(params),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`n8n webhook failed (${response.status}): ${errorText}`);
    }

    const result = await response.json();
    return result as DispatchResult;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error(`n8n dispatch failed: ${String(error)}`);
  }
}

// ============================================================================
// UNIFIED DISPATCHER
// ============================================================================

/**
 * Dispatch action to appropriate handler based on handler type
 *
 * @param actionId - Action to execute
 * @param params - Action parameters
 * @param handlerType - Type of handler to use
 * @returns Dispatch result
 */
export async function dispatch(
  actionId: string,
  params: DispatchParams,
  handlerType: HandlerType
): Promise<DispatchResult> {
  switch (handlerType) {
    case 'internal':
      return dispatchInternal(actionId, params);
    case 'n8n':
      return dispatchN8n(actionId, params);
    default:
      throw new Error(`Unknown handler type: ${handlerType}`);
  }
}

// ============================================================================
// EXPORTS
// ============================================================================

export { INTERNAL_HANDLERS, N8N_WEBHOOK_PATHS };
