import * as React from 'react';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { StatusPill } from '@/components/ui/StatusPill';

// ============================================================================
// TYPES
// ============================================================================

export interface LinkedWorkOrder {
  id: string;
  /** Human-readable number e.g. "WO-2026-001" — NEVER show raw UUID */
  wo_number?: string;
  title: string;
  /** Status enum: draft | open | in_progress | pending_parts | completed | closed | cancelled */
  status: string;
  /** Priority enum: low | medium | high | critical */
  priority?: string;
  assigned_to_name?: string;
  created_at: string;
  due_date?: string;
}

export interface LinkedWorkOrdersSectionProps {
  workOrders: LinkedWorkOrder[];
  /** Equipment ID — used to build "View all" link */
  equipmentId: string;
  /** Top offset for sticky header (56 when inside lens to clear the fixed LensHeader) */
  stickyTop?: number;
}

// ============================================================================
// HELPERS
// ============================================================================

function mapStatusToColor(status: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'cancelled':
      return 'critical';
    case 'in_progress':
    case 'pending_parts':
      return 'warning';
    case 'completed':
    case 'closed':
      return 'success';
    case 'draft':
    case 'open':
    default:
      return 'neutral';
  }
}

function mapPriorityToColor(priority?: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (priority) {
    case 'critical':
      return 'critical';
    case 'high':
      return 'warning';
    default:
      return 'neutral';
  }
}

function formatStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    draft: 'Draft',
    open: 'Open',
    in_progress: 'In Progress',
    pending_parts: 'Pending Parts',
    completed: 'Completed',
    closed: 'Closed',
    cancelled: 'Cancelled',
  };
  return labels[status] ?? status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDate(isoString: string): string {
  try {
    return new Date(isoString).toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return isoString;
  }
}

/** Returns true if a WO is still active (not completed/closed/cancelled) */
function isActiveWorkOrder(wo: LinkedWorkOrder): boolean {
  return !['completed', 'closed', 'cancelled'].includes(wo.status);
}

// ============================================================================
// WORK ORDER ROW — EntityLink pattern
// ============================================================================

interface WorkOrderRowProps {
  wo: LinkedWorkOrder;
}

function WorkOrderRow({ wo }: WorkOrderRowProps) {
  const statusColor = mapStatusToColor(wo.status);
  const statusLabel = formatStatusLabel(wo.status);
  const priorityColor = mapPriorityToColor(wo.priority);

  // Display WO number prefix when available — never expose raw UUID
  const displayTitle = wo.wo_number ? `${wo.wo_number} — ${wo.title}` : wo.title;

  return (
    <a
      href={`/work-orders/${wo.id}`}
      className="flex items-start justify-between gap-4 px-5 py-3 border-b border-surface-border-subtle last:border-b-0 min-h-11 hover:bg-surface-hover transition-colors group"
      aria-label={`View work order: ${displayTitle}`}
    >
      {/* Left: title + meta */}
      <div className="flex-1 min-w-0">
        <p className="text-body-strong text-txt-primary group-hover:text-brand-interactive transition-colors truncate">
          {displayTitle}
        </p>
        <div className="flex items-center gap-2 mt-1">
          <span className="text-caption text-txt-tertiary">
            {formatDate(wo.created_at)}
          </span>
          {wo.assigned_to_name && (
            <span className="text-caption text-txt-tertiary">
              · {wo.assigned_to_name}
            </span>
          )}
          {wo.due_date && (
            <span className="text-caption text-txt-tertiary">
              · Due {formatDate(wo.due_date)}
            </span>
          )}
        </div>
      </div>

      {/* Right: priority + status pills */}
      <div className="flex items-center gap-2 shrink-0">
        {wo.priority && wo.priority !== 'low' && (
          <StatusPill
            status={priorityColor}
            label={wo.priority.charAt(0).toUpperCase() + wo.priority.slice(1)}
          />
        )}
        <StatusPill status={statusColor} label={statusLabel} showDot />
      </div>
    </a>
  );
}

// ============================================================================
// LINKED WORK ORDERS SECTION
// ============================================================================

/**
 * LinkedWorkOrdersSection - List of work orders for this equipment.
 *
 * Each WO renders as an EntityLink (clickable row) navigating to /work-orders/{id}.
 * Active WOs (open/in_progress) are shown first, completed/closed after.
 * Includes WO number prefix to identify work orders without exposing UUIDs.
 */
export function LinkedWorkOrdersSection({
  workOrders,
  equipmentId,
  stickyTop,
}: LinkedWorkOrdersSectionProps) {
  // Active WOs first, then closed/completed
  const active = workOrders.filter(isActiveWorkOrder);
  const completed = workOrders.filter((wo) => !isActiveWorkOrder(wo));
  const sorted = [...active, ...completed];

  return (
    <SectionContainer
      title="Work Orders"
      count={workOrders.length > 0 ? workOrders.length : undefined}
      action={
        workOrders.length > 0
          ? {
              label: 'View all',
              onClick: () => {
                window.location.href = `/work-orders?equipment_id=${equipmentId}`;
              },
            }
          : undefined
      }
      stickyTop={stickyTop}
    >
      {sorted.length === 0 ? (
        <div className="py-8 text-center">
          <p className="text-body text-txt-secondary">
            No work orders found for this equipment.
          </p>
        </div>
      ) : (
        <div className="-mx-4">
          {sorted.map((wo) => (
            <WorkOrderRow key={wo.id} wo={wo} />
          ))}
        </div>
      )}
    </SectionContainer>
  );
}

export default LinkedWorkOrdersSection;
