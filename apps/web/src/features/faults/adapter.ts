import type { EntityListResult } from '@/features/entity-list/types';
import type { Fault } from './types';

function formatAge(dateStr?: string): string {
  if (!dateStr) return '\u2014';
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const diffDays = Math.floor(diffMs / 86_400_000);
  if (diffDays < 1) return '<1d';
  if (diffDays < 7) return `${diffDays}d`;
  const d = new Date(dateStr);
  return `${d.getDate()} ${d.toLocaleDateString('en-GB', { month: 'short' })}`;
}

function faultStatusVariant(status?: string, severity?: string): string {
  const s = status?.toLowerCase();
  const sev = severity?.toLowerCase();
  if (sev === 'critical' || sev === 'emergency') return 'critical';
  if (sev === 'high' || sev === 'medium') return 'warning';
  if (s === 'resolved' || s === 'closed') return 'completed';
  if (s === 'investigating') return 'in_progress';
  return 'open';
}

function faultSeverity(severity?: string): string | null {
  const sev = severity?.toLowerCase();
  if (sev === 'critical' || sev === 'emergency') return 'critical';
  if (sev === 'high' || sev === 'medium') return 'warning';
  return null;
}

export function faultToListResult(fault: Fault): EntityListResult {
  const statusDisplay = fault.status?.replace(/_/g, ' ') || 'Unknown';
  const severityDisplay = fault.severity || '';

  return {
    id: fault.id,
    type: 'pms_faults',
    title: fault.title || `Fault ${fault.fault_number || 'Fault'}`,
    subtitle: `${statusDisplay}${severityDisplay ? ` \u00b7 ${severityDisplay}` : ''}${fault.equipment_name ? ` \u00b7 ${fault.equipment_name}` : ''}`,
    snippet: fault.description,
    metadata: {
      status: fault.status,
      severity: fault.severity,
      equipment_name: fault.equipment_name,
      created_at: fault.created_at,
    },

    // Extended fields for EntityRecordRow
    entityRef: fault.fault_code
      ? `F\u00b7${fault.fault_code}`
      : fault.fault_number
        ? `F\u00b7${fault.fault_number}`
        : '',
    equipmentRef: undefined,
    equipmentName: fault.equipment_name || undefined,
    assignedTo: undefined, // reported_by_name not available in table
    status: severityDisplay || statusDisplay,
    statusVariant: faultStatusVariant(fault.status, fault.severity),
    severity: faultSeverity(fault.severity),
    age: formatAge(fault.created_at),
  };
}
