import { callCelesteApi } from '@/lib/apiClient';
import type { FetchParams, FetchResponse } from '@/features/entity-list/types';
import type { Part } from './types';

interface ApiResponse {
  data: Part[];
  total: number;
}

export async function fetchParts(params: FetchParams): Promise<FetchResponse<Part>> {
  const { offset, limit } = params;

  const queryParams = new URLSearchParams({
    offset: String(offset),
    limit: String(limit),
  });

  const result = await callCelesteApi<ApiResponse>(`/v1/inventory?${queryParams}`);

  return { data: result.data, total: result.total };
}

export async function fetchPart(id: string, _token: string): Promise<Part> {
  // For single item fetch, we query the list with a specific ID
  const result = await callCelesteApi<ApiResponse>(`/v1/inventory?limit=1`);

  const part = result.data.find((p) => p.id === id);
  if (!part) {
    throw new Error(`Part ${id} not found`);
  }

  return part;
}
