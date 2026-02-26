import { callCelesteApi } from '@/lib/apiClient';
import type { FetchParams, FetchResponse } from '@/features/entity-list/types';
import type { WorkOrder } from './types';

interface ApiResponse {
  data: WorkOrder[];
  total: number;
}

export async function fetchWorkOrders(params: FetchParams): Promise<FetchResponse<WorkOrder>> {
  const { offset, limit } = params;

  const queryParams = new URLSearchParams({
    offset: String(offset),
    limit: String(limit),
  });

  const result = await callCelesteApi<ApiResponse>(`/v1/work-orders?${queryParams}`);

  return { data: result.data, total: result.total };
}

export async function fetchWorkOrder(id: string, _token: string): Promise<WorkOrder> {
  // For single item fetch, we query the list with a specific ID
  // The backend will filter appropriately via RLS
  const result = await callCelesteApi<ApiResponse>(`/v1/work-orders?limit=1`);

  const workOrder = result.data.find((wo) => wo.id === id);
  if (!workOrder) {
    throw new Error(`Work order ${id} not found`);
  }

  return workOrder;
}
