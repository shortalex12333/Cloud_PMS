/**
 * useActionQuery - React Query wrapper for CelesteOS actions
 *
 * Combines React Query's caching/refetching capabilities with
 * the existing useActionHandler infrastructure.
 *
 * Usage:
 * ```tsx
 * const { data, isLoading, error, refetch } = useActionQuery(
 *   'view_faults_list',
 *   { parameters: { filters, pagination } }
 * );
 * ```
 */

import { useQuery, useMutation, useQueryClient, type UseQueryOptions } from '@tanstack/react-query';
import { useActionHandler } from './useActionHandler';
import { useCallback } from 'react';
import type { MicroAction } from '@/types/actions';

/**
 * Action response type (matches backend contract)
 */
export type ActionResponse<T = any> = {
  success: boolean;
  card_type?: string;
  card?: T;
  micro_actions?: MicroAction[];
  pagination?: {
    total: number;
    page: number;
    limit: number;
  };
  error?: {
    code: string;
    message: string;
  };
};

/**
 * Hook for querying data via actions (READ operations)
 *
 * @param actionName - The micro-action to execute (e.g., 'view_faults_list')
 * @param actionContext - Context and parameters for the action
 * @param options - React Query options (staleTime, enabled, etc.)
 */
export function useActionQuery<TData = any>(
  actionName: string,
  actionContext?: {
    context?: Record<string, any>;
    parameters?: Record<string, any>;
  },
  options?: Omit<UseQueryOptions<ActionResponse<TData>>, 'queryKey' | 'queryFn'>
) {
  const { executeReadAction } = useActionHandler();

  // Build query key from action name + parameters
  const queryKey = [actionName, actionContext?.parameters || {}];

  return useQuery<ActionResponse<TData>>({
    queryKey,
    queryFn: async () => {
      const response = await executeReadAction(actionName as any, {
        ...actionContext?.context,
        ...actionContext,
      });

      if (!response || !response.success) {
        throw new Error(
          response?.error?.message || `Failed to execute action: ${actionName}`
        );
      }

      return response as ActionResponse<TData>;
    },
    ...options,
  });
}

/**
 * Hook for mutations via actions (CREATE/UPDATE/DELETE operations)
 *
 * @param actionName - The micro-action to execute
 *
 * @example
 * ```tsx
 * const { mutate, isPending } = useActionMutation('create_work_order', {
 *   onSuccess: () => {
 *     queryClient.invalidateQueries({ queryKey: ['view_work_orders_list'] });
 *   }
 * });
 *
 * mutate({
 *   context: { fault_id: '123' },
 *   parameters: { title: 'Fix engine', priority: 'high' }
 * });
 * ```
 */
export function useActionMutation<TData = any, TVariables = any>(
  actionName: string,
  options?: {
    onSuccess?: (data: ActionResponse<TData>) => void;
    onError?: (error: Error) => void;
  }
) {
  const { executeMutationAction } = useActionHandler();

  return useMutation<ActionResponse<TData>, Error, TVariables>({
    mutationFn: async (variables: any) => {
      const response = await executeMutationAction(actionName as any, variables);

      if (!response || !response.success) {
        throw new Error(
          response?.error?.message || `Failed to execute action: ${actionName}`
        );
      }

      return response as ActionResponse<TData>;
    },
    onSuccess: options?.onSuccess,
    onError: options?.onError,
  });
}

/**
 * Hook for list views with filtering, sorting, and pagination
 *
 * Specialized hook for Phase 3 filtered list views.
 * Automatically handles queryParams from useFilters.
 *
 * @example
 * ```tsx
 * const { filters, queryParams } = useFilters();
 * const { data, isLoading, refetch } = useListQuery(
 *   'view_faults_list',
 *   queryParams
 * );
 * ```
 */
export function useListQuery<TItem = any>(
  actionName: string,
  queryParams: Record<string, any>,
  options?: Omit<UseQueryOptions<ActionResponse<{ rows: TItem[] }>>, 'queryKey' | 'queryFn'>
) {
  return useActionQuery<{ rows: TItem[] }>(
    actionName,
    { parameters: queryParams },
    options
  );
}

/**
 * Hook to invalidate action queries
 *
 * Useful after mutations to trigger refetch of related queries.
 *
 * @example
 * ```tsx
 * const invalidate = useInvalidateAction();
 *
 * // After creating a work order
 * await createMutation.mutateAsync(data);
 * invalidate('view_work_orders_list');
 * ```
 */
export function useInvalidateAction() {
  const queryClient = useQueryClient();

  return useCallback(
    (actionName: string, parameters?: Record<string, any>) => {
      if (parameters) {
        // Invalidate specific query with parameters
        queryClient.invalidateQueries({ queryKey: [actionName, parameters] });
      } else {
        // Invalidate all queries for this action
        queryClient.invalidateQueries({ queryKey: [actionName] });
      }
    },
    [queryClient]
  );
}
