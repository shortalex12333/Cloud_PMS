'use client';

/**
 * useFilteredEntityList — React Query hook that queries Supabase directly
 * with server-side filtering, sorting, and pagination.
 *
 * Replaces the old pattern of fetchFn → callCelesteApi → Python backend.
 * Filters are applied at the Supabase query level for efficiency.
 */

import { useInfiniteQuery } from '@tanstack/react-query';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/hooks/useAuth';
import type { ActiveFilters, DateRange } from '../types/filter-config';
import { isDateRange } from '../types/filter-config';
import type { EntityListResult, EntityAdapter } from '../types';

const PAGE_SIZE = 50;

interface UseFilteredEntityListOptions<T> {
  /** React Query key */
  queryKey: string[];
  /** Supabase table name */
  table: string;
  /** Columns to select */
  columns: string;
  /** Adapter to convert raw row to EntityListResult */
  adapter: EntityAdapter<T>;
  /** Active filters to apply */
  filters?: ActiveFilters;
  /** Sort column (default: created_at) */
  sortBy?: string;
  /** Sort direction (default: desc) */
  sortDir?: 'asc' | 'desc';
  /** Keys of filters that should use ilike (text search) instead of eq */
  textFields?: Set<string>;
}

export function useFilteredEntityList<T extends { id: string }>({
  queryKey,
  table,
  columns,
  adapter,
  filters = {},
  sortBy = 'created_at',
  sortDir = 'desc',
  textFields,
}: UseFilteredEntityListOptions<T>) {
  const { user, session } = useAuth();
  const yachtId = user?.yachtId;

  const filterKeys = Object.entries(filters)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
    .join('&');

  const query = useInfiniteQuery({
    queryKey: [...queryKey, yachtId, filterKeys, sortBy, sortDir],
    queryFn: async ({ pageParam = 0 }) => {
      if (!yachtId) throw new Error('Not authenticated');

      let q = supabase
        .from(table)
        .select(columns, { count: 'exact' });

      // Filter out test/seed data on tables that have the is_seed column
      // Enriched views (v_*) have is_seed built in, but filter here too for raw table queries
      const SEED_FILTERED_TABLES = [
        'pms_work_orders', 'pms_faults', 'pms_parts',
        'pms_receiving', 'pms_shopping_list_items', 'pms_purchase_orders',
        'pms_warranty_claims', 'doc_metadata',
      ];
      if (SEED_FILTERED_TABLES.includes(table)) {
        q = q.eq('is_seed', false);
      }

      // Apply filters
      for (const [key, value] of Object.entries(filters)) {
        if (value == null) continue;

        // Special computed filters (prefixed with _)
        if (key === '_stock_status') {
          if (value === 'out') {
            q = q.eq('quantity_on_hand', 0);
          } else if (value === 'low') {
            q = q.gt('quantity_on_hand', 0).not('minimum_quantity', 'is', null);
            // Can't express qty <= min in a single PostgREST filter, so we'll filter client-side
          } else if (value === 'in_stock') {
            q = q.gt('quantity_on_hand', 0);
          }
          continue;
        }

        if (isDateRange(value)) {
          const range = value as DateRange;
          if (range.from) q = q.gte(key, range.from);
          if (range.to) q = q.lte(key, range.to + 'T23:59:59');
          continue;
        }

        if (Array.isArray(value)) {
          q = q.in(key, value);
          continue;
        }

        if (typeof value === 'string') {
          // Text search: use ilike for fields marked as text in config, eq for selects
          if (textFields?.has(key)) {
            q = q.ilike(key, `%${value}%`);
          } else {
            q = q.eq(key, value);
          }
          continue;
        }
      }

      // Sort and paginate
      q = q.order(sortBy, { ascending: sortDir === 'asc' })
        .range(pageParam, pageParam + PAGE_SIZE - 1);

      const { data, error, count } = await q;
      if (error) throw new Error(error.message);

      let rows = (data ?? []) as unknown as T[];

      // Client-side filter for computed fields that can't be expressed in PostgREST
      if (filters._stock_status === 'low') {
        rows = rows.filter((r) => {
          const rec = r as unknown as Record<string, unknown>;
          const qty = (rec.quantity_on_hand as number) ?? 0;
          const min = (rec.minimum_quantity as number) ?? 0;
          return min > 0 && qty <= min && qty > 0;
        });
      }

      return {
        items: rows.map(adapter),
        rawItems: rows,
        total: count ?? 0,
        nextOffset: pageParam + PAGE_SIZE,
      };
    },
    getNextPageParam: (lastPage) => {
      if (lastPage.nextOffset >= lastPage.total) return undefined;
      return lastPage.nextOffset;
    },
    initialPageParam: 0,
    enabled: !!yachtId,
    staleTime: 30_000,
  });

  const items: EntityListResult[] = query.data?.pages.flatMap(p => p.items) ?? [];
  const rawItems: T[] = query.data?.pages.flatMap(p => p.rawItems) ?? [];
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
