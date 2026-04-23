import type { EntityListResult } from '@/features/entity-list/types';
import type { ShoppingListItem } from './types';

function formatAge(dateStr?: string): string {
  if (!dateStr) return '—';
  const diffDays = Math.floor((Date.now() - new Date(dateStr).getTime()) / 86_400_000);
  if (diffDays < 1) return '<1d';
  if (diffDays < 7) return `${diffDays}d`;
  const d = new Date(dateStr);
  return `${d.getDate()} ${d.toLocaleDateString('en-GB', { month: 'short' })}`;
}

function slStatusVariant(status?: string): string {
  const s = status?.toLowerCase();
  if (s === 'approved' || s === 'fulfilled' || s === 'installed') return 'signed';
  if (s === 'ordered' || s === 'partially_fulfilled' || s === 'under_review') return 'in_progress';
  if (s === 'rejected') return 'cancelled';
  return 'pending';
}

function fmt(str?: string): string {
  if (!str) return '';
  return str.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export function shoppingListToListResult(item: ShoppingListItem): EntityListResult {
  const statusDisplay = fmt(item.status) || 'Pending';
  const urgency = item.urgency;
  const qty = item.quantity_requested;
  const unit = item.unit || '';
  const qtyDisplay = qty != null ? `Qty ${qty}${unit ? ` ${unit}` : ''}` : '';
  const candidateTag = item.is_candidate_part ? 'Candidate' : '';

  const subtitleBits = [statusDisplay, qtyDisplay, urgency ? fmt(urgency) : '', candidateTag]
    .filter(Boolean);

  return {
    id: item.id,
    type: 'pms_shopping_list',
    title: item.part_name || 'Shopping List Item',
    subtitle: subtitleBits.join(' · '),
    snippet: item.source_notes,
    metadata: {
      status: item.status,
      urgency,
      source_type: item.source_type,
      part_number: item.part_number,
      quantity_requested: qty,
      requested_by_name: item.requested_by_name,
      required_by_date: item.required_by_date,
      is_candidate_part: item.is_candidate_part,
      created_at: item.created_at,
    },

    // Extended fields for EntityRecordRow
    entityRef: item.part_number || '',
    assignedTo: item.requested_by_name || undefined,
    status: statusDisplay,
    statusVariant: slStatusVariant(item.status),
    severity: null,
    age: formatAge(item.created_at),
  };
}
