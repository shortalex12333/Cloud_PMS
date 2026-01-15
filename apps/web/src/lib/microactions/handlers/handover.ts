/**
 * Handover Domain Handlers
 *
 * TypeScript handlers for handover/communication-related microactions.
 */

import type { ActionContext, ActionResult } from '../types';
import { createClient } from '@/lib/supabaseClient';

/**
 * Add entity to handover
 */
export async function addToHandover(
  context: ActionContext,
  params: {
    entity_id: string;
    entity_type: 'fault' | 'work_order' | 'equipment' | 'part' | 'document';
    section?: string;
    summary?: string;
  }
): Promise<ActionResult> {
  const supabase = createClient();

  if (!params?.entity_id || !params?.entity_type) {
    return {
      success: false,
      action_name: 'add_to_handover',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Entity ID and type are required' },
      confirmation_required: false,
    };
  }

  try {
    // Get or create current handover
    let { data: handover } = await supabase
      .from('handovers')
      .select('id')
      .eq('yacht_id', context.yacht_id)
      .eq('status', 'draft')
      .order('created_at', { ascending: false })
      .limit(1)
      .single();

    if (!handover) {
      // Create new handover
      const { data: newHandover, error: createError } = await supabase
        .from('handovers')
        .insert({
          yacht_id: context.yacht_id,
          status: 'draft',
          created_by: context.user_id,
        })
        .select()
        .single();

      if (createError) {
        return {
          success: false,
          action_name: 'add_to_handover',
          data: null,
          error: { code: 'INTERNAL_ERROR', message: createError.message },
          confirmation_required: false,
        };
      }
      handover = newHandover;
    }

    // Add item to handover
    const { data: item, error: itemError } = await supabase
      .from('handover_items')
      .insert({
        handover_id: handover.id,
        entity_id: params.entity_id,
        entity_type: params.entity_type,
        section: params.section,
        summary: params.summary,
        added_by: context.user_id,
      })
      .select()
      .single();

    if (itemError) {
      return {
        success: false,
        action_name: 'add_to_handover',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: itemError.message },
        confirmation_required: false,
      };
    }

    return {
      success: true,
      action_name: 'add_to_handover',
      data: {
        handover_id: handover.id,
        item,
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'add_to_handover',
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
 * Export handover to PDF
 */
export async function exportHandover(
  context: ActionContext,
  params?: { handover_id?: string; format?: 'pdf' | 'docx' }
): Promise<ActionResult> {
  const supabase = createClient();
  const handoverId = params?.handover_id || context.entity_id;
  const format = params?.format || 'pdf';

  if (!handoverId) {
    return {
      success: false,
      action_name: 'export_handover',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Handover ID is required' },
      confirmation_required: false,
    };
  }

  try {
    // Get handover with items
    const { data: handover, error: hoError } = await supabase
      .from('handovers')
      .select(`
        *,
        handover_items (*)
      `)
      .eq('id', handoverId)
      .single();

    if (hoError || !handover) {
      return {
        success: false,
        action_name: 'export_handover',
        data: null,
        error: { code: 'NOT_FOUND', message: `Handover not found: ${handoverId}` },
        confirmation_required: false,
      };
    }

    // Call export service (handover_export on Render)
    // For now, return the data that would be exported
    return {
      success: true,
      action_name: 'export_handover',
      data: {
        handover_id: handoverId,
        format,
        export_url: `https://handover-export.onrender.com/api/v1/export/${handoverId}?format=${format}`,
        item_count: handover.handover_items?.length || 0,
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'export_handover',
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
 * Edit handover section
 */
export async function editHandoverSection(
  context: ActionContext,
  params: {
    handover_id: string;
    section_id: string;
    content: string;
  }
): Promise<ActionResult> {
  const supabase = createClient();

  if (!params?.handover_id || !params?.section_id || !params?.content) {
    return {
      success: false,
      action_name: 'edit_handover_section',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Handover ID, section ID, and content are required' },
      confirmation_required: false,
    };
  }

  try {
    const { data: item, error } = await supabase
      .from('handover_items')
      .update({
        summary: params.content,
        updated_at: new Date().toISOString(),
        updated_by: context.user_id,
      })
      .eq('id', params.section_id)
      .eq('handover_id', params.handover_id)
      .select()
      .single();

    if (error) {
      return {
        success: false,
        action_name: 'edit_handover_section',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    return {
      success: true,
      action_name: 'edit_handover_section',
      data: { item },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'edit_handover_section',
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
 * View document
 */
export async function viewDocument(
  context: ActionContext,
  params?: { document_id?: string }
): Promise<ActionResult> {
  const supabase = createClient();
  const documentId = params?.document_id || context.entity_id;

  if (!documentId) {
    return {
      success: false,
      action_name: 'view_document',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Document ID is required' },
      confirmation_required: false,
    };
  }

  try {
    const { data: document, error } = await supabase
      .from('documents')
      .select('*')
      .eq('yacht_id', context.yacht_id)
      .eq('id', documentId)
      .single();

    if (error || !document) {
      return {
        success: false,
        action_name: 'view_document',
        data: null,
        error: { code: 'NOT_FOUND', message: `Document not found: ${documentId}` },
        confirmation_required: false,
      };
    }

    // Generate signed URL for storage access
    let signedUrl: string | null = null;
    if (document.storage_path) {
      const { data: urlData } = await supabase.storage
        .from('documents')
        .createSignedUrl(document.storage_path, 3600); // 1 hour expiry
      signedUrl = urlData?.signedUrl || null;
    }

    return {
      success: true,
      action_name: 'view_document',
      data: {
        document,
        signed_url: signedUrl,
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'view_document',
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
 * Get all handover handlers for registration
 */
export const handoverHandlers = {
  add_to_handover: addToHandover,
  export_handover: exportHandover,
  edit_handover_section: editHandoverSection,
  view_document: viewDocument,
};
