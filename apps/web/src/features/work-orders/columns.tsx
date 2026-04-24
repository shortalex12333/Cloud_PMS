'use client';

/**
 * WORK_ORDER_COLUMNS — work-order column spec for the shared EntityTableList.
 *
 * Spec: /Users/celeste7/Desktop/lens_card_upgrades.md:492 + 506-522
 * Cohort component: apps/web/src/features/entity-list/components/EntityTableList.tsx
 * Reference integration: apps/web/src/components/shopping-list/ShoppingListTableList.tsx
 *
 * Column order is fixed by the UX sheet:
 *   W/O Code · Title · Priority · Equipment · Assigned · Severity · Type ·
 *   Status · Created · Frequency · Due · Completed
 *
 * Sort semantics:
 *   - Text columns return a lowercased string (or null → end-of-list).
 *   - Priority / Severity / Status use a *deliberate* rank (Emergency < Critical
 *     < Important < Routine) so users see the most-urgent rows at the top of
 *     an ascending sort, not alphabetical noise.
 *   - Dates return the ISO string (lex-sortable); null rows sort to the end.
 *
 * Every style value is a CSS custom property — no hard-coded colours.
 */

import * as React from 'react';
import { type EntityTableColumn } from '@/features/entity-list/components/EntityTableList';
import type { EntityListResult } from '@/features/entity-list/types';

type Row = EntityListResult;

// ── Pullers + formatters ───────────────────────────────────────────────────
// work-order fields reach the table via `workOrderToListResult`
// (apps/web/src/features/work-orders/adapter.ts). Top-level EntityListResult
// exposes a handful of them directly; everything else lives on `row.metadata`.

function meta<T = unknown>(row: Row, key: string): T | undefined {
  const m = row.metadata as Record<string, unknown> | undefined;
  return m?.[key] as T | undefined;
}

function fmtEnum(str?: string | null): string {
  if (!str) return '';
  return str.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDate(iso?: string | null): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '—';
    return d.toISOString().slice(0, 10);
  } catch {
    return '—';
  }
}

// ── Rank arrays (deliberate business order; NOT alphabetical) ──────────────

const PRIORITY_RANK: Record<string, number> = {
  emergency: 0,
  critical: 1,
  important: 2,
  routine: 3,
};

const SEVERITY_RANK: Record<string, number> = {
  critical: 0,
  high: 1,
  warning: 2,
  medium: 3,
  low: 4,
};

const STATUS_RANK: Record<string, number> = {
  // Open-ish / in-flight first, completed/terminal last
  overdue: 0,
  in_progress: 1,
  pending_parts: 2,
  awaiting_parts: 2,
  planned: 3,
  draft: 4,
  open: 5,
  completed: 6,
  closed: 7,
  cancelled: 8,
  archived: 9,
};

// ── Pill palette (tokens only) ─────────────────────────────────────────────

type PillColour = { fg: string; bg: string; bd: string };

const PRIORITY_PILL: Record<string, PillColour> = {
  emergency: { fg: 'var(--red)',    bg: 'var(--red-bg)',    bd: 'var(--red-border)' },
  critical:  { fg: 'var(--red)',    bg: 'var(--red-bg)',    bd: 'var(--red-border)' },
  important: { fg: 'var(--amber)',  bg: 'var(--amber-bg)',  bd: 'var(--amber-border)' },
  routine:   { fg: 'var(--text-tertiary)', bg: 'var(--surface)', bd: 'var(--border-faint)' },
};

const SEVERITY_PILL: Record<string, PillColour> = {
  critical: { fg: 'var(--red)',    bg: 'var(--red-bg)',    bd: 'var(--red-border)' },
  high:     { fg: 'var(--red)',    bg: 'var(--red-bg)',    bd: 'var(--red-border)' },
  warning:  { fg: 'var(--amber)',  bg: 'var(--amber-bg)',  bd: 'var(--amber-border)' },
  medium:   { fg: 'var(--amber)',  bg: 'var(--amber-bg)',  bd: 'var(--amber-border)' },
  low:      { fg: 'var(--text-tertiary)', bg: 'var(--surface)', bd: 'var(--border-faint)' },
};

const STATUS_PILL: Record<string, PillColour> = {
  overdue:         { fg: 'var(--red)',   bg: 'var(--red-bg)',   bd: 'var(--red-border)' },
  in_progress:     { fg: 'var(--amber)', bg: 'var(--amber-bg)', bd: 'var(--amber-border)' },
  pending_parts:   { fg: 'var(--amber)', bg: 'var(--amber-bg)', bd: 'var(--amber-border)' },
  awaiting_parts:  { fg: 'var(--amber)', bg: 'var(--amber-bg)', bd: 'var(--amber-border)' },
  planned:         { fg: 'var(--mark)',  bg: 'var(--teal-bg)',  bd: 'var(--mark-hover)' },
  open:            { fg: 'var(--mark)',  bg: 'var(--teal-bg)',  bd: 'var(--mark-hover)' },
  draft:           { fg: 'var(--text-tertiary)', bg: 'var(--surface)', bd: 'var(--border-faint)' },
  completed:       { fg: 'var(--green)', bg: 'var(--green-bg)', bd: 'var(--green-border)' },
  closed:          { fg: 'var(--green)', bg: 'var(--green-bg)', bd: 'var(--green-border)' },
  cancelled:       { fg: 'var(--text-tertiary)', bg: 'var(--surface)', bd: 'var(--border-faint)' },
  archived:        { fg: 'var(--text-tertiary)', bg: 'var(--surface)', bd: 'var(--border-faint)' },
};

function Pill({
  value,
  palette,
}: {
  value: string;
  palette: Record<string, PillColour>;
}) {
  const key = value.toLowerCase();
  const style = palette[key] ?? {
    fg: 'var(--text-tertiary)',
    bg: 'var(--surface)',
    bd: 'var(--border-faint)',
  };
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        height: 18,
        padding: '0 6px',
        borderRadius: 3,
        fontSize: 9.5,
        fontWeight: 600,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        whiteSpace: 'nowrap',
        color: style.fg,
        background: style.bg,
        border: `1px solid ${style.bd}`,
      }}
    >
      {fmtEnum(value)}
    </span>
  );
}

// ── Column spec ────────────────────────────────────────────────────────────

export const WORK_ORDER_COLUMNS: EntityTableColumn<Row>[] = [
  {
    key: 'wo_code',
    label: 'W/O Code',
    accessor: (r) => r.entityRef ?? '',
    sortAccessor: (r) => (r.entityRef ?? '').toLowerCase() || null,
    mono: true,
    minWidth: 110,
    maxWidth: 150,
  },
  {
    key: 'title',
    label: 'Title',
    accessor: (r) => r.title ?? '',
    sortAccessor: (r) => (r.title ?? '').toLowerCase() || null,
    minWidth: 240,
    maxWidth: 420,
    wrap: true,
  },
  {
    key: 'priority',
    label: 'Priority',
    accessor: (r) => (meta<string>(r, 'priority') ?? '').toString(),
    sortAccessor: (r) => {
      const p = meta<string>(r, 'priority');
      return p ? PRIORITY_RANK[p.toLowerCase()] ?? null : null;
    },
    render: (r) => {
      const p = meta<string>(r, 'priority');
      return p ? <Pill value={p} palette={PRIORITY_PILL} /> : <>—</>;
    },
    minWidth: 100,
  },
  {
    key: 'equipment_name',
    label: 'Equipment',
    accessor: (r) => r.equipmentName ?? meta<string>(r, 'equipment_name') ?? '',
    sortAccessor: (r) =>
      (r.equipmentName ?? meta<string>(r, 'equipment_name') ?? '')
        .toLowerCase() || null,
    minWidth: 160,
    maxWidth: 260,
  },
  {
    key: 'assigned_to',
    label: 'Assigned',
    accessor: (r) => r.assignedTo ?? meta<string>(r, 'assigned_to_name') ?? '',
    sortAccessor: (r) =>
      (r.assignedTo ?? meta<string>(r, 'assigned_to_name') ?? '')
        .toLowerCase() || null,
    minWidth: 130,
    maxWidth: 200,
  },
  {
    key: 'severity',
    label: 'Severity',
    accessor: (r) => (meta<string>(r, 'severity') ?? '').toString(),
    sortAccessor: (r) => {
      const s = meta<string>(r, 'severity');
      return s ? SEVERITY_RANK[s.toLowerCase()] ?? null : null;
    },
    render: (r) => {
      const s = meta<string>(r, 'severity');
      return s ? <Pill value={s} palette={SEVERITY_PILL} /> : <>—</>;
    },
    minWidth: 100,
  },
  {
    key: 'wo_type',
    label: 'Type',
    accessor: (r) => fmtEnum(meta<string>(r, 'wo_type')),
    sortAccessor: (r) =>
      (meta<string>(r, 'wo_type') ?? '').toLowerCase() || null,
    minWidth: 110,
    maxWidth: 140,
  },
  {
    key: 'status',
    label: 'Status',
    accessor: (r) => (meta<string>(r, 'status') ?? '').toString(),
    sortAccessor: (r) => {
      const s = meta<string>(r, 'status');
      return s ? STATUS_RANK[s.toLowerCase()] ?? null : null;
    },
    render: (r) => {
      const s = meta<string>(r, 'status');
      return s ? <Pill value={s} palette={STATUS_PILL} /> : <>—</>;
    },
    minWidth: 120,
  },
  {
    key: 'created_at',
    label: 'Created',
    accessor: (r) => formatDate(meta<string>(r, 'created_at')),
    sortAccessor: (r) => meta<string>(r, 'created_at') ?? null,
    mono: true,
    minWidth: 110,
  },
  {
    key: 'frequency',
    label: 'Freq',
    accessor: (r) => fmtEnum(meta<string>(r, 'frequency')),
    sortAccessor: (r) =>
      (meta<string>(r, 'frequency') ?? '').toLowerCase() || null,
    minWidth: 90,
    maxWidth: 120,
  },
  {
    key: 'due_date',
    label: 'Due',
    accessor: (r) => formatDate(meta<string>(r, 'due_date')),
    sortAccessor: (r) => meta<string>(r, 'due_date') ?? null,
    mono: true,
    minWidth: 110,
  },
  {
    key: 'completed_at',
    label: 'Completed',
    accessor: (r) => formatDate(meta<string>(r, 'completed_at')),
    sortAccessor: (r) => meta<string>(r, 'completed_at') ?? null,
    mono: true,
    minWidth: 110,
  },
];
