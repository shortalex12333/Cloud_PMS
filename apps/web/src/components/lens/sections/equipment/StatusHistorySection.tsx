import * as React from 'react';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { EntityLink } from '@/components/ui/EntityLink';
import { GhostButton } from '@/components/ui/GhostButton';
import { cn } from '@/lib/utils';

// ============================================================================
// TYPES
// ============================================================================

export type EquipmentStatus =
  | 'operational'
  | 'degraded'
  | 'failed'
  | 'maintenance'
  | 'decommissioned';

export interface StatusHistoryEntry {
  id: string;
  /** Previous status (null for initial entry) */
  old_status?: EquipmentStatus | null;
  /** New status after change */
  new_status: EquipmentStatus;
  /** When the status change occurred */
  changed_at: string;
  /** Who changed the status (display name) */
  changed_by?: string;
  /** Reason for the status change */
  reason?: string;
  /** Linked work order (if status change was due to a WO) */
  work_order_id?: string;
  work_order_number?: string;
  /** Linked fault (if status change was due to a fault) */
  fault_id?: string;
  fault_number?: string;
  /** Duration in this status (computed from next change) */
  duration_hours?: number;
}

export interface StatusHistorySectionProps {
  entries: StatusHistoryEntry[];
  /** Number of entries to show before "Load more" (default: 15) */
  pageSize?: number;
  /** Top offset for sticky header (56 when inside lens to clear the fixed LensHeader) */
  stickyTop?: number;
  /** Callback when a work order link is clicked */
  onWorkOrderClick?: (workOrderId: string) => void;
  /** Callback when a fault link is clicked */
  onFaultClick?: (faultId: string) => void;
}

// ============================================================================
// CONSTANTS
// ============================================================================

const DEFAULT_PAGE_SIZE = 15;

/** Status colors for visual differentiation */
const STATUS_COLORS: Record<EquipmentStatus, { bg: string; text: string; dot: string }> = {
  operational: {
    bg: 'bg-green-50',
    text: 'text-green-700',
    dot: 'bg-green-500',
  },
  degraded: {
    bg: 'bg-yellow-50',
    text: 'text-yellow-700',
    dot: 'bg-yellow-500',
  },
  failed: {
    bg: 'bg-red-50',
    text: 'text-red-700',
    dot: 'bg-red-500',
  },
  maintenance: {
    bg: 'bg-blue-50',
    text: 'text-blue-700',
    dot: 'bg-blue-500',
  },
  decommissioned: {
    bg: 'bg-gray-100',
    text: 'text-gray-600',
    dot: 'bg-gray-400',
  },
};

// ============================================================================
// HELPERS
// ============================================================================

/**
 * Format timestamp per UI_SPEC.md:
 * - Today: "Today at 14:32"
 * - Within 7 days: "Yesterday", "2 days ago"
 * - Older: "23 Jan 2026"
 */
function formatTimestamp(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    const hh = date.getHours().toString().padStart(2, '0');
    const mm = date.getMinutes().toString().padStart(2, '0');
    return `Today at ${hh}:${mm}`;
  }

  if (diffDays < 7) {
    if (diffDays === 1) return 'Yesterday';
    return `${diffDays} days ago`;
  }

  return date.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

/**
 * Format status to human-readable label.
 */
function formatStatus(status: EquipmentStatus): string {
  const labels: Record<EquipmentStatus, string> = {
    operational: 'Operational',
    degraded: 'Degraded',
    failed: 'Failed',
    maintenance: 'Maintenance',
    decommissioned: 'Decommissioned',
  };
  return labels[status] ?? status.charAt(0).toUpperCase() + status.slice(1);
}

/**
 * Format duration in hours to human-readable string.
 */
function formatDuration(hours?: number): string {
  if (!hours || hours <= 0) return '';

  if (hours < 1) {
    const minutes = Math.round(hours * 60);
    return `${minutes}m`;
  }

  if (hours < 24) {
    return `${Math.round(hours)}h`;
  }

  const days = Math.floor(hours / 24);
  const remainingHours = Math.round(hours % 24);

  if (remainingHours === 0) {
    return `${days}d`;
  }

  return `${days}d ${remainingHours}h`;
}

// ============================================================================
// STATUS BADGE
// ============================================================================

interface StatusBadgeProps {
  status: EquipmentStatus;
  size?: 'sm' | 'md';
}

function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const colors = STATUS_COLORS[status] ?? STATUS_COLORS.operational;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full font-medium',
        colors.bg,
        colors.text,
        size === 'sm' ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-0.5 text-[11px]'
      )}
    >
      <span className={cn('w-1.5 h-1.5 rounded-full', colors.dot)} />
      {formatStatus(status)}
    </span>
  );
}

// ============================================================================
// STATUS HISTORY ENTRY ROW
// ============================================================================

interface StatusHistoryEntryRowProps {
  entry: StatusHistoryEntry;
  /** Whether this is the most recent (first) entry */
  isLatest?: boolean;
  onWorkOrderClick?: (workOrderId: string) => void;
  onFaultClick?: (faultId: string) => void;
}

function StatusHistoryEntryRow({
  entry,
  isLatest,
  onWorkOrderClick,
  onFaultClick,
}: StatusHistoryEntryRowProps) {
  const colors = STATUS_COLORS[entry.new_status] ?? STATUS_COLORS.operational;

  return (
    <div className="flex gap-4 px-5 py-3 border-b border-surface-border-subtle last:border-b-0 min-h-11">
      {/* Timeline dot + line */}
      <div className="flex flex-col items-center shrink-0 pt-1.5">
        <div
          className={cn(
            'w-2.5 h-2.5 rounded-full shrink-0',
            isLatest ? colors.dot : 'bg-surface-border'
          )}
        />
        <div className="w-px flex-1 bg-surface-border-subtle mt-1" />
      </div>

      {/* Content */}
      <div className="flex-1 pb-2 min-w-0">
        {/* Status change + timestamp */}
        <div className="flex items-center justify-between gap-2 mb-1 flex-wrap">
          <div className="flex items-center gap-2 flex-wrap">
            {/* Old status (if any) */}
            {entry.old_status && (
              <>
                <StatusBadge status={entry.old_status} size="sm" />
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 12 12"
                  fill="none"
                  className="text-txt-tertiary shrink-0"
                  aria-hidden="true"
                >
                  <path
                    d="M4.5 2.5L8 6L4.5 9.5"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </>
            )}
            {/* New status */}
            <StatusBadge status={entry.new_status} />

            {/* Duration in this status */}
            {entry.duration_hours !== undefined && entry.duration_hours > 0 && (
              <span className="text-[11px] text-txt-tertiary">
                ({formatDuration(entry.duration_hours)})
              </span>
            )}
          </div>

          {/* Timestamp */}
          <span
            className="text-[12px] text-txt-tertiary shrink-0"
            title={new Date(entry.changed_at).toLocaleString()}
          >
            {formatTimestamp(entry.changed_at)}
          </span>
        </div>

        {/* Reason */}
        {entry.reason && (
          <p className="text-[13px] text-txt-secondary leading-[1.5] mt-1">
            {entry.reason}
          </p>
        )}

        {/* Changed by */}
        {entry.changed_by && (
          <p className="text-[12px] text-txt-tertiary mt-1">
            by {entry.changed_by}
          </p>
        )}

        {/* Linked entities */}
        {(entry.work_order_id || entry.fault_id) && (
          <div className="flex items-center gap-3 mt-2">
            {entry.work_order_id && (
              <EntityLink
                entityType="work_order"
                entityId={entry.work_order_id}
                label={entry.work_order_number ?? 'View Work Order'}
                onClick={() => onWorkOrderClick?.(entry.work_order_id!)}
                className="text-[12px]"
              />
            )}
            {entry.fault_id && (
              <EntityLink
                entityType="fault"
                entityId={entry.fault_id}
                label={entry.fault_number ?? 'View Fault'}
                onClick={() => onFaultClick?.(entry.fault_id!)}
                className="text-[12px]"
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// STATUS HISTORY SECTION
// ============================================================================

/**
 * StatusHistorySection - Equipment status change timeline.
 *
 * Displays chronological history of status transitions with:
 * - Visual status badges with color coding
 * - Transition arrows showing old -> new status
 * - Reason for change
 * - Links to related work orders or faults
 * - Duration in each status
 *
 * Uses SectionContainer for sticky header behavior via IntersectionObserver.
 */
export function StatusHistorySection({
  entries,
  pageSize = DEFAULT_PAGE_SIZE,
  stickyTop,
  onWorkOrderClick,
  onFaultClick,
}: StatusHistorySectionProps) {
  const [visibleCount, setVisibleCount] = React.useState(pageSize);

  // Reset pagination when entries change
  React.useEffect(() => {
    setVisibleCount(pageSize);
  }, [entries.length, pageSize]);

  // Sort by changed_at descending (most recent first)
  const sorted = [...entries].sort(
    (a, b) => new Date(b.changed_at).getTime() - new Date(a.changed_at).getTime()
  );

  const visibleEntries = sorted.slice(0, visibleCount);
  const hasMore = sorted.length > visibleCount;
  const remainingCount = sorted.length - visibleCount;

  return (
    <SectionContainer
      title="Status History"
      count={entries.length > 0 ? entries.length : undefined}
      stickyTop={stickyTop}
    >
      {sorted.length === 0 ? (
        <div className="py-8 text-center">
          <p className="text-[14px] text-txt-secondary leading-[1.6]">
            No status changes recorded yet.
          </p>
        </div>
      ) : (
        <>
          <div className="-mx-4">
            {visibleEntries.map((entry, index) => (
              <StatusHistoryEntryRow
                key={entry.id}
                entry={entry}
                isLatest={index === 0}
                onWorkOrderClick={onWorkOrderClick}
                onFaultClick={onFaultClick}
              />
            ))}
          </div>

          {/* Load more */}
          {hasMore && (
            <div className="pt-3 pb-1 text-center">
              <GhostButton
                onClick={() => setVisibleCount((prev) => prev + pageSize)}
              >
                Load {Math.min(remainingCount, pageSize)} more
                {remainingCount > pageSize && ` (${remainingCount} remaining)`}
              </GhostButton>
            </div>
          )}
        </>
      )}
    </SectionContainer>
  );
}

export default StatusHistorySection;
