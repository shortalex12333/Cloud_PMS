import * as React from 'react';
import { SectionContainer } from '@/components/ui/SectionContainer';

// ============================================================================
// TYPES
// ============================================================================

export interface MaintenanceHistoryEntry {
  id: string;
  /** Type of event: work_order | inspection | service | repair */
  event_type: string;
  title: string;
  description?: string;
  performed_by?: string;
  performed_at: string;
  /** Linked work order ID (if event originated from a WO) */
  work_order_id?: string;
  work_order_number?: string;
}

export interface MaintenanceHistorySectionProps {
  entries: MaintenanceHistoryEntry[];
  /** Top offset for sticky header (56 when inside lens to clear the fixed LensHeader) */
  stickyTop?: number;
}

// ============================================================================
// HELPERS
// ============================================================================

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

function formatEventType(eventType: string): string {
  const labels: Record<string, string> = {
    work_order: 'Work Order',
    inspection: 'Inspection',
    service: 'Service',
    repair: 'Repair',
    replacement: 'Replacement',
  };
  return labels[eventType] ?? eventType.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// ============================================================================
// TIMELINE ENTRY
// ============================================================================

interface TimelineEntryProps {
  entry: MaintenanceHistoryEntry;
}

function TimelineEntry({ entry }: TimelineEntryProps) {
  return (
    <div className="flex gap-4 px-5 py-3 border-b border-surface-border-subtle last:border-b-0 min-h-[44px]">
      {/* Timeline dot + line */}
      <div className="flex flex-col items-center shrink-0 pt-1">
        <div className="w-2 h-2 rounded-full bg-brand-interactive shrink-0" />
        <div className="w-px flex-1 bg-surface-border-subtle mt-1" />
      </div>

      {/* Content */}
      <div className="flex-1 pb-2">
        {/* Event type + date */}
        <div className="flex items-center justify-between gap-2 mb-0.5">
          <span className="text-[11px] font-medium text-txt-tertiary uppercase tracking-[0.06em]">
            {formatEventType(entry.event_type)}
          </span>
          <span className="text-[12px] text-txt-tertiary">
            {formatDate(entry.performed_at)}
          </span>
        </div>

        {/* Title */}
        <p className="text-[14px] font-medium text-txt-primary leading-[1.4]">
          {entry.title}
        </p>

        {/* Description */}
        {entry.description && (
          <p className="text-[13px] text-txt-secondary leading-[1.5] mt-0.5">
            {entry.description}
          </p>
        )}

        {/* Performed by */}
        {entry.performed_by && (
          <p className="text-[12px] text-txt-tertiary mt-1">
            by {entry.performed_by}
          </p>
        )}

        {/* Work order link */}
        {entry.work_order_id && (
          <a
            href={`/work-orders/${entry.work_order_id}`}
            className="text-[12px] font-medium text-brand-interactive hover:text-brand-hover transition-colors mt-1 block"
          >
            {entry.work_order_number ?? 'View Work Order'}
          </a>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// MAINTENANCE HISTORY SECTION
// ============================================================================

/**
 * MaintenanceHistorySection - Timeline of maintenance events for this equipment.
 *
 * Displays work orders, inspections, services, and repairs in chronological order
 * (most recent first). Each entry shows event type, title, date, and performer.
 */
export function MaintenanceHistorySection({
  entries,
  stickyTop,
}: MaintenanceHistorySectionProps) {
  // Sort by date descending (most recent first)
  const sorted = [...entries].sort(
    (a, b) => new Date(b.performed_at).getTime() - new Date(a.performed_at).getTime()
  );

  return (
    <SectionContainer
      title="Maintenance History"
      count={entries.length > 0 ? entries.length : undefined}
      stickyTop={stickyTop}
    >
      {sorted.length === 0 ? (
        <div className="py-8 text-center">
          <p className="text-[14px] text-txt-secondary leading-[1.6]">
            No maintenance history recorded yet.
          </p>
        </div>
      ) : (
        <div className="-mx-4">
          {sorted.map((entry) => (
            <TimelineEntry key={entry.id} entry={entry} />
          ))}
        </div>
      )}
    </SectionContainer>
  );
}

export default MaintenanceHistorySection;
