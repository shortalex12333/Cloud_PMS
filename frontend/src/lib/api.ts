// API client for CelesteOS backend

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://api.celeste7.ai/webhook/';

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

// Generic fetch wrapper with error handling
async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const defaultHeaders = {
    'Content-Type': 'application/json',
  };

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
  // Main search endpoint
  search: async (query: string, filters?: any) => {
    return fetchAPI('search', {
      method: 'POST',
      body: JSON.stringify({ query, filters }),
    });
  },

  // Streaming search (for progressive results)
  searchStream: async (query: string) => {
    const url = `${API_BASE_URL}search`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, stream: true }),
    });

    if (!response.ok) {
      throw new ApiError(response.status, 'Search stream failed');
    }

    return response.body;
  },
};

// Document API
export const documentAPI = {
  get: async (documentId: string) => {
    return fetchAPI(`documents/${documentId}`);
  },

  getPresignedUrl: async (documentId: string) => {
    return fetchAPI(`documents/${documentId}/url`);
  },
};

// Work Order API
export const workOrderAPI = {
  create: async (data: any) => {
    return fetchAPI('work-orders', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  list: async (filters?: any) => {
    const params = new URLSearchParams(filters);
    return fetchAPI(`work-orders?${params}`);
  },

  get: async (workOrderId: string) => {
    return fetchAPI(`work-orders/${workOrderId}`);
  },

  update: async (workOrderId: string, data: any) => {
    return fetchAPI(`work-orders/${workOrderId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },
};

// Handover API
export const handoverAPI = {
  create: async (data: any) => {
    return fetchAPI('handovers', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  addItem: async (handoverId: string, item: any) => {
    return fetchAPI(`handovers/${handoverId}/items`, {
      method: 'POST',
      body: JSON.stringify(item),
    });
  },

  export: async (handoverId: string, format: 'pdf' | 'html') => {
    return fetchAPI(`handovers/${handoverId}/export`, {
      method: 'POST',
      body: JSON.stringify({ format }),
    });
  },
};

// Dashboard API
export const dashboardAPI = {
  getMetrics: async (yachtId: string) => {
    return fetchAPI(`dashboard/${yachtId}/metrics`);
  },

  getPredictive: async (yachtId: string) => {
    return fetchAPI(`dashboard/${yachtId}/predictive`);
  },
};

// Parts/Inventory API
export const inventoryAPI = {
  search: async (query: string) => {
    return fetchAPI(`inventory/search?q=${encodeURIComponent(query)}`);
  },

  getLowStock: async (yachtId: string) => {
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
