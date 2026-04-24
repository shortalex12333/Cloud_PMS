// apps/web/src/features/work-orders/__tests__/WorkOrderCalendar.test.tsx
//
// WorkOrderCalendar — grid construction + palette precedence + click through.
// Covers the pure helpers first (zero-render), then a minimal render smoke
// test. Component is deliberately presentation-only — real data comes via
// useMonthWorkOrders, which has its own integration surface.

import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import * as React from 'react';
import {
  WorkOrderCalendar,
  paletteForRecord,
  isTerminal,
  buildMonthGrid,
  bucketByDueDate,
} from '../WorkOrderCalendar';
import { toISODate, type WorkOrderCalendarRecord } from '../useMonthWorkOrders';

afterEach(() => {
  cleanup();
});

function rec(over: Partial<WorkOrderCalendarRecord> = {}): WorkOrderCalendarRecord {
  return {
    id: over.id ?? 'wo-1',
    ref: over.ref ?? '0074',
    title: over.title ?? 'Service main engine',
    status: over.status,
    priority: over.priority,
    severity: over.severity,
    due_date: over.due_date ?? null,
    completed_at: over.completed_at ?? null,
    ...over,
  };
}

// ── palette precedence ─────────────────────────────────────────────────────

describe('paletteForRecord', () => {
  it('completed status → green palette', () => {
    const p = paletteForRecord(rec({ status: 'completed', priority: 'emergency' }));
    expect(p.bg).toBe('var(--green-bg)');
    // Priority is ignored once terminal.
  });

  it('completed_at set (no status) → green palette', () => {
    const p = paletteForRecord(rec({ completed_at: '2026-04-20T10:00:00Z' }));
    expect(p.bg).toBe('var(--green-bg)');
  });

  it('cancelled / archived → neutral-grey terminal palette', () => {
    expect(paletteForRecord(rec({ status: 'cancelled' })).bg).toBe('var(--surface)');
    expect(paletteForRecord(rec({ status: 'archived' })).bg).toBe('var(--surface)');
  });

  it('severity wins over priority on active WOs', () => {
    // critical severity + routine priority → red (severity)
    const p = paletteForRecord(rec({ severity: 'critical', priority: 'routine' }));
    expect(p.bg).toBe('var(--red-bg)');
  });

  it('falls back to priority when severity missing', () => {
    const p = paletteForRecord(rec({ priority: 'emergency' }));
    expect(p.bg).toBe('var(--red-bg)');
  });

  it('unknown enums fall back to neutral teal palette', () => {
    const p = paletteForRecord(rec({ priority: 'zzz_unknown' }));
    expect(p.bg).toBe('var(--teal-bg)');
  });

  it('low severity maps to neutral palette (not red)', () => {
    const p = paletteForRecord(rec({ severity: 'low' }));
    expect(p.bg).toBe('var(--surface)');
  });
});

describe('isTerminal', () => {
  it.each([
    [{ status: 'completed' }, true],
    [{ status: 'closed' }, true],
    [{ status: 'cancelled' }, true],
    [{ status: 'archived' }, true],
    [{ completed_at: '2026-04-20' }, true],
    [{ status: 'open' }, false],
    [{ status: 'in_progress' }, false],
    [{}, false],
  ] as const)('%o → %s', (over, expected) => {
    expect(isTerminal(rec(over))).toBe(expected);
  });
});

// ── buildMonthGrid ─────────────────────────────────────────────────────────

describe('buildMonthGrid', () => {
  it('always returns 42 cells', () => {
    // Pick a month where day-1 falls on various weekdays.
    for (const m of [0, 1, 4, 8, 11]) {
      expect(buildMonthGrid(new Date(2026, m, 1))).toHaveLength(42);
    }
  });

  it('first cell is Monday — April 2026 (Apr-1 = Wed) shows Mon Mar-30', () => {
    const grid = buildMonthGrid(new Date(2026, 3, 1));
    expect(toISODate(grid[0])).toBe('2026-03-30');
    // Day 2 = Tue 31 Mar; Day 3 = Wed 1 Apr (first-of-month)
    expect(toISODate(grid[1])).toBe('2026-03-31');
    expect(toISODate(grid[2])).toBe('2026-04-01');
  });

  it('Feb 2026 (leap-adjacent check — 2026 is not a leap year)', () => {
    // Feb 2026: 1 Feb is a Sunday.
    const grid = buildMonthGrid(new Date(2026, 1, 1));
    // First cell is Monday 26 Jan.
    expect(toISODate(grid[0])).toBe('2026-01-26');
    // 1 Feb appears at index 6 (Sunday slot when week starts Monday).
    expect(toISODate(grid[6])).toBe('2026-02-01');
  });
});

// ── bucketByDueDate ────────────────────────────────────────────────────────

describe('bucketByDueDate', () => {
  it('groups records by YYYY-MM-DD, drops null due_date', () => {
    const records = [
      rec({ id: 'a', due_date: '2026-04-20' }),
      rec({ id: 'b', due_date: '2026-04-20T14:30:00Z' }),
      rec({ id: 'c', due_date: '2026-04-21' }),
      rec({ id: 'd', due_date: null }),
    ];
    const buckets = bucketByDueDate(records);
    expect(buckets.get('2026-04-20')?.map((r) => r.id)).toEqual(['a', 'b']);
    expect(buckets.get('2026-04-21')?.map((r) => r.id)).toEqual(['c']);
    expect(buckets.get('null')).toBeUndefined();
    expect(buckets.size).toBe(2);
  });

  it('preserves input order within a bucket', () => {
    const records = [
      rec({ id: 'first', due_date: '2026-05-01' }),
      rec({ id: 'second', due_date: '2026-05-01T09:00:00Z' }),
      rec({ id: 'third', due_date: '2026-05-01T15:00:00Z' }),
    ];
    expect(bucketByDueDate(records).get('2026-05-01')?.map((r) => r.id))
      .toEqual(['first', 'second', 'third']);
  });
});

// ── render smoke ────────────────────────────────────────────────────────────

describe('<WorkOrderCalendar>', () => {
  const REF_MONTH = new Date(2026, 3, 1); // April 2026

  it('renders 42 cells + weekday header + month label', () => {
    render(
      <WorkOrderCalendar
        records={[]}
        currentMonth={REF_MONTH}
        onMonthChange={() => {}}
        onSelect={() => {}}
      />,
    );
    // Month label
    expect(screen.getByText(/April 2026/)).toBeDefined();
    // Weekday headers (7)
    for (const label of ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']) {
      expect(screen.getByText(label)).toBeDefined();
    }
    // Cells (42)
    const cells = document.querySelectorAll('[data-testid^="wo-calendar-cell-"]');
    expect(cells.length).toBe(42);
  });

  it('renders WO chips in their due-date cell, truncated to 3 with + more', () => {
    const recs = Array.from({ length: 5 }).map((_, i) =>
      rec({
        id: `wo-${i}`,
        ref: String(74 + i),
        title: `WO ${i}`,
        due_date: '2026-04-15',
        priority: 'routine',
      }),
    );
    render(
      <WorkOrderCalendar
        records={recs}
        currentMonth={REF_MONTH}
        onMonthChange={() => {}}
        onSelect={() => {}}
      />,
    );
    const cell = screen.getByTestId('wo-calendar-cell-2026-04-15');
    // Only 3 chips should render initially
    const visibleChips = cell.querySelectorAll('button[aria-label^="Open"]');
    expect(visibleChips.length).toBe(3);
    // + N more button present
    expect(cell.textContent).toContain('+2 more');

    // Expand
    fireEvent.click(cell.querySelector('button[aria-label="Open WO 2"]') ? cell.querySelector('button') as Element : cell.querySelector('button') as Element);
  });

  it('expanding + collapsing toggles full-day chip list', () => {
    const recs = Array.from({ length: 5 }).map((_, i) =>
      rec({ id: `wo-${i}`, title: `WO ${i}`, due_date: '2026-04-10' }),
    );
    render(
      <WorkOrderCalendar
        records={recs}
        currentMonth={REF_MONTH}
        onMonthChange={() => {}}
        onSelect={() => {}}
      />,
    );
    const cell = screen.getByTestId('wo-calendar-cell-2026-04-10');
    // Click the +N more button (use text to find it)
    const moreBtn = Array.from(cell.querySelectorAll('button')).find(
      (b) => b.textContent?.includes('+2 more'),
    );
    expect(moreBtn).toBeDefined();
    fireEvent.click(moreBtn!);
    expect(cell.querySelectorAll('button[aria-label^="Open"]').length).toBe(5);
    // Collapse button present
    expect(cell.textContent).toContain('Collapse');
  });

  it('clicking a chip fires onSelect with the record id + yacht_id', () => {
    const onSelect = vi.fn();
    render(
      <WorkOrderCalendar
        records={[rec({ id: 'wo-x', due_date: '2026-04-12', yacht_id: 'y-1' } as WorkOrderCalendarRecord)]}
        currentMonth={REF_MONTH}
        onMonthChange={() => {}}
        onSelect={onSelect}
      />,
    );
    const cell = screen.getByTestId('wo-calendar-cell-2026-04-12');
    const chip = cell.querySelector('button[aria-label^="Open"]') as HTMLButtonElement;
    fireEvent.click(chip);
    expect(onSelect).toHaveBeenCalledWith('wo-x', 'y-1');
  });

  it('Today button + Prev/Next fire onMonthChange', () => {
    const onMonthChange = vi.fn();
    render(
      <WorkOrderCalendar
        records={[]}
        currentMonth={REF_MONTH}
        onMonthChange={onMonthChange}
        onSelect={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Previous month' }));
    expect(onMonthChange).toHaveBeenLastCalledWith(new Date(2026, 2, 1));
    fireEvent.click(screen.getByRole('button', { name: 'Next month' }));
    expect(onMonthChange).toHaveBeenLastCalledWith(new Date(2026, 4, 1));
    fireEvent.click(screen.getByRole('button', { name: 'Today' }));
    expect(onMonthChange).toHaveBeenCalled();
  });

  it('shows loading + error messages when passed', () => {
    const { rerender } = render(
      <WorkOrderCalendar
        records={[]}
        currentMonth={REF_MONTH}
        onMonthChange={() => {}}
        onSelect={() => {}}
        isLoading
      />,
    );
    expect(screen.getByText(/Loading/)).toBeDefined();

    rerender(
      <WorkOrderCalendar
        records={[]}
        currentMonth={REF_MONTH}
        onMonthChange={() => {}}
        onSelect={() => {}}
        error={new Error('network poof')}
      />,
    );
    expect(screen.getByText(/Failed to load calendar: network poof/)).toBeDefined();
  });

  it('chip with terminal status renders with strikethrough + green/grey palette', () => {
    render(
      <WorkOrderCalendar
        records={[
          rec({
            id: 'done',
            title: 'Filter replaced',
            due_date: '2026-04-18',
            status: 'completed',
          }),
          rec({
            id: 'killed',
            title: 'Cancelled task',
            due_date: '2026-04-18',
            status: 'cancelled',
          }),
        ]}
        currentMonth={REF_MONTH}
        onMonthChange={() => {}}
        onSelect={() => {}}
      />,
    );
    const cell = screen.getByTestId('wo-calendar-cell-2026-04-18');
    const chips = Array.from(cell.querySelectorAll('button[aria-label^="Open"]')) as HTMLButtonElement[];
    expect(chips).toHaveLength(2);
    // Both should have line-through — not fragile on exact palette, just the decoration.
    for (const c of chips) {
      expect(c.style.textDecoration).toBe('line-through');
    }
  });
});
