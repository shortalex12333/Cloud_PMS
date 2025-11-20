// API client for Celeste backend with automatic JWT authentication

import { supabase } from './supabaseClient';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://api.celeste7.ai/webhook/';

export class CelesteApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public data?: any
  ) {
    super(message);
    this.name = 'CelesteApiError';
  }
}

/**
 * Call Celeste API with automatic JWT authentication
 * Uses Supabase session JWT in Authorization header
 * DO NOT send Outlook tokens or any external auth tokens
 */
export async function callCelesteApi<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  // Get current Supabase session for JWT
  const {
    data: { session },
    error: sessionError,
  } = await supabase.auth.getSession();

  if (sessionError) {
    console.error('[apiClient] Session error:', sessionError);
    throw new CelesteApiError(401, 'Authentication required');
  }

  if (!session) {
    console.error('[apiClient] No active session');
    throw new CelesteApiError(401, 'Not authenticated');
  }

  const url = `${API_BASE_URL}${path}`;
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${session.access_token}`,
    ...options?.headers,
  };

  console.log('[apiClient] Request:', {
    method: options?.method || 'GET',
    url,
    hasAuth: !!session.access_token,
    userId: session.user.id,
  });

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    console.log('[apiClient] Response:', {
      status: response.status,
      statusText: response.statusText,
      ok: response.ok,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new CelesteApiError(
        response.status,
        errorData.message || `API Error: ${response.statusText}`,
        errorData
      );
    }

    // Handle empty responses
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
      return {} as T;
    }

    return response.json();
  } catch (error) {
    if (error instanceof CelesteApiError) {
      throw error;
    }

    console.error('[apiClient] Request failed:', error);
    throw new CelesteApiError(
      500,
      error instanceof Error ? error.message : 'Network error'
    );
  }
}

/**
 * Convenience methods for common HTTP verbs
 */
export const celesteApi = {
  get: <T>(path: string) => callCelesteApi<T>(path, { method: 'GET' }),

  post: <T>(path: string, body?: any) =>
    callCelesteApi<T>(path, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    }),

  patch: <T>(path: string, body?: any) =>
    callCelesteApi<T>(path, {
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
    }),

  delete: <T>(path: string) => callCelesteApi<T>(path, { method: 'DELETE' }),
};

/**
 * Search API with streaming support
 */
export async function searchWithStream(query: string): Promise<ReadableStream | null> {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    throw new CelesteApiError(401, 'Not authenticated');
  }

  const url = `${API_BASE_URL}search`;
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${session.access_token}`,
    },
    body: JSON.stringify({ query, stream: true }),
  });

  if (!response.ok) {
    throw new CelesteApiError(response.status, 'Search stream failed');
  }

  return response.body;
}

/**
 * Integration API - OAuth connections
 * Ported from c.os.4.1 email/Microsoft integration
 * Backend handles token storage in api_tokens table
 */
export const integrationsApi = {
  // Microsoft Outlook OAuth
  outlook: {
    // Get OAuth authorization URL
    // Backend generates URL with:
    // - Client ID: 41f6dc82-8127-4330-97e0-c6b26e6aa967
    // - Scopes: Mail.Read, User.Read, MailboxSettings.Read, offline_access
    // - Redirect URI: /integrations/outlook/callback
    // - State: user_id:random_string (for CSRF protection)
    getAuthUrl: async (): Promise<{ url: string }> => {
      return celesteApi.get('/api/integrations/outlook/auth-url');
    },

    // Get connection status
    // Returns: { connected: boolean, email?: string, connectedAt?: string }
    getStatus: async (): Promise<{ connected: boolean; email?: string; connectedAt?: string }> => {
      return celesteApi.get('/api/integrations/outlook/status');
    },

    // Exchange OAuth code for tokens (called from callback page)
    // Backend will:
    // 1. Exchange code for access/refresh tokens via Microsoft token endpoint
    // 2. Fetch user profile from Microsoft Graph
    // 3. Store tokens in api_tokens table (type: 'device', scopes: ['mail:read'])
    // 4. Link to current user via JWT
    handleCallback: async (code: string): Promise<{ success: boolean }> => {
      return celesteApi.get(`/api/integrations/outlook/callback?code=${encodeURIComponent(code)}`);
    },

    // Disconnect account
    // Deletes tokens from api_tokens table
    disconnect: async (): Promise<{ success: boolean }> => {
      return celesteApi.post('/api/integrations/outlook/disconnect');
    },
  },

  // LinkedIn OAuth
  linkedin: {
    // Get OAuth authorization URL
    // Backend generates URL with LinkedIn OAuth2 params
    // Redirect URI: /integrations/linkedin/callback
    getAuthUrl: async (): Promise<{ url: string }> => {
      return celesteApi.get('/api/integrations/linkedin/auth-url');
    },

    // Get connection status
    getStatus: async (): Promise<{ connected: boolean; email?: string; connectedAt?: string }> => {
      return celesteApi.get('/api/integrations/linkedin/status');
    },

    // Exchange OAuth code for tokens
    handleCallback: async (code: string): Promise<{ success: boolean }> => {
      return celesteApi.get(`/api/integrations/linkedin/callback?code=${encodeURIComponent(code)}`);
    },

    // Disconnect account
    disconnect: async (): Promise<{ success: boolean }> => {
      return celesteApi.post('/api/integrations/linkedin/disconnect');
    },
  },
};
