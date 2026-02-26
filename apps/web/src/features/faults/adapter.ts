import type { EntityListResult } from '@/features/entity-list/types';
import type { Fault } from './types';

export function faultToListResult(fault: Fault): EntityListResult {
  const statusDisplay = fault.status?.replace(/_/g, ' ') || 'Unknown';
  const severityDisplay = fault.severity || '';

  return {
    id: fault.id,
    type: 'pms_faults',
    title: fault.title || `Fault ${fault.fault_number || fault.id.slice(0, 8)}`,
    subtitle: `${statusDisplay}${severityDisplay ? ` · ${severityDisplay}` : ''}${fault.equipment_name ? ` · ${fault.equipment_name}` : ''}`,
    snippet: fault.description,
    metadata: {
      status: fault.status,
      severity: fault.severity,
      equipment_name: fault.equipment_name,
      created_at: fault.created_at,
    },
  };
}
