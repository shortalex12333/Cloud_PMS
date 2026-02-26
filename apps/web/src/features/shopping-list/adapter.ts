import type { EntityListResult } from '@/features/entity-list/types';
import type { ShoppingListItem } from './types';

export function shoppingListToListResult(item: ShoppingListItem): EntityListResult {
  const statusDisplay = item.status?.replace(/_/g, ' ') || 'Pending';
  const priorityDisplay = item.priority || '';

  return {
    id: item.id,
    type: 'pms_shopping_list',
    title: item.part_name || `Item ${item.part_number || item.id.slice(0, 8)}`,
    subtitle: `${statusDisplay} · Qty: ${item.quantity_requested}${item.unit_of_measure ? ` ${item.unit_of_measure}` : ''}${priorityDisplay ? ` · ${priorityDisplay}` : ''}`,
    snippet: item.description || item.notes,
    metadata: {
      status: item.status,
      priority: item.priority,
      part_number: item.part_number,
      quantity_requested: item.quantity_requested,
      requested_by_name: item.requested_by_name,
      created_at: item.created_at,
    },
  };
}
