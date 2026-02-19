import * as React from 'react';
import { cn } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { GhostButton } from '@/components/ui/GhostButton';
import { StatusPill } from '@/components/ui/StatusPill';

// ============================================================================
// TYPES
// ============================================================================

export type UsageReason =
  | 'work_order'
  | 'maintenance'
  | 'emergency'
  | 'testing'
  | 'other';

export interface PartUsageEntry {
  id: string;
  /** Quantity used (always positive) */
  quantity: number;
  /** Reason for usage: work_order, maintenance, emergency, testing, other */
  usage_reason?: UsageReason;
  /** ISO timestamp of when usage was logged */
  used_at: string;
  /** Name of crew member who logged usage — NEVER show raw UUID */
  logged_by: string;
  logged_by_id?: string;
  /** Linked work order (if usage was for a WO) */
  work_order_id?: string;
  work_order_number?: string;
  /** Linked equipment (if usage was for specific equipment) */
  equipment_id?: string;
  equipment_name?: string;
  /** Free-text notes */
  notes?: string;
}

export interface UsageLogSectionProps {
  usageLog: PartUsageEntry[];
  pageSize?: number;
  /** Top offset for sticky header (56 when inside lens to clear the fixed LensHeader) */
  stickyTop?: number;
}

// ============================================================================
// CONSTANTS
// ============================================================================

const DEFAULT_PAGE_SIZE = 20;

// ============================================================================
// HELPERS
// ============================================================================

function formatTimestamp(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    const hh = date.getHours().toString().padStart(2, '0');
    const mm = date.getMinutes().toString().padStart(2, '0');
    return `Today at ${hh}:${mm}`;
  }
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  return date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

/**
 * Map usage reason to human-readable label and StatusPill color.
 * emergency = critical (red)
 * work_order/maintenance = warning (orange - work was done)
 * testing/other = neutral
 */
function mapUsageReasonToDisplay(reason?: UsageReason): {
  label: string;
  color: 'critical' | 'warning' | 'success' | 'neutral';
} {
  switch (reason) {
    case 'emergency':
      return { label: 'Emergency', color: 'critical' };
    case 'work_order':
      return { label: 'Work Order', color: 'warning' };
    case 'maintenance':
      return { label: 'Maintenance', color: 'warning' };
    case 'testing':
      return { label: 'Testing', color: 'neutral' };
    case 'other':
      return { label: 'Other', color: 'neutral' };
    default:
      return { label: 'Usage', color: 'neutral' };
  }
}

// ============================================================================
// USAGE ROW
// ============================================================================

interface UsageRowProps {
  entry: PartUsageEntry;
}

function UsageRow({ entry }: UsageRowProps) {
  const [isExpanded, setIsExpanded] = React.useState(false);
  const { label, color } = mapUsageReasonToDisplay(entry.usage_reason);
  const hasDetails = !!entry.notes || !!entry.work_order_number || !!entry.equipment_name;

  return (
    <div
      className={cn(
        'px-5 py-3 min-h-[44px]',
        'border-b border-surface-border-subtle last:border-b-0'
      )}
    >
      {/* Primary row: reason pill + quantity + logged_by + timestamp */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap flex-1 min-w-0">
          <StatusPill status={color} label={label} />
          <span
            className="text-[14px] font-semibold leading-none tabular-nums text-status-warning"
          >
            -{entry.quantity}
          </span>
          <span className="text-[13px] text-txt-secondary leading-none">
            by {entry.logged_by}
          </span>
        </div>
        <span
          className="text-[12px] text-txt-tertiary leading-[1.4] flex-shrink-0"
          title={new Date(entry.used_at).toLocaleString()}
        >
          {formatTimestamp(entry.used_at)}
        </span>
      </div>

      {/* Linked entities shown inline when available */}
      {(entry.work_order_number || entry.equipment_name) && (
        <div className="mt-1.5 flex items-center gap-3 flex-wrap">
          {entry.work_order_number && (
            <a
              href={`/work-orders/${entry.work_order_id}`}
              className="text-[13px] text-brand-interactive hover:underline underline-offset-2 transition-colors"
            >
              {entry.work_order_number}
            </a>
          )}
          {entry.equipment_name && (
            <a
              href={`/equipment/${entry.equipment_id}`}
              className="text-[13px] text-brand-interactive hover:underline underline-offset-2 transition-colors"
            >
              {entry.equipment_name}
            </a>
          )}
        </div>
      )}

      {/* Expand/collapse for notes */}
      {entry.notes && (
        <>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className={cn(
              'mt-1 text-[12px] font-medium text-txt-tertiary',
              'hover:text-txt-secondary transition-colors duration-fast',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-interactive rounded-lg'
            )}
            aria-expanded={isExpanded}
          >
            {isExpanded ? 'Hide notes' : 'Show notes'}
          </button>

          {isExpanded && (
            <div className="mt-2">
              <p className="text-[13px] text-txt-secondary leading-[1.6]">
                {entry.notes}
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ============================================================================
// USAGE LOG SECTION
// ============================================================================

/**
 * UsageLogSection - Paginated read-only log of part usage events.
 *
 * Shows when parts were consumed, for what reason (work order, maintenance,
 * emergency, testing), linked work orders and equipment.
 * Most recent first (caller responsible for sort order).
 * Paginated with "Load more" for > pageSize entries.
 *
 * Uses SectionContainer for sticky header behavior via IntersectionObserver.
 */
export function UsageLogSection({
  usageLog,
  pageSize = DEFAULT_PAGE_SIZE,
  stickyTop,
}: UsageLogSectionProps) {
  const [visibleCount, setVisibleCount] = React.useState(pageSize);

  React.useEffect(() => {
    setVisibleCount(pageSize);
  }, [usageLog.length, pageSize]);

  const visibleEntries = usageLog.slice(0, visibleCount);
  const hasMore = usageLog.length > visibleCount;
  const remainingCount = usageLog.length - visibleCount;

  return (
    <SectionContainer
      title="Usage Log"
      count={usageLog.length > 0 ? usageLog.length : undefined}
      stickyTop={stickyTop}
    >
      {usageLog.length === 0 ? (
        <div className="py-8 text-center">
          <p className="text-[14px] text-txt-secondary leading-[1.6]">
            No usage records yet.
          </p>
        </div>
      ) : (
        <>
          <div className="-mx-4">
            {visibleEntries.map((entry) => (
              <UsageRow key={entry.id} entry={entry} />
            ))}
          </div>

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

export default UsageLogSection;
