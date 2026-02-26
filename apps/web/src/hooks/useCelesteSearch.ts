/**
 * CelesteOS Global Search Hook
 *
 * Spotlight/Raycast-style buffered streaming search:
 * - Debounced keystroke batching
 * - AbortController for request cancellation
 * - Streaming response with stable UI updates
 * - Local instant suggestions
 * - No layout shift, no flicker
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { getYachtId, getYachtSignature } from '@/lib/authHelpers';
import { ensureFreshToken } from '@/lib/tokenRefresh';
import type { SearchResult } from '@/types/search';
import { getActionSuggestions, type ActionSuggestion } from '@/lib/actionClient';

// Constants
const FAST_TYPING_DEBOUNCE = 140; // ms - user typing quickly
const SLOW_TYPING_DEBOUNCE = 80;  // ms - user typing slowly
const MIN_QUERY_INTERVAL = 100;   // ms - minimum between requests
const RECENT_QUERIES_KEY = 'celeste_recent_queries';
const MAX_RECENT_QUERIES = 5;
const CACHE_TTL = 5 * 60 * 1000;  // 5 minutes

// F1 Architecture: L1/L2 Budget Enforcement
const L1_TIMEOUT_MS = 3000;       // 3s timeout for primary search (includes network latency)
const L2_TIMEOUT_MS = 5000;       // 5s timeout for fallback search
const TOKEN_REFRESH_TIMEOUT_MS = 2000; // 2s timeout for token refresh

/**
 * Wrap a promise with a timeout - FIXES AbortError race condition
 * @returns Promise that rejects with TimeoutError if timeout expires
 */
function withTimeout<T>(promise: Promise<T>, timeoutMs: number, operation: string): Promise<T> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error(`${operation} timed out after ${timeoutMs}ms`));
    }, timeoutMs);

    promise
      .then((result) => {
        clearTimeout(timer);
        resolve(result);
      })
      .catch((error) => {
        clearTimeout(timer);
        reject(error);
      });
  });
}

/**
 * Safe token refresh with timeout - prevents indefinite hang
 */
async function safeEnsureFreshToken(): Promise<string | null> {
  try {
    return await withTimeout(
      ensureFreshToken(),
      TOKEN_REFRESH_TIMEOUT_MS,
      'Token refresh'
    );
  } catch (error) {
    console.warn('[useCelesteSearch] Token refresh failed/timed out, proceeding without:', error);
    // Return null - search will proceed without auth (may fail with 401, but won't hang)
    return null;
  }
}

// Certificate action keywords - triggers action suggestions fetch
const CERT_ACTION_KEYWORDS = [
  'add certificate',
  'create certificate',
  'new certificate',
  'link document',
  'attach document',
  'supersede cert',
  'update cert',
  'add vessel cert',
  'add crew cert',
];

/**
 * Detect if query contains explicit certificate micro-action intent
 */
function detectCertActionIntent(query: string): boolean {
  const lowerQuery = query.toLowerCase().trim();
  return CERT_ACTION_KEYWORDS.some(keyword => lowerQuery.includes(keyword));
}

// Work order action keywords
const WO_ACTION_KEYWORDS = [
  'add work order',
  'create work order',
  'new work order',
  'create wo',
  'assign work order',
  'start work order',
  'close work order',
  'cancel work order',
  'add wo note',
  'add wo photo',
  'add part to work order',
  'work order from fault',
];

function detectWorkOrderActionIntent(query: string): boolean {
  const lowerQuery = query.toLowerCase().trim();
  return WO_ACTION_KEYWORDS.some(keyword => lowerQuery.includes(keyword));
}

// Fault action keywords - Fault Lens v1
const FAULT_ACTION_KEYWORDS = [
  'report fault',
  'add fault',
  'create fault',
  'new fault',
  'log fault',
  'acknowledge fault',
  'close fault',
  'update fault',
  'add fault note',
  'add fault photo',
  'diagnose fault',
  'reopen fault',
  'false alarm',
  'work order from fault',
  'fault history',
  'view fault',
];

function detectFaultActionIntent(query: string): boolean {
  const lowerQuery = query.toLowerCase().trim();
  return FAULT_ACTION_KEYWORDS.some(keyword => lowerQuery.includes(keyword));
}

// Shopping List action keywords - Shopping List Lens v1
const SHOPPING_LIST_ACTION_KEYWORDS = [
  'add to shopping list',
  'create shopping list',
  'new shopping list item',
  'request part',
  'need to order',
  'order part',
  'add shopping item',
  'shopping list item',
  'approve shopping',
  'reject shopping',
  'promote to part',
  'promote shopping',
  'shopping list',
  'parts request',
  'order request',
  'need part',
  'requisition',
];

function detectShoppingListActionIntent(query: string): boolean {
  const lowerQuery = query.toLowerCase().trim();
  return SHOPPING_LIST_ACTION_KEYWORDS.some(keyword => lowerQuery.includes(keyword));
}

// Document action keywords - Document Lens v2
const DOCUMENT_ACTION_KEYWORDS = [
  'add document',
  'upload document',
  'create document',
  'new document',
  'upload file',
  'add file',
  'attach file',
  'upload pdf',
  'add doc',
  'upload doc',
  'document upload',
  'file upload',
  'update document',
  'tag document',
  'add document tag',
  'delete document',
  'remove document',
  'get document',
  'download document',
  'view document',
  'document url',
  'link document',
];

function detectDocumentActionIntent(query: string): boolean {
  const lowerQuery = query.toLowerCase().trim();
  return DOCUMENT_ACTION_KEYWORDS.some(keyword => lowerQuery.includes(keyword));
}

// Part/Inventory action keywords - Part Lens (Inventory Item)
const PART_ACTION_KEYWORDS = [
  'receive part',
  'consume part',
  'transfer part',
  'adjust stock',
  'write off part',
  'view part',
  'part details',
  'check stock',
  'inventory',
];

function detectPartActionIntent(query: string): boolean {
  const lowerQuery = query.toLowerCase().trim();
  return PART_ACTION_KEYWORDS.some(keyword => lowerQuery.includes(keyword));
}

// Receiving action keywords - Receiving Lens v1
const RECEIVING_ACTION_KEYWORDS = [
  'upload invoice',
  'create receiving',
  'new receiving',
  'accept receiving',
  'view receiving history',
  'receiving history',
  'attach packing slip',
  'upload packing slip',
  'add receiving item',
  'add item to receiving',
  'link invoice',
  'attach invoice',
  'reject receiving',
  'update receiving',
  'extract receiving',
  'receiving document',
  'view receiving',
  'show receiving',
];

function detectReceivingActionIntent(query: string): boolean {
  const lowerQuery = query.toLowerCase().trim();
  return RECEIVING_ACTION_KEYWORDS.some(keyword => lowerQuery.includes(keyword));
}

// Crew action keywords - Crew Lens v2
const CREW_ACTION_KEYWORDS = [
  'my profile',
  'view profile',
  'own profile',
  'profile details',
  'view my profile',
  'show my profile',
  'update my profile',
  'update profile',
  'edit profile',
  'change name',
  'edit my profile',
  'list crew',
  'crew roster',
  'crew members',
  'all crew',
  'view crew',
  'show crew',
  'crew list',
  'assign role',
  'promote',
  'give role',
  'add role',
  'assign crew role',
  'revoke role',
  'remove role',
  'take away role',
  'revoke crew role',
  'deactivate crew',
  'activate crew',
  'crew status',
  'disable crew',
  'enable crew',
  'crew certificates',
  'view certs',
  'crew certs',
  'certificate status',
  'crew work history',
  'work history',
  'assigned work orders',
  'my work orders',
  'crew details',
  'view crew member',
];

function detectCrewActionIntent(query: string): boolean {
  const lowerQuery = query.toLowerCase().trim();
  return CREW_ACTION_KEYWORDS.some(keyword => lowerQuery.includes(keyword));
}

// Types
interface SearchState {
  query: string;
  results: SearchResult[];
  isStreaming: boolean;
  isLoading: boolean;
  error: string | null;
  suggestions: SearchSuggestion[];
  actionSuggestions: ActionSuggestion[];
}

interface SearchSuggestion {
  type: 'recent' | 'cached' | 'predicted';
  text: string;
  score?: number;
}

interface CachedResult {
  query: string;
  results: SearchResult[];
  timestamp: number;
}

// Valid roles per spec
type ValidRole = 'Engineer' | 'HOD' | 'Captain' | 'ETO' | 'Fleet Manager' | 'Admin' | 'Owner Tech Representative';

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
    'crew': 'Engineer',
    'deck': 'Engineer',
    'interior': 'Engineer',
  };
  return roleMap[role?.toLowerCase() || ''] || 'Engineer';
}

// Session ID management
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

// Recent queries management
function getRecentQueries(): string[] {
  if (typeof localStorage === 'undefined') return [];
  try {
    const stored = localStorage.getItem(RECENT_QUERIES_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

function addRecentQuery(query: string): void {
  if (typeof localStorage === 'undefined' || !query.trim()) return;
  try {
    const recent = getRecentQueries().filter(q => q !== query);
    recent.unshift(query);
    localStorage.setItem(RECENT_QUERIES_KEY, JSON.stringify(recent.slice(0, MAX_RECENT_QUERIES)));
  } catch {
    // Ignore storage errors
  }
}

// Result cache management
const resultCache = new Map<string, CachedResult>();

function getCachedResults(query: string): SearchResult[] | null {
  const cached = resultCache.get(query.toLowerCase());
  // Don't return empty cached results - let search retry
  if (cached && cached.results.length > 0 && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached.results;
  }
  return null;
}

function setCachedResults(query: string, results: SearchResult[]): void {
  // Don't cache empty results - let future searches retry
  if (results.length === 0) {
    return;
  }
  resultCache.set(query.toLowerCase(), {
    query,
    results,
    timestamp: Date.now(),
  });
}

// Find cached results for prefix matches
function findPrefixCachedResults(query: string): SearchResult[] {
  const lowerQuery = query.toLowerCase();
  for (const [key, cached] of resultCache.entries()) {
    if (key.startsWith(lowerQuery) && Date.now() - cached.timestamp < CACHE_TTL) {
      return cached.results;
    }
  }
  return [];
}

/**
 * Build search payload per search-engine-spec.md
 * @param yachtId - yacht_id from AuthContext (NOT from deprecated getYachtId())
 */
async function buildSearchPayload(query: string, streamId: string, yachtId: string | null) {
  const { data: { session } } = await supabase.auth.getSession();
  // Use yacht_id from AuthContext, not from user_metadata (which is never set)
  const yachtSignature = await getYachtSignature(yachtId);

  const rawRole = session?.user?.user_metadata?.role as string || 'crew';

  return {
    query,
    query_type: 'free-text',
    limit: 75, // Spotlight-style grouping needs domain diversity
    auth: session?.user ? {
      user_id: session.user.id,
      yacht_id: yachtId,
      role: mapToValidRole(rawRole),
      email: session.user.email || '',
      yacht_signature: yachtSignature,
    } : undefined,
    context: {
      client_ts: Math.floor(Date.now() / 1000),
      stream_id: streamId,
      session_id: getSessionId(),
      source: 'web',
      client_version: '1.0.0',
      locale: typeof navigator !== 'undefined' ? navigator.language : 'en-US',
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      platform: 'browser',
    },
  };
}

/**
 * Parse SSE stream from F1 search endpoint
 * Handles event: data: format per SSE spec
 */
async function* parseSSEStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  signal: AbortSignal
): AsyncGenerator<SearchResult[], void, unknown> {
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      if (signal.aborted) break;

      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE events (separated by double newlines)
      const events = buffer.split('\n\n');
      buffer = events.pop() || ''; // Keep incomplete event in buffer

      for (const event of events) {
        if (!event.trim()) continue;

        // Parse SSE format: "event: <type>\ndata: <json>"
        const lines = event.split('\n');
        let eventType = 'message';
        let eventData = '';

        for (const line of lines) {
          if (line.startsWith('event:')) {
            eventType = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            eventData = line.slice(5).trim();
          }
        }

        if (!eventData) continue;

        try {
          const parsed = JSON.parse(eventData);

          // Handle different SSE event types from F1 endpoint
          // NOTE: Backend sends "items" not "results" in result_batch
          if (eventType === 'result_batch' && parsed.items) {
            console.log('[useCelesteSearch] 📦 SSE batch received:', parsed.items.length, 'results');
            yield parsed.items;
          } else if (eventType === 'exact_match_win' && parsed.result) {
            console.log('[useCelesteSearch] 🎯 SSE exact match:', parsed.result.title);
            yield [parsed.result];
          } else if (eventType === 'finalized') {
            console.log('[useCelesteSearch] ✅ SSE finalized:', parsed.latency_ms, 'ms');
          } else if (eventType === 'diagnostics') {
            console.log('[useCelesteSearch] 🔍 SSE diagnostics:', parsed.search_id);
          } else if (eventType === 'error') {
            console.error('[useCelesteSearch] ❌ SSE error:', parsed.message);
          }
        } catch (parseError) {
          console.warn('[useCelesteSearch] ⚠️ Failed to parse SSE data:', eventData);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Abortable streaming fetch via F1 SSE endpoint
 * @param yachtId - yacht_id from AuthContext (NOT from deprecated getYachtId())
 */
async function* streamSearch(
  query: string,
  signal: AbortSignal,
  yachtId: string | null
): AsyncGenerator<SearchResult[], void, unknown> {
  console.log('[useCelesteSearch] 🎬 streamSearch STARTED (F1 SSE)');

  // F1 Architecture: Pipeline-core backend, configurable via env var
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const streamId = crypto.randomUUID();

  console.log('[useCelesteSearch] 🔍 F1 SSE search:', { query, API_URL, yachtId });

  // Get fresh token with timeout protection (prevents indefinite hang)
  const jwt = await safeEnsureFreshToken();
  // Use yacht_id from AuthContext, not from user_metadata (which is never set)
  const yachtSignature = await getYachtSignature(yachtId);

  // Build headers for GET request (no Content-Type for GET)
  const headers: Record<string, string> = {
    'Accept': 'text/event-stream',
  };

  if (jwt) {
    headers['Authorization'] = `Bearer ${jwt}`;
  }
  if (yachtSignature) {
    headers['X-Yacht-Signature'] = yachtSignature;
  }

  // F1 SSE endpoint: GET /api/f1/search/stream?q=<query>
  const searchUrl = new URL(`${API_URL}/api/f1/search/stream`);
  searchUrl.searchParams.set('q', query);

  console.log('[useCelesteSearch] 📤 F1 SSE request to:', searchUrl.toString());

  let response;

  try {
    response = await fetch(searchUrl.toString(), {
      method: 'GET',
      headers,
      signal,
    });

    console.log('[useCelesteSearch] 📥 F1 SSE response status:', response.status);

    if (!response.ok) {
      throw new Error(`F1 search failed: ${response.status}`);
    }

    // Parse SSE stream
    if (!response.body) {
      throw new Error('No response body for SSE stream');
    }

    const reader = response.body.getReader();

    // Yield results as they arrive via SSE
    for await (const results of parseSSEStream(reader, signal)) {
      if (signal.aborted) break;

      // Map F1 backend fields to frontend expected fields
      // Backend sends: object_id, object_type, payload, fused_score
      // Frontend expects: id, type, title, subtitle, score
      const mappedResults: SearchResult[] = results.map((result) => {
        const backendResult = result as {
          object_id?: string;
          object_type?: string;
          payload?: { name?: string; title?: string; part_name?: string; code?: string; status?: string; source_table?: string };
          fused_score?: number;
          // Legacy field names (fallback)
          primary_id?: string;
          source_table?: string;
          snippet?: string;
          rrf_score?: number;
        } & SearchResult;

        const payload = backendResult.payload || {};
        return {
          ...backendResult,
          id: backendResult.object_id || backendResult.primary_id || backendResult.id,
          type: (backendResult.object_type || payload.source_table || backendResult.source_table || backendResult.type) as SearchResult['type'],
          title: payload.name || payload.title || payload.part_name || backendResult.title || 'Untitled',
          subtitle: payload.code || payload.status || backendResult.subtitle,
          snippet: backendResult.snippet || (payload as any).snippet,
          score: backendResult.fused_score ?? backendResult.rrf_score ?? backendResult.score ?? 0,
          actions: backendResult.actions || [],
          metadata: { ...backendResult.metadata, payload },
        };
      });

      if (mappedResults.length > 0) {
        console.log('[useCelesteSearch] 🔬 First mapped result:', {
          id: mappedResults[0].id,
          type: mappedResults[0].type,
          title: mappedResults[0].title,
          snippet: mappedResults[0].snippet,
        });
      }

      yield mappedResults;
    }
  } catch (e) {
    // CRITICAL FIX: Check if primary was aborted - if so, don't attempt fallback
    // This fixes "AbortError: signal is aborted without reason"
    if (signal.aborted) {
      console.log('[useCelesteSearch] ⏹️ F1 SSE search aborted, skipping fallback');
      return;
    }

    console.warn('[useCelesteSearch] ⚠️ F1 SSE search failed, using fallback:', e);

    // FALLBACK: Use local database search when pipeline is down
    // CRITICAL FIX: Create NEW AbortController for fallback with L2 timeout
    // This prevents the fallback from immediately aborting due to reused signal
    const fallbackController = new AbortController();
    const fallbackTimeout = setTimeout(() => fallbackController.abort(), L2_TIMEOUT_MS);

    try {
      const fallbackHeaders: Record<string, string> = {
        'Content-Type': 'application/json',
      };

      // Add Authorization header for fallback (requires auth)
      if (jwt) {
        fallbackHeaders['Authorization'] = `Bearer ${jwt}`;
      }

      const fallbackResponse = await fetch('/api/search/fallback', {
        method: 'POST',
        headers: fallbackHeaders,
        body: JSON.stringify({
          query,
          yacht_id: yachtId,
          limit: 75, // Spotlight-style grouping needs domain diversity
        }),
        signal: fallbackController.signal, // Use NEW controller, not original signal
      });

      clearTimeout(fallbackTimeout);

      if (fallbackResponse.ok) {
        const fallbackData = await fallbackResponse.json();
        console.log('[useCelesteSearch] ✅ Using fallback search results:', fallbackData.total_count, 'results');
        if (fallbackData.results && Array.isArray(fallbackData.results)) {
          yield fallbackData.results;
        }
      } else {
        console.error('[useCelesteSearch] ❌ Fallback search also failed:', fallbackResponse.status);
      }
    } catch (fallbackError) {
      clearTimeout(fallbackTimeout);
      // Suppress AbortError from our own timeout
      if (fallbackError instanceof Error && fallbackError.name === 'AbortError') {
        console.warn('[useCelesteSearch] ⏱️ Fallback search timed out after', L2_TIMEOUT_MS, 'ms');
      } else {
        console.error('[useCelesteSearch] ❌ Fallback search failed:', fallbackError);
      }
    }
  }
}

/**
 * Non-streaming fallback fetch via F1 endpoint
 * Collects all SSE results into a single array
 * @param yachtId - yacht_id from AuthContext (NOT from deprecated getYachtId())
 */
async function fetchSearch(query: string, signal: AbortSignal, yachtId: string | null): Promise<SearchResult[]> {
  // F1 Architecture: Pipeline-core backend, configurable via env var
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

  // Get fresh token with timeout protection (prevents indefinite hang)
  const jwt = await safeEnsureFreshToken();
  // Use yacht_id from AuthContext, not from user_metadata (which is never set)
  const yachtSignature = await getYachtSignature(yachtId);

  // Build headers for GET request
  const headers: Record<string, string> = {
    'Accept': 'text/event-stream',
  };

  if (jwt) {
    headers['Authorization'] = `Bearer ${jwt}`;
  }
  if (yachtSignature) {
    headers['X-Yacht-Signature'] = yachtSignature;
  }

  // F1 SSE endpoint: GET /api/f1/search/stream?q=<query>
  const searchUrl = new URL(`${API_URL}/api/f1/search/stream`);
  searchUrl.searchParams.set('q', query);

  try {
    const response = await fetch(searchUrl.toString(), {
      method: 'GET',
      headers,
      signal,
    });

    if (!response.ok) {
      throw new Error(`F1 search failed: ${response.status}`);
    }

    if (!response.body) {
      throw new Error('No response body for SSE stream');
    }

    // Collect all results from SSE stream
    const allResults: SearchResult[] = [];
    const reader = response.body.getReader();

    for await (const results of parseSSEStream(reader, signal)) {
      // Map F1 backend fields to frontend expected fields
      const mappedResults: SearchResult[] = results.map((result) => {
        const backendResult = result as {
          object_id?: string;
          object_type?: string;
          payload?: { name?: string; title?: string; part_name?: string; code?: string; status?: string; source_table?: string };
          fused_score?: number;
          primary_id?: string;
          source_table?: string;
          snippet?: string;
          rrf_score?: number;
        } & SearchResult;

        const payload = backendResult.payload || {};
        return {
          ...backendResult,
          id: backendResult.object_id || backendResult.primary_id || backendResult.id,
          type: (backendResult.object_type || payload.source_table || backendResult.source_table || backendResult.type) as SearchResult['type'],
          title: payload.name || payload.title || payload.part_name || backendResult.title || 'Untitled',
          subtitle: payload.code || payload.status || backendResult.subtitle,
          snippet: backendResult.snippet || (payload as any).snippet,
          score: backendResult.fused_score ?? backendResult.rrf_score ?? backendResult.score ?? 0,
          actions: backendResult.actions || [],
          metadata: { ...backendResult.metadata, payload },
        };
      });
      allResults.push(...mappedResults);
    }

    return allResults;
  } catch (error) {
    // CRITICAL FIX: Check if primary was aborted - if so, don't attempt fallback
    if (signal.aborted) {
      console.log('[useCelesteSearch] ⏹️ F1 search aborted, skipping fallback');
      return [];
    }

    console.warn('[useCelesteSearch] ⚠️ F1 search failed, using fallback:', error);

    // FALLBACK: Use local database search when pipeline is down
    // CRITICAL FIX: Create NEW AbortController for fallback with L2 timeout
    const fallbackController = new AbortController();
    const fallbackTimeout = setTimeout(() => fallbackController.abort(), L2_TIMEOUT_MS);

    try {
      const fallbackHeaders: Record<string, string> = {
        'Content-Type': 'application/json',
      };

      // Add Authorization header for fallback (requires auth)
      if (jwt) {
        fallbackHeaders['Authorization'] = `Bearer ${jwt}`;
      }

      const fallbackResponse = await fetch('/api/search/fallback', {
        method: 'POST',
        headers: fallbackHeaders,
        body: JSON.stringify({
          query,
          yacht_id: yachtId,
          limit: 75, // Spotlight-style grouping needs domain diversity
        }),
        signal: fallbackController.signal, // Use NEW controller, not original signal
      });

      clearTimeout(fallbackTimeout);

      if (!fallbackResponse.ok) {
        console.error('[useCelesteSearch] ❌ Fallback search also failed:', fallbackResponse.status);
        return [];
      }

      const fallbackData = await fallbackResponse.json();
      console.log('[useCelesteSearch] ✅ Using fallback search results:', fallbackData.total_count, 'results');
      return fallbackData.results || [];
    } catch (fallbackError) {
      clearTimeout(fallbackTimeout);
      // Suppress AbortError from our own timeout
      if (fallbackError instanceof Error && fallbackError.name === 'AbortError') {
        console.warn('[useCelesteSearch] ⏱️ Fallback search timed out after', L2_TIMEOUT_MS, 'ms');
      } else {
        console.error('[useCelesteSearch] ❌ Fallback search failed:', fallbackError);
      }
      return [];
    }
  }
}

/**
 * Main search hook
 * @param yachtId - yacht_id from AuthContext. REQUIRED for proper search scoping.
 *                  Pass user?.yachtId from useAuth() hook.
 */
export function useCelesteSearch(yachtId: string | null = null) {
  const [state, setState] = useState<SearchState>({
    query: '',
    results: [],
    isStreaming: false,
    isLoading: false,
    error: null,
    suggestions: [],
    actionSuggestions: [],
  });

  // Refs for debouncing and cancellation
  const abortControllerRef = useRef<AbortController | null>(null);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const lastQueryTimeRef = useRef<number>(0);
  const lastKeystrokeRef = useRef<number>(0);
  const pendingQueryRef = useRef<string>('');

  // Stable result map to prevent reordering
  const resultMapRef = useRef<Map<string, SearchResult>>(new Map());

  /**
   * Get instant suggestions (< 50ms)
   */
  const getInstantSuggestions = useCallback((query: string): SearchSuggestion[] => {
    if (!query.trim()) return [];

    const suggestions: SearchSuggestion[] = [];
    const lowerQuery = query.toLowerCase();

    // Recent queries matching prefix
    const recentQueries = getRecentQueries();
    for (const recent of recentQueries) {
      if (recent.toLowerCase().startsWith(lowerQuery) && recent !== query) {
        suggestions.push({ type: 'recent', text: recent });
      }
    }

    // Cached results for prefix
    const prefixResults = findPrefixCachedResults(query);
    if (prefixResults.length > 0) {
      suggestions.push({ type: 'cached', text: `${prefixResults.length} cached results` });
    }

    return suggestions.slice(0, 5);
  }, []);

  /**
   * Merge new results with stable ordering
   */
  const mergeResults = useCallback((newResults: SearchResult[]): SearchResult[] => {
    const resultMap = resultMapRef.current;

    // Update existing results, add new ones
    for (const result of newResults) {
      resultMap.set(result.id, result);
    }

    // Return results maintaining insertion order, sorted by score
    return Array.from(resultMap.values())
      .sort((a, b) => (b.score || 0) - (a.score || 0));
  }, []);

  /**
   * Clear results for new query
   */
  const clearResultMap = useCallback(() => {
    resultMapRef.current.clear();
  }, []);

  /**
   * Cancel current request
   */
  const cancelCurrentRequest = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }
  }, []);

  /**
   * Fetch action suggestions if query has action intent (cert, WO, fault, shopping list, documents, receiving, crew)
   */
  const fetchActionSuggestionsIfNeeded = useCallback(async (query: string) => {
    const wantsCert = detectCertActionIntent(query);
    const wantsWO = detectWorkOrderActionIntent(query);
    const wantsFault = detectFaultActionIntent(query);
    const wantsShoppingList = detectShoppingListActionIntent(query);
    const wantsDocument = detectDocumentActionIntent(query);
    const wantsReceiving = detectReceivingActionIntent(query);
    const wantsPart = detectPartActionIntent(query);
    const wantsCrew = detectCrewActionIntent(query);

    if (!wantsCert && !wantsWO && !wantsFault && !wantsShoppingList && !wantsDocument && !wantsReceiving && !wantsPart && !wantsCrew) {
      // Clear action suggestions if no intent
      setState(prev => ({ ...prev, actionSuggestions: [] }));
      return;
    }

    try {
      // Determine domain - priority order: crew > parts > receiving > documents > fault > shopping_list > cert > work_orders
      let domain: string;
      if (wantsCrew) {
        domain = 'crew';
      } else if (wantsPart) {
        domain = 'parts';
      } else if (wantsReceiving) {
        domain = 'receiving';
      } else if (wantsDocument) {
        domain = 'documents';
      } else if (wantsFault) {
        domain = 'faults';
      } else if (wantsShoppingList) {
        domain = 'shopping_list';
      } else if (wantsCert) {
        domain = 'certificates';
      } else {
        domain = 'work_orders';
      }

      console.log('[useCelesteSearch] 🎯 Action intent detected for', domain, '— fetching suggestions');
      const response = await getActionSuggestions(query, domain);
      console.log('[useCelesteSearch] 📋 Action suggestions received:', response.actions.length);

      setState(prev => ({
        ...prev,
        actionSuggestions: response.actions,
      }));
    } catch (error) {
      console.warn('[useCelesteSearch] Failed to fetch action suggestions:', error);
      // Don't block search on action suggestion failure
      setState(prev => ({ ...prev, actionSuggestions: [] }));
    }
  }, []);

  /**
   * Execute search
   */
  const executeSearch = useCallback(async (query: string) => {
    console.log('[useCelesteSearch] ⚡ executeSearch called:', query);

    if (!query.trim()) {
      setState(prev => ({
        ...prev,
        results: [],
        isLoading: false,
        isStreaming: false,
        error: null,
        actionSuggestions: [],
      }));
      clearResultMap();
      return;
    }

    // Fetch action suggestions in parallel with search (non-blocking)
    fetchActionSuggestionsIfNeeded(query);

    // Check cache first
    const cached = getCachedResults(query);
    if (cached) {
      console.log('[useCelesteSearch] 💾 Using cached results:', cached.length);
      setState(prev => ({
        ...prev,
        results: cached,
        isLoading: false,
        isStreaming: false,
      }));
      return;
    }

    console.log('[useCelesteSearch] 🚀 Starting new search (no cache)');

    // Create new abort controller
    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;

    // Clear previous results for new query
    clearResultMap();

    console.log('[useCelesteSearch] 📍 Setting loading state...');
    setState(prev => ({
      ...prev,
      isLoading: true,
      isStreaming: true,
      error: null,
    }));

    try {
      // Try streaming first
      let hasResults = false;

      console.log('[useCelesteSearch] 📡 About to call streamSearch with yachtId:', yachtId);
      try {
        for await (const chunk of streamSearch(query, signal, yachtId)) {
          if (signal.aborted) break;

          hasResults = true;
          const merged = mergeResults(chunk);

          setState(prev => ({
            ...prev,
            results: merged,
            isLoading: false,
          }));
        }
      } catch (streamError) {
        // If streaming fails, fall back to regular fetch
        if (!signal.aborted) {
          console.warn('[useCelesteSearch] Streaming failed, using fallback:', streamError);
          const results = await fetchSearch(query, signal, yachtId);
          hasResults = results.length > 0;

          setState(prev => ({
            ...prev,
            results,
            isLoading: false,
          }));
        }
      }

      // Cache results
      if (hasResults && !signal.aborted) {
        const finalResults = Array.from(resultMapRef.current.values());
        setCachedResults(query, finalResults);
        addRecentQuery(query);
      }

      setState(prev => ({
        ...prev,
        isStreaming: false,
        isLoading: false,
      }));

    } catch (error) {
      // Suppress abort errors
      if (error instanceof Error && error.name === 'AbortError') {
        return;
      }

      console.error('[useCelesteSearch] Search error:', error);

      setState(prev => ({
        ...prev,
        isStreaming: false,
        isLoading: false,
        error: 'Connection interrupted — retrying…',
      }));

      // Auto-retry after 2 seconds
      setTimeout(() => {
        if (pendingQueryRef.current === query) {
          executeSearch(query);
        }
      }, 2000);
    }
  }, [clearResultMap, mergeResults, yachtId, fetchActionSuggestionsIfNeeded]);  // CRITICAL: yachtId must be in deps

  /**
   * Handle input change with debouncing
   */
  const handleQueryChange = useCallback((newQuery: string) => {
    console.log('[useCelesteSearch] 🔤 handleQueryChange:', newQuery);
    const now = Date.now();
    pendingQueryRef.current = newQuery;

    // Update query immediately for UI
    setState(prev => ({
      ...prev,
      query: newQuery,
      suggestions: getInstantSuggestions(newQuery),
    }));

    // Cancel any pending request
    cancelCurrentRequest();

    if (!newQuery.trim()) {
      setState(prev => ({
        ...prev,
        results: [],
        isLoading: false,
        isStreaming: false,
        error: null,
        suggestions: [],
      }));
      clearResultMap();
      return;
    }

    // Determine debounce time based on typing speed
    const timeSinceLastKeystroke = now - lastKeystrokeRef.current;
    const isFastTyping = timeSinceLastKeystroke < 100;
    const debounceTime = isFastTyping ? FAST_TYPING_DEBOUNCE : SLOW_TYPING_DEBOUNCE;

    lastKeystrokeRef.current = now;

    // Ensure minimum interval between queries
    const timeSinceLastQuery = now - lastQueryTimeRef.current;
    const effectiveDebounce = Math.max(debounceTime, MIN_QUERY_INTERVAL - timeSinceLastQuery);

    // Set debounce timer
    console.log('[useCelesteSearch] ⏲️ Debouncing for', effectiveDebounce, 'ms');
    debounceTimerRef.current = setTimeout(() => {
      console.log('[useCelesteSearch] ⏲️ Debounce complete, executing search');
      lastQueryTimeRef.current = Date.now();
      executeSearch(newQuery);
    }, effectiveDebounce);
  }, [cancelCurrentRequest, clearResultMap, executeSearch, getInstantSuggestions]);

  /**
   * Force immediate search (e.g., on Enter)
   */
  const search = useCallback((query: string) => {
    cancelCurrentRequest();
    pendingQueryRef.current = query;
    lastQueryTimeRef.current = Date.now();
    executeSearch(query);
  }, [cancelCurrentRequest, executeSearch]);

  /**
   * Clear search
   */
  const clear = useCallback(() => {
    cancelCurrentRequest();
    clearResultMap();
    pendingQueryRef.current = '';
    setState({
      query: '',
      results: [],
      isStreaming: false,
      isLoading: false,
      error: null,
      suggestions: [],
      actionSuggestions: [],
    });
  }, [cancelCurrentRequest, clearResultMap]);

  /**
   * Select a suggestion
   */
  const selectSuggestion = useCallback((suggestion: SearchSuggestion) => {
    if (suggestion.type === 'recent') {
      handleQueryChange(suggestion.text);
      search(suggestion.text);
    }
  }, [handleQueryChange, search]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cancelCurrentRequest();
    };
  }, [cancelCurrentRequest]);

  /**
   * Clear all cached results (for debugging)
   */
  const clearCache = useCallback(() => {
    resultCache.clear();
    console.log('[useCelesteSearch] 🗑️ Cache cleared');
  }, []);

  /**
   * Refetch current search (for refreshing after action)
   */
  const refetch = useCallback(() => {
    if (state.query.trim()) {
      executeSearch(state.query);
    }
  }, [state.query, executeSearch]);

  return {
    // State
    query: state.query,
    results: state.results,
    isStreaming: state.isStreaming,
    isLoading: state.isLoading,
    error: state.error,
    suggestions: state.suggestions,
    actionSuggestions: state.actionSuggestions,

    // Actions
    handleQueryChange,
    search,
    clear,
    clearCache,
    selectSuggestion,
    refetch,

    // Utils
    recentQueries: getRecentQueries(),
  };
}

export type { SearchSuggestion, SearchState };
