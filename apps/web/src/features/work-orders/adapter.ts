import type { EntityListResult } from '@/features/entity-list/types';
import type { WorkOrder } from './types';

export function workOrderToListResult(wo: WorkOrder): EntityListResult {
  const statusDisplay = wo.status?.replace(/_/g, ' ') || 'Unknown';
  const priorityDisplay = wo.priority || '';

  return {
    id: wo.id,
    type: 'pms_work_orders',
    title: wo.title || `WO-${wo.wo_number}`,
    subtitle: `${wo.wo_number} · ${statusDisplay}${priorityDisplay ? ` · ${priorityDisplay}` : ''}`,
    snippet: wo.description,
    metadata: {
      status: wo.status,
      priority: wo.priority,
      equipment_name: wo.equipment_name,
      created_at: wo.created_at,
    },
  };
}
