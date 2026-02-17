import * as React from 'react';
import { cn } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import type { DailyLogEntry, RestPeriod } from '../../HoursOfRestLens';

// ============================================================================
// TYPES
// ============================================================================

export interface DailyLogSectionProps {
  /** Array of daily log entries for the period */
  entries: DailyLogEntry[];
  /** Top offset for sticky header (56 when inside lens to clear the fixed LensHeader) */
  stickyTop?: number;
}

// ============================================================================
// HELPERS
// ============================================================================

/**
 * Format ISO date string to display label.
 * "2026-02-01" → "Sat 1 Feb"
 */
function formatDay(isoDate: string): string {
  const date = new Date(isoDate + 'T00:00:00Z');
  return date.toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    timeZone: 'UTC',
  });
}

/**
 * Convert "HH:MM" time string to minutes-since-midnight.
 * Used for positioning blocks on the 24-hour timeline.
 */
function timeToMinutes(time: string): number {
  const [hh, mm] = time.split(':').map(Number);
  return (hh ?? 0) * 60 + (mm ?? 0);
}

/**
 * Map compliance status to color classes.
 */
function complianceColorClass(
  status: 'compliant' | 'warning' | 'violation'
): string {
  switch (status) {
    case 'violation':
      return 'text-status-critical';
    case 'warning':
      return 'text-status-warning';
    case 'compliant':
    default:
      return 'text-status-success';
  }
}

/**
 * Map compliance status to dot indicator color.
 */
function complianceDotClass(
  status: 'compliant' | 'warning' | 'violation'
): string {
  switch (status) {
    case 'violation':
      return 'bg-status-critical';
    case 'warning':
      return 'bg-status-warning';
    case 'compliant':
    default:
      return 'bg-status-success';
  }
}

// ============================================================================
// VISUAL TIMELINE
// ============================================================================

/**
 * TimelineBar — 24-hour horizontal bar showing rest (green) vs work (gray) blocks.
 *
 * Per plan spec: visual timeline showing rest vs work periods per day.
 * The bar represents 0:00 → 24:00 (1440 minutes).
 * Rest periods are green blocks positioned using CSS percentage widths.
 * Work periods fill the remaining space in gray.
 */
interface TimelineBarProps {
  restPeriods: RestPeriod[];
  complianceStatus: 'compliant' | 'warning' | 'violation';
}

function TimelineBar({ restPeriods, complianceStatus }: TimelineBarProps) {
  const TOTAL_MINUTES = 1440; // 24 hours

  // Build rest segments with percentage positions
  const restSegments = restPeriods.map((period) => {
    const startMins = timeToMinutes(period.start);
    let endMins = timeToMinutes(period.end);

    // Handle overnight periods: e.g., 22:00 → 06:00
    if (endMins <= startMins) {
      endMins += TOTAL_MINUTES;
    }

    const durationMins = Math.min(endMins - startMins, TOTAL_MINUTES);
    const leftPct = (startMins / TOTAL_MINUTES) * 100;
    const widthPct = (durationMins / TOTAL_MINUTES) * 100;

    return {
      leftPct: Math.min(leftPct, 100),
      widthPct: Math.min(widthPct, 100 - leftPct),
      label: `${period.start}–${period.end} (${period.hours}h)`,
    };
  });

  // Color for rest blocks based on compliance
  const restBlockColor =
    complianceStatus === 'violation'
      ? 'bg-status-critical/60'
      : complianceStatus === 'warning'
      ? 'bg-status-warning/60'
      : 'bg-status-success/70';

  return (
    <div
      className="relative h-5 rounded overflow-hidden bg-surface-raised"
      role="img"
      aria-label={`24-hour rest timeline — ${restPeriods.length} rest period${restPeriods.length === 1 ? '' : 's'}`}
    >
      {/* Hour markers at 6-hour intervals */}
      {[6, 12, 18].map((h) => (
        <div
          key={h}
          className="absolute top-0 bottom-0 border-l border-surface-border/30"
          style={{ left: `${(h / 24) * 100}%` }}
          aria-hidden="true"
        />
      ))}

      {/* Rest period blocks (green / amber / red depending on compliance) */}
      {restSegments.map((seg, i) => (
        <div
          key={i}
          className={cn('absolute top-0 bottom-0 rounded-sm', restBlockColor)}
          style={{
            left: `${seg.leftPct}%`,
            width: `${seg.widthPct}%`,
          }}
          title={seg.label}
          aria-label={seg.label}
        />
      ))}

      {/* Hour labels at 0, 6, 12, 18, 24 */}
      <div className="absolute inset-0 flex justify-between px-0.5 pointer-events-none">
        {['0', '6', '12', '18', '24'].map((label) => (
          <span
            key={label}
            className="text-[9px] text-txt-tertiary leading-none self-end mb-0.5"
            aria-hidden="true"
          >
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// DAILY LOG ROW
// ============================================================================

interface DailyLogRowProps {
  entry: DailyLogEntry;
}

function DailyLogRow({ entry }: DailyLogRowProps) {
  const [expanded, setExpanded] = React.useState(false);

  const totalLabel =
    entry.total_rest_hours === 1
      ? '1h rest'
      : `${entry.total_rest_hours}h rest`;

  return (
    <div className="px-5 py-3 border-b border-surface-border-subtle last:border-b-0">
      {/* Row header: day label, compliance dot, hours total, expand toggle */}
      <div
        className="flex items-center gap-3 cursor-pointer select-none"
        onClick={() => setExpanded((e) => !e)}
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setExpanded((prev) => !prev);
          }
        }}
      >
        {/* Compliance dot */}
        <span
          className={cn(
            'inline-block w-2.5 h-2.5 rounded-full flex-shrink-0',
            complianceDotClass(entry.compliance_status)
          )}
          aria-hidden="true"
        />

        {/* Day label */}
        <span className="text-[14px] font-medium text-txt-primary leading-[1.4] w-28 flex-shrink-0">
          {formatDay(entry.record_date)}
        </span>

        {/* Timeline bar — grows to fill remaining space */}
        <div className="flex-1 min-w-0">
          <TimelineBar
            restPeriods={entry.rest_periods}
            complianceStatus={entry.compliance_status}
          />
        </div>

        {/* Hours total */}
        <span
          className={cn(
            'text-[13px] font-medium w-16 text-right flex-shrink-0',
            complianceColorClass(entry.compliance_status)
          )}
        >
          {totalLabel}
        </span>

        {/* Expand chevron */}
        {entry.rest_periods.length > 0 && (
          <span
            className={cn(
              'text-txt-tertiary text-[12px] flex-shrink-0 transition-transform duration-150',
              expanded && 'rotate-90'
            )}
            aria-hidden="true"
          >
            ›
          </span>
        )}
      </div>

      {/* Expanded period details */}
      {expanded && entry.rest_periods.length > 0 && (
        <div className="mt-2 pl-6 space-y-1">
          {entry.rest_periods.map((period, i) => (
            <div key={i} className="flex items-center gap-2 text-[13px] text-txt-secondary">
              <span className="w-2 h-0.5 bg-surface-border-subtle flex-shrink-0" aria-hidden="true" />
              <span>
                {period.start}–{period.end}
              </span>
              <span className="text-txt-tertiary">({period.hours}h)</span>
            </div>
          ))}
        </div>
      )}

      {/* No rest logged state */}
      {entry.rest_periods.length === 0 && (
        <p className="mt-1 pl-6 text-[13px] text-status-critical">No rest logged</p>
      )}
    </div>
  );
}

// ============================================================================
// DAILY LOG SECTION
// ============================================================================

/**
 * DailyLogSection — Shows daily rest periods with 24-hour visual timeline.
 *
 * Per plan spec: visual timeline showing rest vs work periods per day.
 * Each row has a green/amber/red compliance dot, day label, timeline bar, and hours total.
 * Expandable to show individual rest period times.
 *
 * Empty state: contextual message when no daily records are present.
 */
export function DailyLogSection({ entries, stickyTop }: DailyLogSectionProps) {
  return (
    <SectionContainer
      title="Daily Log"
      count={entries.length}
      stickyTop={stickyTop}
    >
      {/* Legend */}
      <div className="flex items-center gap-4 px-5 py-2 border-b border-surface-border-subtle">
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-sm bg-status-success/70" aria-hidden="true" />
          <span className="text-[12px] text-txt-tertiary">Compliant</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-sm bg-status-warning/60" aria-hidden="true" />
          <span className="text-[12px] text-txt-tertiary">Near threshold</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-sm bg-status-critical/60" aria-hidden="true" />
          <span className="text-[12px] text-txt-tertiary">Violation</span>
        </div>
        <div className="ml-auto text-[11px] text-txt-tertiary">0h ··· 6 ··· 12 ··· 18 ··· 24h</div>
      </div>

      {entries.length === 0 ? (
        <div className="py-8 text-center">
          <p className="text-[14px] text-txt-secondary leading-[1.6]">
            No daily records for this period. Hours will appear here once logged.
          </p>
        </div>
      ) : (
        <div className="-mx-4">
          {entries.map((entry) => (
            <DailyLogRow key={entry.id} entry={entry} />
          ))}
        </div>
      )}
    </SectionContainer>
  );
}

export default DailyLogSection;
