/**
 * CelesteOS Search API - Type Definitions
 *
 * Option A (Minimal) Payload Contract:
 * - Identity extracted from JWT by backend
 * - Body contains only domain-specific fields
 */

// ============================================
// REQUEST TYPES
// ============================================

/**
 * Required headers for all CelesteOS API endpoints
 */
export interface CelesteHeaders {
  /** Format: "Bearer <supabase_jwt>" */
  authorization: string;
  /** Format: sha256(yacht_id + YACHT_SALT) */
  'x-yacht-signature': string;
  /** Must be "application/json" */
  'content-type': 'application/json';
}

/**
 * Search mode options
 */
export type SearchMode = 'auto' | 'standard' | 'deep';

/**
 * Document type filter options
 */
export type DocumentType =
  | 'manual'
  | 'drawing'
  | 'handover'
  | 'invoice'
  | 'email'
  | 'note'
  | 'work_order';

/**
 * Optional filters for search refinement
 */
export interface SearchFilters {
  equipment_id?: string;
  document_type?: DocumentType;
}

/**
 * Minimal search request body (Option A)
 *
 * IMPORTANT: Does NOT contain user_id or yacht_id
 * Backend extracts identity from JWT claims
 */
export interface SearchRequestBody {
  /** The user's search query */
  query: string;
  /** Search mode: auto, standard, or deep (GraphRAG) */
  mode?: SearchMode;
  /** Optional filters to narrow results */
  filters?: SearchFilters;
}

/**
 * Fields that MUST NOT appear in request body
 * These are security violations
 */
export interface ForbiddenBodyFields {
  user_id?: string;
  yacht_id?: string;
  jwt?: string;
  token?: string;
  authorization?: string;
  NEXT_PUBLIC_SUPABASE_URL?: string;
  [key: `NEXT_PUBLIC_${string}`]: string | undefined;
}

// ============================================
// RESPONSE TYPES
// ============================================

/**
 * Detected intent from query analysis
 */
export type SearchIntent =
  | 'diagnose_fault'
  | 'find_document'
  | 'create_work_order'
  | 'add_to_handover'
  | 'find_part'
  | 'predictive_request'
  | 'general_search';

/**
 * Extracted entities from query
 */
export interface ExtractedEntities {
  equipment_id?: string;
  equipment_name?: string;
  fault_code?: string;
  part_number?: string;
  document_type?: DocumentType;
  system_name?: string;
  location?: string;
  severity?: 'low' | 'medium' | 'high' | 'critical' | 'emergency';
}

/**
 * Base result card structure
 */
export interface BaseResultCard {
  type: string;
  score: number;
  actions: string[];
}

/**
 * Document chunk result card
 */
export interface DocumentChunkCard extends BaseResultCard {
  type: 'document_chunk';
  title: string;
  document_id: string;
  chunk_index: number;
  page_number?: number;
  text_preview: string;
}

/**
 * Fault result card
 */
export interface FaultCard extends BaseResultCard {
  type: 'fault';
  fault_code: string;
  equipment_id: string;
  summary: string;
}

/**
 * Work order result card
 */
export interface WorkOrderCard extends BaseResultCard {
  type: 'work_order';
  work_order_id: string;
  title: string;
  status: 'open' | 'in_progress' | 'completed' | 'cancelled';
}

/**
 * Part result card
 */
export interface PartCard extends BaseResultCard {
  type: 'part';
  part_id: string;
  name: string;
  part_number: string;
  in_stock: number;
  location?: string;
}

/**
 * Predictive insight card
 */
export interface PredictiveCard extends BaseResultCard {
  type: 'predictive';
  equipment: string;
  risk_score: number;
  summary: string;
}

/**
 * History event card
 */
export interface HistoryEventCard extends BaseResultCard {
  type: 'history_event';
  work_order_id: string;
  summary: string;
  date: string;
}

/**
 * Union of all result card types
 */
export type ResultCard =
  | DocumentChunkCard
  | FaultCard
  | WorkOrderCard
  | PartCard
  | PredictiveCard
  | HistoryEventCard;

/**
 * Micro-action attached to results
 */
export interface MicroAction {
  label: string;
  action: string;
  equipment_id?: string;
  context?: Record<string, unknown>;
}

/**
 * Full search response
 */
export interface SearchResponse {
  query_id: string;
  intent: SearchIntent;
  entities: ExtractedEntities;
  results: ResultCard[];
  actions: MicroAction[];
}

// ============================================
// JWT TYPES (Backend extracts these)
// ============================================

/**
 * JWT claims structure (extracted by backend, NOT sent by frontend)
 */
export interface JWTClaims {
  user_id: string;
  yacht_id: string;
  role: 'crew' | 'engineer' | 'hod' | 'captain' | 'admin';
  email: string;
  exp: number;
  iat: number;
}
