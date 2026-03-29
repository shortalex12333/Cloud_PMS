import type { EntityListResult } from '@/features/entity-list/types';
import type { ShoppingListItem } from './types';

function formatAge(dateStr?: string): string {
  if (!dateStr) return '\u2014';
  const diffDays = Math.floor((Date.now() - new Date(dateStr).getTime()) / 86_400_000);
  if (diffDays < 1) return '<1d';
  if (diffDays < 7) return `${diffDays}d`;
  const d = new Date(dateStr);
  return `${d.getDate()} ${d.toLocaleDateString('en-GB', { month: 'short' })}`;
}

function slStatusVariant(status?: string): string {
  const s = status?.toLowerCase();
  if (s === 'approved') return 'signed';
  if (s === 'ordered') return 'in_progress';
  if (s === 'cancelled') return 'cancelled';
  return 'pending';
}

export function shoppingListToListResult(item: ShoppingListItem): EntityListResult {
  const statusDisplay = item.status?.replace(/_/g, ' ') || 'Pending';
  const priorityDisplay = item.priority || '';

  return {
    id: item.id,
    type: 'pms_shopping_list',
    title: item.part_name || `Item ${item.part_number || item.id.slice(0, 8)}`,
    subtitle: `${statusDisplay} \u00b7 Qty: ${item.quantity_requested}${item.unit_of_measure ? ` ${item.unit_of_measure}` : ''}${priorityDisplay ? ` \u00b7 ${priorityDisplay}` : ''}`,
    snippet: item.description || item.notes,
    metadata: {
      status: item.status,
      priority: item.priority,
      part_number: item.part_number,
      quantity_requested: item.quantity_requested,
      requested_by_name: item.requested_by_name,
      created_at: item.created_at,
    },

    // Extended fields for EntityRecordRow
    entityRef: item.part_number || item.id.slice(0, 8),
    assignedTo: item.requested_by_name || undefined,
    status: statusDisplay,
    statusVariant: slStatusVariant(item.status),
    severity: null,
    age: formatAge(item.created_at),
  };
}
