/**
 * Handover Domain Handlers
 *
 * TypeScript handlers for handover/communication-related microactions.
 */

import type { ActionContext, ActionResult } from '../types';
import { supabase } from '@/lib/supabaseClient';

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

      if (createError || !newHandover) {
        return {
          success: false,
          action_name: 'add_to_handover',
          data: null,
          error: { code: 'INTERNAL_ERROR', message: createError?.message || 'Failed to create handover' },
          confirmation_required: false,
        };
      }
      handover = newHandover;
    }

    // Add item to handover - handover is guaranteed non-null at this point
    const { data: item, error: itemError } = await supabase
      .from('handover_items')
      .insert({
        handover_id: handover!.id,
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
        handover_id: handover!.id,
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
 * Add document to handover
 */
export async function addDocumentToHandover(
  context: ActionContext,
  params: {
    document_id: string;
    section?: string;
    page_numbers?: string;
    summary?: string;
  }
): Promise<ActionResult> {
  if (!params?.document_id) {
    return {
      success: false,
      action_name: 'add_document_to_handover',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Document ID is required' },
      confirmation_required: false,
    };
  }

  // Delegate to add_to_handover with entity_type = 'document'
  return addToHandover(context, {
    entity_id: params.document_id,
    entity_type: 'document',
    section: params.section || params.page_numbers,
    summary: params.summary,
  });
}

/**
 * Add predictive insight to handover
 */
export async function addPredictiveInsightToHandover(
  context: ActionContext,
  params: {
    equipment_id: string;
    insight_type?: string;
    summary?: string;
  }
): Promise<ActionResult> {
  if (!params?.equipment_id) {
    return {
      success: false,
      action_name: 'add_predictive_insight_to_handover',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Equipment ID is required' },
      confirmation_required: false,
    };
  }

  try {
    // Get predictive state for equipment
    const { data: predState } = await supabase
      .from('predictive_state')
      .select('*')
      .eq('equipment_id', params.equipment_id)
      .single();

    // Get equipment name
    const { data: equipment } = await supabase
      .from('pms_equipment')
      .select('name')
      .eq('id', params.equipment_id)
      .single();

    const summary = params.summary || (predState
      ? `${equipment?.name || 'Equipment'}: Risk score ${predState.risk_score || 0}, ${predState.anomalies?.length || 0} anomalies detected`
      : `${equipment?.name || 'Equipment'}: No predictive data available`);

    // Add to handover with special section for predictive insights
    return addToHandover(context, {
      entity_id: params.equipment_id,
      entity_type: 'equipment',
      section: 'predictive_insights',
      summary,
    });
  } catch (err) {
    return {
      success: false,
      action_name: 'add_predictive_insight_to_handover',
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
 * Regenerate handover summary using AI
 */
export async function regenerateHandoverSummary(
  context: ActionContext,
  params?: { handover_id?: string }
): Promise<ActionResult> {
  const handoverId = params?.handover_id || context.entity_id;

  if (!handoverId) {
    return {
      success: false,
      action_name: 'regenerate_handover_summary',
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
        action_name: 'regenerate_handover_summary',
        data: null,
        error: { code: 'NOT_FOUND', message: `Handover not found: ${handoverId}` },
        confirmation_required: false,
      };
    }

    // Generate summary from items
    const items = handover.handover_items || [];
    const summary = generateHandoverSummary(items);

    // Update handover with new summary
    const { data: updatedHandover, error: updateError } = await supabase
      .from('handovers')
      .update({
        summary,
        updated_at: new Date().toISOString(),
      })
      .eq('id', handoverId)
      .select()
      .single();

    if (updateError) {
      return {
        success: false,
        action_name: 'regenerate_handover_summary',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: updateError.message },
        confirmation_required: false,
      };
    }

    return {
      success: true,
      action_name: 'regenerate_handover_summary',
      data: {
        handover: updatedHandover,
        summary,
        item_count: items.length,
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'regenerate_handover_summary',
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
 * Generate handover summary from items
 */
function generateHandoverSummary(items: Array<{ entity_type: string; summary?: string }>): string {
  const faultCount = items.filter((i) => i.entity_type === 'fault').length;
  const woCount = items.filter((i) => i.entity_type === 'work_order').length;
  const equipmentCount = items.filter((i) => i.entity_type === 'equipment').length;
  const docCount = items.filter((i) => i.entity_type === 'document').length;

  const parts: string[] = [];
  if (faultCount > 0) parts.push(`${faultCount} fault(s)`);
  if (woCount > 0) parts.push(`${woCount} work order(s)`);
  if (equipmentCount > 0) parts.push(`${equipmentCount} equipment item(s)`);
  if (docCount > 0) parts.push(`${docCount} document(s)`);

  return `Handover includes ${parts.length > 0 ? parts.join(', ') : 'no items'}.`;
}

/**
 * View related documents
 */
export async function viewRelatedDocuments(
  context: ActionContext,
  params?: { document_id?: string; equipment_id?: string; keyword?: string }
): Promise<ActionResult> {
  const documentId = params?.document_id || context.entity_id;

  try {
    let relatedDocs: Array<{
      id: string;
      name: string;
      document_type?: string;
      relevance_score?: number;
    }> = [];

    if (documentId) {
      // Find documents related to this document via chunks
      const { data: sourceDoc } = await supabase
        .from('documents')
        .select('name, document_type')
        .eq('id', documentId)
        .single();

      if (sourceDoc) {
        // Search for documents with similar content
        const { data: relatedChunks } = await supabase
          .from('document_chunks')
          .select('document_id')
          .eq('yacht_id', context.yacht_id)
          .ilike('content', `%${sourceDoc.name}%`)
          .limit(20);

        if (relatedChunks) {
          const docIds = [...new Set(relatedChunks.map((c) => c.document_id).filter((id) => id !== documentId))];
          if (docIds.length > 0) {
            const { data: docs } = await supabase
              .from('documents')
              .select('id, name, document_type')
              .in('id', docIds)
              .limit(10);
            relatedDocs = docs || [];
          }
        }
      }
    } else if (params?.equipment_id) {
      // Find documents related to equipment
      const { data: equipment } = await supabase
        .from('pms_equipment')
        .select('name')
        .eq('id', params.equipment_id)
        .single();

      if (equipment) {
        const { data: chunks } = await supabase
          .from('document_chunks')
          .select('document_id')
          .eq('yacht_id', context.yacht_id)
          .ilike('content', `%${equipment.name}%`)
          .limit(20);

        if (chunks) {
          const docIds = [...new Set(chunks.map((c) => c.document_id))];
          if (docIds.length > 0) {
            const { data: docs } = await supabase
              .from('documents')
              .select('id, name, document_type')
              .in('id', docIds)
              .limit(10);
            relatedDocs = docs || [];
          }
        }
      }
    } else if (params?.keyword) {
      // Search documents by keyword
      const { data: chunks } = await supabase
        .from('document_chunks')
        .select('document_id')
        .eq('yacht_id', context.yacht_id)
        .ilike('content', `%${params.keyword}%`)
        .limit(20);

      if (chunks) {
        const docIds = [...new Set(chunks.map((c) => c.document_id))];
        if (docIds.length > 0) {
          const { data: docs } = await supabase
            .from('documents')
            .select('id, name, document_type')
            .in('id', docIds)
            .limit(10);
          relatedDocs = docs || [];
        }
      }
    }

    return {
      success: true,
      action_name: 'view_related_documents',
      data: {
        source_document_id: documentId,
        related_documents: relatedDocs,
        count: relatedDocs.length,
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'view_related_documents',
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
 * View specific document section
 */
export async function viewDocumentSection(
  context: ActionContext,
  params: { document_id: string; section_id?: string; page_number?: number }
): Promise<ActionResult> {
  if (!params?.document_id) {
    return {
      success: false,
      action_name: 'view_document_section',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Document ID is required' },
      confirmation_required: false,
    };
  }

  try {
    // Get document chunks for specific section/page
    let query = supabase
      .from('document_chunks')
      .select('id, section_title, page_number, content, chunk_index')
      .eq('document_id', params.document_id)
      .order('chunk_index');

    if (params.section_id) {
      query = query.eq('id', params.section_id);
    } else if (params.page_number) {
      query = query.eq('page_number', params.page_number);
    }

    const { data: chunks, error } = await query.limit(10);

    if (error) {
      return {
        success: false,
        action_name: 'view_document_section',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    // Get document metadata
    const { data: document } = await supabase
      .from('documents')
      .select('id, name, document_type')
      .eq('id', params.document_id)
      .single();

    return {
      success: true,
      action_name: 'view_document_section',
      data: {
        document_id: params.document_id,
        document_name: document?.name,
        sections: chunks || [],
        section_count: chunks?.length || 0,
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'view_document_section',
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
  add_document_to_handover: addDocumentToHandover,
  add_predictive_insight_to_handover: addPredictiveInsightToHandover,
  export_handover: exportHandover,
  edit_handover_section: editHandoverSection,
  regenerate_handover_summary: regenerateHandoverSummary,
  view_document: viewDocument,
  view_related_documents: viewRelatedDocuments,
  view_document_section: viewDocumentSection,
};
