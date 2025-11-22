/**
 * CelesteOS Centralized API Client - Worker 9 Integration Layer
 *
 * Single source of truth for all API communication.
 * Features:
 * - AsyncGenerator streaming with back-pressure
 * - AbortController for query cancellation
 * - Automatic JWT attachment from Supabase
 * - Type-safe requests and responses
 *
 * Usage:
 * ```typescript
 * import { celesteClient } from '@/lib/celesteApi';
 *
 * // Streaming search
 * for await (const result of celesteClient.search(request, signal)) {
 *   handleResult(result);
 * }
 *
 * // Execute action
 * const response = await celesteClient.executeAction(request);
 *
 * // Get predictive state
 * const state = await celesteClient.getPredictiveState(equipmentId);
 * ```
 */

import { supabase } from './supabaseClient';
import type {
  CelesteSearchRequest,
  CelesteSearchResponse,
  SearchResultCard,
  SearchStreamChunk,
  CelesteActionRequest,
  CelesteActionResponse,
  PredictiveState,
  PredictiveOverview,
  DashboardMetrics,
  ActionErrorCode,
} from '@/types/api-contracts';

// ============================================================================
// CONFIGURATION
// ============================================================================

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'https://api.celeste7.ai';
const WEBHOOK_BASE_URL = `${API_BASE_URL}/webhook`;
const API_V1_URL = `${API_BASE_URL}/v1`;

const DEFAULT_TIMEOUT = 30000; // 30 seconds
const STREAM_TIMEOUT = 120000; // 2 minutes for streaming

// ============================================================================
// ERROR HANDLING
// ============================================================================

export class CelesteApiError extends Error {
  constructor(
    public code: ActionErrorCode,
    message: string,
    public status?: number,
    public details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'CelesteApiError';
  }
}

// ============================================================================
// INTERNAL HELPERS
// ============================================================================

/**
 * Get current auth token from Supabase
 */
async function getAuthToken(): Promise<string | null> {
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

/**
 * Build headers with auth
 */
async function buildHeaders(includeAuth = true): Promise<HeadersInit> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };

  if (includeAuth) {
    const token = await getAuthToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  return headers;
}

/**
 * Generic fetch wrapper with timeout and error handling
 */
async function fetchWithTimeout<T>(
  url: string,
  options: RequestInit = {},
  timeout = DEFAULT_TIMEOUT
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new CelesteApiError(
        (errorData.error_code as ActionErrorCode) || 'unknown_error',
        errorData.message || `API Error: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    return response.json();
  } catch (error) {
    if (error instanceof CelesteApiError) {
      throw error;
    }
    if (error instanceof Error && error.name === 'AbortError') {
      throw new CelesteApiError('network_error', 'Request timed out');
    }
    throw new CelesteApiError(
      'network_error',
      error instanceof Error ? error.message : 'Network error'
    );
  } finally {
    clearTimeout(timeoutId);
  }
}

/**
 * Parse line-delimited JSON stream
 */
async function* parseLineDelimitedJSON<T>(
  stream: ReadableStream<Uint8Array>,
  signal?: AbortSignal
): AsyncGenerator<T> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      // Check for cancellation
      if (signal?.aborted) {
        break;
      }

      const { done, value } = await reader.read();

      if (done) {
        // Process any remaining data in buffer
        if (buffer.trim()) {
          try {
            yield JSON.parse(buffer.trim()) as T;
          } catch {
            console.warn('[celesteApi] Failed to parse final buffer:', buffer);
          }
        }
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // Process complete lines
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed) {
          try {
            yield JSON.parse(trimmed) as T;
          } catch {
            console.warn('[celesteApi] Failed to parse line:', trimmed);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// ============================================================================
// SEARCH API
// ============================================================================

/**
 * Streaming search with AsyncGenerator
 * Supports cancellation via AbortSignal
 */
async function* searchStream(
  request: CelesteSearchRequest,
  signal?: AbortSignal
): AsyncGenerator<SearchResultCard, CelesteSearchResponse | void, unknown> {
  const url = `${WEBHOOK_BASE_URL}/search`;
  const headers = await buildHeaders();

  console.log('[celesteApi] Starting search stream:', {
    query: request.query,
    mode: request.mode,
  });

  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify({ ...request, stream: true }),
    signal,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new CelesteApiError(
      'unknown_error',
      errorData.message || 'Search failed',
      response.status,
      errorData
    );
  }

  if (!response.body) {
    throw new CelesteApiError('network_error', 'No response body');
  }

  let finalResponse: CelesteSearchResponse | undefined;

  for await (const chunk of parseLineDelimitedJSON<SearchStreamChunk>(response.body, signal)) {
    if (signal?.aborted) {
      console.log('[celesteApi] Search cancelled');
      return;
    }

    switch (chunk.type) {
      case 'result':
        if (chunk.result) {
          yield chunk.result;
        }
        break;

      case 'complete':
        finalResponse = {
          query_id: chunk.query_id || '',
          intent: chunk.intent || 'general_search',
          entities: chunk.entities || {},
          results: [],
          suggested_actions: [],
          total_results: chunk.total_results || 0,
          search_time_ms: chunk.search_time_ms || 0,
          streaming_complete: true,
        };
        break;

      case 'intent':
      case 'entities':
      case 'action':
        // These are metadata events, can be collected if needed
        break;
    }
  }

  if (finalResponse) {
    return finalResponse;
  }
}

/**
 * Non-streaming search - returns all results at once
 */
async function search(
  request: CelesteSearchRequest,
  signal?: AbortSignal
): Promise<CelesteSearchResponse> {
  const url = `${WEBHOOK_BASE_URL}/search`;
  const headers = await buildHeaders();

  console.log('[celesteApi] Executing search:', { query: request.query });

  return fetchWithTimeout<CelesteSearchResponse>(
    url,
    {
      method: 'POST',
      headers,
      body: JSON.stringify({ ...request, stream: false }),
      signal,
    },
    DEFAULT_TIMEOUT
  );
}

// ============================================================================
// ACTION ROUTER API
// ============================================================================

/**
 * Execute an action through the Action Router
 */
async function executeAction(
  request: CelesteActionRequest,
  signal?: AbortSignal
): Promise<CelesteActionResponse> {
  const url = `${API_V1_URL}/actions/execute`;
  const headers = await buildHeaders();

  console.log('[celesteApi] Executing action:', {
    action: request.action,
    context: request.context,
  });

  const response = await fetchWithTimeout<CelesteActionResponse>(
    url,
    {
      method: 'POST',
      headers,
      body: JSON.stringify(request),
      signal,
    },
    DEFAULT_TIMEOUT
  );

  if (response.status === 'error') {
    throw new CelesteApiError(
      response.error_code || 'execution_failed',
      response.message || 'Action execution failed'
    );
  }

  return response;
}

// ============================================================================
// PREDICTIVE API
// ============================================================================

/**
 * Get predictive state for equipment
 */
async function getPredictiveState(
  equipmentId: string,
  signal?: AbortSignal
): Promise<PredictiveState> {
  const url = `${API_V1_URL}/predictive/${equipmentId}`;
  const headers = await buildHeaders();

  console.log('[celesteApi] Getting predictive state:', { equipmentId });

  return fetchWithTimeout<PredictiveState>(
    url,
    { method: 'GET', headers, signal },
    DEFAULT_TIMEOUT
  );
}

/**
 * Get predictive overview for dashboard
 */
async function getPredictiveOverview(
  yachtId: string,
  signal?: AbortSignal
): Promise<PredictiveOverview> {
  const url = `${API_V1_URL}/predictive/overview/${yachtId}`;
  const headers = await buildHeaders();

  return fetchWithTimeout<PredictiveOverview>(
    url,
    { method: 'GET', headers, signal },
    DEFAULT_TIMEOUT
  );
}

// ============================================================================
// DASHBOARD API
// ============================================================================

/**
 * Get dashboard metrics
 */
async function getDashboardMetrics(
  yachtId: string,
  signal?: AbortSignal
): Promise<DashboardMetrics> {
  const url = `${API_V1_URL}/dashboard/${yachtId}/metrics`;
  const headers = await buildHeaders();

  return fetchWithTimeout<DashboardMetrics>(
    url,
    { method: 'GET', headers, signal },
    DEFAULT_TIMEOUT
  );
}

// ============================================================================
// DOCUMENT API
// ============================================================================

interface PresignedUrlResponse {
  url: string;
  expires_at: string;
}

/**
 * Get presigned URL for document download
 */
async function getDocumentUrl(
  documentId: string,
  signal?: AbortSignal
): Promise<PresignedUrlResponse> {
  const url = `${WEBHOOK_BASE_URL}/documents/${documentId}/url`;
  const headers = await buildHeaders();

  return fetchWithTimeout<PresignedUrlResponse>(
    url,
    { method: 'GET', headers, signal },
    DEFAULT_TIMEOUT
  );
}

// ============================================================================
// QUERY CANCELLATION HELPER
// ============================================================================

/**
 * Creates a cancellable search operation
 * Returns abort function to cancel in-flight request
 */
function createCancellableSearch(
  request: CelesteSearchRequest,
  onResult: (result: SearchResultCard) => void,
  onComplete?: (response: CelesteSearchResponse) => void,
  onError?: (error: CelesteApiError) => void
): { cancel: () => void } {
  const controller = new AbortController();

  (async () => {
    try {
      const generator = searchStream(request, controller.signal);
      let result = await generator.next();

      while (!result.done) {
        if (controller.signal.aborted) break;
        onResult(result.value as SearchResultCard);
        result = await generator.next();
      }

      if (result.value && onComplete) {
        onComplete(result.value as CelesteSearchResponse);
      }
    } catch (error) {
      if (!controller.signal.aborted && onError) {
        onError(
          error instanceof CelesteApiError
            ? error
            : new CelesteApiError('unknown_error', String(error))
        );
      }
    }
  })();

  return {
    cancel: () => controller.abort(),
  };
}

// ============================================================================
// EXPORTED CLIENT
// ============================================================================

export const celesteClient = {
  // Search
  search,
  searchStream,
  createCancellableSearch,

  // Actions
  executeAction,

  // Predictive
  getPredictiveState,
  getPredictiveOverview,

  // Dashboard
  getDashboardMetrics,

  // Documents
  getDocumentUrl,
};

export default celesteClient;
