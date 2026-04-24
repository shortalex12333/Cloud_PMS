// apps/web/src/features/work-orders/__tests__/useMonthWorkOrders.test.ts
//
// Pure helper coverage for useMonthWorkOrders. The hook itself is
// integration-tested implicitly via WorkOrderCalendar consumer; these tests
// lock the date-bucketing primitives that both rely on.

import { describe, it, expect } from 'vitest';
import {
  toISODate,
  firstOfMonth,
  lastOfMonth,
  recordDueDateKey,
  type WorkOrderCalendarRecord,
} from '../useMonthWorkOrders';

describe('toISODate', () => {
  it('formats local date as YYYY-MM-DD with zero padding', () => {
    // Construct using local-time components so the test is TZ-stable.
    expect(toISODate(new Date(2026, 0, 1))).toBe('2026-01-01');
    expect(toISODate(new Date(2026, 8, 9))).toBe('2026-09-09');
    expect(toISODate(new Date(2026, 11, 31))).toBe('2026-12-31');
  });
});

describe('firstOfMonth / lastOfMonth', () => {
  it('firstOfMonth returns the 1st at midnight local', () => {
    const d = firstOfMonth(new Date(2026, 3, 17));
    expect(d.getDate()).toBe(1);
    expect(d.getMonth()).toBe(3);
    expect(d.getFullYear()).toBe(2026);
  });

  it('lastOfMonth returns the calendar-last day', () => {
    expect(lastOfMonth(new Date(2026, 1, 15)).getDate()).toBe(28); // Feb 2026 (non-leap)
    expect(lastOfMonth(new Date(2028, 1, 15)).getDate()).toBe(29); // Feb 2028 (leap)
    expect(lastOfMonth(new Date(2026, 3, 1)).getDate()).toBe(30);  // April → 30 days
    expect(lastOfMonth(new Date(2026, 11, 15)).getDate()).toBe(31); // December → 31
  });
});

describe('recordDueDateKey', () => {
  function rec(due_date: string | null | undefined): WorkOrderCalendarRecord {
    return {
      id: 'x',
      title: 't',
      due_date,
    } as WorkOrderCalendarRecord;
  }

  it('returns null when due_date is absent / null / empty string', () => {
    expect(recordDueDateKey(rec(null))).toBeNull();
    expect(recordDueDateKey(rec(undefined))).toBeNull();
    // @ts-expect-error — intentional empty-string test
    expect(recordDueDateKey(rec(''))).toBeNull();
  });

  it('trims ISO timestamps down to YYYY-MM-DD', () => {
    expect(recordDueDateKey(rec('2026-04-20'))).toBe('2026-04-20');
    expect(recordDueDateKey(rec('2026-04-20T14:30:00Z'))).toBe('2026-04-20');
    expect(recordDueDateKey(rec('2026-04-20T00:00:00.123+02:00'))).toBe('2026-04-20');
  });
});
