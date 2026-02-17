import * as React from 'react';
import { cn } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { GhostButton } from '@/components/ui/GhostButton';

// ============================================================================
// TYPES
// ============================================================================

export interface AuditLogEntry {
  id: string;
  action: string;
  actor: string;
  actor_id?: string;
  timestamp: string;
  /** Additional details about the action (optional) */
  details?: Record<string, unknown>;
  /** Human-readable description of what changed */
  description?: string;
}

export interface HistorySectionProps {
  history: AuditLogEntry[];
  /** Number of entries to show before "Load more" (default: 20) */
  pageSize?: number;
}

// ============================================================================
// CONSTANTS
// ============================================================================

const DEFAULT_PAGE_SIZE = 20;

// ============================================================================
// HELPERS
// ============================================================================

/**
 * Format timestamp per UI_SPEC.md:
 * - Today: "Today at 14:32"
 * - Within 7 days: "Yesterday", "2 days ago"
 * - Older: "Jan 23, 2026"
 */
function formatTimestamp(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

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
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

/**
 * Convert action key to human-readable label.
 * Backend sends snake_case action names — displayed as Title Case.
 */
function formatActionLabel(action: string): string {
  return action
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

// ============================================================================
// HISTORY ENTRY ROW
// ============================================================================

interface HistoryEntryRowProps {
  entry: AuditLogEntry;
}

function HistoryEntryRow({ entry }: HistoryEntryRowProps) {
  const [isExpanded, setIsExpanded] = React.useState(false);

  const hasDetails =
    entry.description ||
    (entry.details && Object.keys(entry.details).length > 0);

  return (
    <div
      className={cn(
        // Row layout: 20px horizontal, 12px vertical per UI_SPEC.md
        'px-5 py-3 min-h-[44px]',
        // Subtle internal divider (not full-width per Apple pattern)
        'border-b border-surface-border-subtle last:border-b-0'
      )}
    >
      {/* Primary row: action label + actor + timestamp */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          {/* Action: body-strong weight, primary color */}
          <span className="text-[14px] font-medium text-txt-primary leading-[1.6]">
            {formatActionLabel(entry.action)}
          </span>

          {/* Actor: secondary color */}
          <span className="text-[13px] text-txt-secondary ml-2 leading-[1.6]">
            by {entry.actor}
          </span>
        </div>

        {/* Timestamp: caption style, tertiary, right-aligned */}
        <span
          className="text-[12px] text-txt-tertiary leading-[1.4] flex-shrink-0"
          title={new Date(entry.timestamp).toLocaleString()}
        >
          {formatTimestamp(entry.timestamp)}
        </span>
      </div>

      {/* Expand/collapse for details */}
      {hasDetails && (
        <>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className={cn(
              'mt-1 text-[12px] font-medium text-txt-tertiary',
              'hover:text-txt-secondary transition-colors duration-150',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-interactive rounded-sm'
            )}
            aria-expanded={isExpanded}
          >
            {isExpanded ? 'Hide details' : 'Show details'}
          </button>

          {isExpanded && (
            <div className="mt-2 pl-0">
              {/* Human-readable description */}
              {entry.description && (
                <p className="text-[13px] text-txt-secondary leading-[1.6] mb-1">
                  {entry.description}
                </p>
              )}

              {/* Technical details as key-value list */}
              {entry.details && Object.keys(entry.details).length > 0 && (
                <dl className="space-y-0.5">
                  {Object.entries(entry.details).map(([key, value]) => (
                    <div key={key} className="flex gap-2">
                      <dt className="text-[12px] text-txt-tertiary capitalize">
                        {key.replace(/_/g, ' ')}:
                      </dt>
                      <dd className="text-[12px] text-txt-secondary">
                        {typeof value === 'object'
                          ? JSON.stringify(value)
                          : String(value)}
                      </dd>
                    </div>
                  ))}
                </dl>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ============================================================================
// HISTORY SECTION
// ============================================================================

/**
 * HistorySection - Read-only ledger of audit log entries for a work order.
 *
 * - No action button (read-only by design)
 * - No empty state (work orders always have at least a creation entry)
 * - Most recent first (caller is responsible for sort order)
 * - Shows pageSize entries, with "Load more" for additional entries
 * - Each entry: action label, actor, timestamp, collapsible details
 *
 * Uses SectionContainer for sticky header behavior via IntersectionObserver.
 */
export function HistorySection({
  history,
  pageSize = DEFAULT_PAGE_SIZE,
}: HistorySectionProps) {
  const [visibleCount, setVisibleCount] = React.useState(pageSize);

  // Reset pagination when history changes (e.g. after new action)
  React.useEffect(() => {
    setVisibleCount(pageSize);
  }, [history.length, pageSize]);

  const visibleEntries = history.slice(0, visibleCount);
  const hasMore = history.length > visibleCount;
  const remainingCount = history.length - visibleCount;

  return (
    // No action prop: HistorySection is read-only, no adjacent button
    <SectionContainer title="History">
      {history.length === 0 ? (
        // Defensive empty state — should not normally render per spec
        // (work orders always have creation entry), but handle gracefully
        <div className="py-6 text-center">
          <p className="text-[14px] text-txt-secondary">
            No history entries found.
          </p>
        </div>
      ) : (
        <>
          <div className="-mx-4">
            {visibleEntries.map((entry) => (
              <HistoryEntryRow key={entry.id} entry={entry} />
            ))}
          </div>

          {/* Load more — only shown when more entries exist */}
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

export default HistorySection;
