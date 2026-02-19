/**
 * Save Extracted Receiving Data
 *
 * Handles saving OCR/AI extracted data from uploaded documents to Supabase
 * Tables: pms_receiving_documents, pms_receiving_extractions
 */

import { supabase } from '@/lib/supabaseClient';

/**
 * Save extracted data to receiving record
 *
 * Flow:
 * 1. Insert document link to pms_receiving_documents
 * 2. Insert extraction results to pms_receiving_extractions (advisory)
 * 3. Return success status
 *
 * @param receivingId - UUID of receiving record
 * @param yachtId - UUID of yacht (for RLS)
 * @param documentId - UUID of uploaded document
 * @param docType - Document type (invoice, packing_slip, photo, other)
 * @param comment - Optional comment
 * @param extractedData - Extracted data from image-processing service
 * @returns Success status
 */
export async function saveExtractedData(
  receivingId: string,
  yachtId: string,
  documentId: string,
  docType: 'invoice' | 'packing_slip' | 'photo' | 'other',
  comment: string | undefined,
  extractedData: any
): Promise<{ success: boolean; error?: string }> {
  try {
    // Step 1: Link document to receiving record
    const { error: docError } = await supabase
      .from('pms_receiving_documents')
      .insert({
        yacht_id: yachtId,
        receiving_id: receivingId,
        document_id: documentId,
        doc_type: docType,
        comment: comment || null,
      });

    if (docError) {
      console.error('[saveExtractedData] Failed to link document:', docError);
      return {
        success: false,
        error: `Failed to link document: ${docError.message}`,
      };
    }

    // Step 2: Save extraction results (advisory only)
    if (extractedData && Object.keys(extractedData).length > 0) {
      const { error: extractionError } = await supabase
        .from('pms_receiving_extractions')
        .insert({
          yacht_id: yachtId,
          receiving_id: receivingId,
          source_document_id: documentId,
          payload: extractedData,
        });

      if (extractionError) {
        console.error('[saveExtractedData] Failed to save extraction:', extractionError);
        // Don't fail the entire operation if extraction save fails
        console.warn('Document linked but extraction results not saved');
      }
    }

    return { success: true };
  } catch (err) {
    console.error('[saveExtractedData] Unexpected error:', err);
    return {
      success: false,
      error: err instanceof Error ? err.message : 'Unknown error',
    };
  }
}

/**
 * Auto-populate line items from extraction (optional)
 *
 * Creates draft line items in pms_receiving_items from extracted data
 * User must review and approve before finalizing
 *
 * @param receivingId - UUID of receiving record
 * @param yachtId - UUID of yacht (for RLS)
 * @param lineItems - Extracted line items
 * @returns Success status
 */
export async function autoPopulateLineItems(
  receivingId: string,
  yachtId: string,
  lineItems: Array<{
    description: string;
    quantity?: number;
    unit_price?: number;
    currency?: string;
  }>
): Promise<{ success: boolean; inserted: number; error?: string }> {
  try {
    if (!lineItems || lineItems.length === 0) {
      return { success: true, inserted: 0 };
    }

    const items = lineItems.map((item) => ({
      yacht_id: yachtId,
      receiving_id: receivingId,
      description: item.description,
      quantity_received: item.quantity || 0,
      unit_price: item.unit_price || null,
      currency: item.currency || null,
      properties: {
        auto_populated: true,
        source: 'ocr_extraction',
      },
    }));

    const { data, error } = await supabase
      .from('pms_receiving_items')
      .insert(items)
      .select();

    if (error) {
      console.error('[autoPopulateLineItems] Failed to insert items:', error);
      return {
        success: false,
        inserted: 0,
        error: error.message,
      };
    }

    return {
      success: true,
      inserted: data?.length || 0,
    };
  } catch (err) {
    console.error('[autoPopulateLineItems] Unexpected error:', err);
    return {
      success: false,
      inserted: 0,
      error: err instanceof Error ? err.message : 'Unknown error',
    };
  }
}

/**
 * Update receiving header from extraction
 *
 * Optionally update vendor info and totals from extraction
 * Only updates if fields are currently empty
 *
 * @param receivingId - UUID of receiving record
 * @param extractedData - Extracted data
 * @returns Success status
 */
export async function updateReceivingHeader(
  receivingId: string,
  extractedData: {
    vendor_name?: string;
    vendor_reference?: string;
    total?: number;
    currency?: string;
  }
): Promise<{ success: boolean; error?: string }> {
  try {
    // Fetch current receiving record to avoid overwriting user data
    const { data: current, error: fetchError } = await supabase
      .from('pms_receiving')
      .select('vendor_name, vendor_reference, total, currency')
      .eq('id', receivingId)
      .single();

    if (fetchError) {
      console.error('[updateReceivingHeader] Failed to fetch current record:', fetchError);
      return { success: false, error: fetchError.message };
    }

    // Build update object (only update empty fields)
    const updates: Record<string, any> = {};
    if (!current.vendor_name && extractedData.vendor_name) {
      updates.vendor_name = extractedData.vendor_name;
    }
    if (!current.vendor_reference && extractedData.vendor_reference) {
      updates.vendor_reference = extractedData.vendor_reference;
    }
    if (!current.total && extractedData.total) {
      updates.total = extractedData.total;
    }
    if (!current.currency && extractedData.currency) {
      updates.currency = extractedData.currency;
    }

    // Only update if there are changes
    if (Object.keys(updates).length === 0) {
      return { success: true };
    }

    const { error: updateError } = await supabase
      .from('pms_receiving')
      .update(updates)
      .eq('id', receivingId);

    if (updateError) {
      console.error('[updateReceivingHeader] Failed to update:', updateError);
      return { success: false, error: updateError.message };
    }

    return { success: true };
  } catch (err) {
    console.error('[updateReceivingHeader] Unexpected error:', err);
    return {
      success: false,
      error: err instanceof Error ? err.message : 'Unknown error',
    };
  }
}
