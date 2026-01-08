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

// Constants
const FAST_TYPING_DEBOUNCE = 140; // ms - user typing quickly
const SLOW_TYPING_DEBOUNCE = 80;  // ms - user typing slowly
const MIN_QUERY_INTERVAL = 100;   // ms - minimum between requests
const RECENT_QUERIES_KEY = 'celeste_recent_queries';
const MAX_RECENT_QUERIES = 5;
const CACHE_TTL = 5 * 60 * 1000;  // 5 minutes

// Types
interface SearchState {
  query: string;
  results: SearchResult[];
  isStreaming: boolean;
  isLoading: boolean;
  error: string | null;
  suggestions: SearchSuggestion[];
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
 */
async function buildSearchPayload(query: string, streamId: string) {
  const { data: { session } } = await supabase.auth.getSession();
  const yachtId = await getYachtId();
  const yachtSignature = await getYachtSignature(yachtId);

  const rawRole = session?.user?.user_metadata?.role as string || 'crew';

  return {
    query,
    query_type: 'free-text',
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
 * Abortable streaming fetch
 */
async function* streamSearch(
  query: string,
  signal: AbortSignal
): AsyncGenerator<SearchResult[], void, unknown> {
  console.log('[useCelesteSearch] 🎬 streamSearch STARTED');
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const streamId = crypto.randomUUID();

  console.log('[useCelesteSearch] 🔍 Streaming search:', { query, API_URL });

  // Get fresh token (auto-refreshes if expiring soon)
  const jwt = await ensureFreshToken();
  const yachtId = await getYachtId();
  const yachtSignature = await getYachtSignature(yachtId);

  const payload = await buildSearchPayload(query, streamId);

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (jwt) {
    headers['Authorization'] = `Bearer ${jwt}`;
  }
  if (yachtSignature) {
    headers['X-Yacht-Signature'] = yachtSignature;
  }

  // POST to API_URL/webhook/search endpoint
  const searchUrl = `${API_URL}/webhook/search`;
  console.log('[useCelesteSearch] 📤 Sending request to:', searchUrl);
  console.log('[useCelesteSearch] 📤 Payload:', payload);

  const response = await fetch(searchUrl, {
    method: 'POST',
    headers,
    body: JSON.stringify({ ...payload, stream: true }),
    signal,
  });

  console.log('[useCelesteSearch] 📥 Response status:', response.status);

  if (!response.ok) {
    throw new Error(`Search failed: ${response.status}`);
  }

  // SIMPLIFIED: Backend sends complete JSON response, not streaming chunks
  // Parse the full response as JSON
  try {
    const data = await response.json();
    console.log('[useCelesteSearch] ✅ Parsed response:', {
      success: data.success,
      hasResults: !!data.results,
      resultCount: data.results?.length || 0,
      totalCount: data.total_count,
      timing: data.timing_ms
    });

    if (data.results && Array.isArray(data.results)) {
      // DEBUG: Log first result structure to diagnose rendering issue
      if (data.results.length > 0) {
        const firstResult = data.results[0];
        console.log('[useCelesteSearch] 🔬 First result structure:', {
          keys: Object.keys(firstResult),

          // Frontend expected fields
          id: firstResult.id,
          type: firstResult.type,
          title: firstResult.title,
          subtitle: firstResult.subtitle,

          // Backend field names
          primary_id: firstResult.primary_id,
          source_table: firstResult.source_table,
          snippet: firstResult.snippet,

          // Full object
          fullResult: firstResult
        });
      }
      yield data.results;
    } else {
      console.warn('[useCelesteSearch] ⚠️ No results array in response:', data);
    }
  } catch (e) {
    console.error('[useCelesteSearch] ❌ Failed to parse JSON response:', e);
    throw new Error('Failed to parse search response');
  }
}

/**
 * Non-streaming fallback fetch
 */
async function fetchSearch(query: string, signal: AbortSignal): Promise<SearchResult[]> {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const streamId = crypto.randomUUID();

  // Get fresh token (auto-refreshes if expiring soon)
  const jwt = await ensureFreshToken();
  const yachtId = await getYachtId();
  const yachtSignature = await getYachtSignature(yachtId);

  const payload = await buildSearchPayload(query, streamId);

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (jwt) {
    headers['Authorization'] = `Bearer ${jwt}`;
  }
  if (yachtSignature) {
    headers['X-Yacht-Signature'] = yachtSignature;
  }

  const searchUrl = `${API_URL}/webhook/search`;
  const response = await fetch(searchUrl, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    throw new Error(`Search failed: ${response.status}`);
  }

  const data = await response.json();
  return data.results || [];
}

/**
 * Main search hook
 */
export function useCelesteSearch() {
  const [state, setState] = useState<SearchState>({
    query: '',
    results: [],
    isStreaming: false,
    isLoading: false,
    error: null,
    suggestions: [],
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
      }));
      clearResultMap();
      return;
    }

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

      console.log('[useCelesteSearch] 📡 About to call streamSearch...');
      try {
        for await (const chunk of streamSearch(query, signal)) {
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
          const results = await fetchSearch(query, signal);
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
  }, [clearResultMap, mergeResults]);

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

  return {
    // State
    query: state.query,
    results: state.results,
    isStreaming: state.isStreaming,
    isLoading: state.isLoading,
    error: state.error,
    suggestions: state.suggestions,

    // Actions
    handleQueryChange,
    search,
    clear,
    clearCache,
    selectSuggestion,

    // Utils
    recentQueries: getRecentQueries(),
  };
}

export type { SearchSuggestion, SearchState };
