/**
 * PURCHASE_ORDER_COLUMNS — column spec for the shared EntityTableList.
 *
 * One file per lens, matches the pattern from DOCUMENTS04
 * (DOCUMENT_COLUMNS) per the spec at
 * docs/ongoing_work/documents/ENTITY_TABLE_LIST_SPEC_2026-04-23.md.
 *
 * Accessors read from EntityListResult — FilteredEntityList passes each
 * row through poAdapter in apps/web/src/app/purchasing/page.tsx first.
 * Domain-specific fields (supplier_name, currency, total_amount, ordered_at,
 * received_at, expected_delivery) live on `metadata` because
 * EntityListResult only standardises a small set of top-level keys.
 */

import * as React from 'react';
import type { EntityTableColumn } from '@/features/entity-list/components/EntityTableList';
import type { EntityListResult } from '@/features/entity-list/types';

// ── Helpers ────────────────────────────────────────────────────────────────

function meta(row: EntityListResult, key: string): string {
  const v = row.metadata?.[key];
  return typeof v === 'string' && v.length > 0 ? v : '';
}

function metaNumber(row: EntityListResult, key: string): number | null {
  const v = row.metadata?.[key];
  return typeof v === 'number' && !isNaN(v) ? v : null;
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    return d.toISOString().slice(0, 10);
  } catch {
    return '';
  }
}

function formatAmount(row: EntityListResult): string {
  const total = metaNumber(row, 'total_amount');
  if (total == null) return '';
  const currency = meta(row, 'currency') || 'USD';
  const symbol = currency === 'EUR' ? '€' : currency === 'GBP' ? '£' : '$';
  return `${symbol}${total.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })}`;
}

// Status pill — same palette as EntityRecordRow + receiving/columns.tsx so
// tabular and card views render identically. Uses tokens only; no hard-coded
// colours per CEO directive.
function StatusPill({ row }: { row: EntityListResult }) {
  const v = row.statusVariant || 'open';
  const palette: Record<string, { bg: string; color: string; border: string }> = {
    overdue:     { bg: 'var(--red-bg)',    color: 'var(--red)',     border: 'var(--red-border)' },
    critical:    { bg: 'var(--red-bg)',    color: 'var(--red)',     border: 'var(--red-border)' },
    due_soon:    { bg: 'var(--amber-bg)',  color: 'var(--amber)',   border: 'var(--amber-border)' },
    warning:     { bg: 'var(--amber-bg)',  color: 'var(--amber)',   border: 'var(--amber-border)' },
    expiring:    { bg: 'var(--amber-bg)',  color: 'var(--amber)',   border: 'var(--amber-border)' },
    draft:       { bg: 'var(--amber-bg)',  color: 'var(--amber)',   border: 'var(--amber-border)' },
    in_progress: { bg: 'var(--teal-bg)',   color: 'var(--mark)',    border: 'var(--mark-hover)' },
    pending:     { bg: 'var(--teal-bg)',   color: 'var(--mark)',    border: 'var(--mark-hover)' },
    completed:   { bg: 'var(--green-bg)',  color: 'var(--green)',   border: 'var(--green-border)' },
    signed:      { bg: 'var(--green-bg)',  color: 'var(--green)',   border: 'var(--green-border)' },
    open:        { bg: 'var(--status-neutral-bg)', color: 'var(--txt3)',      border: 'var(--border-sub)' },
    cancelled:   { bg: 'var(--status-neutral-bg)', color: 'var(--txt-ghost)', border: 'var(--border-faint)' },
  };
  const p = palette[v] || palette.open;
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        height: 17,
        padding: '0 5px',
        borderRadius: 3,
        fontSize: 8.5,
        fontWeight: 600,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        whiteSpace: 'nowrap',
        background: p.bg,
        color: p.color,
        border: `1px solid ${p.border}`,
      }}
    >
      {row.status || '—'}
    </span>
  );
}

// ── Column spec ────────────────────────────────────────────────────────────

export const PURCHASE_ORDER_COLUMNS: EntityTableColumn<EntityListResult>[] = [
  {
    key: 'po_number',
    label: 'PO Number',
    accessor: (r) => r.entityRef || '',
    mono: true,
    minWidth: 130,
  },
  {
    key: 'supplier',
    label: 'Supplier',
    // adapter writes supplier_name (or description fallback) as title
    accessor: (r) => r.title || '',
    minWidth: 200,
    wrap: true,
  },
  {
    key: 'status',
    label: 'Status',
    accessor: (r) => r.status || '',
    render: (r) => <StatusPill row={r} />,
    minWidth: 120,
  },
  {
    key: 'currency',
    label: 'Ccy',
    accessor: (r) => meta(r, 'currency'),
    mono: true,
    minWidth: 60,
  },
  {
    key: 'items',
    label: 'Items',
    accessor: (r) => {
      const n = metaNumber(r, 'item_count');
      return n == null ? '' : String(n);
    },
    sortAccessor: (r) => metaNumber(r, 'item_count'),
    mono: true,
    minWidth: 60,
    align: 'right',
  },
  {
    key: 'total',
    label: 'Total',
    accessor: (r) => formatAmount(r),
    sortAccessor: (r) => metaNumber(r, 'total_amount'),
    mono: true,
    minWidth: 100,
    align: 'right',
  },
  {
    key: 'requester',
    label: 'Requested By',
    accessor: (r) => meta(r, 'ordered_by_name'),
    minWidth: 140,
    wrap: true,
  },
  {
    key: 'ordered_at',
    label: 'Ordered',
    accessor: (r) => formatDate(meta(r, 'ordered_at')),
    sortAccessor: (r) => meta(r, 'ordered_at') || null,
    mono: true,
    minWidth: 110,
  },
  {
    key: 'received_at',
    label: 'Received',
    accessor: (r) => formatDate(meta(r, 'received_at')),
    sortAccessor: (r) => meta(r, 'received_at') || null,
    mono: true,
    minWidth: 110,
  },
  {
    key: 'created_at',
    label: 'Created',
    accessor: (r) => formatDate(meta(r, 'created_at')),
    sortAccessor: (r) => meta(r, 'created_at') || null,
    mono: true,
    minWidth: 110,
    align: 'right',
  },
];
