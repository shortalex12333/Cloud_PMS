/**
 * RECEIVING_COLUMNS — column spec for the shared EntityTableList.
 *
 * One file per lens, matches the pattern from DOCUMENTS04
 * (DOCUMENT_COLUMNS) per the spec at
 * docs/ongoing_work/documents/ENTITY_TABLE_LIST_SPEC_2026-04-23.md.
 *
 * The accessors read from EntityListResult — that's what FilteredEntityList
 * passes through after running each row through the per-lens adapter
 * (`receivingToListResult` for us, see ./adapter.ts). Rich domain fields
 * (vendor_name, po_number, received_date) live on `metadata` because
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

// Status pill — uses the same token map as EntityRecordRow's pill so the
// tabular and card views render identically. No new tokens.
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
    open:        { bg: 'var(--status-neutral-bg)', color: 'var(--txt3)', border: 'var(--border-sub)' },
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

// Business-rank sort for status. Ordering reflects the receiving lifecycle
// (draft → in_review → accepted) so an asc sort puts rows in flow order.
// rejected is the sad-path terminal — sinks to the bottom of asc (rank 99)
// and rises to the top of desc (where the user is most likely scanning for
// recently flagged issues). Pattern shared with SHOPPING05's STATUS_RANK.
const STATUS_RANK: Record<string, number> = {
  draft: 0,
  in_review: 1,
  accepted: 2,
  rejected: 99,
};
function statusRank(row: EntityListResult): number | null {
  const k = (row.metadata?.status as string | undefined) || row.status?.toLowerCase();
  if (!k) return null;
  const v = STATUS_RANK[k];
  return typeof v === 'number' ? v : 50;
}

// ── Column spec ────────────────────────────────────────────────────────────

export const RECEIVING_COLUMNS: EntityTableColumn<EntityListResult>[] = [
  {
    key: 'ref',
    label: 'Ref',
    accessor: (r) => r.entityRef || '',
    mono: true,
    minWidth: 100,
  },
  {
    key: 'vendor',
    label: 'Vendor',
    // adapter sets title = vendor_name (or "Draft Receiving")
    accessor: (r) => r.title || '',
    minWidth: 200,
    wrap: true,
  },
  {
    key: 'po_number',
    label: 'PO Number',
    accessor: (r) => meta(r, 'po_number'),
    sortAccessor: (r) => meta(r, 'po_number') || null,
    mono: true,
    minWidth: 120,
  },
  {
    key: 'status',
    label: 'Status',
    accessor: (r) => r.status || '',
    sortAccessor: statusRank, // business-flow order, not alphabetic
    render: (r) => <StatusPill row={r} />,
    minWidth: 110,
  },
  {
    key: 'received_date',
    label: 'Received',
    accessor: (r) => formatDate(meta(r, 'received_date')),
    sortAccessor: (r) => meta(r, 'received_date') || null,
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
