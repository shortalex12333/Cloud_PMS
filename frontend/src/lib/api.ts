// API client for CelesteOS backend

import type { SearchResponse } from '@/types/search';
import { supabase } from './supabaseClient';
import { ensureFreshToken } from './tokenRefresh';

// Normalize base URL to ensure consistent trailing slash handling
const rawBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://api.celeste7.ai/webhook';
const API_BASE_URL = rawBaseUrl.replace(/\/+$/, '') + '/';

// API error handling
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public data?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// Get auth headers with fresh token (auto-refreshes if expiring soon)
async function getAuthHeaders(): Promise<Record<string, string>> {
  try {
    const token = await ensureFreshToken();
    return { 'Authorization': `Bearer ${token}` };
  } catch (err) {
    console.warn('[API] Failed to get fresh token:', err);
  }
  return {};
}

// Generic fetch wrapper with error handling and auth
async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {},
  includeAuth = true
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const defaultHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  // Add auth headers if requested
  if (includeAuth) {
    const authHeaders = await getAuthHeaders();
    Object.assign(defaultHeaders, authHeaders);
  }

  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      errorData.message || `API Error: ${response.statusText}`,
      errorData
    );
  }

  return response.json();
}

// Search API
export const searchAPI = {
  // Main search endpoint - includes JWT in header, yacht_id in body
  search: async (query: string, filters?: any, yachtId?: string | null): Promise<SearchResponse> => {
    return fetchAPI<SearchResponse>('search', {
      method: 'POST',
      body: JSON.stringify({
        query,
        filters,
        yacht_id: yachtId || undefined,
      }),
    });
  },

  // Streaming search (for progressive results) - includes auth
  searchStream: async (query: string, yachtId?: string | null): Promise<ReadableStream<Uint8Array> | null> => {
    const url = `${API_BASE_URL}search`;
    const authHeaders = await getAuthHeaders();

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders,
      },
      body: JSON.stringify({
        query,
        stream: true,
        yacht_id: yachtId || undefined,
      }),
    });

    if (!response.ok) {
      throw new ApiError(response.status, 'Search stream failed');
    }

    return response.body;
  },
};

// Document API
export const documentAPI = {
  get: async (documentId: string): Promise<any> => {
    return fetchAPI(`documents/${documentId}`);
  },

  getPresignedUrl: async (documentId: string): Promise<{ url: string }> => {
    return fetchAPI(`documents/${documentId}/url`);
  },
};

// Work Order API
export const workOrderAPI = {
  create: async (data: any): Promise<any> => {
    return fetchAPI('work-orders', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  list: async (filters?: any): Promise<any> => {
    const params = new URLSearchParams(filters);
    return fetchAPI(`work-orders?${params}`);
  },

  get: async (workOrderId: string): Promise<any> => {
    return fetchAPI(`work-orders/${workOrderId}`);
  },

  update: async (workOrderId: string, data: any): Promise<any> => {
    return fetchAPI(`work-orders/${workOrderId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },
};

// Handover API
export const handoverAPI = {
  create: async (data: any): Promise<any> => {
    return fetchAPI('handovers', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  addItem: async (handoverId: string, item: any): Promise<any> => {
    return fetchAPI(`handovers/${handoverId}/items`, {
      method: 'POST',
      body: JSON.stringify(item),
    });
  },

  export: async (handoverId: string, format: 'pdf' | 'html'): Promise<any> => {
    return fetchAPI(`handovers/${handoverId}/export`, {
      method: 'POST',
      body: JSON.stringify({ format }),
    });
  },
};

// Dashboard API
export const dashboardAPI = {
  getMetrics: async (yachtId: string): Promise<any> => {
    return fetchAPI(`dashboard/${yachtId}/metrics`);
  },

  getPredictive: async (yachtId: string): Promise<any> => {
    return fetchAPI(`dashboard/${yachtId}/predictive`);
  },
};

// Parts/Inventory API
export const inventoryAPI = {
  search: async (query: string): Promise<any> => {
    return fetchAPI(`inventory/search?q=${encodeURIComponent(query)}`);
  },

  getLowStock: async (yachtId: string): Promise<any> => {
    return fetchAPI(`inventory/${yachtId}/low-stock`);
  },
};

// Export all APIs
export const api = {
  search: searchAPI,
  documents: documentAPI,
  workOrders: workOrderAPI,
  handover: handoverAPI,
  dashboard: dashboardAPI,
  inventory: inventoryAPI,
};

export default api;
