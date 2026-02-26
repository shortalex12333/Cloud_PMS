import { callCelesteApi } from '@/lib/apiClient';
import type { FetchParams, FetchResponse } from '@/features/entity-list/types';
import type { Fault } from './types';

interface ApiResponse {
  data: Fault[];
  total: number;
}

export async function fetchFaults(params: FetchParams): Promise<FetchResponse<Fault>> {
  const { offset, limit } = params;

  const queryParams = new URLSearchParams({
    offset: String(offset),
    limit: String(limit),
  });

  const result = await callCelesteApi<ApiResponse>(`/v1/faults?${queryParams}`);

  return { data: result.data, total: result.total };
}

export async function fetchFault(id: string, _token: string): Promise<Fault> {
  // For single item fetch, we query the list with a specific ID
  const result = await callCelesteApi<ApiResponse>(`/v1/faults?limit=1`);

  const fault = result.data.find((f) => f.id === id);
  if (!fault) {
    throw new Error(`Fault ${id} not found`);
  }

  return fault;
}
