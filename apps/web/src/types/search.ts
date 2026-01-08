// Search-specific TypeScript types

export type SearchIntent =
  | 'diagnose_fault'
  | 'find_document'
  | 'create_work_order'
  | 'add_to_handover'
  | 'find_part'
  | 'general_search'
  | 'predictive_request'
  | 'show_history';

export type ResultCardType =
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

export type MicroAction =
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

export interface SearchEntity {
  equipment_id?: string;
  equipment_name?: string;
  fault_code?: string;
  part_number?: string;
  document_type?: string;
  system_type?: string;
  [key: string]: any;
}

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

export interface SearchResponse {
  query_id: string;
  intent: SearchIntent;
  entities: SearchEntity;
  results: SearchResult[];
  actions: Array<{
    label: string;
    action: MicroAction;
    context?: Record<string, any>;
  }>;
  total_results?: number;
  search_time_ms?: number;
}

export interface SearchFilters {
  equipment_id?: string;
  date_from?: string;
  date_to?: string;
  result_types?: ResultCardType[];
  min_score?: number;
}

export interface SearchHistory {
  id: string;
  query: string;
  timestamp: string;
  results_count: number;
  intent?: SearchIntent;
}

// Streaming search state
export interface SearchStreamState {
  query: string;
  loading: boolean;
  streaming: boolean;
  results: SearchResult[];
  error?: string;
  complete: boolean;
}
