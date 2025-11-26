import { useState, useCallback } from 'react'
import { search as apiSearch, SearchFilters, SearchResponse, SearchResult, SearchAction } from '@/lib/api-client'

// Re-export types for convenience
export type { SearchFilters, SearchResponse, SearchResult, SearchAction }

export type SearchResultType = SearchResult['type']

/**
 * Search state
 */
export interface SearchState {
  isLoading: boolean
  error: string | null
  response: SearchResponse | null
}

/**
 * Hook for making authenticated search requests to the CelesteOS API.
 *
 * Uses centralized API client with:
 * - Base URL: https://api.celeste7.ai/webhook/v1/search
 * - Automatic JWT token refresh before requests
 * - Loading and error states
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
      const data = await apiSearch(query, filters)

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
