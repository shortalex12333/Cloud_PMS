// CelesteOS Type Definitions

export interface YachtSignature {
  id: string;
  yacht_id: string;
  signature: string;
  created_at: string;
}

export interface User {
  id: string;
  yacht_id: string;
  email: string;
  name: string;
  role: 'chief_engineer' | 'eto' | 'captain' | 'manager' | 'vendor' | 'crew';
  is_active: boolean;
  created_at: string;
}

export interface Equipment {
  id: string;
  yacht_id: string;
  parent_id?: string;
  name: string;
  code?: string;
  description: string;
  location?: string;
  manufacturer?: string;
  model?: string;
  serial_number?: string;
  installed_date?: string;
  criticality?: 'low' | 'medium' | 'high';
  system_type?: string;
  metadata?: Record<string, any>;
}

export interface WorkOrder {
  id: string;
  yacht_id: string;
  equipment_id?: string;
  title: string;
  description: string;
  type: 'scheduled' | 'corrective' | 'unplanned';
  priority: 'routine' | 'important' | 'critical';
  status: 'planned' | 'in_progress' | 'completed' | 'deferred' | 'cancelled';
  due_date?: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface Fault {
  id: string;
  yacht_id: string;
  equipment_id: string;
  fault_code?: string;
  title: string;
  description: string;
  severity: 'low' | 'medium' | 'high';
  detected_at: string;
  resolved_at?: string;
}

export interface Part {
  id: string;
  yacht_id: string;
  name: string;
  part_number: string;
  manufacturer?: string;
  description: string;
  category?: string;
  metadata?: Record<string, any>;
}

export interface Document {
  id: string;
  yacht_id: string;
  source: 'nas' | 'email' | 'upload' | 'migration';
  filename: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  storage_path: string;
  indexed: boolean;
  indexed_at?: string;
  created_at: string;
}

export interface DocumentChunk {
  id: string;
  yacht_id: string;
  document_id: string;
  chunk_index: number;
  text: string;
  page_number?: number;
  metadata?: Record<string, any>;
}

// Search Engine Types
export type SearchIntent =
  | 'diagnose_fault'
  | 'find_document'
  | 'create_work_order'
  | 'add_to_handover'
  | 'find_part'
  | 'general_search'
  | 'predictive_request';

export type ResultCardType =
  | 'document_chunk'
  | 'fault'
  | 'work_order'
  | 'part'
  | 'equipment'
  | 'predictive'
  | 'handover_item';

export type MicroAction =
  | 'create_work_order'
  | 'add_to_handover'
  | 'open_document'
  | 'order_part'
  | 'view_history'
  | 'show_predictive'
  | 'add_note'
  | 'attach_photo';

export interface SearchEntity {
  equipment_id?: string;
  fault_code?: string;
  part_number?: string;
  document_type?: string;
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
}

// Handover Types
export interface HandoverDraft {
  id: string;
  yacht_id: string;
  period_start?: string;
  period_end?: string;
  title: string;
  description: string;
  created_by: string;
  status: 'draft' | 'finalised';
  created_at: string;
}

export interface HandoverItem {
  id: string;
  handover_id: string;
  source_type: 'work_order' | 'fault' | 'doc_chunk' | 'note' | 'part';
  source_id: string;
  summary: string;
  detail?: string;
  importance: 'low' | 'normal' | 'high';
}

// Predictive Types
export interface PredictiveInsight {
  equipment_id: string;
  equipment_name: string;
  risk_score: number;
  summary: string;
  contributing_factors: string[];
  recommended_actions: string[];
}

// Dashboard Types
export interface DashboardMetrics {
  total_equipment: number;
  active_work_orders: number;
  overdue_tasks: number;
  high_risk_systems: number;
  parts_low_stock: number;
}
