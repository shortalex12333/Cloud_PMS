/**
 * CERTIFICATE_COLUMNS — tabulated list-view column spec.
 *
 * Contract: apps/web/src/features/entity-list/components/EntityTableList.tsx
 * Rollout: docs/ongoing_work/documents/ENTITY_TABLE_LIST_SPEC_2026-04-23.md
 * Domain spec: docs/ongoing_work/certificates/CERTIFICATE_FILTER_SPEC_2026_04_23.md
 *
 * Rendered via `FilteredEntityList` when the `tableColumns` prop is passed.
 * Every accessor reads from `row.metadata` (the raw cert row piped through
 * the adapter in `app/certificates/page.tsx`) because the flat
 * `EntityListResult` shape doesn't carry cert-specific DB columns like
 * `issue_date` or `issuing_authority`.
 *
 * Every colour, font and spacing unit in the rendered cells comes from
 * `apps/web/src/styles/tokens.css`. No hex codes, no hardcoded pixel
 * sizes for text — lens.css already sets the base.
 *
 * UUIDs are NEVER surfaced. Only user-legible strings / numbers / dates.
 */
import * as React from 'react';
import type { EntityTableColumn } from '../components/EntityTableList';
import type { EntityListResult } from '../types';

interface CertRow {
  id?: string;
  certificate_number?: string | null;
  certificate_name?: string | null;
  certificate_type?: string | null;
  issuing_authority?: string | null;
  issue_date?: string | null;
  expiry_date?: string | null;
  status?: string | null;
  domain?: 'vessel' | 'crew' | null;
  person_name?: string | null;
}

/** Pull the raw cert row that `certAdapter` tunnels via `metadata`. */
function raw(r: EntityListResult): CertRow {
  return (r.metadata ?? {}) as CertRow;
}

/** Compact ISO date (YYYY-MM-DD) or em-dash. */
function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '—';
    return d.toISOString().slice(0, 10);
  } catch {
    return '—';
  }
}

/** Days from today to ISO date. Negative = already past. Null if no date. */
function daysTo(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return null;
  return Math.ceil((t - Date.now()) / 86_400_000);
}

// ── Cell renderers ──────────────────────────────────────────────────────────

/** Status pill — uses the same token palette as IdentityStrip pills. */
function StatusCell({ status }: { status: string | null | undefined }) {
  if (!status) return <span style={{ color: 'var(--txt-ghost)' }}>—</span>;
  let bg = 'var(--surface-el)';
  let color = 'var(--txt2)';
  let border = 'var(--border-sub)';
  switch (status) {
    case 'valid':
      bg = 'var(--teal-bg)'; color = 'var(--teal)'; border = 'var(--teal-border)'; break;
    case 'expired':
    case 'revoked':
      bg = 'var(--red-bg)'; color = 'var(--red)'; border = 'var(--red-border)'; break;
    case 'suspended':
    case 'expiring_soon':
      bg = 'var(--amber-bg)'; color = 'var(--amber)'; border = 'var(--amber-border)'; break;
    case 'superseded':
      bg = 'var(--surface-el)'; color = 'var(--txt-ghost)'; border = 'var(--border-sub)'; break;
  }
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: 4,
        background: bg,
        color,
        border: `1px solid ${border}`,
        fontSize: 11,
        fontWeight: 500,
        letterSpacing: '0.02em',
        textTransform: 'capitalize',
        whiteSpace: 'nowrap',
      }}
    >
      {status.replace(/_/g, ' ')}
    </span>
  );
}

/** Days-to-expiry chip — red if overdue, amber if <=30d, ghost otherwise. */
function DaysChip({ days }: { days: number | null }) {
  if (days === null) return <span style={{ color: 'var(--txt-ghost)' }}>—</span>;
  const label = days < 0 ? `${Math.abs(days)}d overdue` : `${days}d`;
  let color = 'var(--txt2)';
  if (days < 0) color = 'var(--red)';
  else if (days <= 30) color = 'var(--amber)';
  return <span style={{ color, fontFamily: 'var(--font-mono)', fontSize: 12 }}>{label}</span>;
}

function CategoryCell({ domain }: { domain?: CertRow['domain'] }) {
  if (!domain) return <span style={{ color: 'var(--txt-ghost)' }}>—</span>;
  return (
    <span style={{ color: 'var(--txt2)', fontSize: 13, textTransform: 'capitalize' }}>
      {domain}
    </span>
  );
}

// ── Column spec ─────────────────────────────────────────────────────────────

export const CERTIFICATE_COLUMNS: EntityTableColumn<EntityListResult>[] = [
  {
    key: 'certificate_number',
    label: 'Cert No.',
    accessor: (r) => raw(r).certificate_number ?? '',
    sortAccessor: (r) => (raw(r).certificate_number ?? '').toLowerCase() || null,
    mono: true,
    minWidth: 140,
  },
  {
    key: 'name',
    label: 'Name / Holder',
    accessor: (r) => r.title,
    sortAccessor: (r) => r.title.toLowerCase(),
    wrap: true,
    minWidth: 240,
    maxWidth: 360,
  },
  {
    key: 'certificate_type',
    label: 'Type',
    accessor: (r) => raw(r).certificate_type ?? '',
    sortAccessor: (r) => (raw(r).certificate_type ?? '').toLowerCase() || null,
    minWidth: 110,
  },
  {
    key: 'domain',
    label: 'Category',
    accessor: (r) => raw(r).domain ?? '',
    sortAccessor: (r) => raw(r).domain ?? null,
    render: (r) => <CategoryCell domain={raw(r).domain} />,
    minWidth: 100,
  },
  {
    key: 'issuing_authority',
    label: 'Authority',
    accessor: (r) => raw(r).issuing_authority ?? '',
    sortAccessor: (r) => (raw(r).issuing_authority ?? '').toLowerCase() || null,
    minWidth: 160,
    maxWidth: 220,
  },
  {
    key: 'issue_date',
    label: 'Issued',
    accessor: (r) => fmtDate(raw(r).issue_date),
    sortAccessor: (r) => raw(r).issue_date ?? null,
    mono: true,
    minWidth: 110,
  },
  {
    key: 'expiry_date',
    label: 'Expires',
    accessor: (r) => fmtDate(raw(r).expiry_date),
    sortAccessor: (r) => raw(r).expiry_date ?? null,
    mono: true,
    minWidth: 110,
  },
  {
    key: 'days_to_expiry',
    label: 'Days',
    accessor: (r) => {
      const d = daysTo(raw(r).expiry_date);
      return d === null ? '—' : d;
    },
    sortAccessor: (r) => daysTo(raw(r).expiry_date),
    render: (r) => <DaysChip days={daysTo(raw(r).expiry_date)} />,
    align: 'right',
    mono: true,
    minWidth: 90,
  },
  {
    key: 'status',
    label: 'Status',
    accessor: (r) => raw(r).status ?? r.status ?? '',
    sortAccessor: (r) => (raw(r).status ?? r.status ?? '').toLowerCase() || null,
    render: (r) => <StatusCell status={raw(r).status ?? r.status ?? null} />,
    minWidth: 120,
  },
];
