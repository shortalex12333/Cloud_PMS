'use client';

/**
 * ShoppingListTableList — shopping-list-specific column spec + thin wrapper
 * around the shared `EntityTableList` component.
 *
 * Spec: docs/ongoing_work/documents/ENTITY_TABLE_LIST_SPEC_2026-04-23.md
 * Shared component: apps/web/src/features/entity-list/components/EntityTableList.tsx
 *
 * This file defines only:
 *   1. `SHOPPING_LIST_COLUMNS` — the column spec for /shopping-list
 *      (Part # · Item · Status · Urgency · Qty Req · Qty Approved · Source ·
 *       Supplier · Requester · Required By · Created)
 *   2. A thin wrapper component matching the pattern used by DocumentsTableList.
 *
 * Everything generic (sort cycle, aria-sort, keyboard nav, null-to-end,
 * sessionStorage persistence, tokens) lives in EntityTableList.
 *
 * Sort semantics:
 *   - Text columns: sortAccessor returns lowercased-string or null to push
 *     empty values to the end.
 *   - Status / urgency: sortAccessor returns a deliberately-ordered index so
 *     "critical" sorts above "normal", "approved" above "candidate", etc.
 *   - Numeric (qty): sortAccessor returns the raw number or null.
 *   - Dates: sortAccessor returns ISO string (lex-sortable); null to end.
 */

import * as React from 'react';
import {
  EntityTableList,
  type EntityTableColumn,
} from '@/features/entity-list/components/EntityTableList';
import type { EntityListResult } from '@/features/entity-list/types';

// ── Formatters + value pullers ─────────────────────────────────────────────
//
// Shopping list rows reach the table as `EntityListResult` objects produced
// by `shoppingListToListResult` (features/shopping-list/adapter.ts). The
// adapter surfaces the raw DB fields on `item.metadata.*`. Pull from there
// for anything the top-level EntityListResult shape doesn't expose.

type Row = EntityListResult;

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

// ── Status / urgency → sortable rank + pill colour ─────────────────────────
//
// Rank arrays define the *business-meaningful* sort order, not alphabetical.
// Asc: lowest rank first. Desc: highest rank first. Unknown values return
// null so they sort to the end per EntityTableList's contract.

const STATUS_RANK: Record<string, number> = {
  candidate: 0,
  under_review: 1,
  approved: 2,
  ordered: 3,
  partially_fulfilled: 4,
  fulfilled: 5,
  installed: 6,
  rejected: 7, // terminal unhappy path — last
};

const URGENCY_RANK: Record<string, number> = {
  critical: 0,
  high: 1,
  normal: 2,
  low: 3,
};

const STATUS_PILL_COLOR: Record<string, { fg: string; bg: string; bd: string }> = {
  candidate:          { fg: 'var(--text-tertiary)',   bg: 'var(--surface)',      bd: 'var(--border-faint)' },
  under_review:       { fg: 'var(--amber)',           bg: 'var(--amber-bg)',     bd: 'var(--amber-border)' },
  approved:           { fg: 'var(--green)',           bg: 'var(--green-bg)',     bd: 'var(--green-border)' },
  ordered:            { fg: 'var(--mark)',            bg: 'var(--teal-bg)',      bd: 'var(--mark-hover)' },
  partially_fulfilled:{ fg: 'var(--mark)',            bg: 'var(--teal-bg)',      bd: 'var(--mark-hover)' },
  fulfilled:          { fg: 'var(--green)',           bg: 'var(--green-bg)',     bd: 'var(--green-border)' },
  installed:          { fg: 'var(--green)',           bg: 'var(--green-bg)',     bd: 'var(--green-border)' },
  rejected:           { fg: 'var(--red)',             bg: 'var(--red-bg)',       bd: 'var(--red-border)' },
};

const URGENCY_PILL_COLOR: Record<string, { fg: string; bg: string; bd: string }> = {
  critical: { fg: 'var(--red)',    bg: 'var(--red-bg)',    bd: 'var(--red-border)' },
  high:     { fg: 'var(--amber)',  bg: 'var(--amber-bg)',  bd: 'var(--amber-border)' },
  normal:   { fg: 'var(--text-tertiary)', bg: 'var(--surface)', bd: 'var(--border-faint)' },
  low:      { fg: 'var(--text-tertiary)', bg: 'var(--surface)', bd: 'var(--border-faint)' },
};

function Pill({ value, palette }: { value: string; palette: Record<string, { fg: string; bg: string; bd: string }> }) {
  const style = palette[value.toLowerCase()] ?? {
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

export const SHOPPING_LIST_COLUMNS: EntityTableColumn<Row>[] = [
  {
    key: 'part_number',
    label: 'Part #',
    accessor: (r) => r.entityRef ?? '',
    sortAccessor: (r) => (r.entityRef ?? '').toLowerCase() || null,
    mono: true,
    minWidth: 120,
    maxWidth: 160,
  },
  {
    key: 'part_name',
    label: 'Item',
    accessor: (r) => r.title ?? '',
    sortAccessor: (r) => (r.title ?? '').toLowerCase() || null,
    minWidth: 220,
    maxWidth: 360,
    wrap: true,
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
      return s ? <Pill value={s} palette={STATUS_PILL_COLOR} /> : <>—</>;
    },
    minWidth: 130,
  },
  {
    key: 'urgency',
    label: 'Urgency',
    accessor: (r) => (meta<string>(r, 'urgency') ?? '').toString(),
    sortAccessor: (r) => {
      const u = meta<string>(r, 'urgency');
      return u ? URGENCY_RANK[u.toLowerCase()] ?? null : null;
    },
    render: (r) => {
      const u = meta<string>(r, 'urgency');
      return u ? <Pill value={u} palette={URGENCY_PILL_COLOR} /> : <>—</>;
    },
    minWidth: 90,
  },
  {
    key: 'quantity_requested',
    label: 'Qty Req',
    accessor: (r) => {
      const q = meta<number>(r, 'quantity_requested');
      return q != null ? String(q) : '—';
    },
    sortAccessor: (r) => meta<number>(r, 'quantity_requested') ?? null,
    align: 'right',
    mono: true,
    minWidth: 70,
    maxWidth: 90,
  },
  {
    key: 'source_type',
    label: 'Source',
    accessor: (r) => fmtEnum(meta<string>(r, 'source_type')),
    sortAccessor: (r) => (meta<string>(r, 'source_type') ?? '').toLowerCase() || null,
    minWidth: 140,
  },
  {
    key: 'requested_by_name',
    label: 'Requester',
    accessor: (r) => r.assignedTo ?? meta<string>(r, 'requested_by_name') ?? '',
    sortAccessor: (r) => (r.assignedTo ?? meta<string>(r, 'requested_by_name') ?? '').toLowerCase() || null,
    minWidth: 130,
    maxWidth: 180,
  },
  {
    key: 'required_by_date',
    label: 'Required By',
    accessor: (r) => formatDate(meta<string>(r, 'required_by_date')),
    sortAccessor: (r) => meta<string>(r, 'required_by_date') ?? null,
    mono: true,
    minWidth: 110,
  },
  {
    key: 'created_at',
    label: 'Created',
    accessor: (r) => formatDate(meta<string>(r, 'created_at')),
    sortAccessor: (r) => meta<string>(r, 'created_at') ?? null,
    mono: true,
    minWidth: 110,
  },
];

// ── Thin wrapper component ─────────────────────────────────────────────────

export interface ShoppingListTableListProps {
  rows: Row[];
  onSelect: (id: string, yachtId?: string) => void;
  selectedId?: string | null;
  isLoading?: boolean;
}

export default function ShoppingListTableList({
  rows,
  onSelect,
  selectedId,
  isLoading,
}: ShoppingListTableListProps) {
  return (
    <EntityTableList<Row>
      rows={rows}
      columns={SHOPPING_LIST_COLUMNS}
      onSelect={onSelect}
      selectedId={selectedId ?? null}
      domain="shopping-list"
      isLoading={isLoading}
      emptyMessage="No shopping list items."
      loadingMessage="Loading shopping list…"
    />
  );
}
