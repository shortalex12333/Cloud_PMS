/**
 * CelesteOS API Contracts - Worker 9 Integration Layer
 *
 * CANONICAL TYPE DEFINITIONS for all cross-service communication.
 * All workers MUST conform to these types.
 *
 * Services:
 * - Frontend ↔ Cloud API
 * - Cloud API ↔ Search Engine
 * - Cloud API ↔ Action Router
 * - Cloud API ↔ Predictive Engine
 * - Cloud API ↔ GraphRAG
 *
 * DO NOT modify without coordinating with Workers 2, 3, 6, 7.
 */

// ============================================================================
// SEARCH CONTRACTS
// ============================================================================

/**
 * Search request sent to POST /webhook/search
 */
export interface CelesteSearchRequest {
  query: string;
  mode?: 'auto' | 'standard' | 'deep';
  stream?: boolean;
  filters?: CelesteSearchFilters;
  context?: {
    yacht_id?: string;
    equipment_id?: string;
    user_role?: string;
  };
}

export interface CelesteSearchFilters {
  equipment_id?: string;
  document_type?: string[];
  result_types?: SearchResultType[];
  date_range?: {
    start: string;  // ISO 8601
    end: string;    // ISO 8601
  };
  min_score?: number;
}

export type SearchResultType =
  | 'document_chunk'
  | 'fault'
  | 'work_order'
  | 'part'
  | 'equipment'
  | 'predictive'
  | 'handover_item'
  | 'email'
  | 'note';

export type SearchIntent =
  | 'diagnose_fault'
  | 'find_document'
  | 'create_work_order'
  | 'add_to_handover'
  | 'find_part'
  | 'general_search'
  | 'predictive_request'
  | 'show_history';

/**
 * Search response from POST /webhook/search
 */
export interface CelesteSearchResponse {
  query_id: string;
  intent: SearchIntent;
  entities: SearchEntities;
  results: SearchResultCard[];
  suggested_actions: SuggestedAction[];
  total_results: number;
  search_time_ms: number;
  streaming_complete?: boolean;
}

export interface SearchEntities {
  equipment_id?: string;
  equipment_name?: string;
  fault_code?: string;
  part_number?: string;
  document_type?: string;
  system_type?: string;
  severity?: 'normal' | 'urgent' | 'critical' | 'emergency';
}

/**
 * Unified search result card - all result types extend this
 */
export interface SearchResultCard {
  id: string;
  type: SearchResultType;
  title: string;
  subtitle?: string;
  preview?: string;
  score: number;
  timestamp?: string;
  source?: string;
  metadata?: Record<string, unknown>;
  actions: MicroActionType[];
}

export interface SuggestedAction {
  label: string;
  action: MicroActionType;
  context?: Record<string, unknown>;
  icon?: string;
  variant?: 'primary' | 'secondary' | 'danger';
}

// ============================================================================
// ACTION ROUTER CONTRACTS
// ============================================================================

/**
 * All supported action types
 */
export type MicroActionType =
  | 'create_work_order'
  | 'add_to_handover'
  | 'open_document'
  | 'order_part'
  | 'view_history'
  | 'show_predictive'
  | 'add_note'
  | 'attach_photo'
  | 'resolve_fault'
  | 'assign_task'
  | 'close_work_order'
  | 'export_handover';

/**
 * Action request sent to POST /v1/actions/execute
 */
export interface CelesteActionRequest {
  action: MicroActionType;
  context: ActionContext;
  payload: Record<string, unknown>;
}

export interface ActionContext {
  yacht_id: string;
  user_id?: string;
  equipment_id?: string;
  fault_id?: string;
  work_order_id?: string;
  handover_id?: string;
  document_id?: string;
  part_id?: string;
  predictive_id?: string;
}

/**
 * Action response from POST /v1/actions/execute
 */
export interface CelesteActionResponse {
  status: 'success' | 'error';
  action: MicroActionType;
  result?: ActionResult;
  error_code?: ActionErrorCode;
  message?: string;
  timestamp: string;
}

export interface ActionResult {
  created_id?: string;
  updated_count?: number;
  redirect_url?: string;
  data?: Record<string, unknown>;
}

export type ActionErrorCode =
  | 'unauthenticated'
  | 'unauthorized'
  | 'invalid_action'
  | 'invalid_context'
  | 'invalid_payload'
  | 'resource_not_found'
  | 'validation_failed'
  | 'execution_failed'
  | 'network_error'
  | 'unknown_error';

// ============================================================================
// PREDICTIVE ENGINE CONTRACTS
// ============================================================================

/**
 * Predictive state for equipment - from GET /v1/predictive/{equipment_id}
 */
export interface PredictiveState {
  id: string;
  yacht_id: string;
  equipment_id: string;
  equipment_name: string;

  // Risk assessment
  risk_score: number;           // 0.0 - 1.0
  risk_level: RiskLevel;

  // Signal breakdown (each 0.0 - 1.0)
  signals: {
    fault_signal: number;
    work_order_signal: number;
    crew_activity_signal: number;
    part_consumption_signal: number;
    global_knowledge_signal: number;
  };

  // Analysis
  summary: string;
  contributing_factors: string[];
  recommended_actions: string[];

  // Timestamps
  last_calculated: string;      // ISO 8601
  next_calculation?: string;    // ISO 8601
}

export type RiskLevel = 'normal' | 'monitor' | 'emerging' | 'high' | 'critical';

/**
 * Predictive insight - individual finding
 */
export interface PredictiveInsight {
  id: string;
  equipment_id: string;
  equipment_name: string;
  insight_type: 'risk' | 'pattern' | 'anomaly' | 'recommendation';
  severity: 'info' | 'warning' | 'critical';
  title: string;
  description: string;
  confidence: number;           // 0.0 - 1.0
  created_at: string;           // ISO 8601
  trend?: 'improving' | 'stable' | 'degrading';
}

/**
 * Dashboard predictive overview
 */
export interface PredictiveOverview {
  high_risk_count: number;
  emerging_risk_count: number;
  equipment_states: PredictiveState[];
  recent_insights: PredictiveInsight[];
  last_updated: string;
}

// ============================================================================
// STREAMING CONTRACTS
// ============================================================================

/**
 * Line-delimited JSON stream event
 */
export interface StreamEvent<T = unknown> {
  type: 'data' | 'progress' | 'error' | 'complete';
  data?: T;
  progress?: {
    current: number;
    total: number;
    phase?: string;
  };
  error?: {
    code: string;
    message: string;
  };
  timestamp: string;
}

/**
 * Search stream chunk
 */
export interface SearchStreamChunk {
  type: 'result' | 'intent' | 'entities' | 'action' | 'complete';
  result?: SearchResultCard;
  intent?: SearchIntent;
  entities?: SearchEntities;
  action?: SuggestedAction;
  query_id?: string;
  total_results?: number;
  search_time_ms?: number;
}

// ============================================================================
// API RESPONSE WRAPPERS
// ============================================================================

export interface ApiSuccessResponse<T> {
  success: true;
  data: T;
  timestamp: string;
}

export interface ApiErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
  timestamp: string;
}

export type ApiResponse<T> = ApiSuccessResponse<T> | ApiErrorResponse;

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    page_size: number;
    total_count: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
  timestamp: string;
}

// ============================================================================
// EQUIPMENT & DASHBOARD CONTRACTS
// ============================================================================

export interface EquipmentStats {
  total: number;
  operational: number;
  needs_attention: number;
  critical: number;
}

export interface WorkOrderStats {
  open: number;
  in_progress: number;
  overdue: number;
  completed_this_week: number;
}

export interface DashboardMetrics {
  equipment_stats: EquipmentStats;
  work_order_stats: WorkOrderStats;
  predictive_overview: PredictiveOverview;
  recent_faults: Array<{
    id: string;
    fault_code: string;
    equipment_name: string;
    severity: string;
    occurred_at: string;
  }>;
}

// ============================================================================
// TYPE GUARDS
// ============================================================================

export function isApiError(response: ApiResponse<unknown>): response is ApiErrorResponse {
  return !response.success;
}

export function isSearchResultCard(obj: unknown): obj is SearchResultCard {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'id' in obj &&
    'type' in obj &&
    'title' in obj &&
    'score' in obj
  );
}

export function isPredictiveState(obj: unknown): obj is PredictiveState {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'equipment_id' in obj &&
    'risk_score' in obj &&
    'risk_level' in obj
  );
}
