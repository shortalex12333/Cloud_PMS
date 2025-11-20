/**
 * CelesteOS API Client
 *
 * Centralized API client for all CelesteOS backend services:
 * - Search Engine (Task 6)
 * - Predictive Engine (Task 7)
 * - Action Router (work orders, handovers, notes)
 *
 * Features:
 * - JWT authentication on all requests
 * - Streaming support for search
 * - Type-safe responses
 * - Consistent error handling
 * - Yacht signature handling
 */

// ============================================
// Types
// ============================================

export interface ApiConfig {
  baseUrl: string;
  searchEngineUrl?: string;
  predictiveEngineUrl?: string;
  getAuthToken: () => string | null;
  getYachtSignature: () => string | null;
}

export interface SearchRequest {
  query: string;
  mode?: 'auto' | 'standard' | 'deep';
  filters?: {
    equipment_id?: string;
    document_type?: string;
    date_range?: {
      start: string;
      end: string;
    };
  };
}

export interface SearchEntity {
  type: 'equipment' | 'fault_code' | 'part_number' | 'document_type' | 'action' | 'location';
  value: string;
  confidence?: number;
}

export interface SearchIntent {
  intent:
    | 'diagnose_fault'
    | 'find_document'
    | 'create_work_order'
    | 'add_to_handover'
    | 'find_part'
    | 'general_search'
    | 'predictive_request';
  confidence?: number;
}

export interface MicroAction {
  action: string;
  label: string;
  equipment_id?: string;
  context?: Record<string, any>;
}

export interface SearchResultCard {
  type:
    | 'document_chunk'
    | 'fault'
    | 'work_order'
    | 'part'
    | 'predictive'
    | 'handover'
    | 'equipment';
  title?: string;
  document_id?: string;
  chunk_index?: number;
  page_number?: number;
  text_preview?: string;
  score?: number;
  actions?: MicroAction[];
  metadata?: Record<string, any>;

  // Predictive card specific
  equipment?: string;
  equipment_id?: string;
  risk_score?: number;
  trend?: '↑' | '↓' | '→';
  summary?: string;
  severity?: 'low' | 'medium' | 'high' | 'critical';
  contributing_factors?: string[];
  recommendations?: string[];
}

export interface SearchResponse {
  query_id: string;
  intent: string;
  entities: Record<string, any>;
  results: SearchResultCard[];
  actions: MicroAction[];
  metadata?: {
    mode_used: string;
    retrieval_time_ms: number;
    total_results: number;
  };
}

export interface PredictiveState {
  id: string;
  yacht_id: string;
  equipment_id: string;
  equipment_name?: string;
  risk_score: number;
  trend: '↑' | '↓' | '→';
  fault_signal: number;
  work_order_signal: number;
  crew_signal: number;
  part_signal: number;
  global_signal: number;
  updated_at: string;
}

export interface PredictiveInsight {
  id: string;
  yacht_id: string;
  equipment_id?: string;
  equipment_name?: string;
  insight_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  summary: string;
  explanation: string;
  recommended_action?: string;
  contributing_signals?: Record<string, number>;
  related_entities?: Record<string, any>;
  created_at: string;
}

export interface CreateWorkOrderRequest {
  equipment_id: string;
  title: string;
  description: string;
  priority: 'routine' | 'important' | 'critical';
  type?: 'scheduled' | 'corrective' | 'unplanned';
}

export interface AddHandoverItemRequest {
  handover_id: string;
  source_type: 'work_order' | 'fault' | 'doc_chunk' | 'note' | 'part';
  source_id: string;
  summary: string;
  importance?: 'low' | 'normal' | 'high';
}

export interface CreateNoteRequest {
  text: string;
  equipment_id?: string;
  tags?: string[];
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data?: any
  ) {
    super(`API Error ${status}: ${statusText}`);
    this.name = 'ApiError';
  }
}

// ============================================
// API Client
// ============================================

export class CelesteApiClient {
  private config: ApiConfig;

  constructor(config: ApiConfig) {
    this.config = config;
  }

  // ============================================
  // Core Request Methods
  // ============================================

  private getHeaders(includeAuth = true): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    if (includeAuth) {
      const token = this.config.getAuthToken();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const yachtSignature = this.config.getYachtSignature();
      if (yachtSignature) {
        headers['X-Yacht-Signature'] = yachtSignature;
      }
    }

    return headers;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.config.baseUrl}${endpoint}`;

    const response = await fetch(url, {
      ...options,
      headers: {
        ...this.getHeaders(),
        ...options.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      throw new ApiError(response.status, response.statusText, errorData);
    }

    return response.json();
  }

  private async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  private async post<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  private async patch<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  private async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }

  // ============================================
  // Search Engine API (Task 6)
  // ============================================

  /**
   * Search with streaming support
   * Returns an async generator that yields results as they arrive
   */
  async *searchStream(request: SearchRequest): AsyncGenerator<SearchResultCard, void, unknown> {
    const searchUrl = this.config.searchEngineUrl || this.config.baseUrl;
    const url = `${searchUrl}/v1/search`;

    const response = await fetch(url, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new ApiError(response.status, response.statusText);
    }

    if (!response.body) {
      throw new Error('Response body is null');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete JSON objects (line by line)
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.trim()) {
            try {
              const card = JSON.parse(line) as SearchResultCard;
              yield card;
            } catch (e) {
              console.warn('Failed to parse search result:', line);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  /**
   * Search without streaming (returns all results at once)
   */
  async search(request: SearchRequest): Promise<SearchResponse> {
    const searchUrl = this.config.searchEngineUrl || this.config.baseUrl;
    return this.post<SearchResponse>(`${searchUrl}/v1/search`, request);
  }

  // ============================================
  // Predictive Engine API (Task 7)
  // ============================================

  /**
   * Get risk states for a yacht
   */
  async getPredictiveState(yachtId: string, equipmentId?: string): Promise<{
    yacht_id: string;
    total_equipment: number;
    high_risk_count: number;
    emerging_risk_count: number;
    monitor_count: number;
    normal_count: number;
    equipment_risks: PredictiveState[];
  }> {
    const predictiveUrl = this.config.predictiveEngineUrl || this.config.baseUrl;
    const params = new URLSearchParams({ yacht_id: yachtId });
    if (equipmentId) {
      params.append('equipment_id', equipmentId);
    }

    return this.get(`${predictiveUrl}/v1/predictive/state?${params}`);
  }

  /**
   * Get predictive insights for a yacht
   */
  async getPredictiveInsights(
    yachtId: string,
    minSeverity: 'low' | 'medium' | 'high' | 'critical' = 'low',
    limit = 50
  ): Promise<{
    yacht_id: string;
    total_insights: number;
    critical_count: number;
    high_count: number;
    medium_count: number;
    low_count: number;
    insights: PredictiveInsight[];
  }> {
    const predictiveUrl = this.config.predictiveEngineUrl || this.config.baseUrl;
    const params = new URLSearchParams({
      yacht_id: yachtId,
      min_severity: minSeverity,
      limit: limit.toString(),
    });

    return this.get(`${predictiveUrl}/v1/predictive/insights?${params}`);
  }

  /**
   * Get predictive card for equipment (for search integration)
   */
  async getPredictiveCard(equipmentId: string): Promise<SearchResultCard> {
    const predictiveUrl = this.config.predictiveEngineUrl || this.config.baseUrl;
    return this.get(`${predictiveUrl}/v1/predictive/predictive-cards/${equipmentId}`);
  }

  /**
   * Get detected anomalies for a yacht
   */
  async getAnomalies(yachtId: string): Promise<{
    yacht_id: string;
    total_anomalies: number;
    critical_anomalies: number;
    high_anomalies: number;
    moderate_anomalies: number;
    anomalies: any[];
  }> {
    const predictiveUrl = this.config.predictiveEngineUrl || this.config.baseUrl;
    const params = new URLSearchParams({ yacht_id: yachtId });
    return this.get(`${predictiveUrl}/v1/predictive/anomalies?${params}`);
  }

  /**
   * Trigger predictive computation for a yacht
   */
  async runPredictive(yachtId: string, forceRecalculate = false): Promise<{
    status: string;
    yacht_id: string;
    computed_at: string;
    summary: any;
  }> {
    const predictiveUrl = this.config.predictiveEngineUrl || this.config.baseUrl;
    const params = new URLSearchParams({
      yacht_id: yachtId,
      force_recalculate: forceRecalculate.toString(),
    });

    return this.post(`${predictiveUrl}/v1/predictive/run-for-yacht?${params}`);
  }

  // ============================================
  // Action Router API
  // ============================================

  /**
   * Create a work order
   */
  async createWorkOrder(request: CreateWorkOrderRequest): Promise<{ work_order_id: string }> {
    return this.post('/v1/work-order/create', request);
  }

  /**
   * Add item to handover
   */
  async addToHandover(request: AddHandoverItemRequest): Promise<{ item_id: string; status: string }> {
    return this.post('/v1/handover/add-item', request);
  }

  /**
   * Create a note
   */
  async createNote(request: CreateNoteRequest): Promise<{ note_id: string }> {
    return this.post('/v1/notes/create', request);
  }

  /**
   * Create a new handover draft
   */
  async createHandover(title: string, periodStart?: string, periodEnd?: string): Promise<{ handover_id: string }> {
    return this.post('/v1/handover/create', {
      title,
      period_start: periodStart,
      period_end: periodEnd,
    });
  }

  // ============================================
  // Dashboard Data API
  // ============================================

  /**
   * Get dashboard summary data
   */
  async getDashboardSummary(yachtId: string): Promise<{
    yacht_id: string;
    predictive_summary: any;
    recent_insights: PredictiveInsight[];
    high_risk_equipment: PredictiveState[];
    recent_faults: any[];
    overdue_work_orders: any[];
  }> {
    const params = new URLSearchParams({ yacht_id: yachtId });
    return this.get(`/v1/dashboard/summary?${params}`);
  }

  // ============================================
  // Health & Utility
  // ============================================

  /**
   * Check API health
   */
  async health(): Promise<{ status: string; service: string; version: string }> {
    return this.get('/health');
  }

  /**
   * Check predictive engine health
   */
  async predictiveHealth(): Promise<{ status: string; service: string; version: string }> {
    const predictiveUrl = this.config.predictiveEngineUrl || this.config.baseUrl;
    return this.get(`${predictiveUrl}/health`);
  }
}

// ============================================
// Singleton Instance (Optional)
// ============================================

let apiClientInstance: CelesteApiClient | null = null;

/**
 * Initialize the global API client
 */
export function initApiClient(config: ApiConfig): void {
  apiClientInstance = new CelesteApiClient(config);
}

/**
 * Get the global API client instance
 */
export function getApiClient(): CelesteApiClient {
  if (!apiClientInstance) {
    throw new Error('API client not initialized. Call initApiClient() first.');
  }
  return apiClientInstance;
}

/**
 * Create a new API client instance (for specific use cases)
 */
export function createApiClient(config: ApiConfig): CelesteApiClient {
  return new CelesteApiClient(config);
}

// ============================================
// Export default singleton getter
// ============================================

export default {
  init: initApiClient,
  get: getApiClient,
  create: createApiClient,
};
