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
 * Receiving API - Document uploads and processing
 *
 * Handles multipart file uploads to receiving records with OCR/AI extraction.
 * Backend proxy enforces MIME types, file size limits, and JWT authentication.
 *
 * Free tier Render service behavior:
 * - Spins down after 15 min idle → HTTP 503 on cold start
 * - Wake time: 30-60 seconds
 * - Component handles 503 retry logic (3 attempts, 30s backoff)
 */
export const receivingApi = {
  /**
   * Upload document to receiving record
   *
   * Sends file to backend proxy which forwards to image-processing service.
   * Backend validates: MIME type, file size (15MB), JWT authentication.
   * Image-processing performs: OCR extraction, AI normalization, storage.
   *
   * @param receivingId - UUID of receiving record
   * @param file - File to upload (image/jpeg, image/png, image/heic, application/pdf)
   * @param docType - Document type classification
   * @param comment - Optional comment about the document
   * @returns Upload result with document_id, storage_path, extracted_data
   * @throws CelesteApiError with specific codes:
   *   - 400: Invalid file type or size
   *   - 401: Missing or invalid JWT
   *   - 403: RLS denied (user lacks permission)
   *   - 413: File too large (>15MB)
   *   - 415: Unsupported media type
   *   - 503: Service unavailable (Render spin-up, component retries)
   *   - 504: Gateway timeout
   */
  uploadDocument: async (
    receivingId: string,
    file: File,
    docType: 'invoice' | 'packing_slip' | 'photo' | 'other' = 'other',
    comment?: string
  ): Promise<{
    document_id: string;
    storage_path: string;
    extracted_data?: any;
    processing_status: string;
  }> => {
    // Get yacht_id from user profile
    const yachtId = await getYachtId();

    // Get secure auth headers (JWT + X-Yacht-Signature)
    const authHeaders = await getAuthHeaders(yachtId);

    // Prepare multipart form data
    const formData = new FormData();
    formData.append('file', file);
    formData.append('doc_type', docType);
    if (comment) {
      formData.append('comment', comment);
    }

    const url = `${API_BASE_URL}/api/receiving/${receivingId}/upload`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        ...authHeaders,
        // NOTE: Do NOT set Content-Type - browser sets it automatically with boundary for multipart/form-data
      },
      body: formData,
    });

    // Handle 401 - JWT missing or invalid
    if (response.status === 401) {
      throw new CelesteApiError(401, 'Authentication required');
    }

    // Handle 403 - RLS denied (user lacks permission)
    if (response.status === 403) {
      throw new CelesteApiError(403, 'Access denied to receiving record');
    }

    // Handle 404 - receiving record not found
    if (response.status === 404) {
      throw new CelesteApiError(404, 'Receiving record not found');
    }

    // Handle 413 - file too large (>15MB)
    if (response.status === 413) {
      throw new CelesteApiError(413, 'File too large (max 15MB)');
    }

    // Handle 415 - unsupported media type
    if (response.status === 415) {
      throw new CelesteApiError(415, 'Unsupported file type');
    }

    // Handle 503 - service unavailable (Render spin-up)
    // Component will retry with 30s backoff
    if (response.status === 503) {
      throw new CelesteApiError(503, 'Service starting up, please retry');
    }

    // Handle 504 - gateway timeout
    if (response.status === 504) {
      throw new CelesteApiError(504, 'Upload timed out');
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new CelesteApiError(
        response.status,
        errorData.detail || `Upload failed: ${response.statusText}`
      );
    }

    return await response.json();
  },

  /**
   * Get document processing status
   *
   * Polls image-processing service for OCR/AI extraction status.
   * Used to check if processing is complete and retrieve results.
   *
   * @param receivingId - UUID of receiving record
   * @param documentId - UUID of document
   * @returns Processing status and extraction results (if complete)
   * @throws CelesteApiError if document not found or access denied
   */
  getDocumentStatus: async (
    receivingId: string,
    documentId: string
  ): Promise<{
    status: 'pending' | 'processing' | 'completed' | 'failed';
    extracted_data?: any;
    error?: string;
  }> => {
    // Get yacht_id from user profile
    const yachtId = await getYachtId();

    // Get secure auth headers
    const authHeaders = await getAuthHeaders(yachtId);

    const url = `${API_BASE_URL}/api/receiving/${receivingId}/documents/${documentId}/status`;
    const response = await fetch(url, {
      method: 'GET',
      headers: authHeaders,
    });

    if (response.status === 401) {
      throw new CelesteApiError(401, 'Authentication required');
    }

    if (response.status === 404) {
      throw new CelesteApiError(404, 'Document not found');
    }

    if (!response.ok) {
      throw new CelesteApiError(response.status, 'Failed to get document status');
    }

    return await response.json();
  },
};
