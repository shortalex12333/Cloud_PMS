'use client';

import { useInfiniteQuery } from '@tanstack/react-query';
import { useAuth } from '@/hooks/useAuth';
import type { FetchParams, FetchResponse, EntityAdapter, EntityListResult } from '../types';

const PAGE_SIZE = 50;

interface UseEntityListOptions<T> {
  queryKey: string[];
  fetchFn: (params: FetchParams) => Promise<FetchResponse<T>>;
  adapter: EntityAdapter<T>;
}

export function useEntityList<T extends { id: string }>({
  queryKey,
  fetchFn,
  adapter,
}: UseEntityListOptions<T>) {
  const { user, session } = useAuth();
  const token = session?.access_token;
  const yachtId = user?.yachtId;

  const query = useInfiniteQuery({
    queryKey: [...queryKey, yachtId],
    queryFn: async ({ pageParam = 0 }) => {
      if (!yachtId || !token) {
        throw new Error('Not authenticated');
      }

      const response = await fetchFn({
        yachtId,
        token,
        offset: pageParam,
        limit: PAGE_SIZE,
      });

      return {
        items: response.data.map(adapter),
        rawItems: response.data, // Keep raw items for filtering
        total: response.total,
        nextOffset: pageParam + PAGE_SIZE,
      };
    },
    getNextPageParam: (lastPage) => {
      if (lastPage.nextOffset >= lastPage.total) {
        return undefined;
      }
      return lastPage.nextOffset;
    },
    initialPageParam: 0,
    enabled: !!yachtId && !!token,
    staleTime: 30000,
  });

  // Flatten all pages into single array
  const items: EntityListResult[] = query.data?.pages.flatMap((page) => page.items) ?? [];
  const rawItems: T[] = query.data?.pages.flatMap((page) => page.rawItems) ?? [];
  const total = query.data?.pages[0]?.total ?? 0;

  return {
    items,
    rawItems,
    total,
    isLoading: query.isLoading,
    isFetchingNextPage: query.isFetchingNextPage,
    hasNextPage: query.hasNextPage,
    fetchNextPage: query.fetchNextPage,
    error: query.error,
    refetch: query.refetch,
  };
}
