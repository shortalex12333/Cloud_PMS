/**
 * useListViews - Specialized React Query hooks for Phase 3 list views
 *
 * Provides typed hooks for faults, parts, and work orders list views
 * with automatic caching, refetching, and state management.
 */

import { useListQuery, useInvalidateAction } from './useActionQuery';
import type { UseQueryOptions } from '@tanstack/react-query';

/**
 * Type definitions for list items
 */
export type Fault = {
  id: string;
  yacht_id: string;
  equipment_id?: string;
  title: string;
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  status: 'open' | 'in_progress' | 'resolved' | 'closed';
  location?: {
    deck?: string;
    room?: string;
  };
  reported_by: string;
  created_at: string;
  resolved_at?: string;
};

export type Part = {
  id: string;
  yacht_id: string;
  part_number: string;
  part_name: string;
  description?: string;
  category: string;
  manufacturer?: string;
  supplier?: string;
  quantity_on_hand: number;
  quantity_minimum: number;
  quantity_on_order?: number;
  unit_price?: number;
  location?: {
    deck?: string;
    room?: string;
    storage?: string;
  };
  last_ordered_at?: string;
  created_at: string;
};

export type WorkOrder = {
  id: string;
  yacht_id: string;
  fault_id?: string;
  equipment_id?: string;
  title: string;
  description: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
  assigned_to?: string;
  created_by: string;
  estimated_hours?: number;
  actual_hours?: number;
  parts_required?: string[];
  created_at: string;
  completed_at?: string;
  due_date?: string;
};

/**
 * List response type
 */
type ListResponse<T> = {
  rows: T[];
  total?: number;
  page?: number;
  limit?: number;
};

/**
 * Hook for fetching faults list with filters
 *
 * @param queryParams - Filters, sorting, and pagination from useFilters
 * @param options - React Query options
 *
 * @example
 * ```tsx
 * const { filters, queryParams } = useFilters();
 * const { data, isLoading } = useFaultsList(queryParams);
 * const faults = data?.card?.rows || [];
 * ```
 */
export function useFaultsList(
  queryParams: Record<string, any>,
  options?: Omit<UseQueryOptions<any>, 'queryKey' | 'queryFn'>
) {
  return useListQuery<Fault>('view_faults_list', queryParams, options);
}

/**
 * Hook for fetching parts inventory with filters
 *
 * @param queryParams - Filters, sorting, and pagination from useFilters
 * @param options - React Query options
 *
 * @example
 * ```tsx
 * const { filters, queryParams } = useFilters();
 * const { data, isLoading } = usePartsList(queryParams);
 * const parts = data?.card?.rows || [];
 * ```
 */
export function usePartsList(
  queryParams: Record<string, any>,
  options?: Omit<UseQueryOptions<any>, 'queryKey' | 'queryFn'>
) {
  return useListQuery<Part>('view_parts_inventory', queryParams, options);
}

/**
 * Hook for fetching work orders list with filters
 *
 * @param queryParams - Filters, sorting, and pagination from useFilters
 * @param options - React Query options
 *
 * @example
 * ```tsx
 * const { filters, queryParams } = useFilters();
 * const { data, isLoading } = useWorkOrdersList(queryParams);
 * const workOrders = data?.card?.rows || [];
 * ```
 */
export function useWorkOrdersList(
  queryParams: Record<string, any>,
  options?: Omit<UseQueryOptions<any>, 'queryKey' | 'queryFn'>
) {
  return useListQuery<WorkOrder>('view_work_orders_list', queryParams, options);
}

/**
 * Re-export invalidation hook for convenience
 */
export { useInvalidateAction };
