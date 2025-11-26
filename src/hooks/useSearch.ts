import { useState, useCallback } from 'react'
import { ensureFreshToken, getCurrentSession } from '@/lib/auth-helpers'

const SEARCH_API_URL = 'https://api.celeste7.ai/search'

/**
 * Search result card types
 */
export type SearchResultType =
  | 'document_chunk'
  | 'fault'
  | 'work_order'
  | 'part'
  | 'predictive'
  | 'history_event'

/**
 * Micro-action attached to search results
 */
export interface SearchAction {
  label: string
  action: string
  equipment_id?: string
  context?: Record<string, unknown>
}

/**
 * Individual search result
 */
export interface SearchResult {
  type: SearchResultType
  document_id?: string
  work_order_id?: string
  chunk_index?: number
  score: number
  text_preview?: string
  summary?: string
  title?: string
  actions?: string[]
}

/**
 * Full search response from the API
 */
export interface SearchResponse {
  query_id: string
  intent: string
  entities: {
    equipment_id?: string
    fault_code?: string
    part_number?: string
  }
  results: SearchResult[]
  actions: SearchAction[]
}

/**
 * Search state
 */
export interface SearchState {
  isLoading: boolean
  error: string | null
  response: SearchResponse | null
}

/**
 * Search filters
 */
export interface SearchFilters {
  equipment_id?: string | null
  document_type?: string | null
}

/**
 * Search payload sent to the API
 */
interface SearchPayload {
  query: string
  query_type: 'free-text'
  auth: {
    user_id: string
    yacht_id: string | null
    yacht_signature: null
  }
  context: {
    client_ts: number
    stream_id: string
    session_id: string
    source: 'web'
    client_version: string
    locale: string
    timezone: string
    platform: 'browser'
  }
  filters?: SearchFilters
  stream: boolean
}

/**
 * Hook for making authenticated search requests to the CelesteOS API.
 *
 * Automatically handles:
 * - JWT token refresh before requests (prevents "token expired" errors)
 * - Loading and error states
 * - Request context (timestamps, session IDs, locale, etc.)
 *
 * @example
 * ```tsx
 * const { search, isLoading, error, response } = useSearch()
 *
 * const handleSearch = async () => {
 *   await search('fault code E047 on main engine')
 * }
 * ```
 */
export function useSearch() {
  const [state, setState] = useState<SearchState>({
    isLoading: false,
    error: null,
    response: null
  })

  const search = useCallback(async (
    query: string,
    filters?: SearchFilters
  ): Promise<SearchResponse | null> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }))

    try {
      // Get fresh token before making request (fixes JWT expired errors)
      const token = await ensureFreshToken()
      const session = await getCurrentSession()

      const payload: SearchPayload = {
        query,
        query_type: 'free-text',
        auth: {
          user_id: session.userId,
          yacht_id: session.yachtId,
          yacht_signature: null
        },
        context: {
          client_ts: Math.floor(Date.now() / 1000),
          stream_id: crypto.randomUUID(),
          session_id: crypto.randomUUID(),
          source: 'web',
          client_version: '1.0.0',
          locale: navigator.language,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
          platform: 'browser'
        },
        filters: filters || undefined,
        stream: true
      }

      const response = await fetch(SEARCH_API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Search failed: ${response.status} - ${errorText}`)
      }

      const data: SearchResponse = await response.json()

      setState({
        isLoading: false,
        error: null,
        response: data
      })

      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Search failed'

      setState({
        isLoading: false,
        error: errorMessage,
        response: null
      })

      // Re-throw authentication errors so caller can redirect to login
      if (errorMessage === 'Not authenticated' || errorMessage === 'Failed to refresh token') {
        throw err
      }

      return null
    }
  }, [])

  const clearResults = useCallback(() => {
    setState({
      isLoading: false,
      error: null,
      response: null
    })
  }, [])

  return {
    search,
    clearResults,
    isLoading: state.isLoading,
    error: state.error,
    response: state.response,
    results: state.response?.results || [],
    actions: state.response?.actions || []
  }
}
