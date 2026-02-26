import type { EntityListResult } from '@/features/entity-list/types';
import type { Part } from './types';

export function partToListResult(part: Part): EntityListResult {
  const stockStatus = part.minimum_quantity && part.quantity_on_hand <= part.minimum_quantity
    ? 'Low Stock'
    : 'In Stock';

  return {
    id: part.id,
    type: 'pms_parts',
    title: part.name || `Part ${part.part_number}`,
    subtitle: `${part.part_number} · ${stockStatus} · Qty: ${part.quantity_on_hand}${part.unit_of_measure ? ` ${part.unit_of_measure}` : ''}`,
    snippet: part.description,
    metadata: {
      part_number: part.part_number,
      quantity_on_hand: part.quantity_on_hand,
      minimum_quantity: part.minimum_quantity,
      category: part.category,
      location: part.location,
      created_at: part.created_at,
    },
  };
}
