/**
 * CelesteOS Cloud API Client
 *
 * Typed wrapper for all Cloud API endpoints.
 * This is the ONLY way frontend communicates with backend services.
 *
 * Architecture:
 * Frontend → api.ts → Cloud API → Search Engine / Predictive Engine / Supabase
 *
 * DO NOT call Supabase directly for business logic.
 * DO NOT call Search/Predictive engines directly.
 * ALL calls go through Cloud API.
 */

import {
  ApiResponse,
  ApiError,
  PaginatedResponse,
  SearchRequest,
  SearchResponse,
  StreamEvent,
  WorkOrder,
  CreateWorkOrderRequest,
  Fault,
  Part,
  StockLevel,
  Equipment,
  EquipmentHierarchy,
  Handover,
  HandoverItem,
  CreateHandoverRequest,
  AddHandoverItemRequest,
  ExportHandoverRequest,
  ExportHandoverResponse,
  PredictiveState,
  PredictiveInsight,
  Document,
  InitUploadRequest,
  InitUploadResponse,
  CompleteUploadRequest,
  CompleteUploadResponse,
  DashboardOverview,
  EquipmentSummary,
  WorkOrderSummary,
  FaultSummary,
  User,
} from '../types';
import { getAccessToken } from './supabase';

// ============================================================================
// CONFIGURATION
// ============================================================================

const CLOUD_API_URL = process.env.NEXT_PUBLIC_CLOUD_API_URL || '';
const SEARCH_ENGINE_URL = process.env.NEXT_PUBLIC_SEARCH_ENGINE_URL || '';
const PREDICTIVE_ENGINE_URL = process.env.NEXT_PUBLIC_PREDICTIVE_ENGINE_URL || '';

if (!CLOUD_API_URL) {
  console.warn('CLOUD_API_URL not configured');
}

// ============================================================================
// HTTP CLIENT
// ============================================================================

class APIClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  /**
   * Get authorization headers with JWT
   */
  private async getHeaders(includeAuth = true): Promise<HeadersInit> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    if (includeAuth) {
      const token = await getAccessToken();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    }

    return headers;
  }

  /**
   * Handle API response
   */
  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        error: {
          code: 'UNKNOWN_ERROR',
          message: response.statusText,
        },
        timestamp: new Date().toISOString(),
      }));

      throw new APIError(
        error.error.message,
        response.status,
        error.error.code,
        error.error.details
      );
    }

    return response.json();
  }

  /**
   * GET request
   */
  async get<T>(
    endpoint: string,
    params?: Record<string, string>,
    includeAuth = true
  ): Promise<T> {
    const url = new URL(`${this.baseUrl}${endpoint}`);

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.append(key, value);
      });
    }

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: await this.getHeaders(includeAuth),
    });

    return this.handleResponse<T>(response);
  }

  /**
   * POST request
   */
  async post<T>(
    endpoint: string,
    body?: any,
    includeAuth = true
  ): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'POST',
      headers: await this.getHeaders(includeAuth),
      body: body ? JSON.stringify(body) : undefined,
    });

    return this.handleResponse<T>(response);
  }

  /**
   * PATCH request
   */
  async patch<T>(
    endpoint: string,
    body?: any,
    includeAuth = true
  ): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'PATCH',
      headers: await this.getHeaders(includeAuth),
      body: body ? JSON.stringify(body) : undefined,
    });

    return this.handleResponse<T>(response);
  }

  /**
   * DELETE request
   */
  async delete<T>(
    endpoint: string,
    includeAuth = true
  ): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'DELETE',
      headers: await this.getHeaders(includeAuth),
    });

    return this.handleResponse<T>(response);
  }

  /**
   * Stream SSE (Server-Sent Events)
   */
  async *stream<T>(
    endpoint: string,
    params?: Record<string, string>
  ): AsyncGenerator<StreamEvent<T>, void, unknown> {
    const url = new URL(`${this.baseUrl}${endpoint}`);

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.append(key, value);
      });
    }

    const token = await getAccessToken();
    const headers: HeadersInit = {
      Accept: 'text/event-stream',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers,
    });

    if (!response.ok) {
      throw new Error(`Stream failed: ${response.statusText}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('No response body');
    }

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          yield {
            type: 'complete',
            timestamp: new Date().toISOString(),
          };
          break;
        }

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            try {
              const parsed = JSON.parse(data);
              yield {
                type: 'data',
                data: parsed as T,
                timestamp: new Date().toISOString(),
              };
            } catch (error) {
              console.error('Failed to parse SSE data:', error);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }
}

// ============================================================================
// API ERROR CLASS
// ============================================================================

export class APIError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public code: string,
    public details?: Record<string, any>
  ) {
    super(message);
    this.name = 'APIError';
  }
}

// ============================================================================
// API CLIENTS
// ============================================================================

const cloudAPI = new APIClient(CLOUD_API_URL);

// ============================================================================
// SEARCH API
// ============================================================================

export const searchAPI = {
  /**
   * Perform search query
   * GET /v1/search
   */
  async search(request: SearchRequest): Promise<SearchResponse> {
    const params: Record<string, string> = {
      q: request.query,
    };

    if (request.mode) {
      params.mode = request.mode;
    }

    if (request.filters?.equipment_id) {
      params.equipment_id = request.filters.equipment_id;
    }

    if (request.filters?.document_type) {
      params.document_type = request.filters.document_type;
    }

    return cloudAPI.get<ApiResponse<SearchResponse>>('/v1/search', params)
      .then(res => res.data);
  },

  /**
   * Stream search results
   */
  streamSearch(request: SearchRequest): AsyncGenerator<StreamEvent<SearchResponse>, void, unknown> {
    const params: Record<string, string> = {
      q: request.query,
      stream: 'true',
    };

    if (request.mode) {
      params.mode = request.mode;
    }

    return cloudAPI.stream<SearchResponse>('/v1/search', params);
  },
};

// ============================================================================
// PREDICTIVE API
// ============================================================================

export const predictiveAPI = {
  /**
   * Get predictive state for all equipment
   * GET /v1/predictive/state
   */
  async getState(): Promise<PredictiveState[]> {
    return cloudAPI.get<ApiResponse<PredictiveState[]>>('/v1/predictive/state')
      .then(res => res.data);
  },

  /**
   * Get predictive state for specific equipment
   * GET /v1/predictive/state/:equipmentId
   */
  async getEquipmentState(equipmentId: string): Promise<PredictiveState> {
    return cloudAPI.get<ApiResponse<PredictiveState>>(`/v1/predictive/state/${equipmentId}`)
      .then(res => res.data);
  },

  /**
   * Get predictive insights
   * GET /v1/predictive/insights
   */
  async getInsights(): Promise<PredictiveInsight[]> {
    return cloudAPI.get<ApiResponse<PredictiveInsight[]>>('/v1/predictive/insights')
      .then(res => res.data);
  },

  /**
   * Trigger predictive calculation
   * POST /v1/predictive/calculate
   */
  async triggerCalculation(): Promise<{ status: string }> {
    return cloudAPI.post<ApiResponse<{ status: string }>>('/v1/predictive/calculate')
      .then(res => res.data);
  },
};

// ============================================================================
// WORK ORDER API
// ============================================================================

export const workOrderAPI = {
  /**
   * List work orders
   * GET /v1/work-orders
   */
  async list(params?: {
    status?: string;
    equipment_id?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<WorkOrder>> {
    const queryParams: Record<string, string> = {};

    if (params?.status) queryParams.status = params.status;
    if (params?.equipment_id) queryParams.equipment_id = params.equipment_id;
    if (params?.page) queryParams.page = params.page.toString();
    if (params?.page_size) queryParams.page_size = params.page_size.toString();

    return cloudAPI.get<PaginatedResponse<WorkOrder>>('/v1/work-orders', queryParams);
  },

  /**
   * Get work order by ID
   * GET /v1/work-orders/:id
   */
  async get(id: string): Promise<WorkOrder> {
    return cloudAPI.get<ApiResponse<WorkOrder>>(`/v1/work-orders/${id}`)
      .then(res => res.data);
  },

  /**
   * Create work order
   * POST /v1/work-orders
   */
  async create(request: CreateWorkOrderRequest): Promise<WorkOrder> {
    return cloudAPI.post<ApiResponse<WorkOrder>>('/v1/work-orders', request)
      .then(res => res.data);
  },

  /**
   * Update work order
   * PATCH /v1/work-orders/:id
   */
  async update(id: string, updates: Partial<WorkOrder>): Promise<WorkOrder> {
    return cloudAPI.patch<ApiResponse<WorkOrder>>(`/v1/work-orders/${id}`, updates)
      .then(res => res.data);
  },
};

// ============================================================================
// FAULT API
// ============================================================================

export const faultAPI = {
  /**
   * List faults
   * GET /v1/faults
   */
  async list(params?: {
    equipment_id?: string;
    resolved?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Fault>> {
    const queryParams: Record<string, string> = {};

    if (params?.equipment_id) queryParams.equipment_id = params.equipment_id;
    if (params?.resolved !== undefined) queryParams.resolved = params.resolved.toString();
    if (params?.page) queryParams.page = params.page.toString();
    if (params?.page_size) queryParams.page_size = params.page_size.toString();

    return cloudAPI.get<PaginatedResponse<Fault>>('/v1/faults', queryParams);
  },

  /**
   * Get fault by ID
   * GET /v1/faults/:id
   */
  async get(id: string): Promise<Fault> {
    return cloudAPI.get<ApiResponse<Fault>>(`/v1/faults/${id}`)
      .then(res => res.data);
  },
};

// ============================================================================
// EQUIPMENT API
// ============================================================================

export const equipmentAPI = {
  /**
   * List equipment
   * GET /v1/equipment
   */
  async list(): Promise<Equipment[]> {
    return cloudAPI.get<ApiResponse<Equipment[]>>('/v1/equipment')
      .then(res => res.data);
  },

  /**
   * Get equipment hierarchy
   * GET /v1/equipment/hierarchy
   */
  async getHierarchy(): Promise<EquipmentHierarchy[]> {
    return cloudAPI.get<ApiResponse<EquipmentHierarchy[]>>('/v1/equipment/hierarchy')
      .then(res => res.data);
  },

  /**
   * Get equipment by ID
   * GET /v1/equipment/:id
   */
  async get(id: string): Promise<Equipment> {
    return cloudAPI.get<ApiResponse<Equipment>>(`/v1/equipment/${id}`)
      .then(res => res.data);
  },
};

// ============================================================================
// PARTS & INVENTORY API
// ============================================================================

export const inventoryAPI = {
  /**
   * List parts
   * GET /v1/parts
   */
  async listParts(params?: {
    category?: string;
    equipment_id?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Part>> {
    const queryParams: Record<string, string> = {};

    if (params?.category) queryParams.category = params.category;
    if (params?.equipment_id) queryParams.equipment_id = params.equipment_id;
    if (params?.page) queryParams.page = params.page.toString();
    if (params?.page_size) queryParams.page_size = params.page_size.toString();

    return cloudAPI.get<PaginatedResponse<Part>>('/v1/parts', queryParams);
  },

  /**
   * Get part by ID
   * GET /v1/parts/:id
   */
  async getPart(id: string): Promise<Part> {
    return cloudAPI.get<ApiResponse<Part>>(`/v1/parts/${id}`)
      .then(res => res.data);
  },

  /**
   * Get stock level for part
   * GET /v1/inventory/:partId
   */
  async getStockLevel(partId: string): Promise<StockLevel> {
    return cloudAPI.get<ApiResponse<StockLevel>>(`/v1/inventory/${partId}`)
      .then(res => res.data);
  },

  /**
   * Get low stock parts
   * GET /v1/inventory/low-stock
   */
  async getLowStock(): Promise<Array<{ part: Part; stock_level: StockLevel }>> {
    return cloudAPI.get<ApiResponse<Array<{ part: Part; stock_level: StockLevel }>>>('/v1/inventory/low-stock')
      .then(res => res.data);
  },
};

// ============================================================================
// HANDOVER API
// ============================================================================

export const handoverAPI = {
  /**
   * List handovers
   * GET /v1/handovers
   */
  async list(): Promise<Handover[]> {
    return cloudAPI.get<ApiResponse<Handover[]>>('/v1/handovers')
      .then(res => res.data);
  },

  /**
   * Get handover by ID
   * GET /v1/handovers/:id
   */
  async get(id: string): Promise<Handover> {
    return cloudAPI.get<ApiResponse<Handover>>(`/v1/handovers/${id}`)
      .then(res => res.data);
  },

  /**
   * Get handover items
   * GET /v1/handovers/:id/items
   */
  async getItems(handoverId: string): Promise<HandoverItem[]> {
    return cloudAPI.get<ApiResponse<HandoverItem[]>>(`/v1/handovers/${handoverId}/items`)
      .then(res => res.data);
  },

  /**
   * Create handover
   * POST /v1/handovers
   */
  async create(request: CreateHandoverRequest): Promise<Handover> {
    return cloudAPI.post<ApiResponse<Handover>>('/v1/handovers', request)
      .then(res => res.data);
  },

  /**
   * Add item to handover
   * POST /v1/handovers/items
   */
  async addItem(request: AddHandoverItemRequest): Promise<HandoverItem> {
    return cloudAPI.post<ApiResponse<HandoverItem>>('/v1/handovers/items', request)
      .then(res => res.data);
  },

  /**
   * Export handover
   * POST /v1/handovers/:id/export
   */
  async export(request: ExportHandoverRequest): Promise<ExportHandoverResponse> {
    return cloudAPI.post<ApiResponse<ExportHandoverResponse>>(
      `/v1/handovers/${request.handover_id}/export`,
      { format: request.format }
    ).then(res => res.data);
  },
};

// ============================================================================
// DOCUMENT API
// ============================================================================

export const documentAPI = {
  /**
   * List documents
   * GET /v1/documents
   */
  async list(params?: {
    source?: string;
    indexed?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Document>> {
    const queryParams: Record<string, string> = {};

    if (params?.source) queryParams.source = params.source;
    if (params?.indexed !== undefined) queryParams.indexed = params.indexed.toString();
    if (params?.page) queryParams.page = params.page.toString();
    if (params?.page_size) queryParams.page_size = params.page_size.toString();

    return cloudAPI.get<PaginatedResponse<Document>>('/v1/documents', queryParams);
  },

  /**
   * Get document by ID
   * GET /v1/documents/:id
   */
  async get(id: string): Promise<Document> {
    return cloudAPI.get<ApiResponse<Document>>(`/v1/documents/${id}`)
      .then(res => res.data);
  },

  /**
   * Get signed URL for document
   * GET /v1/documents/:id/url
   */
  async getSignedUrl(id: string): Promise<{ url: string; expires_at: string }> {
    return cloudAPI.get<ApiResponse<{ url: string; expires_at: string }>>(`/v1/documents/${id}/url`)
      .then(res => res.data);
  },
};

// ============================================================================
// INGESTION API (for mobile/web uploads)
// ============================================================================

export const ingestionAPI = {
  /**
   * Initialize upload
   * POST /v1/ingest/init
   */
  async initUpload(request: InitUploadRequest): Promise<InitUploadResponse> {
    return cloudAPI.post<ApiResponse<InitUploadResponse>>('/v1/ingest/init', request)
      .then(res => res.data);
  },

  /**
   * Upload chunk
   * PATCH /v1/ingest/chunk
   */
  async uploadChunk(
    uploadId: string,
    chunkIndex: number,
    chunkData: ArrayBuffer,
    chunkSha256: string
  ): Promise<{ status: string }> {
    const token = await getAccessToken();

    const response = await fetch(`${CLOUD_API_URL}/v1/ingest/chunk`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/octet-stream',
        'Authorization': `Bearer ${token}`,
        'Upload-ID': uploadId,
        'Chunk-Index': chunkIndex.toString(),
        'Chunk-SHA256': chunkSha256,
      },
      body: chunkData,
    });

    if (!response.ok) {
      throw new Error(`Chunk upload failed: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Complete upload
   * POST /v1/ingest/complete
   */
  async completeUpload(request: CompleteUploadRequest): Promise<CompleteUploadResponse> {
    return cloudAPI.post<ApiResponse<CompleteUploadResponse>>('/v1/ingest/complete', request)
      .then(res => res.data);
  },
};

// ============================================================================
// DASHBOARD API
// ============================================================================

export const dashboardAPI = {
  /**
   * Get dashboard overview
   * GET /v1/dashboard/overview
   */
  async getOverview(): Promise<DashboardOverview> {
    return cloudAPI.get<ApiResponse<DashboardOverview>>('/v1/dashboard/overview')
      .then(res => res.data);
  },

  /**
   * Get equipment summary
   * GET /v1/dashboard/equipment-summary
   */
  async getEquipmentSummary(): Promise<EquipmentSummary> {
    return cloudAPI.get<ApiResponse<EquipmentSummary>>('/v1/dashboard/equipment-summary')
      .then(res => res.data);
  },

  /**
   * Get work order summary
   * GET /v1/dashboard/work-order-summary
   */
  async getWorkOrderSummary(): Promise<WorkOrderSummary> {
    return cloudAPI.get<ApiResponse<WorkOrderSummary>>('/v1/dashboard/work-order-summary')
      .then(res => res.data);
  },

  /**
   * Get fault summary
   * GET /v1/dashboard/fault-summary
   */
  async getFaultSummary(): Promise<FaultSummary> {
    return cloudAPI.get<ApiResponse<FaultSummary>>('/v1/dashboard/fault-summary')
      .then(res => res.data);
  },
};

// ============================================================================
// USER API
// ============================================================================

export const userAPI = {
  /**
   * Get current user context
   * GET /v1/users/me
   */
  async getMe(): Promise<User> {
    return cloudAPI.get<ApiResponse<User>>('/v1/users/me')
      .then(res => res.data);
  },
};

// ============================================================================
// HEALTH CHECK
// ============================================================================

export const healthAPI = {
  /**
   * Health check
   * GET /v1/health
   */
  async check(): Promise<{ status: string; uptime: number }> {
    return cloudAPI.get<{ status: string; uptime: number }>('/v1/health', undefined, false);
  },
};

// ============================================================================
// EXPORTS
// ============================================================================

export const api = {
  search: searchAPI,
  predictive: predictiveAPI,
  workOrders: workOrderAPI,
  faults: faultAPI,
  equipment: equipmentAPI,
  inventory: inventoryAPI,
  handovers: handoverAPI,
  documents: documentAPI,
  ingestion: ingestionAPI,
  dashboard: dashboardAPI,
  users: userAPI,
  health: healthAPI,
};

export default api;
