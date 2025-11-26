/**
 * CelesteOS Integration Layer - Type Definitions
 *
 * This file defines all data contracts between:
 * - Frontend ↔ Cloud API
 * - Cloud API ↔ Search Engine
 * - Cloud API ↔ Predictive Engine
 * - Cloud API ↔ Supabase
 *
 * DO NOT modify these types without updating all dependent services.
 */

// ============================================================================
// CORE ENTITIES
// ============================================================================

export interface Yacht {
  id: string;
  name: string;
  imo?: string;
  mmsi?: string;
  flag_state?: string;
  length_m?: number;
  status: 'active' | 'inactive' | 'demo';
  created_at: string;
  updated_at: string;
}

export interface User {
  id: string;
  yacht_id: string;
  email: string;
  name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type UserRole =
  | 'chief_engineer'
  | 'eto'
  | 'captain'
  | 'manager'
  | 'crew'
  | 'vendor';

// ============================================================================
// AUTHENTICATION
// ============================================================================

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  expires_at: number;
}

export interface AuthUser {
  user: User;
  yacht: Yacht;
  tokens: AuthTokens;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

// ============================================================================
// SEARCH ENGINE
// ============================================================================

export interface SearchRequest {
  query: string;
  mode?: 'auto' | 'standard' | 'deep';
  filters?: SearchFilters;
}

export interface SearchFilters {
  equipment_id?: string;
  document_type?: DocumentType;
  date_range?: {
    start: string;
    end: string;
  };
}

export type DocumentType =
  | 'manual'
  | 'drawing'
  | 'handover'
  | 'invoice'
  | 'email'
  | 'photo'
  | 'note';

export interface SearchResponse {
  query_id: string;
  intent: SearchIntent;
  entities: ExtractedEntities;
  results: SearchResultCard[];
  actions: MicroAction[];
  processing_time_ms: number;
}

export type SearchIntent =
  | 'diagnose_fault'
  | 'find_document'
  | 'create_work_order'
  | 'add_to_handover'
  | 'find_part'
  | 'general_search'
  | 'predictive_request';

export interface ExtractedEntities {
  equipment_id?: string;
  equipment_name?: string;
  fault_code?: string;
  part_number?: string;
  document_type?: DocumentType;
  severity?: 'normal' | 'urgent' | 'critical' | 'emergency';
  location?: string;
}

// ============================================================================
// SEARCH RESULT CARDS
// ============================================================================

export type SearchResultCard =
  | DocumentChunkCard
  | FaultCard
  | WorkOrderCard
  | PartCard
  | PredictiveCard
  | EquipmentCard;

export interface BaseCard {
  id: string;
  type: string;
  score: number;
  timestamp?: string;
}

export interface DocumentChunkCard extends BaseCard {
  type: 'document_chunk';
  title: string;
  document_id: string;
  chunk_index: number;
  page_number?: number;
  text_preview: string;
  actions: MicroAction[];
}

export interface FaultCard extends BaseCard {
  type: 'fault';
  fault_code: string;
  equipment_id: string;
  equipment_name: string;
  summary: string;
  severity: 'normal' | 'urgent' | 'critical';
  first_occurrence: string;
  last_occurrence: string;
  occurrence_count: number;
  actions: MicroAction[];
}

export interface WorkOrderCard extends BaseCard {
  type: 'work_order';
  work_order_id: string;
  title: string;
  status: WorkOrderStatus;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  equipment_id?: string;
  equipment_name?: string;
  assigned_to?: string;
  due_date?: string;
  actions: MicroAction[];
}

export type WorkOrderStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'cancelled'
  | 'overdue';

export interface PartCard extends BaseCard {
  type: 'part';
  part_id: string;
  name: string;
  part_number: string;
  manufacturer?: string;
  in_stock: number;
  min_quantity: number;
  location?: string;
  compatible_equipment: string[];
  actions: MicroAction[];
}

export interface PredictiveCard extends BaseCard {
  type: 'predictive';
  equipment_id: string;
  equipment_name: string;
  risk_score: number;
  risk_level: 'normal' | 'monitor' | 'emerging' | 'high';
  summary: string;
  contributing_factors: string[];
  recommended_actions: string[];
  actions: MicroAction[];
}

export interface EquipmentCard extends BaseCard {
  type: 'equipment';
  equipment_id: string;
  name: string;
  category: string;
  manufacturer?: string;
  model?: string;
  serial_number?: string;
  last_maintenance?: string;
  next_maintenance?: string;
  status: 'operational' | 'degraded' | 'failed' | 'maintenance';
  actions: MicroAction[];
}

// ============================================================================
// MICRO ACTIONS
// ============================================================================

export interface MicroAction {
  label: string;
  action: ActionType;
  context?: Record<string, any>;
  icon?: string;
  variant?: 'primary' | 'secondary' | 'danger';
}

export type ActionType =
  | 'create_work_order'
  | 'add_to_handover'
  | 'open_document'
  | 'order_part'
  | 'view_history'
  | 'show_predictive'
  | 'add_note'
  | 'attach_photo'
  | 'view_equipment'
  | 'update_inventory';

// ============================================================================
// EQUIPMENT
// ============================================================================

export interface Equipment {
  id: string;
  yacht_id: string;
  parent_id?: string;
  name: string;
  category: string;
  manufacturer?: string;
  model?: string;
  serial_number?: string;
  installation_date?: string;
  status: 'operational' | 'degraded' | 'failed' | 'maintenance';
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface EquipmentHierarchy extends Equipment {
  children?: EquipmentHierarchy[];
}

// ============================================================================
// WORK ORDERS
// ============================================================================

export interface WorkOrder {
  id: string;
  yacht_id: string;
  equipment_id?: string;
  title: string;
  description?: string;
  status: WorkOrderStatus;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  work_type: 'preventive' | 'corrective' | 'inspection' | 'modification';
  assigned_to?: string;
  scheduled_date?: string;
  due_date?: string;
  completed_date?: string;
  estimated_hours?: number;
  actual_hours?: number;
  parts_used?: string[];
  notes?: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface CreateWorkOrderRequest {
  equipment_id?: string;
  title: string;
  description?: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  work_type?: 'preventive' | 'corrective' | 'inspection' | 'modification';
  assigned_to?: string;
  scheduled_date?: string;
  due_date?: string;
}

// ============================================================================
// FAULTS
// ============================================================================

export interface Fault {
  id: string;
  yacht_id: string;
  equipment_id: string;
  fault_code: string;
  severity: 'normal' | 'urgent' | 'critical';
  description?: string;
  first_occurrence: string;
  last_occurrence: string;
  occurrence_count: number;
  resolved: boolean;
  resolved_at?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// PARTS & INVENTORY
// ============================================================================

export interface Part {
  id: string;
  yacht_id: string;
  part_number: string;
  name: string;
  description?: string;
  manufacturer?: string;
  category?: string;
  unit_price?: number;
  currency?: string;
  supplier_id?: string;
  compatible_equipment: string[];
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface StockLevel {
  id: string;
  yacht_id: string;
  part_id: string;
  quantity: number;
  min_quantity: number;
  max_quantity?: number;
  location?: string;
  last_counted?: string;
  last_restocked?: string;
  updated_at: string;
}

// ============================================================================
// HANDOVER
// ============================================================================

export interface Handover {
  id: string;
  yacht_id: string;
  title: string;
  period_start: string;
  period_end: string;
  status: 'draft' | 'finalized' | 'exported';
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface HandoverItem {
  id: string;
  handover_id: string;
  source_type: 'fault' | 'work_order' | 'note' | 'document' | 'predictive';
  source_id: string;
  summary: string;
  priority?: number;
  category?: string;
  added_at: string;
}

export interface CreateHandoverRequest {
  title: string;
  period_start: string;
  period_end: string;
}

export interface AddHandoverItemRequest {
  handover_id: string;
  source_type: 'fault' | 'work_order' | 'note' | 'document' | 'predictive';
  source_id: string;
  summary: string;
  priority?: number;
  category?: string;
}

export interface ExportHandoverRequest {
  handover_id: string;
  format: 'pdf' | 'html';
}

export interface ExportHandoverResponse {
  url: string;
  expires_at: string;
}

// ============================================================================
// PREDICTIVE MAINTENANCE
// ============================================================================

export interface PredictiveState {
  id: string;
  yacht_id: string;
  equipment_id: string;
  risk_score: number;
  risk_level: 'normal' | 'monitor' | 'emerging' | 'high';
  fault_signal: number;
  work_order_signal: number;
  crew_activity_signal: number;
  part_consumption_signal: number;
  global_knowledge_signal: number;
  summary: string;
  contributing_factors: string[];
  recommended_actions: string[];
  last_calculated: string;
  next_calculation?: string;
}

export interface PredictiveInsight {
  equipment_id: string;
  equipment_name: string;
  insight_type: 'risk' | 'pattern' | 'anomaly' | 'recommendation';
  severity: 'info' | 'warning' | 'critical';
  title: string;
  description: string;
  confidence: number;
  created_at: string;
}

// ============================================================================
// DOCUMENTS
// ============================================================================

export interface Document {
  id: string;
  yacht_id: string;
  filename: string;
  storage_path: string;
  sha256: string;
  size_bytes: number;
  source: 'nas' | 'email' | 'mobile' | 'web';
  document_type?: DocumentType;
  indexed: boolean;
  indexed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentChunk {
  id: string;
  yacht_id: string;
  document_id: string;
  chunk_index: number;
  page_number?: number;
  text: string;
  metadata?: Record<string, any>;
  created_at: string;
}

// ============================================================================
// INGESTION
// ============================================================================

export interface InitUploadRequest {
  filename: string;
  sha256: string;
  size_bytes: number;
  source: 'nas' | 'email' | 'mobile' | 'web';
}

export interface InitUploadResponse {
  upload_id: string;
  storage_key: string;
  expected_chunks: number;
}

export interface CompleteUploadRequest {
  upload_id: string;
  total_chunks: number;
  sha256: string;
  filename: string;
}

export interface CompleteUploadResponse {
  document_id: string;
  status: 'received' | 'processing' | 'indexed' | 'failed';
  queued_for_indexing: boolean;
}

// ============================================================================
// DASHBOARD
// ============================================================================

export interface DashboardOverview {
  high_risk_equipment: PredictiveState[];
  overdue_work_orders: WorkOrder[];
  low_stock_parts: Array<{
    part: Part;
    stock_level: StockLevel;
  }>;
  recent_faults: Fault[];
  upcoming_maintenance: WorkOrder[];
}

export interface EquipmentSummary {
  total: number;
  operational: number;
  degraded: number;
  failed: number;
  in_maintenance: number;
}

export interface WorkOrderSummary {
  total: number;
  pending: number;
  in_progress: number;
  completed: number;
  overdue: number;
}

export interface FaultSummary {
  total_active: number;
  critical: number;
  urgent: number;
  normal: number;
  resolved_last_30d: number;
}

// ============================================================================
// API RESPONSE WRAPPERS
// ============================================================================

export interface ApiResponse<T> {
  data: T;
  timestamp: string;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, any>;
  };
  timestamp: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    page_size: number;
    total_count: number;
    total_pages: number;
  };
  timestamp: string;
}

// ============================================================================
// STREAMING
// ============================================================================

export interface StreamEvent<T> {
  type: 'data' | 'error' | 'complete';
  data?: T;
  error?: string;
  timestamp: string;
}
