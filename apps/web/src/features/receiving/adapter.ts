import type { EntityListResult } from '@/features/entity-list/types';
import type { ReceivingItem } from './types';

function formatAge(dateStr?: string): string {
  if (!dateStr) return '\u2014';
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffDays = Math.floor((now - then) / 86_400_000);
  if (diffDays < 1) return '<1d';
  if (diffDays < 7) return `${diffDays}d`;
  const d = new Date(dateStr);
  return `${d.getDate()} ${d.toLocaleDateString('en-GB', { month: 'short' })}`;
}

function receivingStatusVariant(status?: string): string {
  const s = status?.toLowerCase();
  if (s === 'rejected') return 'critical';
  if (s === 'pending') return 'pending';
  if (s === 'accepted' || s === 'received') return 'signed';
  return 'open';
}

export function receivingToListResult(item: ReceivingItem): EntityListResult {
  const statusDisplay = item.status?.replace(/_/g, ' ') || 'Pending';
  const dateDisplay = item.received_date
    ? new Date(item.received_date).toLocaleDateString()
    : item.expected_date
      ? `Expected: ${new Date(item.expected_date).toLocaleDateString()}`
      : '';

  return {
    id: item.id,
    type: 'pms_receiving',
    title: item.supplier_name || `Receiving ${item.receiving_number || item.id.slice(0, 8)}`,
    subtitle: `${statusDisplay}${dateDisplay ? ` \u00b7 ${dateDisplay}` : ''}${item.items_count ? ` \u00b7 ${item.items_count} items` : ''}`,
    snippet: item.description || item.notes,
    metadata: {
      status: item.status,
      supplier_name: item.supplier_name,
      received_date: item.received_date,
      items_count: item.items_count,
      created_at: item.created_at,
    },

    // Extended fields for EntityRecordRow
    entityRef: item.receiving_number || item.id.slice(0, 8),
    assignedTo: undefined,
    status: statusDisplay,
    statusVariant: receivingStatusVariant(item.status),
    severity: item.status?.toLowerCase() === 'rejected' ? 'critical' : null,
    age: formatAge(item.created_at),
  };
}
