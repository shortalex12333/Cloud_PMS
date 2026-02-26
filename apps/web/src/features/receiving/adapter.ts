import type { EntityListResult } from '@/features/entity-list/types';
import type { ReceivingItem } from './types';

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
    subtitle: `${statusDisplay}${dateDisplay ? ` · ${dateDisplay}` : ''}${item.items_count ? ` · ${item.items_count} items` : ''}`,
    snippet: item.description || item.notes,
    metadata: {
      status: item.status,
      supplier_name: item.supplier_name,
      received_date: item.received_date,
      items_count: item.items_count,
      created_at: item.created_at,
    },
  };
}
