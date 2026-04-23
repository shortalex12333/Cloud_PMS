import { supabase } from '@/lib/supabaseClient';
import type { FetchParams, FetchResponse } from '@/features/entity-list/types';
import type { ReceivingItem, ReceivingAttachment } from '../types';

export async function fetchReceivingItems(params: FetchParams): Promise<FetchResponse<ReceivingItem>> {
  const { offset, limit } = params;

  const { data, count, error } = await supabase
    .from('pms_receiving')
    .select(
      'id, vendor_name, vendor_reference, status, received_date, notes, po_number, created_at',
      { count: 'exact' },
    )
    .order('created_at', { ascending: false })
    .range(offset, offset + limit - 1);

  if (error) {
    throw new Error(`Failed to fetch receiving items: ${error.message}`);
  }

  // Map DB column vendor_name to the TypeScript type's supplier_name
  const mapped = (data ?? []).map((row) => ({
    ...row,
    supplier_name: (row as Record<string, unknown>).vendor_name as string | undefined,
  }));

  return { data: mapped as ReceivingItem[], total: count ?? 0 };
}

export async function fetchReceivingItem(id: string, _token: string): Promise<ReceivingItem> {
  const { data, error } = await supabase
    .from('pms_receiving')
    .select(
      'id, vendor_name, vendor_reference, status, received_date, notes, po_number, created_at',
    )
    .eq('id', id)
    .single();

  if (error || !data) {
    throw new Error(`Receiving item ${id} not found`);
  }

  return {
    ...data,
    supplier_name: (data as Record<string, unknown>).vendor_name as string | undefined,
  } as ReceivingItem;
}

/**
 * Fetch attachments/documents for a receiving event.
 *
 * Action 6: view_receiving_photos (read-only escape hatch)
 * Purpose: View attached photos/documents
 * Allowed Roles: All Crew (read-only)
 * Tables Read: pms_receiving_documents (joined with pms_documents for file metadata)
 *
 * NOTE: This still calls the Python backend because it needs signed URLs
 * which require server-side storage token generation.
 */
export async function fetchReceivingAttachments(
  receivingId: string,
  token: string,
): Promise<ReceivingAttachment[]> {
  const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

  const response = await fetch(`${BASE_URL}/v1/actions/execute`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      action: 'view_receiving_history',
      params: {
        receiving_id: receivingId,
      },
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch receiving attachments: ${response.status}`);
  }

  const json = await response.json();
  const documents = json.documents || json.result?.documents || [];

  return documents.map((doc: Record<string, unknown>) => ({
    id: doc.id,
    receiving_id: doc.receiving_id,
    document_id: doc.document_id,
    doc_type: doc.doc_type || 'other',
    comment: doc.comment,
    created_at: doc.created_at,
    document: doc.document,
    url: doc.url || doc.signed_url,
  }));
}
