import * as React from 'react';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { GhostButton } from '@/components/ui/GhostButton';

// ============================================================================
// TYPES
// ============================================================================

export interface HoursLogEntry {
  id: string;
  /** Current cumulative hours reading */
  hours_reading: number;
  /** Delta from previous reading (computed) */
  hours_since_last?: number;
  /** How hours were recorded: manual | automatic | estimated | rollover */
  reading_type?: string;
  /** Date/time the reading was recorded */
  recorded_at: string;
  /** Who recorded the reading (display name) */
  recorded_by?: string;
  /** Optional notes about the reading */
  notes?: string;
  /** Source system: celeste | email_import | telemetry */
  source?: string;
}

export interface HoursLogSectionProps {
  entries: HoursLogEntry[];
  /** Number of entries to show before "Load more" (default: 10) */
  pageSize?: number;
  /** Whether user can add a new hours reading */
  canAddReading?: boolean;
  /** Callback when "Log Hours" button is clicked */
  onAddReading?: () => void;
  /** Top offset for sticky header (56 when inside lens to clear the fixed LensHeader) */
  stickyTop?: number;
}

// ============================================================================
// CONSTANTS
// ============================================================================

const DEFAULT_PAGE_SIZE = 10;

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
 * Format hours reading with proper decimal places.
 */
function formatHours(hours: number): string {
  // Show up to 1 decimal if fractional, otherwise whole number
  if (hours % 1 === 0) {
    return hours.toLocaleString('en-US');
  }
  return hours.toLocaleString('en-US', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
}

/**
 * Format reading type to human-readable label.
 */
function formatReadingType(type?: string): string {
  if (!type) return 'Manual';
  const labels: Record<string, string> = {
    manual: 'Manual',
    automatic: 'Auto',
    estimated: 'Est.',
    rollover: 'Rollover',
  };
  return labels[type] ?? type.charAt(0).toUpperCase() + type.slice(1);
}

// ============================================================================
// HOURS LOG ENTRY ROW
// ============================================================================

interface HoursLogEntryRowProps {
  entry: HoursLogEntry;
  /** Whether this is the most recent (first) entry */
  isLatest?: boolean;
}

function HoursLogEntryRow({ entry, isLatest }: HoursLogEntryRowProps) {
  return (
    <div className="flex items-start gap-4 px-5 py-3 border-b border-surface-border-subtle last:border-b-0 min-h-[44px]">
      {/* Hours reading - primary value */}
      <div className="shrink-0 w-24 text-right">
        <span
          className={`text-[16px] font-semibold tabular-nums ${
            isLatest ? 'text-brand-interactive' : 'text-txt-primary'
          }`}
        >
          {formatHours(entry.hours_reading)}
        </span>
        <span className="text-[12px] text-txt-tertiary ml-1">hrs</span>
      </div>

      {/* Delta indicator */}
      <div className="shrink-0 w-16 text-center">
        {entry.hours_since_last !== undefined && entry.hours_since_last > 0 ? (
          <span className="text-[12px] text-txt-secondary">
            +{formatHours(entry.hours_since_last)}
          </span>
        ) : (
          <span className="text-[12px] text-txt-tertiary">-</span>
        )}
      </div>

      {/* Details */}
      <div className="flex-1 min-w-0">
        {/* Date + Type */}
        <div className="flex items-center gap-2">
          <span className="text-[13px] text-txt-primary">
            {formatTimestamp(entry.recorded_at)}
          </span>
          <span className="text-[11px] px-1.5 py-0.5 rounded bg-surface-secondary text-txt-tertiary font-medium">
            {formatReadingType(entry.reading_type)}
          </span>
        </div>

        {/* Recorded by */}
        {entry.recorded_by && (
          <p className="text-[12px] text-txt-tertiary mt-0.5">
            by {entry.recorded_by}
          </p>
        )}

        {/* Notes */}
        {entry.notes && (
          <p className="text-[12px] text-txt-secondary mt-1 line-clamp-2">
            {entry.notes}
          </p>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// HOURS LOG SECTION
// ============================================================================

/**
 * HoursLogSection - Running hours log for equipment with meters.
 *
 * Displays chronological history of hours readings with:
 * - Cumulative hours reading (primary value)
 * - Delta from previous reading
 * - Reading type (manual/automatic/estimated)
 * - Date, time, and recorder
 *
 * Uses SectionContainer for sticky header behavior via IntersectionObserver.
 */
export function HoursLogSection({
  entries,
  pageSize = DEFAULT_PAGE_SIZE,
  canAddReading = false,
  onAddReading,
  stickyTop,
}: HoursLogSectionProps) {
  const [visibleCount, setVisibleCount] = React.useState(pageSize);

  // Reset pagination when entries change
  React.useEffect(() => {
    setVisibleCount(pageSize);
  }, [entries.length, pageSize]);

  // Sort by recorded_at descending (most recent first)
  const sorted = [...entries].sort(
    (a, b) => new Date(b.recorded_at).getTime() - new Date(a.recorded_at).getTime()
  );

  const visibleEntries = sorted.slice(0, visibleCount);
  const hasMore = sorted.length > visibleCount;
  const remainingCount = sorted.length - visibleCount;

  return (
    <SectionContainer
      title="Hours Log"
      count={entries.length > 0 ? entries.length : undefined}
      action={
        canAddReading && onAddReading
          ? { label: '+ Log Hours', onClick: onAddReading }
          : undefined
      }
      stickyTop={stickyTop}
    >
      {sorted.length === 0 ? (
        <div className="py-8 text-center">
          <p className="text-[14px] text-txt-secondary leading-[1.6]">
            No hours readings recorded yet.
          </p>
          {canAddReading && onAddReading && (
            <GhostButton onClick={onAddReading} className="mt-3">
              + Log Hours
            </GhostButton>
          )}
        </div>
      ) : (
        <>
          {/* Header row */}
          <div className="flex items-center gap-4 px-5 py-2 border-b border-surface-border text-[11px] text-txt-tertiary uppercase tracking-[0.06em] font-medium">
            <div className="shrink-0 w-24 text-right">Reading</div>
            <div className="shrink-0 w-16 text-center">Delta</div>
            <div className="flex-1">Details</div>
          </div>

          {/* Entries */}
          <div className="-mx-4">
            {visibleEntries.map((entry, index) => (
              <HoursLogEntryRow
                key={entry.id}
                entry={entry}
                isLatest={index === 0}
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

export default HoursLogSection;
