import type { FetchParams, FetchResponse } from '@/features/entity-list/types';
import type { ReceivingItem } from './types';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

export async function fetchReceivingItems(params: FetchParams): Promise<FetchResponse<ReceivingItem>> {
  const { yachtId, token, offset, limit } = params;

  const url = new URL(`${BASE_URL}/v1/receiving`);
  url.searchParams.set('yacht_id', yachtId);
  url.searchParams.set('offset', String(offset));
  url.searchParams.set('limit', String(limit));

  const response = await fetch(url.toString(), {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch receiving items: ${response.status}`);
  }

  const json = await response.json();
  const items = json.receiving || json.items || json.data || [];
  const total = json.total ?? json.pagination?.total ?? items.length;

  return { data: items, total };
}

export async function fetchReceivingItem(id: string, token: string): Promise<ReceivingItem> {
  const response = await fetch(`${BASE_URL}/v1/entity/receiving/${id}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch receiving item: ${response.status}`);
  }

  return response.json();
}
