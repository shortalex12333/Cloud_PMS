export interface ReceivingItem {
  id: string;
  receiving_number?: string;
  supplier_name?: string;
  description?: string;
  status: string;
  received_date?: string;
  expected_date?: string;
  items_count?: number;
  total_value?: number;
  currency?: string;
  notes?: string;
  created_at: string;
  updated_at?: string;
}

/**
 * Receiving attachment/document from pms_receiving_documents
 * Linked via receiving_id to a receiving event
 */
export interface ReceivingAttachment {
  id: string;
  receiving_id: string;
  document_id: string;
  doc_type: 'invoice' | 'packing_slip' | 'photo' | 'other';
  comment?: string;
  created_at: string;
  /** Resolved document metadata (from pms_documents join or separate fetch) */
  document?: {
    id: string;
    filename: string;
    storage_path: string;
    mime_type: string;
    size_bytes: number;
  };
  /** Signed URL for display (resolved by API or client) */
  url?: string;
}
