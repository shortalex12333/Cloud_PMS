'use client'

import { useState, FormEvent } from 'react'
import { useSearch, SearchFilters } from '@/hooks/useSearch'

/**
 * SearchBar component demonstrating token refresh before API calls.
 *
 * Uses ensureFreshToken() internally via useSearch hook to prevent
 * "JWT token expired" errors on the search endpoint.
 *
 * @example
 * ```tsx
 * // Basic usage
 * <SearchBar />
 *
 * // With error handling callback
 * <SearchBar onAuthError={() => router.push('/login')} />
 * ```
 */
export function SearchBar({
  onAuthError
}: {
  onAuthError?: () => void
}) {
  const [query, setQuery] = useState('')
  const [filters, setFilters] = useState<SearchFilters>({
    equipment_id: null,
    document_type: null
  })

  const {
    search,
    clearResults,
    isLoading,
    error,
    results,
    actions
  } = useSearch()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()

    if (!query.trim()) return

    try {
      await search(query, filters)
    } catch (err) {
      // Handle authentication errors
      if (err instanceof Error && (
        err.message === 'Not authenticated' ||
        err.message === 'Failed to refresh token'
      )) {
        onAuthError?.()
      }
    }
  }

  return (
    <div className="search-container">
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search manuals, faults, work orders..."
          disabled={isLoading}
        />

        {/* Optional filters */}
        <select
          value={filters.document_type || ''}
          onChange={(e) => setFilters(prev => ({
            ...prev,
            document_type: e.target.value || null
          }))}
        >
          <option value="">All document types</option>
          <option value="manual">Manuals</option>
          <option value="drawing">Drawings</option>
          <option value="handover">Handover</option>
          <option value="invoice">Invoices</option>
        </select>

        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Searching...' : 'Search'}
        </button>

        {results.length > 0 && (
          <button type="button" onClick={clearResults}>
            Clear
          </button>
        )}
      </form>

      {/* Error display */}
      {error && (
        <div className="error">
          {error}
        </div>
      )}

      {/* Results display */}
      {results.length > 0 && (
        <div className="results">
          {results.map((result, index) => (
            <div key={index} className={`result-card result-${result.type}`}>
              <span className="type-badge">{result.type}</span>
              {result.title && <h3>{result.title}</h3>}
              {result.text_preview && <p>{result.text_preview}</p>}
              {result.summary && <p>{result.summary}</p>}
              <span className="score">Score: {result.score.toFixed(2)}</span>
            </div>
          ))}
        </div>
      )}

      {/* Available actions */}
      {actions.length > 0 && (
        <div className="actions">
          <h4>Quick Actions</h4>
          {actions.map((action, index) => (
            <button
              key={index}
              onClick={() => {
                // Execute micro-action via action router
                console.log('Execute action:', action)
              }}
            >
              {action.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
