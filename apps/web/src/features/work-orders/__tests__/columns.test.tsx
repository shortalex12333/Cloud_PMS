// apps/web/src/features/work-orders/__tests__/columns.test.tsx
//
// Unit tests for WORK_ORDER_COLUMNS — pure accessor / sortAccessor logic.
// Render slots intentionally skipped here; they're trivial thin React wrappers
// around accessor output and are covered implicitly by the EntityTableList
// integration test suite used by the cohort (documents/shopping/receiving).

import { describe, it, expect } from 'vitest';
import { WORK_ORDER_COLUMNS } from '../columns';
import type { EntityListResult } from '@/features/entity-list/types';

function row(over: Partial<EntityListResult> & {
  meta?: Record<string, unknown>;
}): EntityListResult {
  return {
    id: over.id ?? 'wo-1',
    type: 'pms_work_orders',
    title: over.title ?? 'Service main engine',
    subtitle: '',
    snippet: '',
    entityRef: over.entityRef,
    equipmentRef: undefined,
    equipmentName: over.equipmentName,
    assignedTo: over.assignedTo,
    status: over.status,
    statusVariant: over.statusVariant,
    severity: over.severity ?? null,
    age: over.age,
    metadata: over.meta ?? {},
  } as EntityListResult;
}

function colByKey(key: string) {
  const c = WORK_ORDER_COLUMNS.find((col) => col.key === key);
  if (!c) throw new Error(`missing column ${key}`);
  return c;
}

describe('WORK_ORDER_COLUMNS', () => {
  it('exposes every UX-sheet column in the spec order', () => {
    expect(WORK_ORDER_COLUMNS.map((c) => c.key)).toEqual([
      'wo_code',
      'title',
      'priority',
      'equipment_name',
      'assigned_to',
      'severity',
      'wo_type',
      'status',
      'created_at',
      'frequency',
      'due_date',
      'completed_at',
    ]);
  });

  it('wo_code pulls from entityRef and sorts lowercased', () => {
    const col = colByKey('wo_code');
    const r = row({ entityRef: 'WO·0074' });
    expect(col.accessor(r)).toBe('WO·0074');
    expect(col.sortAccessor!(r)).toBe('wo·0074');
  });

  it('title wraps and sorts by lowercase, empty → null', () => {
    const col = colByKey('title');
    expect(col.wrap).toBe(true);
    expect(col.sortAccessor!(row({ title: '' }))).toBeNull();
    expect(col.sortAccessor!(row({ title: 'Alpha' }))).toBe('alpha');
  });

  it('priority sort follows deliberate rank (emergency before routine)', () => {
    const col = colByKey('priority');
    const rank = (p: string) =>
      col.sortAccessor!(row({ meta: { priority: p } })) as number | null;
    expect(rank('emergency')).toBeLessThan(rank('routine')!);
    expect(rank('critical')).toBeLessThan(rank('important')!);
    expect(rank('gibberish')).toBeNull();
  });

  it('severity sort rank, null-to-end', () => {
    const col = colByKey('severity');
    const rank = (s: string | undefined) =>
      col.sortAccessor!(row({ meta: { severity: s } }));
    expect(rank('critical')).toBe(0);
    expect(rank('low')).toBe(4);
    expect(rank(undefined)).toBeNull();
  });

  it('status sort puts in_progress above completed, terminal states last', () => {
    const col = colByKey('status');
    const rank = (s: string) =>
      col.sortAccessor!(row({ meta: { status: s } })) as number | null;
    expect(rank('in_progress')).toBeLessThan(rank('completed')!);
    expect(rank('completed')).toBeLessThan(rank('archived')!);
    expect(rank('overdue')).toBeLessThan(rank('in_progress')!);
  });

  it('equipment_name prefers row.equipmentName, falls back to meta', () => {
    const col = colByKey('equipment_name');
    expect(col.accessor(row({ equipmentName: 'Port Gen' }))).toBe('Port Gen');
    expect(
      col.accessor(row({ equipmentName: undefined, meta: { equipment_name: 'Stbd Gen' } })),
    ).toBe('Stbd Gen');
  });

  it('assigned_to prefers assignedTo (adapter-filtered), then meta name', () => {
    const col = colByKey('assigned_to');
    expect(col.accessor(row({ assignedTo: 'Alex Kapranos' }))).toBe('Alex Kapranos');
    expect(
      col.accessor(
        row({ assignedTo: undefined, meta: { assigned_to_name: 'Paul Thomson' } }),
      ),
    ).toBe('Paul Thomson');
  });

  it('wo_type humanises enum and falls back when absent', () => {
    const col = colByKey('wo_type');
    expect(col.accessor(row({ meta: { wo_type: 'scheduled_preventive' } }))).toBe(
      'Scheduled Preventive',
    );
    expect(col.accessor(row({ meta: {} }))).toBe('');
  });

  it('date columns render — when iso missing, else YYYY-MM-DD, sort raw iso', () => {
    const cols = ['created_at', 'due_date', 'completed_at'].map(colByKey);
    for (const col of cols) {
      expect(col.mono).toBe(true);
      expect(col.accessor(row({ meta: {} }))).toBe('—');
      const iso = '2026-03-29T00:00:00Z';
      expect(col.accessor(row({ meta: { [col.key]: iso } }))).toBe('2026-03-29');
      expect(col.sortAccessor!(row({ meta: { [col.key]: iso } }))).toBe(iso);
      expect(col.sortAccessor!(row({ meta: {} }))).toBeNull();
    }
  });

  it('frequency humanises enum, empty stays empty', () => {
    const col = colByKey('frequency');
    expect(col.accessor(row({ meta: { frequency: 'every_quarter' } }))).toBe(
      'Every Quarter',
    );
    expect(col.accessor(row({ meta: {} }))).toBe('');
  });
});
