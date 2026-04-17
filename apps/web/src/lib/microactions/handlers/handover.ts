/**
 * Handover Domain Handlers
 *
 * TypeScript handlers for handover/communication-related microactions.
 */

import type { ActionContext, ActionResult } from '../types';
import { supabase } from '@/lib/supabaseClient';

/**
 * Add entity to handover
 *
 * After schema consolidation (2026-02-05), handover_items are standalone.
 * No parent container table - items are inserted directly into handover_items.
 */
async function addToHandover(
  context: ActionContext,
  params: {
    entity_id: string;
    entity_type: 'fault' | 'work_order' | 'equipment' | 'part' | 'document';
    section?: string;
    summary?: string;
    category?: string;
    is_critical?: boolean;
    requires_action?: boolean;
    action_summary?: string;
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
    // Route through Render API action router — direct supabase inserts hit MASTER DB
    // (handover_items lives in TENANT DB, only accessible via Render service_role)
    const { data: sessionData } = await supabase.auth.getSession();
    const token = sessionData?.session?.access_token;
    if (!token) {
      return {
        success: false,
        action_name: 'add_to_handover',
        data: null,
        error: { code: 'FORBIDDEN', message: 'Authentication required' },
        confirmation_required: false,
      };
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
    const res = await fetch(`${apiUrl}/v1/actions/execute`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: 'add_to_handover',
        context: { yacht_id: context.yacht_id },
        payload: {
          entity_id: params.entity_id,
          entity_type: params.entity_type,
          section: params.section,
          summary: params.summary,
          category: params.category || 'standard',
          is_critical: params.is_critical || false,
          requires_action: params.requires_action || false,
          action_summary: params.action_summary,
        },
      }),
    });

    const result = await res.json();
    if (!res.ok || result.status === 'error') {
      return {
        success: false,
        action_name: 'add_to_handover',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: result.message || `Failed (${res.status})` },
        confirmation_required: false,
      };
    }

    return {
      success: true,
      action_name: 'add_to_handover',
      data: { item_id: result.result?.item_id, item: result.result?.handover_item },
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
 * Export handover via backend API
 *
 * Calls POST /v1/handover/export on the backend, which:
 * 1. Fetches items from handover_items
 * 2. Delegates to LLM microservice for professional summaries
 * 3. Creates handover_exports record + ledger notification
 * 4. Uploads HTML to Supabase Storage
 */
async function exportHandover(
  context: ActionContext,
  params?: { format?: 'pdf' | 'docx'; department?: string }
): Promise<ActionResult> {

  const format = params?.format || 'html';

  try {
    // Get auth token for backend call
    const { data: sessionData } = await supabase.auth.getSession();
    const token = sessionData?.session?.access_token;
    if (!token) {
      return {
        success: false,
        action_name: 'export_handover',
        data: null,
        error: { code: 'FORBIDDEN', message: 'Authentication required' },
        confirmation_required: false,
      };
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

    const response = await fetch(`${apiUrl}/v1/handover/export`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        export_type: format,
        filter_by_user: false,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Export failed' }));
      return {
        success: false,
        action_name: 'export_handover',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: errorData.detail || `Export failed (${response.status})` },
        confirmation_required: false,
      };
    }

    const result = await response.json();

    return {
      success: true,
      action_name: 'export_handover',
      data: {
        export_id: result.export_id,
        format,
        total_items: result.total_items,
        sections_count: result.sections_count,
        document_hash: result.document_hash,
        html_preview_url: result.html_preview_url,
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
 * Edit handover item
 *
 * After schema consolidation (2026-02-05), items are standalone.
 * Update by item_id directly, no parent handover_id needed.
 */
async function editHandoverSection(
  context: ActionContext,
  params: {
    item_id: string;
    content?: string;
    category?: string;
    is_critical?: boolean;
    requires_action?: boolean;
    action_summary?: string;
  }
): Promise<ActionResult> {


  if (!params?.item_id) {
    return {
      success: false,
      action_name: 'edit_handover_section',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Item ID is required' },
      confirmation_required: false,
    };
  }

  try {
    // Route through Render API — PATCH /v1/handover/items/{id}
    const { data: sessionData } = await supabase.auth.getSession();
    const token = sessionData?.session?.access_token;
    if (!token) {
      return { success: false, action_name: 'edit_handover_section', data: null,
        error: { code: 'FORBIDDEN', message: 'Authentication required' }, confirmation_required: false };
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
    const body: Record<string, unknown> = {};
    if (params.content !== undefined) body.summary = params.content;
    if (params.category !== undefined) body.category = params.category;

    const res = await fetch(`${apiUrl}/v1/handover/items/${params.item_id}`, {
      method: 'PATCH',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const result = await res.json();

    if (!res.ok || result.status === 'error') {
      return {
        success: false,
        action_name: 'edit_handover_section',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: result.detail || `Failed (${res.status})` },
        confirmation_required: false,
      };
    }

    return {
      success: true,
      action_name: 'edit_handover_section',
      data: { item: result.item },
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
async function viewDocument(
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
 *
 * PR-D4 (2026-04-17): Extended to accept the document-provenance fields that
 * `entity_prefill.py` populates into the Add-to-Handover popup:
 *   - `title` (filename)
 *   - `doc_type`
 *   - `source_doc_id` (copy of document_id — provenance)
 *   - `link` (storage_path)
 *   - `page_numbers` (user-editable when relevant)
 *
 * These are forwarded to `add_to_handover` as `action_summary` (section-scoped
 * human text) and embedded on the resulting handover_item via the backend's
 * metadata write-through — the handler on the Render side will merge them
 * into handover_items.metadata so the provenance survives the hand-off.
 */
async function addDocumentToHandover(
  context: ActionContext,
  params: {
    document_id: string;
    /** Prefilled: filename rendered as the handover row title context */
    title?: string;
    /** Prefilled: manual / spec_sheet / certificate / etc. */
    doc_type?: string;
    /** Prefilled: echo of document_id for audit provenance */
    source_doc_id?: string;
    /** Prefilled: storage_path used to deep-link back to the file */
    link?: string;
    /** User-editable */
    section?: string;
    /** User-editable */
    summary?: string;
    /** User-editable — optional page range */
    page_numbers?: string;
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

  // Build the human-visible action summary by concatenating user text +
  // provenance tag. The backend `add_to_handover` handler stores this on the
  // `action_summary` column and the full handover row links back via
  // `entity_id`/`entity_type` so downstream exports can still resolve the doc.
  const provenanceFragments = [
    params.title ? `Document: ${params.title}` : null,
    params.doc_type ? `Type: ${params.doc_type}` : null,
    params.page_numbers ? `Pages: ${params.page_numbers}` : null,
    params.link ? `Ref: ${params.link}` : null,
  ].filter(Boolean);
  const provenance = provenanceFragments.join(' · ');

  const actionSummary =
    params.summary && provenance
      ? `${params.summary}\n\n${provenance}`
      : params.summary || provenance || undefined;

  // Delegate to add_to_handover with entity_type = 'document'.
  // entity_id = document_id preserves the live relationship with doc_metadata;
  // source_doc_id is passed through action_summary until a dedicated schema
  // column exists (handover_items has no source_doc_id column today —
  // verified against TENANT vzsohavtuotocgrfkfyd on 2026-04-17).
  return addToHandover(context, {
    entity_id: params.document_id,
    entity_type: 'document',
    section: params.section || params.page_numbers,
    summary: params.summary,
    action_summary: actionSummary,
  });
}

/**
 * Add predictive insight to handover
 */
async function addPredictiveInsightToHandover(
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
 * Generate handover summary for current items
 *
 * After schema consolidation (2026-02-05), there's no parent handover record.
 * This generates a summary from all active handover_items for the yacht.
 */
async function regenerateHandoverSummary(
  context: ActionContext,
  params?: { department?: string }
): Promise<ActionResult> {
  try {
    // Route through Render API — GET /v1/handover/items
    const { data: sessionData } = await supabase.auth.getSession();
    const token = sessionData?.session?.access_token;
    if (!token) {
      return { success: false, action_name: 'regenerate_handover_summary', data: null,
        error: { code: 'FORBIDDEN', message: 'Authentication required' }, confirmation_required: false };
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
    const res = await fetch(`${apiUrl}/v1/handover/items`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      return { success: false, action_name: 'regenerate_handover_summary', data: null,
        error: { code: 'INTERNAL_ERROR', message: `Failed to fetch items (${res.status})` }, confirmation_required: false };
    }
    const json = await res.json();
    let items = (json.items || []) as Record<string, unknown>[];
    if (params?.department) {
      items = items.filter(i => i.section === params.department);
    }

    if (!items) {
      return {
        success: false,
        action_name: 'regenerate_handover_summary',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to fetch handover items' },
        confirmation_required: false,
      };
    }

    // Generate summary from items
    const summary = generateHandoverSummary(items || []);

    return {
      success: true,
      action_name: 'regenerate_handover_summary',
      data: {
        summary,
        item_count: items?.length || 0,
        department: params?.department || 'all',
        critical_count: items?.filter((i) => i.is_critical).length || 0,
        action_required_count: items?.filter((i) => i.requires_action).length || 0,
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
function generateHandoverSummary(
  items: Array<{
    entity_type?: string;
    summary?: string;
    is_critical?: boolean;
    requires_action?: boolean;
    category?: string;
  }>
): string {
  const faultCount = items.filter((i) => i.entity_type === 'fault').length;
  const woCount = items.filter((i) => i.entity_type === 'work_order').length;
  const equipmentCount = items.filter((i) => i.entity_type === 'equipment').length;
  const docCount = items.filter((i) => i.entity_type === 'document').length;
  const criticalCount = items.filter((i) => i.is_critical).length;
  const actionCount = items.filter((i) => i.requires_action).length;

  const parts: string[] = [];
  if (criticalCount > 0) parts.push(`${criticalCount} CRITICAL`);
  if (actionCount > 0) parts.push(`${actionCount} requiring action`);
  if (faultCount > 0) parts.push(`${faultCount} fault(s)`);
  if (woCount > 0) parts.push(`${woCount} work order(s)`);
  if (equipmentCount > 0) parts.push(`${equipmentCount} equipment item(s)`);
  if (docCount > 0) parts.push(`${docCount} document(s)`);

  return `Handover includes ${parts.length > 0 ? parts.join(', ') : 'no items'}.`;
}

/**
 * View related documents
 */
async function viewRelatedDocuments(
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
async function viewDocumentSection(
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
