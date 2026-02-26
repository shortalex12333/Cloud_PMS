import type { FetchParams, FetchResponse } from '@/features/entity-list/types';
import type { Equipment } from './types';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

export async function fetchEquipment(params: FetchParams): Promise<FetchResponse<Equipment>> {
  const { yachtId, token, offset, limit } = params;

  const url = new URL(`${BASE_URL}/v1/equipment`);
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
    throw new Error(`Failed to fetch equipment: ${response.status}`);
  }

  const json = await response.json();
  const items = json.equipment || json.items || json.data || [];
  const total = json.total ?? json.pagination?.total ?? items.length;

  return { data: items, total };
}

export async function fetchEquipmentItem(id: string, token: string): Promise<Equipment> {
  const response = await fetch(`${BASE_URL}/v1/entity/equipment/${id}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch equipment: ${response.status}`);
  }

  return response.json();
}
