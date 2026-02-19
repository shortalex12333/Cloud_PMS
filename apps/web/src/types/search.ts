// Search-specific TypeScript types

type ResultCardType =
  | 'document_chunk'
  | 'fault'
  | 'work_order'
  | 'part'
  | 'equipment'
  | 'predictive'
  | 'handover_item'
  | 'email'
  | 'note'
  // Backend source_table values (from result_normalizer.py)
  | 'pms_parts'
  | 'pms_equipment'
  | 'v_inventory'
  | 'search_fault_code_catalog'
  | 'search_document_chunks'
  | 'graph_nodes'
  | 'document';

type MicroAction =
  | 'create_work_order'
  | 'add_to_handover'
  | 'open_document'
  | 'order_part'
  | 'view_history'
  | 'show_predictive'
  | 'add_note'
  | 'attach_photo'
  | 'resolve_fault'
  | 'assign_task';

export interface SearchResult {
  type: ResultCardType;
  id: string;
  title: string;
  subtitle?: string;
  preview?: string;
  score: number;
  metadata?: Record<string, any>;
  actions: MicroAction[];
  timestamp?: string;
  source?: string;

  // Backend field names (for compatibility with result_normalizer.py)
  primary_id?: string;      // Backend uses primary_id instead of id
  source_table?: string;    // Backend uses source_table instead of type
  snippet?: string;         // Backend uses snippet instead of subtitle
  raw_data?: Record<string, any>; // Backend includes raw_data alongside metadata
}
