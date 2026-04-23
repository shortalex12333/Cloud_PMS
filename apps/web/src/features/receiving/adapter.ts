import type { EntityListResult } from '@/features/entity-list/types';
import type { ReceivingItem } from './types';

function formatAge(dateStr?: string): string {
  if (!dateStr) return '—';
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
  if (s === 'in_review') return 'pending';
  if (s === 'accepted') return 'signed';
  return 'open';
}

export function receivingToListResult(item: ReceivingItem): EntityListResult {
  const raw = item as unknown as Record<string, unknown>;
  const statusDisplay = item.status?.replace(/_/g, ' ') || 'Draft';

  // API sends vendor_name and a pre-formatted ref — never expose raw UUIDs
  const vendorName = (raw.vendor_name as string | undefined) || item.supplier_name || '';
  const poNum = (raw.po_number as string | undefined) || '';
  const entityRef = (raw.ref as string | undefined) || (raw.receiving_number as string | undefined) || '';

  const dateDisplay = item.received_date
    ? new Date(item.received_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
    : '';

  const subtitleParts: string[] = [statusDisplay];
  if (dateDisplay) subtitleParts.push(dateDisplay);
  if (poNum) subtitleParts.push(`PO ${poNum}`);

  return {
    id: item.id,
    type: 'pms_receiving',
    title: vendorName || (raw.title as string | undefined) || 'Draft Receiving',
    subtitle: subtitleParts.join(' · '),
    snippet: item.notes,
    metadata: {
      status: item.status,
      vendor_name: vendorName,
      received_date: item.received_date,
      po_number: poNum,
      created_at: item.created_at,
    },
    entityRef,
    assignedTo: undefined,
    status: statusDisplay,
    statusVariant: receivingStatusVariant(item.status),
    severity: item.status?.toLowerCase() === 'rejected' ? 'critical' : null,
    age: formatAge(item.created_at),
  };
}
