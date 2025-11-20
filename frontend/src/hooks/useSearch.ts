/**
 * CelesteOS Search Hook
 *
 * Provides search functionality with streaming support.
 */

import { useState, useCallback } from 'react';
import { api } from '../lib/api';
import {
  SearchRequest,
  SearchResponse,
  SearchResultCard,
  MicroAction,
} from '../types';

interface SearchState {
  query: string;
  results: SearchResultCard[];
  actions: MicroAction[];
  loading: boolean;
  streaming: boolean;
  error: string | null;
}

export function useSearch() {
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
   */
  const search = useCallback(async (request: SearchRequest) => {
    setState(prev => ({
      ...prev,
      query: request.query,
      loading: true,
      error: null,
    }));

    try {
      const response = await api.search.search(request);

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
  }, []);

  /**
   * Perform streaming search
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
      const stream = api.search.streamSearch(request);

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
  }, []);

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
