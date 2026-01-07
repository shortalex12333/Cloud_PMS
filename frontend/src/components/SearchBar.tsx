'use client';

/**
 * CelesteOS Global Search Bar
 *
 * Spotlight/Raycast-style search with:
 * - Buffered debounced input
 * - Streaming results with stable ordering
 * - Instant suggestions (recent queries, cached results)
 * - No layout shift or flicker
 */

import { useEffect, useRef, useCallback } from 'react';
import { Search, X, Clock, Loader2 } from 'lucide-react';
import ResultCard from './ResultCard';
import { useCelesteSearch, type SearchSuggestion } from '@/hooks/useCelesteSearch';

export default function SearchBar() {
  const {
    query,
    results,
    isStreaming,
    isLoading,
    error,
    suggestions,
    handleQueryChange,
    search,
    clear,
    selectSuggestion,
    recentQueries,
  } = useCelesteSearch();

  const inputRef = useRef<HTMLInputElement>(null);
  const resultsContainerRef = useRef<HTMLDivElement>(null);

  // Focus search bar on mount (Spotlight behavior)
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Handle keyboard shortcuts
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && query.trim()) {
      e.preventDefault();
      search(query);
    } else if (e.key === 'Escape') {
      clear();
      inputRef.current?.blur();
    }
  }, [query, search, clear]);

  // Handle input change
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    handleQueryChange(e.target.value);
  }, [handleQueryChange]);

  // Handle clear button
  const handleClear = useCallback(() => {
    clear();
    inputRef.current?.focus();
  }, [clear]);

  // Handle suggestion click
  const handleSuggestionClick = useCallback((suggestion: SearchSuggestion) => {
    selectSuggestion(suggestion);
    inputRef.current?.focus();
  }, [selectSuggestion]);

  // Handle recent query click
  const handleRecentClick = useCallback((recentQuery: string) => {
    handleQueryChange(recentQuery);
    search(recentQuery);
    inputRef.current?.focus();
  }, [handleQueryChange, search]);

  const showResults = query.trim().length > 0;
  const showSuggestions = suggestions.length > 0 && results.length === 0 && !isLoading;
  const showRecentQueries = !query.trim() && recentQueries.length > 0;
  const showEmptyState = query.trim().length > 0 && results.length === 0 && !isLoading && !isStreaming;

  return (
    <div className="w-full">
      {/* Search Input */}
      <div className="relative">
        <div className="relative flex items-center">
          <Search className="absolute left-4 h-5 w-5 text-muted-foreground" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Search anything... (fault code, system, part, note, document)"
            className="w-full pl-12 pr-12 py-4 text-lg bg-card border border-border rounded-lg shadow-lg focus:outline-none focus:ring-2 focus:ring-ring transition-shadow"
            autoComplete="off"
            spellCheck={false}
          />

          {/* Loading/Streaming indicator */}
          {(isLoading || isStreaming) && (
            <div className="absolute right-12 top-1/2 -translate-y-1/2">
              <Loader2 className="h-5 w-5 text-primary animate-spin" />
            </div>
          )}

          {/* Clear button */}
          {query && (
            <button
              onClick={handleClear}
              className="absolute right-4 p-1 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted transition-colors"
              aria-label="Clear search"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Streaming progress bar */}
        {isStreaming && (
          <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-muted overflow-hidden rounded-b-lg">
            <div className="h-full bg-primary animate-pulse-progress" />
          </div>
        )}
      </div>

      {/* Error message */}
      {error && (
        <div className="mt-2 px-4 py-2 text-sm text-amber-600 bg-amber-50 dark:bg-amber-900/20 dark:text-amber-400 rounded-md">
          {error}
        </div>
      )}

      {/* Suggestions dropdown */}
      {showSuggestions && (
        <div className="mt-2 bg-card border border-border rounded-lg shadow-lg overflow-hidden">
          {suggestions.map((suggestion, index) => (
            <button
              key={`${suggestion.type}-${index}`}
              onClick={() => handleSuggestionClick(suggestion)}
              className="w-full px-4 py-2 text-left hover:bg-muted flex items-center gap-2 transition-colors"
            >
              {suggestion.type === 'recent' && (
                <Clock className="h-4 w-4 text-muted-foreground" />
              )}
              <span className="text-sm">{suggestion.text}</span>
            </button>
          ))}
        </div>
      )}

      {/* Recent queries (when input is empty) */}
      {showRecentQueries && (
        <div className="mt-4">
          <p className="text-xs text-muted-foreground mb-2 px-1">Recent searches</p>
          <div className="flex flex-wrap gap-2">
            {recentQueries.map((recentQuery, index) => (
              <button
                key={index}
                onClick={() => handleRecentClick(recentQuery)}
                className="px-3 py-1.5 text-sm bg-muted hover:bg-accent rounded-md transition-colors flex items-center gap-1.5"
              >
                <Clock className="h-3 w-3 text-muted-foreground" />
                {recentQuery}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Results Container - stable layout */}
      {showResults && (
        <div
          ref={resultsContainerRef}
          className="mt-4 space-y-2"
          style={{ minHeight: results.length > 0 ? `${Math.min(results.length, 5) * 80}px` : undefined }}
        >
          {results.length > 0 ? (
            results.map((result) => (
              <ResultCard
                key={result.id}
                result={result}
                // Prevent layout shift during streaming
                className="transition-opacity duration-150"
              />
            ))
          ) : showEmptyState ? (
            <div className="text-center py-12 text-muted-foreground">
              <p>No results found for &quot;{query}&quot;</p>
              <p className="text-sm mt-2">
                Try searching for equipment, fault codes, or documents
              </p>
            </div>
          ) : null}
        </div>
      )}

      {/* Empty State Helper - only when no query */}
      {!query && !showRecentQueries && (
        <div className="mt-12 text-center text-sm text-muted-foreground space-y-2">
          <p className="font-medium">Try searching for:</p>
          <div className="flex flex-wrap justify-center gap-2 mt-4">
            {['fault code E047', 'MTU manual', 'stabiliser leak'].map((example) => (
              <button
                key={example}
                onClick={() => handleRecentClick(example)}
                className="px-3 py-1 bg-muted rounded-md hover:bg-accent text-xs transition-colors"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
