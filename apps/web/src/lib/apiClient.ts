/**
 * Secure API Client for Celeste Backend
 *
 * All requests include:
 * - JWT (Authorization: Bearer <token>)
 * - Yacht signature (X-Yacht-Signature: <hash>)
 *
 * Security guarantees:
 * - Auto-refresh expired tokens
 * - Retry 401s once with new token
 * - Never log JWT or yacht signature
 * - Fail fast if authentication unavailable
 */

import { supabase } from './supabaseClient';
import { getAuthHeaders, handle401, getYachtId, getYachtSignature, AuthError } from './authHelpers';

// Re-export AuthError for convenience
export { AuthError };

// Use same env var as actionClient for consistency
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

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
 * Call Celeste API with secure authentication
 *
 * Every request includes:
 * - Authorization: Bearer <JWT>
 * - X-Yacht-Signature: <sha256(yacht_id + salt)>
 *
 * Automatically retries 401s with token refresh.
 *
 * @param path - API path (e.g., '/webhook/search', '/v1/actions/execute')
 * @param options - Fetch options (method, body, etc.)
 * @returns Parsed JSON response
 * @throws CelesteApiError on request failure
 * @throws AuthError if authentication unavailable
 */
export async function callCelesteApi<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const executeRequest = async (): Promise<T> => {
    // Get yacht_id from user profile
    const yachtId = await getYachtId();

    // Get secure auth headers (JWT + yacht signature)
    const authHeaders = await getAuthHeaders(yachtId);

    const url = `${API_BASE_URL}${path}`;
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...authHeaders,
      ...options?.headers, // Allow overriding content-type if needed
    };

    // Security: DO NOT log JWT, yacht_signature, or Authorization header
    if (process.env.NODE_ENV === 'development') {
      console.log('[apiClient] Request:', {
        method: options?.method || 'GET',
        path, // Log path, not full URL
        hasAuth: true, // Confirm auth present without logging token
      });
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (process.env.NODE_ENV === 'development') {
        console.log('[apiClient] Response:', {
          status: response.status,
          ok: response.ok,
        });
      }

      // Handle 401 Unauthorized - retry with token refresh
      if (response.status === 401) {
        console.warn('[apiClient] 401 Unauthorized, attempting token refresh...');
        return await handle401(() => executeRequest());
      }

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
      if (error instanceof CelesteApiError || error instanceof AuthError) {
        throw error;
      }

      console.error('[apiClient] Request failed:', error);
      throw new CelesteApiError(
        500,
        error instanceof Error ? error.message : 'Network error'
      );
    }
  };

  return executeRequest();
}

// Valid roles per roles.md spec
type ValidRole = 'Engineer' | 'HOD' | 'Captain' | 'ETO' | 'Fleet Manager' | 'Admin' | 'Owner Tech Representative';

// Map internal roles to spec-compliant roles
function mapToValidRole(role: string | null | undefined): ValidRole {
  const roleMap: Record<string, ValidRole> = {
    'chief_engineer': 'Engineer',
    'engineer': 'Engineer',
    'eto': 'ETO',
    'captain': 'Captain',
    'manager': 'HOD',
    'hod': 'HOD',
    'fleet_manager': 'Fleet Manager',
    'admin': 'Admin',
    'owner': 'Owner Tech Representative',
    'crew': 'Engineer', // Default crew to Engineer for search access
    'deck': 'Engineer',
    'interior': 'Engineer',
  };
  return roleMap[role?.toLowerCase() || ''] || 'Engineer';
}

// Get browser/client info for telemetry
function getClientTelemetry() {
  const ua = typeof navigator !== 'undefined' ? navigator.userAgent : '';
  const isMobile = /Mobile|Android|iPhone/i.test(ua);

  return {
    client_version: '1.0.0', // TODO: pull from package.json
    platform: isMobile ? 'mobile_web' : 'desktop_web',
    input_mode: 'keyboard' as const,
    locale: typeof navigator !== 'undefined' ? navigator.language : 'en-US',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  };
}

// Session ID - persistent for the browser session
let _sessionId: string | null = null;
function getSessionId(): string {
  if (!_sessionId) {
    _sessionId = typeof sessionStorage !== 'undefined'
      ? sessionStorage.getItem('celeste_session_id') || crypto.randomUUID()
      : crypto.randomUUID();
    if (typeof sessionStorage !== 'undefined') {
      sessionStorage.setItem('celeste_session_id', _sessionId);
    }
  }
  return _sessionId;
}

/**
 * Get full auth context for search payload
 * Includes user_id, yacht_id, role, email, yacht_signature
 */
async function getFullAuthContext(): Promise<{
  user_id: string;
  yacht_id: string | null;
  role: ValidRole;
  email: string;
  yacht_signature: string | null;
} | null> {
  try {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session?.user) return null;

    // Get yacht_id with timeout
    const yachtId = await getYachtId();

    // Get yacht signature
    const yachtSignature = await getYachtSignature(yachtId);

    // Get role from user metadata and map to valid role
    const rawRole = (session.user.user_metadata?.role as string) || 'crew';
    const role = mapToValidRole(rawRole);

    return {
      user_id: session.user.id,
      yacht_id: yachtId,
      role,
      email: session.user.email || '',
      yacht_signature: yachtSignature,
    };
  } catch (err) {
    console.warn('[apiClient] Failed to get auth context:', err);
    return null;
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

  /**
   * Search with full context payload per search-engine-spec.md
   */
  search: async <T>(query: string, options?: {
    filters?: any;
    streamId?: string;
    queryType?: 'free-text' | 'fault' | 'equipment' | 'document' | 'work-order';
  }): Promise<T> => {
    const authContext = await getFullAuthContext();
    const telemetry = getClientTelemetry();
    const sessionId = getSessionId();

    const payload = {
      query,
      query_type: options?.queryType || 'free-text',
      auth: authContext ? {
        user_id: authContext.user_id,
        yacht_id: authContext.yacht_id,
        role: authContext.role,
        email: authContext.email,
        yacht_signature: authContext.yacht_signature,
      } : undefined,
      context: {
        client_ts: Math.floor(Date.now() / 1000),
        stream_id: options?.streamId || crypto.randomUUID(),
        session_id: sessionId,
        source: 'web',
        locale: telemetry.locale,
        timezone: telemetry.timezone,
        client_version: telemetry.client_version,
        platform: 'browser',
      },
    };

    return callCelesteApi<T>('/webhook/search', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};

/**
 * Search API with streaming support
 *
 * Opens streaming connection with JWT + yacht signature.
 * If token expires during typing, caller should close and reopen.
 *
 * @param query - Search query string
 * @returns ReadableStream of search results
 * @throws CelesteApiError on connection failure
 * @throws AuthError if authentication unavailable
 */
export async function searchWithStream(query: string): Promise<ReadableStream | null> {
  // Get yacht_id from user profile
  const yachtId = await getYachtId();

  // Get secure auth headers (JWT + yacht signature)
  const authHeaders = await getAuthHeaders(yachtId);

  const url = `${API_BASE_URL}/webhook/search`;
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders,
    },
    body: JSON.stringify({ query, stream: true }),
  });

  // Handle 401 - don't auto-retry for streams, let caller handle reconnection
  if (response.status === 401) {
    throw new CelesteApiError(401, 'Authentication expired, please refresh');
  }

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

/**
 * Document Viewer API
 *
 * Secure document access for both cloud storage and local NAS mode.
 * All document requests require JWT + yacht signature.
 *
 * Security model:
 * - Cloud mode: Documents served via backend with auth verification
 * - Local NAS mode: Pre-signed URLs generated with JWT validation
 * - No direct file access without authentication
 */
export const documentsApi = {
  /**
   * Get secure document URL
   *
   * Returns a pre-signed URL or authenticated endpoint for document access.
   * Works for both cloud storage and local NAS mode.
   *
   * @param documentId - Document ID
   * @param mode - 'cloud' or 'nas'
   * @returns Secure document URL with embedded auth
   * @throws CelesteApiError if document not found or access denied
   */
  getSecureUrl: async (
    documentId: string,
    mode: 'cloud' | 'nas' = 'cloud'
  ): Promise<{ url: string; expiresAt: number }> => {
    return celesteApi.post('/v1/documents/secure-url', {
      document_id: documentId,
      mode,
    });
  },

  /**
   * Stream document with auth headers
   *
   * For direct document streaming (e.g., PDFs, images).
   * Returns blob URL that can be used in <iframe> or <img>.
   *
   * @param documentId - Document ID
   * @returns Blob URL for document
   * @throws CelesteApiError if document not found or access denied
   */
  streamDocument: async (documentId: string): Promise<string> => {
    // Get yacht_id from user profile
    const yachtId = await getYachtId();

    // Get secure auth headers
    const authHeaders = await getAuthHeaders(yachtId);

    const url = `${API_BASE_URL}/v1/documents/${documentId}/stream`;
    const response = await fetch(url, {
      method: 'GET',
      headers: authHeaders,
    });

    // Handle 401 - document access requires valid auth
    if (response.status === 401) {
      throw new CelesteApiError(401, 'Authentication required to view document');
    }

    if (response.status === 403) {
      throw new CelesteApiError(403, 'Access denied to this document');
    }

    if (!response.ok) {
      throw new CelesteApiError(response.status, 'Failed to load document');
    }

    // Convert response to blob and create object URL
    const blob = await response.blob();
    return URL.createObjectURL(blob);
  },

  /**
   * Get document metadata
   *
   * @param documentId - Document ID
   * @returns Document metadata (title, type, size, etc.)
   */
  getMetadata: async (documentId: string) => {
    return celesteApi.get(`/v1/documents/${documentId}/metadata`);
  },
};
