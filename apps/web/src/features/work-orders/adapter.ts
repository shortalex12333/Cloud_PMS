import type { EntityListResult } from '@/features/entity-list/types';
import type { WorkOrder } from './types';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
function isUUID(s: string): boolean { return UUID_RE.test(s); }

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

function woStatusVariant(status?: string, priority?: string): string {
  const s = status?.toLowerCase();
  if (s === 'overdue') return 'overdue';
  if (s === 'in_progress' || s === 'in progress') return 'in_progress';
  if (s === 'completed' || s === 'closed') return 'completed';
  if (s === 'cancelled') return 'cancelled';
  if (s === 'due_soon' || s === 'due soon') return 'due_soon';
  if (priority?.toLowerCase() === 'emergency') return 'critical';
  return 'open';
}

function woSeverity(status?: string, priority?: string): string | null {
  const s = status?.toLowerCase();
  if (s === 'overdue') return 'critical';
  if (s === 'due_soon' || s === 'due soon') return 'warning';
  if (priority?.toLowerCase() === 'emergency') return 'critical';
  if (priority?.toLowerCase() === 'critical') return 'warning';
  return null;
}

export function workOrderToListResult(wo: WorkOrder): EntityListResult {
  const statusDisplay = wo.status?.replace(/_/g, ' ') || 'Unknown';
  const priorityDisplay = wo.priority || '';

  return {
    id: wo.id,
    type: 'pms_work_orders',
    title: wo.title || `WO-${wo.wo_number}`,
    subtitle: `${wo.wo_number} \u00b7 ${statusDisplay}${priorityDisplay ? ` \u00b7 ${priorityDisplay}` : ''}`,
    snippet: wo.description,
    metadata: {
      status: wo.status,
      priority: wo.priority,
      equipment_name: wo.equipment_name,
      created_at: wo.created_at,
    },

    // Extended fields for EntityRecordRow
    entityRef: wo.wo_number ? `WO\u00b7${wo.wo_number}` : wo.id.slice(0, 8),
    equipmentRef: wo.equipment_id ? wo.equipment_id.slice(0, 8) : undefined,
    equipmentName: wo.equipment_name || undefined,
    assignedTo: wo.assigned_to_name || (wo.assigned_to && !isUUID(wo.assigned_to) ? wo.assigned_to : undefined),
    status: statusDisplay,
    statusVariant: woStatusVariant(wo.status, wo.priority),
    severity: woSeverity(wo.status, wo.priority),
    age: formatAge(wo.created_at),
  };
}
