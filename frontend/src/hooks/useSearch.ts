/**
 * CelesteOS Search Hook
 *
 * Provides search functionality with streaming support.
 * Automatically includes JWT token and yacht_id from auth context.
 */

import { useState, useCallback } from 'react';
import { api } from '../lib/api';
import { useAuth } from './useAuth';
import type { SearchRequest } from '@/types';
import type {
  SearchResponse,
  SearchResult,
  MicroAction,
} from '@/types/search';

interface SearchState {
  query: string;
  results: SearchResult[];
  actions: Array<{
    label: string;
    action: MicroAction;
    context?: Record<string, any>;
  }>;
  loading: boolean;
  streaming: boolean;
  error: string | null;
}

export function useSearch() {
  const { user } = useAuth();
  const [state, setState] = useState<SearchState>({
    query: '',
    results: [],
    actions: [],
    loading: false,
    streaming: false,
    error: null,
  });

  /**
   * Perform search (non-streaming)
   * JWT token is auto-included via api.ts, yacht_id passed from user context
   */
  const search = useCallback(async (request: SearchRequest) => {
    setState(prev => ({
      ...prev,
      query: request.query,
      loading: true,
      error: null,
    }));

    try {
      // Pass yacht_id from authenticated user
      const response = await api.search.search(
        request.query,
        request.filters,
        user?.yachtId
      );

      setState({
        query: request.query,
        results: response.results,
        actions: response.actions,
        loading: false,
        streaming: false,
        error: null,
      });

      return response;
    } catch (error) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Search failed',
      }));
      throw error;
    }
  }, [user?.yachtId]);

  /**
   * Perform streaming search
   * JWT token is auto-included via api.ts, yacht_id passed from user context
   */
  const searchStream = useCallback(async (request: SearchRequest) => {
    setState(prev => ({
      ...prev,
      query: request.query,
      results: [],
      actions: [],
      streaming: true,
      loading: true,
      error: null,
    }));

    try {
      // Pass yacht_id from authenticated user
      const stream = api.search.searchStream(request.query, user?.yachtId) as any;

      for await (const event of stream) {
        if (event.type === 'data' && event.data) {
          setState(prev => ({
            ...prev,
            results: event.data!.results,
            actions: event.data!.actions,
            loading: false,
          }));
        } else if (event.type === 'complete') {
          setState(prev => ({
            ...prev,
            streaming: false,
            loading: false,
          }));
        } else if (event.type === 'error') {
          setState(prev => ({
            ...prev,
            streaming: false,
            loading: false,
            error: event.error || 'Stream error',
          }));
        }
      }
    } catch (error) {
      setState(prev => ({
        ...prev,
        streaming: false,
        loading: false,
        error: error instanceof Error ? error.message : 'Search stream failed',
      }));
      throw error;
    }
  }, [user?.yachtId]);

  /**
   * Clear search results
   */
  const clear = useCallback(() => {
    setState({
      query: '',
      results: [],
      actions: [],
      loading: false,
      streaming: false,
      error: null,
    });
  }, []);

  return {
    ...state,
    search,
    searchStream,
    clear,
  };
}
