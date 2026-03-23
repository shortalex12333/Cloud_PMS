import { supabase } from '@/lib/supabaseClient';
import type { FetchParams, FetchResponse } from '@/features/entity-list/types';
import type { ShoppingListItem, ShoppingListStateHistory } from './types';

export async function fetchShoppingList(params: FetchParams): Promise<FetchResponse<ShoppingListItem>> {
  const { offset, limit } = params;

  const { data, count, error } = await supabase
    .from('pms_shopping_list_items')
    .select(
      'id, part_name, part_number, manufacturer, status, urgency, quantity_requested, quantity_approved, unit, part_id, source_type, source_work_order_id, source_receiving_id, source_notes, requested_by, required_by_date, created_at, updated_at',
      { count: 'exact' },
    )
    .order('created_at', { ascending: false })
    .range(offset, offset + limit - 1);

  if (error) {
    throw new Error(`Failed to fetch shopping list: ${error.message}`);
  }

  return { data: (data ?? []) as ShoppingListItem[], total: count ?? 0 };
}

export async function fetchShoppingListItem(id: string, _token: string): Promise<ShoppingListItem> {
  const { data, error } = await supabase
    .from('pms_shopping_list_items')
    .select(
      'id, part_name, part_number, manufacturer, status, urgency, quantity_requested, quantity_approved, unit, part_id, source_type, source_work_order_id, source_receiving_id, source_notes, requested_by, required_by_date, created_at, updated_at',
    )
    .eq('id', id)
    .single();

  if (error || !data) {
    throw new Error(`Shopping list item ${id} not found`);
  }

  return data as ShoppingListItem;
}

export async function fetchShoppingListHistory(
  itemId: string,
  _token: string,
): Promise<ShoppingListStateHistory[]> {
  const { data, error } = await supabase
    .from('pms_shopping_list_state_history')
    .select(
      'id, shopping_list_item_id, previous_state, new_state, transition_reason, transition_notes, changed_by, changed_by_name, changed_at, related_order_id, related_receiving_event_id',
    )
    .eq('shopping_list_item_id', itemId)
    .order('changed_at', { ascending: false });

  if (error) {
    // Return empty array if history table not available
    return [];
  }

  return (data ?? []) as ShoppingListStateHistory[];
}
