'use client';

import { useState, useEffect, useRef } from 'react';
import { Search } from 'lucide-react';
import ResultCard from './ResultCard';
import { debounce } from '@/lib/utils';
import { celesteApi, CelesteApiError } from '@/lib/apiClient';
import type { SearchResponse, SearchResult } from '@/types';

export default function SearchBar() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus search bar on mount (Spotlight behavior)
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Debounced search function with API integration
  const performSearch = debounce(async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      setResults([]);
      setShowResults(false);
      return;
    }

    setLoading(true);
    setShowResults(true);

    console.log('[SearchBar] Initiating search:', {
      query: searchQuery,
      timestamp: new Date().toISOString(),
    });

    try {
      // Use authenticated API client
      const data = await celesteApi.post<SearchResponse>('search', {
        query: searchQuery,
      });

      console.log('[SearchBar] Search results received:', {
        resultCount: data.results?.length || 0,
        data,
      });

      setResults(data.results || []);
    } catch (error) {
      console.error('[SearchBar] Search error:', error);

      // Show user-friendly error for auth issues
      if (error instanceof CelesteApiError && error.status === 401) {
        console.error('[SearchBar] Authentication required');
        // AuthContext will handle redirect to login
        return;
      }

      console.log('[SearchBar] Falling back to mock data');

      // Fallback to mock results if API fails
      const mockResults: SearchResult[] = [
        {
          type: 'document_chunk',
          id: '1',
          title: 'CAT 3516 Cooling System Manual',
          subtitle: 'Page 34',
          preview:
            'The cooling system operates at optimal pressure between 10-15 PSI...',
          score: 0.92,
          actions: ['open_document', 'add_to_handover'],
        },
        {
          type: 'fault',
          id: '2',
          title: 'Fault E047 - Overheat Detected',
          subtitle: 'Port Generator',
          preview: 'Occurred 3 times in the past 30 days',
          score: 0.87,
          actions: ['create_work_order', 'view_history'],
        },
        {
          type: 'work_order',
          id: '3',
          title: 'Replace Coolant Temperature Sensor',
          subtitle: 'Completed 2024-01-15',
          preview: 'Replaced due to repeated E047 fault',
          score: 0.82,
          actions: ['view_history', 'add_to_handover'],
        },
      ];

      setResults(mockResults);
    } finally {
      setLoading(false);
    }
  }, 300);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    performSearch(value);
  };

  const handleClear = () => {
    setQuery('');
    setResults([]);
    setShowResults(false);
    inputRef.current?.focus();
  };

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
            placeholder="Search anything... (fault code, system, part, note, document)"
            className="w-full pl-12 pr-4 py-4 text-lg bg-card border border-border rounded-lg shadow-lg focus:outline-none focus:ring-2 focus:ring-ring"
          />
          {query && (
            <button
              onClick={handleClear}
              className="absolute right-4 text-sm text-muted-foreground hover:text-foreground"
            >
              Clear
            </button>
          )}
        </div>

        {/* Loading Indicator */}
        {loading && (
          <div className="absolute right-4 top-1/2 -translate-y-1/2">
            <div className="h-5 w-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        )}
      </div>

      {/* Results Container */}
      {showResults && (
        <div className="mt-4 space-y-2 animate-slide-in">
          {results.length > 0 ? (
            results.map((result) => (
              <ResultCard key={result.id} result={result} />
            ))
          ) : (
            !loading && (
              <div className="text-center py-12 text-muted-foreground">
                <p>No results found</p>
                <p className="text-sm mt-2">
                  Try searching for equipment, fault codes, or documents
                </p>
              </div>
            )
          )}
        </div>
      )}

      {/* Empty State Helper */}
      {!showResults && !query && (
        <div className="mt-12 text-center text-sm text-muted-foreground space-y-2">
          <p className="font-medium">Try searching for:</p>
          <div className="flex flex-wrap justify-center gap-2 mt-4">
            <button
              onClick={() => {
                setQuery('fault code E047');
                performSearch('fault code E047');
              }}
              className="px-3 py-1 bg-muted rounded-md hover:bg-accent text-xs"
            >
              fault code E047
            </button>
            <button
              onClick={() => {
                setQuery('MTU manual');
                performSearch('MTU manual');
              }}
              className="px-3 py-1 bg-muted rounded-md hover:bg-accent text-xs"
            >
              MTU manual
            </button>
            <button
              onClick={() => {
                setQuery('stabiliser leak');
                performSearch('stabiliser leak');
              }}
              className="px-3 py-1 bg-muted rounded-md hover:bg-accent text-xs"
            >
              stabiliser leak
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
