import type { FetchParams, FetchResponse } from '@/features/entity-list/types';
import type { ShoppingListItem } from './types';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

export async function fetchShoppingList(params: FetchParams): Promise<FetchResponse<ShoppingListItem>> {
  const { yachtId, token, offset, limit } = params;

  const url = new URL(`${BASE_URL}/v1/shopping-list`);
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
    throw new Error(`Failed to fetch shopping list: ${response.status}`);
  }

  const json = await response.json();
  const items = json.shopping_list || json.items || json.data || [];
  const total = json.total ?? json.pagination?.total ?? items.length;

  return { data: items, total };
}

export async function fetchShoppingListItem(id: string, token: string): Promise<ShoppingListItem> {
  const response = await fetch(`${BASE_URL}/v1/entity/shopping_list/${id}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch shopping list item: ${response.status}`);
  }

  return response.json();
}
