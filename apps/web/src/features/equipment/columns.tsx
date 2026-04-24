/**
 * EQUIPMENT_COLUMNS — tabulated list-view column spec for /equipment.
 *
 * Contract: apps/web/src/features/entity-list/components/EntityTableList.tsx
 * Pattern: mirrors certificate-columns.tsx (Pattern B — accessors off metadata).
 * Pill idiom: ported from ShoppingListTableList (STATUS_PILL_COLOR + Pill fn).
 *
 * Rendered via `FilteredEntityList` when the `tableColumns` prop is passed
 * from `app/equipment/page.tsx`. Every accessor reads from `row.metadata`
 * (the equipment row piped through `equipmentToListResult`) because
 * `EntityListResult` doesn't carry equipment-specific DB columns.
 *
 * Tokens only — no raw hex, no named colours, no inline rgba. See
 * apps/web/src/styles/tokens.css. This constraint is a CEO standing rule.
 */
import * as React from 'react';
import type { EntityTableColumn } from '../entity-list/components/EntityTableList';
import type { EntityListResult } from '../entity-list/types';
import { formatRelativeTime } from '@/lib/utils';

// ── Metadata shape (matches equipmentToListResult's metadata block) ─────────

interface EquipmentRowMeta {
  code?: string | null;
  system_type?: string | null;
  manufacturer?: string | null;
  model?: string | null;
  criticality?: string | null;
  status?: string | null;
  running_hours?: number | null;
  location?: string | null;
  deleted_at?: string | null;
  updated_at?: string | null;
}

function meta(r: EntityListResult): EquipmentRowMeta {
  return (r.metadata ?? {}) as EquipmentRowMeta;
}

function isArchived(r: EntityListResult): boolean {
  return Boolean(meta(r).deleted_at);
}

// ── Sort ranks (deliberate order — failed/critical first, then degrading) ───

const CRITICALITY_RANK: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

const STATUS_RANK: Record<string, number> = {
  failed: 0,
  degraded: 1,
  maintenance: 2,
  operational: 3,
  decommissioned: 4,
};

// ── Pill palette (token-only, mirrors shopping list idiom) ──────────────────

interface PillStyle { fg: string; bg: string; bd: string }

const CRITICALITY_PILL: Record<string, PillStyle> = {
  critical: { fg: 'var(--red)',            bg: 'var(--red-bg)',    bd: 'var(--red-border)' },
  high:     { fg: 'var(--amber)',          bg: 'var(--amber-bg)',  bd: 'var(--amber-border)' },
  medium:   { fg: 'var(--text-tertiary)',  bg: 'var(--surface)',   bd: 'var(--border-faint)' },
  low:      { fg: 'var(--text-tertiary)',  bg: 'var(--surface)',   bd: 'var(--border-faint)' },
};

const STATUS_PILL: Record<string, PillStyle> = {
  failed:          { fg: 'var(--red)',            bg: 'var(--red-bg)',    bd: 'var(--red-border)' },
  degraded:        { fg: 'var(--amber)',          bg: 'var(--amber-bg)',  bd: 'var(--amber-border)' },
  maintenance:     { fg: 'var(--mark)',           bg: 'var(--teal-bg)',   bd: 'var(--mark-hover)' },
  operational:     { fg: 'var(--green)',          bg: 'var(--green-bg)',  bd: 'var(--green-border)' },
  decommissioned:  { fg: 'var(--text-tertiary)',  bg: 'var(--surface)',   bd: 'var(--border-faint)' },
};

const ARCHIVED_PILL: PillStyle = {
  fg: 'var(--text-tertiary)',
  bg: 'var(--surface)',
  bd: 'var(--border-faint)',
};

function fmtEnum(v: string): string {
  return v.replace(/_/g, ' ');
}

function Pill({ value, palette }: { value: string; palette: Record<string, PillStyle> }) {
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

function ArchivedBadge() {
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
        color: ARCHIVED_PILL.fg,
        background: ARCHIVED_PILL.bg,
        border: `1px solid ${ARCHIVED_PILL.bd}`,
      }}
    >
      Archived
    </span>
  );
}

// ── Accessor helpers ────────────────────────────────────────────────────────

function codeOf(r: EntityListResult): string | null {
  // Prefer top-level entityRef (adapter sets this from equipment_number);
  // fall back to metadata.code for the enriched-view path.
  const top = r.entityRef && r.entityRef.trim() ? r.entityRef : null;
  if (top) return top;
  const m = meta(r).code;
  return m && m.trim() ? m : null;
}

function updatedAtOf(r: EntityListResult): string | null {
  const m = meta(r);
  // EntityListResult doesn't carry a flat updatedAt; the adapter tunnels
  // it via metadata.updated_at (and falls through to created_at).
  return m.updated_at ?? (m as { created_at?: string | null }).created_at ?? null;
}

// ── Cell renderers (row-aware so they can apply archived-row treatment) ─────

function NameCell({ row }: { row: EntityListResult }) {
  const archived = isArchived(row);
  return (
    <span
      style={{
        textDecoration: archived ? 'line-through' : 'none',
        color: archived ? 'var(--text-tertiary)' : 'var(--text-primary)',
        opacity: archived ? 0.6 : 1,
      }}
    >
      {row.title}
    </span>
  );
}

/** Wrap any plain-text accessor so archived rows get reduced opacity. */
function DimIfArchived({ row, children }: { row: EntityListResult; children: React.ReactNode }) {
  const archived = isArchived(row);
  if (!archived) return <>{children}</>;
  return (
    <span style={{ opacity: 0.6, color: 'var(--text-tertiary)' }}>{children}</span>
  );
}

function textOrDash(v: string | number | null | undefined): React.ReactNode {
  if (v === null || v === undefined || v === '') {
    return <span style={{ color: 'var(--text-tertiary)' }}>—</span>;
  }
  return <>{v}</>;
}

function StatusCell({ row }: { row: EntityListResult }) {
  if (isArchived(row)) return <ArchivedBadge />;
  const v = meta(row).status;
  if (!v) return <span style={{ color: 'var(--text-tertiary)' }}>—</span>;
  return <Pill value={v} palette={STATUS_PILL} />;
}

function CriticalityCell({ row }: { row: EntityListResult }) {
  const v = meta(row).criticality;
  if (!v) return <span style={{ color: 'var(--text-tertiary)' }}>—</span>;
  const archived = isArchived(row);
  return (
    <span style={{ opacity: archived ? 0.6 : 1 }}>
      <Pill value={v} palette={CRITICALITY_PILL} />
    </span>
  );
}

function UpdatedCell({ row }: { row: EntityListResult }) {
  const iso = updatedAtOf(row);
  if (!iso) return <span style={{ color: 'var(--text-tertiary)' }}>—</span>;
  return <DimIfArchived row={row}><span>{formatRelativeTime(iso)}</span></DimIfArchived>;
}

// ── Column spec ─────────────────────────────────────────────────────────────

export const EQUIPMENT_COLUMNS: EntityTableColumn<EntityListResult>[] = [
  {
    key: 'code',
    label: 'Code',
    accessor: (r) => codeOf(r) ?? '',
    sortAccessor: (r) => {
      const c = codeOf(r);
      return c ? c.toLowerCase() : null;
    },
    render: (r) => <DimIfArchived row={r}>{textOrDash(codeOf(r))}</DimIfArchived>,
    mono: true,
    minWidth: 110,
  },
  {
    key: 'name',
    label: 'Name',
    accessor: (r) => r.title,
    sortAccessor: (r) => r.title.toLowerCase(),
    render: (r) => <NameCell row={r} />,
    wrap: true,
    minWidth: 240,
    maxWidth: 520,
  },
  {
    key: 'system_type',
    label: 'System',
    accessor: (r) => meta(r).system_type ?? '',
    sortAccessor: (r) => {
      const v = meta(r).system_type;
      return v ? v.toLowerCase() : null;
    },
    render: (r) => <DimIfArchived row={r}>{textOrDash(meta(r).system_type)}</DimIfArchived>,
    minWidth: 120,
  },
  {
    key: 'manufacturer',
    label: 'Manufacturer',
    accessor: (r) => meta(r).manufacturer ?? '',
    sortAccessor: (r) => {
      const v = meta(r).manufacturer;
      return v ? v.toLowerCase() : null;
    },
    render: (r) => <DimIfArchived row={r}>{textOrDash(meta(r).manufacturer)}</DimIfArchived>,
    minWidth: 140,
    maxWidth: 220,
  },
  {
    key: 'model',
    label: 'Model',
    accessor: (r) => meta(r).model ?? '',
    sortAccessor: (r) => {
      const v = meta(r).model;
      return v ? v.toLowerCase() : null;
    },
    render: (r) => <DimIfArchived row={r}>{textOrDash(meta(r).model)}</DimIfArchived>,
    mono: true,
    minWidth: 120,
    maxWidth: 200,
  },
  {
    key: 'criticality',
    label: 'Criticality',
    accessor: (r) => meta(r).criticality ?? '',
    sortAccessor: (r) => {
      const v = meta(r).criticality;
      if (!v) return null;
      const rank = CRITICALITY_RANK[v.toLowerCase()];
      return rank === undefined ? null : rank;
    },
    render: (r) => <CriticalityCell row={r} />,
    minWidth: 110,
  },
  {
    key: 'status',
    label: 'Status',
    accessor: (r) => meta(r).status ?? r.status ?? '',
    sortAccessor: (r) => {
      if (isArchived(r)) return null;
      const v = meta(r).status ?? r.status;
      if (!v) return null;
      const rank = STATUS_RANK[v.toLowerCase()];
      return rank === undefined ? null : rank;
    },
    render: (r) => <StatusCell row={r} />,
    minWidth: 130,
  },
  {
    key: 'running_hours',
    label: 'Hrs',
    accessor: (r) => {
      const v = meta(r).running_hours;
      return v === null || v === undefined ? '' : v;
    },
    sortAccessor: (r) => {
      const v = meta(r).running_hours;
      if (v === null || v === undefined) return null;
      const n = typeof v === 'number' ? v : Number(v);
      return Number.isFinite(n) ? n : null;
    },
    align: 'right',
    mono: true,
    minWidth: 80,
    render: (r) => {
      const v = meta(r).running_hours;
      return (
        <DimIfArchived row={r}>
          {textOrDash(v === null || v === undefined ? '' : v)}
        </DimIfArchived>
      );
    },
  },
  {
    key: 'location',
    label: 'Location',
    accessor: (r) => meta(r).location ?? '',
    sortAccessor: (r) => {
      const v = meta(r).location;
      return v ? v.toLowerCase() : null;
    },
    render: (r) => <DimIfArchived row={r}>{textOrDash(meta(r).location)}</DimIfArchived>,
    minWidth: 140,
    maxWidth: 220,
  },
  {
    key: 'updated_at',
    label: 'Updated',
    accessor: (r) => updatedAtOf(r) ?? '',
    sortAccessor: (r) => updatedAtOf(r) ?? null,
    render: (r) => <UpdatedCell row={r} />,
    align: 'right',
    mono: true,
    minWidth: 120,
  },
];
