'use client';

/**
 * WorkOrderCalendar — month-grid calendar view for /work-orders.
 *
 * UX spec: /Users/celeste7/Desktop/lens_card_upgrades.md:455-476.
 *   - Monthly grid, Seahub-style, driven by `due_date`.
 *   - Each WO renders as a coloured chip inside its due-date cell.
 *   - Click a chip → open the existing WO overlay (same `onSelect` the list
 *     view uses — zero UX drift).
 *   - Completed and cancelled WOs stay visible: green shading for completed,
 *     grey+strikethrough for cancelled / deleted. CEO spec line 476:
 *     "IF work order is deleted, in fault, completed etc. STILL SHOW THIS ON
 *      CALENDAR, dont hide it."
 *   - Colour precedence for active WOs: severity > priority. Falls back to
 *     neutral for unknown enums.
 *   - Overflow handling: max 3 chips visible per cell; "+N more" opens an
 *     in-cell expanded list. Simple, mobile-friendly, no multi-day-span bars
 *     (CEO explicit MVP scope — no Apple-Calendar-level overlap solver).
 *
 * 100% tokenised. No third-party calendar lib.
 */

import * as React from 'react';
import {
  toISODate,
  firstOfMonth,
  lastOfMonth,
  recordDueDateKey,
  type WorkOrderCalendarRecord,
} from './useMonthWorkOrders';

// ── Types ──────────────────────────────────────────────────────────────────

export interface WorkOrderCalendarProps {
  records: WorkOrderCalendarRecord[];
  /** The month currently being displayed. */
  currentMonth: Date;
  /** Change month (prev / next / today). */
  onMonthChange: (next: Date) => void;
  /** Click a WO chip → open its overlay. Same handler the list view uses. */
  onSelect: (id: string, yachtId?: string) => void;
  isLoading?: boolean;
  error?: Error | null;
}

// ── Colour precedence (tokens only) ────────────────────────────────────────

type ChipPalette = { fg: string; bg: string; bd: string };

const CHIP_COMPLETED: ChipPalette = {
  fg: 'var(--green)',
  bg: 'var(--green-bg)',
  bd: 'var(--green-border)',
};
const CHIP_TERMINAL: ChipPalette = {
  fg: 'var(--text-tertiary)',
  bg: 'var(--surface)',
  bd: 'var(--border-faint)',
};

const SEVERITY_PALETTE: Record<string, ChipPalette> = {
  critical: { fg: 'var(--red)',   bg: 'var(--red-bg)',   bd: 'var(--red-border)' },
  high:     { fg: 'var(--red)',   bg: 'var(--red-bg)',   bd: 'var(--red-border)' },
  warning:  { fg: 'var(--amber)', bg: 'var(--amber-bg)', bd: 'var(--amber-border)' },
  medium:   { fg: 'var(--amber)', bg: 'var(--amber-bg)', bd: 'var(--amber-border)' },
  low:      { fg: 'var(--text-tertiary)', bg: 'var(--surface)', bd: 'var(--border-faint)' },
};

const PRIORITY_PALETTE: Record<string, ChipPalette> = {
  emergency: { fg: 'var(--red)',   bg: 'var(--red-bg)',   bd: 'var(--red-border)' },
  critical:  { fg: 'var(--red)',   bg: 'var(--red-bg)',   bd: 'var(--red-border)' },
  important: { fg: 'var(--amber)', bg: 'var(--amber-bg)', bd: 'var(--amber-border)' },
  routine:   { fg: 'var(--mark)',  bg: 'var(--teal-bg)',  bd: 'var(--mark-hover)' },
};

const CHIP_NEUTRAL: ChipPalette = {
  fg: 'var(--mark)',
  bg: 'var(--teal-bg)',
  bd: 'var(--mark-hover)',
};

/**
 * Determine the colour palette for a chip. CEO spec (line 476): precedence is
 * severity > priority for active WOs; terminal states override everything.
 */
export function paletteForRecord(r: WorkOrderCalendarRecord): ChipPalette {
  const status = (r.status ?? '').toLowerCase();
  if (status === 'completed' || status === 'closed' || r.completed_at) {
    return CHIP_COMPLETED;
  }
  if (status === 'cancelled' || status === 'archived') {
    return CHIP_TERMINAL;
  }
  const sev = (r.severity ?? '').toLowerCase();
  if (sev && SEVERITY_PALETTE[sev]) return SEVERITY_PALETTE[sev];
  const pri = (r.priority ?? '').toLowerCase();
  if (pri && PRIORITY_PALETTE[pri]) return PRIORITY_PALETTE[pri];
  return CHIP_NEUTRAL;
}

export function isTerminal(r: WorkOrderCalendarRecord): boolean {
  const s = (r.status ?? '').toLowerCase();
  return (
    s === 'completed' ||
    s === 'closed' ||
    s === 'cancelled' ||
    s === 'archived' ||
    Boolean(r.completed_at)
  );
}

// ── Grid helpers ───────────────────────────────────────────────────────────

const WEEKDAY_LABELS_MON_FIRST = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

/**
 * Return 42 date objects covering the month display — six rows of seven days,
 * including trailing days from the previous month and leading days of the
 * next so the grid is always rectangular. Week starts Monday (maritime norm).
 */
export function buildMonthGrid(monthAnchor: Date): Date[] {
  const first = firstOfMonth(monthAnchor);
  // Day-of-week with Monday=0..Sunday=6.
  const dowMonZero = (first.getDay() + 6) % 7;
  const gridStart = new Date(
    first.getFullYear(),
    first.getMonth(),
    1 - dowMonZero,
  );
  const cells: Date[] = [];
  for (let i = 0; i < 42; i++) {
    cells.push(
      new Date(
        gridStart.getFullYear(),
        gridStart.getMonth(),
        gridStart.getDate() + i,
      ),
    );
  }
  return cells;
}

/** Bucket records by their due_date (YYYY-MM-DD). NULL due dates drop silently. */
export function bucketByDueDate(
  records: WorkOrderCalendarRecord[],
): Map<string, WorkOrderCalendarRecord[]> {
  const out = new Map<string, WorkOrderCalendarRecord[]>();
  for (const r of records) {
    const key = recordDueDateKey(r);
    if (!key) continue;
    const list = out.get(key);
    if (list) list.push(r);
    else out.set(key, [r]);
  }
  return out;
}

// ── Component ──────────────────────────────────────────────────────────────

export function WorkOrderCalendar({
  records,
  currentMonth,
  onMonthChange,
  onSelect,
  isLoading,
  error,
}: WorkOrderCalendarProps) {
  const [expandedCell, setExpandedCell] = React.useState<string | null>(null);

  const monthLabel = React.useMemo(
    () =>
      currentMonth.toLocaleDateString('en-GB', {
        month: 'long',
        year: 'numeric',
      }),
    [currentMonth],
  );

  const todayKey = React.useMemo(() => toISODate(new Date()), []);
  const grid = React.useMemo(() => buildMonthGrid(currentMonth), [currentMonth]);
  const buckets = React.useMemo(() => bucketByDueDate(records), [records]);

  const handlePrev = () =>
    onMonthChange(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1));
  const handleNext = () =>
    onMonthChange(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1));
  const handleToday = () => onMonthChange(firstOfMonth(new Date()));

  return (
    <div
      data-testid="wo-calendar"
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: 'var(--surface-base)',
      }}
    >
      {/* Toolbar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '14px 20px',
          borderBottom: '1px solid var(--border-faint)',
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <IconButton aria-label="Previous month" onClick={handlePrev}>
            ‹
          </IconButton>
          <IconButton aria-label="Next month" onClick={handleNext}>
            ›
          </IconButton>
          <button
            type="button"
            onClick={handleToday}
            style={{
              appearance: 'none',
              WebkitAppearance: 'none',
              marginLeft: 8,
              padding: '6px 12px',
              background: 'var(--neutral-bg)',
              border: '1px solid var(--border-sub)',
              borderRadius: 6,
              cursor: 'pointer',
              fontSize: 12,
              fontWeight: 500,
              color: 'var(--txt2)',
            }}
          >
            Today
          </button>
          <span
            style={{
              marginLeft: 16,
              fontSize: 14,
              fontWeight: 600,
              color: 'var(--txt)',
            }}
          >
            {monthLabel}
          </span>
        </div>
        <span style={{ fontSize: 12, color: 'var(--txt3)' }}>
          {isLoading
            ? 'Loading…'
            : `${records.length} work order${records.length === 1 ? '' : 's'} in this month`}
        </span>
      </div>

      {error && (
        <div
          style={{
            padding: '16px 20px',
            fontSize: 12,
            color: 'var(--red)',
            background: 'var(--red-bg)',
            borderBottom: '1px solid var(--red-border)',
          }}
        >
          Failed to load calendar: {error.message}
        </div>
      )}

      {/* Weekday header */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(7, minmax(0, 1fr))',
          borderBottom: '1px solid var(--border-faint)',
          flexShrink: 0,
        }}
      >
        {WEEKDAY_LABELS_MON_FIRST.map((label) => (
          <div
            key={label}
            style={{
              padding: '8px 10px',
              fontSize: 10,
              fontWeight: 600,
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              color: 'var(--txt2)',
              borderRight: '1px solid var(--border-faint)',
            }}
          >
            {label}
          </div>
        ))}
      </div>

      {/* Month grid */}
      <div
        style={{
          flex: 1,
          display: 'grid',
          gridTemplateColumns: 'repeat(7, minmax(0, 1fr))',
          gridTemplateRows: 'repeat(6, minmax(110px, 1fr))',
          overflow: 'auto',
        }}
      >
        {grid.map((day) => {
          const key = toISODate(day);
          const inMonth = day.getMonth() === currentMonth.getMonth();
          const isToday = key === todayKey;
          const dayRecords = buckets.get(key) ?? [];
          const expanded = expandedCell === key;
          return (
            <DayCell
              key={key}
              day={day}
              isoKey={key}
              inMonth={inMonth}
              isToday={isToday}
              records={dayRecords}
              expanded={expanded}
              onToggleExpanded={() =>
                setExpandedCell(expanded ? null : key)
              }
              onSelectRecord={onSelect}
            />
          );
        })}
      </div>
    </div>
  );
}

// ── Day cell ───────────────────────────────────────────────────────────────

const VISIBLE_CHIP_LIMIT = 3;

function DayCell({
  day,
  isoKey,
  inMonth,
  isToday,
  records,
  expanded,
  onToggleExpanded,
  onSelectRecord,
}: {
  day: Date;
  isoKey: string;
  inMonth: boolean;
  isToday: boolean;
  records: WorkOrderCalendarRecord[];
  expanded: boolean;
  onToggleExpanded: () => void;
  onSelectRecord: (id: string, yachtId?: string) => void;
}) {
  const visible = expanded
    ? records
    : records.slice(0, VISIBLE_CHIP_LIMIT);
  const hidden = records.length - visible.length;

  return (
    <div
      data-testid={`wo-calendar-cell-${isoKey}`}
      data-in-month={inMonth}
      data-is-today={isToday}
      style={{
        borderRight: '1px solid var(--border-faint)',
        borderBottom: '1px solid var(--border-faint)',
        padding: 6,
        background: inMonth ? 'var(--surface-base)' : 'var(--neutral-bg)',
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        minHeight: 110,
        position: 'relative',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 2,
        }}
      >
        <span
          style={{
            fontSize: 11,
            fontFamily: 'var(--font-mono)',
            fontWeight: isToday ? 700 : 500,
            color: inMonth
              ? isToday
                ? 'var(--mark)'
                : 'var(--txt)'
              : 'var(--txt3)',
          }}
        >
          {day.getDate()}
        </span>
        {isToday && (
          <span
            style={{
              fontSize: 9,
              fontWeight: 700,
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              color: 'var(--mark)',
            }}
          >
            Today
          </span>
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        {visible.map((r) => (
          <WorkOrderChip key={r.id} record={r} onClick={onSelectRecord} />
        ))}
        {hidden > 0 && !expanded && (
          <button
            type="button"
            onClick={onToggleExpanded}
            style={{
              appearance: 'none',
              WebkitAppearance: 'none',
              background: 'transparent',
              border: '1px dashed var(--border-sub)',
              borderRadius: 3,
              padding: '2px 6px',
              cursor: 'pointer',
              fontSize: 10,
              fontWeight: 600,
              color: 'var(--txt2)',
              alignSelf: 'flex-start',
            }}
          >
            +{hidden} more
          </button>
        )}
        {expanded && records.length > VISIBLE_CHIP_LIMIT && (
          <button
            type="button"
            onClick={onToggleExpanded}
            style={{
              appearance: 'none',
              WebkitAppearance: 'none',
              background: 'transparent',
              border: '1px dashed var(--border-sub)',
              borderRadius: 3,
              padding: '2px 6px',
              cursor: 'pointer',
              fontSize: 10,
              fontWeight: 600,
              color: 'var(--txt2)',
              alignSelf: 'flex-start',
            }}
          >
            Collapse
          </button>
        )}
      </div>
    </div>
  );
}

// ── Chip ───────────────────────────────────────────────────────────────────

function WorkOrderChip({
  record,
  onClick,
}: {
  record: WorkOrderCalendarRecord;
  onClick: (id: string, yachtId?: string) => void;
}) {
  const palette = paletteForRecord(record);
  const terminal = isTerminal(record);
  const ref = record.ref ? `WO·${record.ref}` : '';
  return (
    <button
      type="button"
      onClick={() => onClick(record.id, record.yacht_id)}
      aria-label={`Open ${record.title ?? 'work order'}`}
      title={record.title ?? 'Work order'}
      style={{
        appearance: 'none',
        WebkitAppearance: 'none',
        textAlign: 'left',
        display: 'flex',
        alignItems: 'center',
        gap: 5,
        padding: '3px 6px',
        borderRadius: 3,
        background: palette.bg,
        border: `1px solid ${palette.bd}`,
        color: palette.fg,
        cursor: 'pointer',
        fontSize: 11,
        lineHeight: 1.25,
        textDecoration: terminal ? 'line-through' : undefined,
        opacity: terminal ? 0.78 : 1,
        minWidth: 0,
      }}
    >
      {ref && (
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontWeight: 700,
            fontSize: 10,
            flexShrink: 0,
          }}
        >
          {ref}
        </span>
      )}
      <span
        style={{
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          minWidth: 0,
        }}
      >
        {record.title ?? 'Work order'}
      </span>
    </button>
  );
}

// ── Icon button ────────────────────────────────────────────────────────────

function IconButton({
  children,
  onClick,
  'aria-label': ariaLabel,
}: {
  children: React.ReactNode;
  onClick: () => void;
  'aria-label': string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={ariaLabel}
      style={{
        appearance: 'none',
        WebkitAppearance: 'none',
        width: 32,
        height: 32,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--neutral-bg)',
        border: '1px solid var(--border-sub)',
        borderRadius: 6,
        cursor: 'pointer',
        fontSize: 16,
        fontWeight: 700,
        color: 'var(--txt)',
      }}
    >
      {children}
    </button>
  );
}
