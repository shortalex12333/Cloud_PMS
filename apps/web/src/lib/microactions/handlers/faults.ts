/**
 * Fault Domain Handlers
 *
 * TypeScript handlers for fault-related microactions.
 * These handlers interact with Supabase to fetch and manipulate fault data.
 */

import type { ActionContext, ActionResult } from '../types';
import { supabase } from '@/lib/supabaseClient';

interface FaultData {
  id: string;
  yacht_id: string;
  equipment_id?: string;
  fault_code?: string;
  title?: string;
  description?: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  detected_at?: string;
  resolved_at?: string;
  created_at: string;
  is_active?: boolean;
  days_open?: number;
}

interface DiagnosisResult {
  fault: FaultData;
  diagnosis: {
    findings: Array<{
      id: string;
      finding: string;
      details: Record<string, unknown>;
    }>;
    finding_count: number;
  };
  remedies: {
    suggested_actions: Array<{
      id: string;
      action: string;
      procedure?: string;
      parts_needed?: string[];
      estimated_time?: number;
    }>;
    remedy_count: number;
  };
  history: {
    previous_occurrences: number;
    fault_code?: string;
  };
}

/**
 * Calculate days a fault has been open
 */
function calculateDaysOpen(fault: FaultData): number {
  const reportedAt = fault.detected_at || fault.created_at;
  if (!reportedAt) return 0;

  try {
    const reported = new Date(reportedAt);
    const end = fault.resolved_at ? new Date(fault.resolved_at) : new Date();
    return Math.floor((end.getTime() - reported.getTime()) / (1000 * 60 * 60 * 24));
  } catch {
    return 0;
  }
}

/**
 * View fault details
 */
export async function viewFault(
  context: ActionContext,
  params?: { fault_id?: string }
): Promise<ActionResult> {
  
  const faultId = params?.fault_id || context.entity_id;

  if (!faultId) {
    return {
      success: false,
      action_name: 'view_fault',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Fault ID is required' },
      confirmation_required: false,
    };
  }

  try {
    const { data: fault, error } = await supabase
      .from('pms_faults')
      .select('*')
      .eq('yacht_id', context.yacht_id)
      .eq('id', faultId)
      .single();

    if (error || !fault) {
      return {
        success: false,
        action_name: 'view_fault',
        data: null,
        error: { code: 'NOT_FOUND', message: `Fault not found: ${faultId}` },
        confirmation_required: false,
      };
    }

    // Add computed fields
    const enrichedFault: FaultData = {
      ...fault,
      is_active: !fault.resolved_at,
      days_open: calculateDaysOpen(fault),
    };

    // Get related work orders count
    const { count: woCount } = await supabase
      .from('pms_work_orders')
      .select('id', { count: 'exact', head: true })
      .eq('fault_id', faultId);

    return {
      success: true,
      action_name: 'view_fault',
      data: {
        fault: enrichedFault,
        related_work_orders_count: woCount || 0,
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'view_fault',
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
 * Diagnose fault - get analysis and suggested remedies
 */
export async function diagnoseFault(
  context: ActionContext,
  params?: { fault_id?: string }
): Promise<ActionResult> {
  
  const faultId = params?.fault_id || context.entity_id;

  if (!faultId) {
    return {
      success: false,
      action_name: 'diagnose_fault',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Fault ID is required' },
      confirmation_required: false,
    };
  }

  try {
    // Get fault details
    const { data: fault, error: faultError } = await supabase
      .from('pms_faults')
      .select('*')
      .eq('id', faultId)
      .single();

    if (faultError || !fault) {
      return {
        success: false,
        action_name: 'diagnose_fault',
        data: null,
        error: { code: 'NOT_FOUND', message: `Fault not found: ${faultId}` },
        confirmation_required: false,
      };
    }

    const faultCode = fault.fault_code;

    // Get diagnostic findings from graph edges (if available)
    const diagnosis: DiagnosisResult['diagnosis'] = { findings: [], finding_count: 0 };
    try {
      const { data: diagData } = await supabase
        .from('graph_edges')
        .select('target_id, properties')
        .eq('source_id', faultId)
        .eq('edge_type', 'DIAGNOSED_BY');

      if (diagData) {
        diagnosis.findings = diagData.map((d) => ({
          id: d.target_id,
          finding: d.properties?.label || 'Unknown finding',
          details: d.properties || {},
        }));
        diagnosis.finding_count = diagnosis.findings.length;
      }
    } catch {
      // Graph edges table may not exist
    }

    // Get suggested remedies from maintenance templates
    const remedies: DiagnosisResult['remedies'] = { suggested_actions: [], remedy_count: 0 };
    if (faultCode) {
      try {
        const { data: templateData } = await supabase
          .from('maintenance_templates')
          .select('id, action, procedure, parts_needed, estimated_time')
          .eq('fault_code', faultCode);

        if (templateData) {
          remedies.suggested_actions = templateData;
          remedies.remedy_count = templateData.length;
        }
      } catch {
        // Templates table may not exist
      }
    }

    // Get historical occurrences
    let historyCount = 0;
    if (faultCode) {
      const { count } = await supabase
        .from('pms_faults')
        .select('id', { count: 'exact', head: true })
        .eq('yacht_id', context.yacht_id)
        .eq('fault_code', faultCode);
      historyCount = count || 0;
    }

    const result: DiagnosisResult = {
      fault: {
        ...fault,
        is_active: !fault.resolved_at,
        days_open: calculateDaysOpen(fault),
      },
      diagnosis,
      remedies,
      history: {
        previous_occurrences: historyCount,
        fault_code: faultCode,
      },
    };

    return {
      success: true,
      action_name: 'diagnose_fault',
      data: result,
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'diagnose_fault',
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
 * View fault history for equipment or specific fault
 */
export async function viewFaultHistory(
  context: ActionContext,
  params?: { offset?: number; limit?: number }
): Promise<ActionResult> {
  
  const entityId = context.entity_id;
  const offset = params?.offset || 0;
  const limit = params?.limit || 20;

  try {
    // Query faults - entity_id could be fault or equipment
    const { data: faults, count, error } = await supabase
      .from('pms_faults')
      .select('id, fault_code, title, description, severity, detected_at, resolved_at', {
        count: 'exact',
      })
      .eq('yacht_id', context.yacht_id)
      .or(`id.eq.${entityId},equipment_id.eq.${entityId}`)
      .order('detected_at', { ascending: false })
      .range(offset, offset + limit - 1);

    if (error) {
      return {
        success: false,
        action_name: 'view_fault_history',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    const enrichedFaults = (faults || []).map((fault) => ({
      ...fault,
      is_active: !fault.resolved_at,
      days_open: calculateDaysOpen(fault as FaultData),
    }));

    const summary = {
      total: count || 0,
      active: enrichedFaults.filter((f) => f.is_active).length,
      by_severity: {
        critical: enrichedFaults.filter((f) => f.severity === 'critical').length,
        high: enrichedFaults.filter((f) => f.severity === 'high').length,
        medium: enrichedFaults.filter((f) => f.severity === 'medium').length,
        low: enrichedFaults.filter((f) => f.severity === 'low').length,
      },
    };

    return {
      success: true,
      action_name: 'view_fault_history',
      data: {
        entity_id: entityId,
        faults: enrichedFaults,
        summary,
        pagination: { offset, limit, total: count || 0 },
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'view_fault_history',
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
 * Suggest parts needed for fault repair
 */
export async function suggestParts(
  context: ActionContext,
  params?: { fault_id?: string }
): Promise<ActionResult> {
  
  const faultId = params?.fault_id || context.entity_id;

  if (!faultId) {
    return {
      success: false,
      action_name: 'suggest_parts',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Fault ID is required' },
      confirmation_required: false,
    };
  }

  try {
    // Get fault details
    const { data: fault, error: faultError } = await supabase
      .from('pms_faults')
      .select('id, fault_code, equipment_id')
      .eq('id', faultId)
      .single();

    if (faultError || !fault) {
      return {
        success: false,
        action_name: 'suggest_parts',
        data: null,
        error: { code: 'NOT_FOUND', message: `Fault not found: ${faultId}` },
        confirmation_required: false,
      };
    }

    // Get suggested parts from maintenance templates
    const partNames: string[] = [];
    if (fault.fault_code) {
      try {
        const { data: templates } = await supabase
          .from('maintenance_templates')
          .select('parts_needed')
          .eq('fault_code', fault.fault_code);

        for (const t of templates || []) {
          if (t.parts_needed) {
            if (Array.isArray(t.parts_needed)) {
              partNames.push(...t.parts_needed);
            } else if (typeof t.parts_needed === 'string') {
              partNames.push(t.parts_needed);
            }
          }
        }
      } catch {
        // Templates table may not exist
      }
    }

    // Get inventory status for suggested parts
    const suggestedParts: Array<{
      id: string;
      name: string;
      part_number?: string;
      stock_status: string;
      is_available: boolean;
    }> = [];

    if (partNames.length > 0) {
      const { data: parts } = await supabase
        .from('pms_parts')
        .select('id, name, part_number, description, category')
        .eq('yacht_id', context.yacht_id)
        .in('name', partNames);

      for (const part of parts || []) {
        suggestedParts.push({
          ...part,
          stock_status: 'UNKNOWN',
          is_available: true,
        });
      }
    }

    return {
      success: true,
      action_name: 'suggest_parts',
      data: {
        fault_id: faultId,
        fault_code: fault.fault_code,
        suggested_parts: suggestedParts,
        summary: {
          total_suggested: suggestedParts.length,
          available: suggestedParts.filter((p) => p.is_available).length,
          unavailable: suggestedParts.filter((p) => !p.is_available).length,
        },
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'suggest_parts',
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
 * Add note to fault
 */
export async function addFaultNote(
  context: ActionContext,
  params: { fault_id: string; note_text: string }
): Promise<ActionResult> {
  

  if (!params?.fault_id || !params?.note_text) {
    return {
      success: false,
      action_name: 'add_fault_note',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Fault ID and note text are required' },
      confirmation_required: false,
    };
  }

  try {
    // Insert note into attachments or notes table
    const { data, error } = await supabase
      .from('notes')
      .insert({
        entity_type: 'fault',
        entity_id: params.fault_id,
        content: params.note_text,
        created_by: context.user_id,
        yacht_id: context.yacht_id,
      })
      .select()
      .single();

    if (error) {
      return {
        success: false,
        action_name: 'add_fault_note',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    return {
      success: true,
      action_name: 'add_fault_note',
      data: { note: data },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'add_fault_note',
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
 * Add photo to fault
 */
export async function addFaultPhoto(
  context: ActionContext,
  params: {
    fault_id?: string;
    entity_type?: string;
    entity_id?: string;
    caption?: string;
    file_name?: string;
    file_size?: number;
    file_type?: string;
    photo_url?: string;
  }
): Promise<ActionResult> {
  const faultId = params?.fault_id || params?.entity_id || context.entity_id;

  if (!faultId) {
    return {
      success: false,
      action_name: 'add_fault_photo',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Fault ID is required' },
      confirmation_required: false,
    };
  }

  try {
    // In production, this would store photo metadata after upload
    const photoRecord = {
      entity_type: 'fault',
      entity_id: faultId,
      yacht_id: context.yacht_id,
      file_name: params?.file_name || 'photo.jpg',
      file_size: params?.file_size || 0,
      mime_type: params?.file_type || 'image/jpeg',
      caption: params?.caption || '',
      storage_path: params?.photo_url || `faults/${faultId}/${Date.now()}.jpg`,
      created_by: context.user_id,
      created_at: new Date().toISOString(),
    };

    // Try to insert into attachments table
    const { data, error } = await supabase
      .from('attachments')
      .insert(photoRecord)
      .select()
      .single();

    if (error) {
      return {
        success: false,
        action_name: 'add_fault_photo',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: error.message },
        confirmation_required: false,
      };
    }

    return {
      success: true,
      action_name: 'add_fault_photo',
      data: { attachment: data },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'add_fault_photo',
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
 * Create work order from fault
 */
export async function createWorkOrderFromFault(
  context: ActionContext,
  params: {
    fault_id: string;
    title?: string;
    priority?: 'low' | 'medium' | 'high' | 'critical';
    assignee_id?: string;
  }
): Promise<ActionResult> {
  

  if (!params?.fault_id) {
    return {
      success: false,
      action_name: 'create_work_order_from_fault',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Fault ID is required' },
      confirmation_required: false,
    };
  }

  try {
    // Get fault details
    const { data: fault, error: faultError } = await supabase
      .from('pms_faults')
      .select('*')
      .eq('id', params.fault_id)
      .single();

    if (faultError || !fault) {
      return {
        success: false,
        action_name: 'create_work_order_from_fault',
        data: null,
        error: { code: 'NOT_FOUND', message: `Fault not found: ${params.fault_id}` },
        confirmation_required: false,
      };
    }

    // Create work order
    const { data: workOrder, error: woError } = await supabase
      .from('pms_work_orders')
      .insert({
        yacht_id: context.yacht_id,
        fault_id: params.fault_id,
        equipment_id: fault.equipment_id,
        title: params.title || fault.title || 'Work Order from Fault',
        description: fault.description,
        priority: params.priority || 'medium',
        status: 'draft',
        assigned_to: params.assignee_id,
        created_by: context.user_id,
      })
      .select()
      .single();

    if (woError) {
      return {
        success: false,
        action_name: 'create_work_order_from_fault',
        data: null,
        error: { code: 'INTERNAL_ERROR', message: woError.message },
        confirmation_required: false,
      };
    }

    return {
      success: true,
      action_name: 'create_work_order_from_fault',
      data: {
        work_order: workOrder,
        fault_id: params.fault_id,
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'create_work_order_from_fault',
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
 * Show manual section for equipment/fault context
 * Matches Python handler: manual_handlers.py show_manual_section_execute
 */
export async function showManualSection(
  context: ActionContext,
  params?: {
    equipment_id?: string;
    fault_code?: string;
    section_id?: string;
  }
): Promise<ActionResult> {
  const equipmentId = params?.equipment_id || context.entity_id;

  if (!equipmentId) {
    return {
      success: false,
      action_name: 'show_manual_section',
      data: null,
      error: { code: 'VALIDATION_ERROR', message: 'Equipment ID is required' },
      confirmation_required: false,
    };
  }

  try {
    // 1. Get equipment details
    const { data: equipment, error: eqError } = await supabase
      .from('pms_equipment')
      .select('id, name, manufacturer, model')
      .eq('id', equipmentId)
      .eq('yacht_id', context.yacht_id)
      .single();

    if (eqError || !equipment) {
      return {
        success: false,
        action_name: 'show_manual_section',
        data: null,
        error: { code: 'NOT_FOUND', message: `Equipment not found: ${equipmentId}` },
        confirmation_required: false,
      };
    }

    // 2. Find manual (document) by manufacturer + model
    const { data: manuals } = await supabase
      .from('documents')
      .select('id, filename, oem, model, storage_path, doc_type, created_at')
      .eq('oem', equipment.manufacturer || '')
      .eq('model', equipment.model || '')
      .limit(1);

    const manual = manuals?.[0];

    if (!manual) {
      return {
        success: false,
        action_name: 'show_manual_section',
        data: null,
        error: {
          code: 'NOT_FOUND',
          message: `No manual available for ${equipment.manufacturer || ''} ${equipment.model || ''}`,
        },
        confirmation_required: false,
      };
    }

    // 3. Find relevant section
    let section: {
      id: string;
      text: string;
      page_number: number;
      chunk_index?: number;
      metadata?: Record<string, unknown>;
    } | null = null;

    if (params?.section_id) {
      // Direct section lookup
      const { data: sectionData } = await supabase
        .from('document_chunks')
        .select('id, text, page_number, chunk_index, metadata')
        .eq('id', params.section_id)
        .eq('document_id', manual.id)
        .single();

      if (!sectionData) {
        return {
          success: false,
          action_name: 'show_manual_section',
          data: null,
          error: { code: 'NOT_FOUND', message: `Section not found: ${params.section_id}` },
          confirmation_required: false,
        };
      }
      section = sectionData;
    } else if (params?.fault_code) {
      // Search for fault code in document chunks
      const { data: searchResults } = await supabase
        .from('document_chunks')
        .select('id, text, page_number, chunk_index, metadata')
        .eq('document_id', manual.id)
        .ilike('text', `%${params.fault_code}%`)
        .order('page_number')
        .limit(1);

      if (searchResults?.[0]) {
        section = searchResults[0];
      } else {
        // Fallback to first section
        const { data: fallback } = await supabase
          .from('document_chunks')
          .select('id, text, page_number, chunk_index, metadata')
          .eq('document_id', manual.id)
          .order('page_number')
          .limit(1);
        section = fallback?.[0] || null;
      }
    } else {
      // No fault_code or section_id - show first section
      const { data: firstSection } = await supabase
        .from('document_chunks')
        .select('id, text, page_number, chunk_index, metadata')
        .eq('document_id', manual.id)
        .order('page_number')
        .limit(1);
      section = firstSection?.[0] || null;
    }

    if (!section) {
      return {
        success: false,
        action_name: 'show_manual_section',
        data: null,
        error: { code: 'NOT_FOUND', message: 'No sections found in manual' },
        confirmation_required: false,
      };
    }

    // 4. Get related sections (nearby pages)
    const currentPage = section.page_number || 1;
    const { data: relatedData } = await supabase
      .from('document_chunks')
      .select('id, text, page_number, chunk_index, metadata')
      .eq('document_id', manual.id)
      .gte('page_number', Math.max(1, currentPage - 2))
      .lte('page_number', currentPage + 2)
      .neq('id', section.id)
      .order('page_number')
      .limit(5);

    const relatedSections = (relatedData || []).map((r) => ({
      id: r.id,
      title:
        (r.metadata as Record<string, unknown>)?.heading ||
        `Page ${r.page_number || '?'}`,
      page_number: r.page_number || 0,
    }));

    // 5. Generate signed URL (if storage_path exists)
    let signedUrl: string | null = null;
    if (manual.storage_path) {
      try {
        const { data: urlData } = await supabase.storage
          .from('documents')
          .createSignedUrl(manual.storage_path, 1800); // 30 min
        signedUrl = urlData?.signedUrl || null;
      } catch {
        // Signed URL generation may fail
      }
    }

    // 6. Extract section title
    const sectionMetadata = section.metadata as Record<string, unknown> | undefined;
    let sectionTitle = (sectionMetadata?.heading as string) || '';
    if (!sectionTitle) {
      const textLines = (section.text || '').split('\n');
      sectionTitle = textLines[0] || `Page ${section.page_number || '?'}`;
    }

    return {
      success: true,
      action_name: 'show_manual_section',
      data: {
        document: {
          id: manual.id,
          title: manual.filename || '',
          manufacturer: manual.oem || '',
          model: manual.model || '',
          storage_path: manual.storage_path || '',
          signed_url: signedUrl,
        },
        section: {
          id: section.id,
          title: sectionTitle,
          page_number: section.page_number || 0,
          text_preview: (section.text || '').substring(0, 500),
        },
        related_sections: relatedSections,
      },
      error: null,
      confirmation_required: false,
    };
  } catch (err) {
    return {
      success: false,
      action_name: 'show_manual_section',
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
 * Get all fault handlers for registration
 */
export const faultHandlers = {
  view_fault: viewFault,
  diagnose_fault: diagnoseFault,
  view_fault_history: viewFaultHistory,
  suggest_parts: suggestParts,
  add_fault_note: addFaultNote,
  add_fault_photo: addFaultPhoto,
  create_work_order_from_fault: createWorkOrderFromFault,
  show_manual_section: showManualSection,
};
