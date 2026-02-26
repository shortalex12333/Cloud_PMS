import type { FetchParams, FetchResponse } from '@/features/entity-list/types';
import type { ReceivingItem, ReceivingAttachment } from './types';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

export async function fetchReceivingItems(params: FetchParams): Promise<FetchResponse<ReceivingItem>> {
  const { yachtId, token, offset, limit } = params;

  const url = new URL(`${BASE_URL}/v1/receiving`);
  url.searchParams.set('yacht_id', yachtId);
  url.searchParams.set('offset', String(offset));
  url.searchParams.set('limit', String(limit));

  const response = await fetch(url.toString(), {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch receiving items: ${response.status}`);
  }

  const json = await response.json();
  const items = json.receiving || json.items || json.data || [];
  const total = json.total ?? json.pagination?.total ?? items.length;

  return { data: items, total };
}

export async function fetchReceivingItem(id: string, token: string): Promise<ReceivingItem> {
  const response = await fetch(`${BASE_URL}/v1/entity/receiving/${id}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch receiving item: ${response.status}`);
  }

  return response.json();
}

/**
 * Fetch attachments/documents for a receiving event.
 *
 * Action 6: view_receiving_photos (read-only escape hatch)
 * Purpose: View attached photos/documents
 * Allowed Roles: All Crew (read-only)
 * Tables Read: pms_receiving_documents (joined with pms_documents for file metadata)
 *
 * @param receivingId - The receiving event ID
 * @param token - JWT auth token
 * @returns Array of receiving attachments with document metadata and signed URLs
 */
export async function fetchReceivingAttachments(
  receivingId: string,
  token: string
): Promise<ReceivingAttachment[]> {
  // Use the view_receiving_history action which returns documents
  // This is more efficient than a separate endpoint and reuses existing backend logic
  const response = await fetch(`${BASE_URL}/v1/actions/execute`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
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

  // Extract documents from the response
  const documents = json.documents || json.result?.documents || [];

  // Map to ReceivingAttachment format with signed URLs
  // The backend returns document metadata; we need to fetch signed URLs for display
  return documents.map((doc: any) => ({
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
