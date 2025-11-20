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
