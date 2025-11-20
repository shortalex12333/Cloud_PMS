import {
  APIResponse,
  DashboardSummary,
  PredictiveInsightsRequest,
  PredictiveInsightsResponse,
  SearchRequest,
  SearchResponse,
  WorkOrderSummary,
  InventorySummary,
  FaultsSummary,
  UpcomingTask,
} from '@/types/api'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:3000/api'

class APIError extends Error {
  constructor(public status: number, message: string, public data?: any) {
    super(message)
    this.name = 'APIError'
  }
}

// Generic fetch wrapper with auth
async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`

  // TODO: Get token from auth context when implementing auth
  // For now, this is a placeholder
  const token = typeof window !== 'undefined'
    ? localStorage.getItem('auth_token')
    : null

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new APIError(
        response.status,
        errorData.message || `HTTP ${response.status}: ${response.statusText}`,
        errorData
      )
    }

    return await response.json()
  } catch (error) {
    if (error instanceof APIError) {
      throw error
    }
    throw new APIError(0, 'Network error or failed to parse response')
  }
}

// Search API
export const searchAPI = {
  search: async (request: SearchRequest): Promise<SearchResponse> => {
    return apiFetch<SearchResponse>('/v1/search', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  },
}

// Dashboard API
export const dashboardAPI = {
  getSummary: async (): Promise<DashboardSummary> => {
    // TODO: Replace with real endpoint when backend is ready
    return apiFetch<DashboardSummary>('/v1/dashboard/summary')
  },

  getWorkOrders: async (): Promise<WorkOrderSummary> => {
    return apiFetch<WorkOrderSummary>('/v1/work-orders/summary')
  },

  getInventory: async (): Promise<InventorySummary> => {
    return apiFetch<InventorySummary>('/v1/inventory/low-stock')
  },

  getFaults: async (): Promise<FaultsSummary> => {
    return apiFetch<FaultsSummary>('/v1/faults/summary')
  },

  getUpcomingTasks: async (days: number = 14): Promise<UpcomingTask[]> => {
    return apiFetch<UpcomingTask[]>(`/v1/tasks/upcoming?days=${days}`)
  },
}

// Predictive Maintenance API
export const predictiveAPI = {
  getInsights: async (
    request?: PredictiveInsightsRequest
  ): Promise<PredictiveInsightsResponse> => {
    const params = new URLSearchParams()
    if (request?.equipment_id) params.set('equipment_id', request.equipment_id)
    if (request?.limit) params.set('limit', request.limit.toString())

    return apiFetch<PredictiveInsightsResponse>(
      `/v1/predictive/insights?${params.toString()}`
    )
  },

  getState: async (): Promise<any> => {
    return apiFetch<any>('/v1/predictive/state')
  },
}

// Export all APIs
export const api = {
  search: searchAPI,
  dashboard: dashboardAPI,
  predictive: predictiveAPI,
}

export default api
