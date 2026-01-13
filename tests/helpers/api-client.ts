/**
 * API Client Helper
 *
 * HTTP client for Render backend API with auth
 */

import { getAccessToken } from './auth';

export interface ApiResponse<T = any> {
  status: number;
  statusText: string;
  headers: Record<string, string>;
  data: T;
  request: {
    method: string;
    url: string;
    headers: Record<string, string>;
    body?: any;
  };
}

/**
 * API Client for Render backend
 */
export class ApiClient {
  private baseUrl: string;
  private accessToken: string | null = null;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || process.env.RENDER_API_URL || '';
    if (!this.baseUrl) {
      throw new Error('RENDER_API_URL must be set');
    }
  }

  /**
   * Set access token
   */
  setAccessToken(token: string): void {
    this.accessToken = token;
  }

  /**
   * Get access token (from cache or fresh login)
   */
  async ensureAuth(): Promise<string> {
    if (!this.accessToken) {
      this.accessToken = await getAccessToken();
    }
    return this.accessToken;
  }

  /**
   * Make HTTP request
   */
  async request<T = any>(
    method: string,
    path: string,
    body?: any,
    options?: {
      skipAuth?: boolean;
      headers?: Record<string, string>;
    }
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${path}`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options?.headers,
    };

    if (!options?.skipAuth) {
      const token = await this.ensureAuth();
      headers['Authorization'] = `Bearer ${token}`;
    }

    const requestInfo = {
      method,
      url,
      headers: { ...headers },
      body,
    };

    const response = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    const responseHeaders: Record<string, string> = {};
    response.headers.forEach((value, key) => {
      responseHeaders[key] = value;
    });

    let data: T;
    const contentType = response.headers.get('content-type');
    if (contentType?.includes('application/json')) {
      data = await response.json();
    } else {
      data = (await response.text()) as any;
    }

    return {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
      data,
      request: requestInfo,
    };
  }

  /**
   * GET request
   */
  async get<T = any>(path: string, options?: { skipAuth?: boolean }): Promise<ApiResponse<T>> {
    return this.request<T>('GET', path, undefined, options);
  }

  /**
   * POST request
   */
  async post<T = any>(path: string, body?: any, options?: { skipAuth?: boolean }): Promise<ApiResponse<T>> {
    return this.request<T>('POST', path, body, options);
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<ApiResponse<{ status: string }>> {
    return this.get('/health', { skipAuth: true });
  }

  /**
   * Search endpoint
   */
  async search(query: string, limit: number = 10, yachtId?: string): Promise<ApiResponse<{
    success: boolean;
    results: any[];
    total_count: number;
  }>> {
    const yacht_id = yachtId || process.env.TEST_USER_YACHT_ID;
    return this.post('/search', { query, limit, yacht_id });
  }

  /**
   * Execute microaction
   *
   * API expects: { action, context, payload }
   * - action: The action ID (e.g., "add_equipment")
   * - context: Includes yacht_id, user context
   * - payload: The action-specific parameters
   */
  async executeAction(
    actionName: string,
    payload: Record<string, any>,
    context?: Record<string, any>
  ): Promise<ApiResponse<{
    success: boolean;
    status?: string;
    result?: any;
    [key: string]: any;
  }>> {
    const yacht_id = payload.yacht_id || process.env.TEST_USER_YACHT_ID;
    return this.post('/v1/actions/execute', {
      action: actionName,
      context: {
        yacht_id,
        ...context,
      },
      payload,
    });
  }

  /**
   * Get document signed URL
   */
  async signDocument(docId: string): Promise<ApiResponse<{
    signed_url: string;
    expires_at: string;
  }>> {
    return this.post(`/v1/documents/${docId}/sign`);
  }
}

/**
 * Create API client with auth
 */
export async function createAuthenticatedClient(): Promise<ApiClient> {
  const client = new ApiClient();
  await client.ensureAuth();
  return client;
}
