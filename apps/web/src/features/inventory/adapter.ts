import type { EntityListResult } from '@/features/entity-list/types';
import type { Part } from './types';

function partStatusVariant(qty: number, min?: number | null): string {
  if (qty === 0) return 'critical';
  if (min && qty <= min) return 'warning';
  return 'open';
}

function partSeverity(qty: number, min?: number | null): string | null {
  if (qty === 0) return 'critical';
  if (min && qty <= min) return 'warning';
  return null;
}

export function partToListResult(part: Part): EntityListResult {
  const qty = part.quantity_on_hand ?? 0;
  const min = part.minimum_quantity;
  const stockLabel = qty === 0 ? 'Zero Stock' : (min && qty <= min) ? 'Low Stock' : 'In Stock';

  return {
    id: part.id,
    type: 'pms_parts',
    title: part.name || `Part ${part.part_number}`,
    subtitle: `${part.part_number} \u00b7 ${stockLabel} \u00b7 Qty: ${qty}${part.unit_of_measure ? ` ${part.unit_of_measure}` : ''}`,
    snippet: part.description,
    metadata: {
      part_number: part.part_number,
      quantity_on_hand: qty,
      minimum_quantity: min,
      category: part.category,
      location: part.location,
      created_at: part.created_at,
    },

    // Extended fields for EntityRecordRow
    entityRef: part.part_number || part.id.slice(0, 8),
    equipmentName: undefined,
    assignedTo: undefined,
    status: stockLabel,
    statusVariant: partStatusVariant(qty, min),
    severity: partSeverity(qty, min),
    age: '\u2014',
  };
}
