/**
 * useFilters Hook
 *
 * Generic filter state management for list views
 * Handles URL query params, filter application, and pagination reset
 * Builds unified query format for master-view-workflow
 */

import { useState, useCallback, useMemo, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import type { LocationFilterValue } from '@/components/filters/LocationFilter';
import type { TimeRangeValue } from '@/components/filters/TimeRangeFilter';
import type { QuantityFilterValue } from '@/components/filters/QuantityFilter';

export interface FilterState {
  location?: LocationFilterValue;
  status?: string[];
  timeRange?: TimeRangeValue;
  quantity?: QuantityFilterValue;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  page: number;
  limit: number;
}

export interface QueryParams {
  filters: {
    location?: LocationFilterValue;
    status?: string[];
    time_range?: TimeRangeValue;
    quantity?: QuantityFilterValue;
  };
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  limit: number;
  offset: number;
}

interface UseFiltersOptions {
  defaultLimit?: number;
  defaultSortBy?: string;
  defaultSortOrder?: 'asc' | 'desc';
  syncWithUrl?: boolean;
}

export function useFilters({
  defaultLimit = 50,
  defaultSortBy = 'created_at',
  defaultSortOrder = 'desc',
  syncWithUrl = true,
}: UseFiltersOptions = {}) {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Initialize state from URL or defaults
  const [filters, setFilters] = useState<FilterState>(() => {
    if (!syncWithUrl) {
      return {
        page: 1,
        limit: defaultLimit,
        sortBy: defaultSortBy,
        sortOrder: defaultSortOrder,
      };
    }

    // Parse URL params
    return {
      location: searchParams.get('location')
        ? JSON.parse(searchParams.get('location')!)
        : undefined,
      status: searchParams.get('status')
        ? searchParams.get('status')!.split(',')
        : undefined,
      timeRange: searchParams.get('timeRange')
        ? JSON.parse(searchParams.get('timeRange')!)
        : undefined,
      quantity: searchParams.get('quantity')
        ? JSON.parse(searchParams.get('quantity')!)
        : undefined,
      sortBy: searchParams.get('sortBy') || defaultSortBy,
      sortOrder: (searchParams.get('sortOrder') as 'asc' | 'desc') || defaultSortOrder,
      page: parseInt(searchParams.get('page') || '1', 10),
      limit: parseInt(searchParams.get('limit') || String(defaultLimit), 10),
    };
  });

  // Sync filters to URL
  useEffect(() => {
    if (!syncWithUrl) return;

    const params = new URLSearchParams();

    if (filters.location) {
      params.set('location', JSON.stringify(filters.location));
    }
    if (filters.status && filters.status.length > 0) {
      params.set('status', filters.status.join(','));
    }
    if (filters.timeRange) {
      params.set('timeRange', JSON.stringify(filters.timeRange));
    }
    if (filters.quantity) {
      params.set('quantity', JSON.stringify(filters.quantity));
    }
    if (filters.sortBy) {
      params.set('sortBy', filters.sortBy);
    }
    if (filters.sortOrder) {
      params.set('sortOrder', filters.sortOrder);
    }
    params.set('page', String(filters.page));
    params.set('limit', String(filters.limit));

    router.push(`?${params.toString()}`, { scroll: false });
  }, [filters, router, syncWithUrl]);

  /**
   * Apply a specific filter (resets to page 1)
   */
  const applyFilter = useCallback((filterName: keyof FilterState, value: any) => {
    setFilters((prev) => ({
      ...prev,
      [filterName]: value,
      page: 1, // Reset to page 1 when filters change
    }));
  }, []);

  /**
   * Clear a specific filter
   */
  const clearFilter = useCallback((filterName: keyof FilterState) => {
    setFilters((prev) => {
      const newFilters = { ...prev };
      delete newFilters[filterName];
      return {
        ...newFilters,
        page: 1, // Reset to page 1
      };
    });
  }, []);

  /**
   * Clear all filters (keeps pagination settings)
   */
  const clearAllFilters = useCallback(() => {
    setFilters({
      page: 1,
      limit: filters.limit,
      sortBy: defaultSortBy,
      sortOrder: defaultSortOrder,
    });
  }, [filters.limit, defaultSortBy, defaultSortOrder]);

  /**
   * Set page number
   */
  const setPage = useCallback((page: number) => {
    setFilters((prev) => ({ ...prev, page }));
  }, []);

  /**
   * Set sort
   */
  const setSort = useCallback((sortBy: string, sortOrder: 'asc' | 'desc') => {
    setFilters((prev) => ({
      ...prev,
      sortBy,
      sortOrder,
      page: 1, // Reset to page 1 when sort changes
    }));
  }, []);

  /**
   * Set items per page
   */
  const setLimit = useCallback((limit: number) => {
    setFilters((prev) => ({
      ...prev,
      limit,
      page: 1, // Reset to page 1 when limit changes
    }));
  }, []);

  /**
   * Build unified query params for master-view-workflow
   * Matches the expected format: { filters, sort_by, sort_order, limit, offset }
   */
  const queryParams = useMemo<QueryParams>(() => {
    const offset = (filters.page - 1) * filters.limit;

    return {
      filters: {
        location: filters.location,
        status: filters.status,
        time_range: filters.timeRange,
        quantity: filters.quantity,
      },
      sort_by: filters.sortBy,
      sort_order: filters.sortOrder,
      limit: filters.limit,
      offset,
    };
  }, [filters]);

  /**
   * Check if any filters are active
   */
  const hasActiveFilters = useMemo(() => {
    return !!(
      filters.location ||
      (filters.status && filters.status.length > 0) ||
      filters.timeRange ||
      filters.quantity
    );
  }, [filters]);

  /**
   * Get active filter count
   */
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters.location) count++;
    if (filters.status && filters.status.length > 0) count++;
    if (filters.timeRange) count++;
    if (filters.quantity) count++;
    return count;
  }, [filters]);

  return {
    // State
    filters,
    queryParams,
    hasActiveFilters,
    activeFilterCount,

    // Filter actions
    applyFilter,
    clearFilter,
    clearAllFilters,

    // Pagination actions
    setPage,
    setLimit,

    // Sort actions
    setSort,
  };
}

/**
 * Type helper for filter names
 */
export type FilterName = keyof Pick<FilterState, 'location' | 'status' | 'timeRange' | 'quantity'>;

/**
 * Type helper for sort fields
 */
export interface SortField {
  value: string;
  label: string;
}
