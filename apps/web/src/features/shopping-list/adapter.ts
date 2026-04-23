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

/**
 * Adapter input is a superset of ShoppingListItem — the backend
 * (vessel_surface_routes._format_record shopping_list branch) emits two extra
 * keys on every row:
 *   - ref   — never empty (part_number || SL-<id6>); guarantees every row
 *             takes the rich EntityRecordRow template via entityRef
 *             (FilteredEntityList.tsx:260-289 switches on entityRef truthiness).
 *   - part_name — real DB value; without this the adapter's
 *             `item.part_name || 'Shopping List Item'` fallback collapsed
 *             to the literal, hiding the real item name.
 */
type AdapterInput = ShoppingListItem & {
  ref?: string;
  part_name?: string;
  requested_by_name?: string;
};

export function shoppingListToListResult(item: AdapterInput): EntityListResult {
  const qty = item.quantity_requested;
  const unit = item.unit || '';
  const qtyDisplay = qty != null ? `Qty ${qty}${unit ? ` ${unit}` : ''}` : '';

  // Subtitle is line 2 under the title. Pill already shows status and the
  // age column already shows the date — don't duplicate. Show: qty, urgency
  // (only when non-default), candidate flag.
  const urgencyLabel = item.urgency && item.urgency !== 'normal' ? fmt(item.urgency) : '';
  const subtitleBits = [
    qtyDisplay,
    urgencyLabel,
    item.is_candidate_part ? 'Candidate' : '',
  ].filter(Boolean);

  // entityRef must be truthy for the rich renderer to kick in. Backend
  // always emits `ref` with SL-<id6> fallback; keep part_number as
  // secondary fallback for any caller on the old shape.
  const entityRef = item.ref || item.part_number || '';

  return {
    id: item.id,
    type: 'pms_shopping_list',
    title: item.part_name || 'Shopping List Item',
    subtitle: subtitleBits.join(' · '),
    snippet: item.source_notes,
    metadata: {
      status: item.status,
      urgency: item.urgency,
      source_type: item.source_type,
      part_number: item.part_number,
      quantity_requested: qty,
      requested_by_name: item.requested_by_name,
      required_by_date: item.required_by_date,
      is_candidate_part: item.is_candidate_part,
      created_at: item.created_at,
    },

    // Extended fields for EntityRecordRow
    entityRef,
    assignedTo: item.requested_by_name || undefined,
    status: fmt(item.status) || 'Pending',
    statusVariant: slStatusVariant(item.status),
    severity: null,
    age: formatAge(item.created_at),
  };
}
