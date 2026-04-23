'use client';

/**
 * DocumentsTableList — tabulated list view for /documents.
 *
 * Per doc_cert_ux_change.md (2026-04-23): replace the search-results-style
 * list with a tabulated format where every column is clickable to sort.
 *
 *   Code | Filename | Type | System | OEM | Model | Uploaded by | Size |
 *   Created | Updated
 *
 * Each column header toggles ASC → DESC → unset when clicked. Sort state
 * lives locally in this component (not in the URL) since the full corpus is
 * already in memory — sorting never re-fetches.
 *
 * Row click opens the same EntityDetailOverlay flow the tree view uses.
 *
 * Token-only styling (zero hex / raw rgba / raw px for colours). Uses
 * var(--surface-*) / var(--text-*) / var(--space-*) tokens throughout.
 */

import * as React from 'react';
import type { Doc } from './docTreeBuilder';

export interface DocumentsTableListProps {
  docs: Doc[];
  onSelect: (id: string) => void;
  /** UUID of the currently-selected doc (highlighted row). */
  selectedDocId?: string | null;
  /** Optional loading state — renders a short skeleton. */
  isLoading?: boolean;
}

type SortKey =
  | 'filename'
  | 'doc_type'
  | 'system_type'
  | 'oem'
  | 'model'
  | 'uploaded_by_name'
  | 'size_bytes'
  | 'created_at'
  | 'updated_at';

type SortState = { key: SortKey; dir: 'asc' | 'desc' } | null;

// ── Column spec ──────────────────────────────────────────────────────────
// key        — field on Doc (or derived)
// label      — header cell text
// accessor   — returns the cell's display value
// sortAccessor — returns a sortable primitive (string / number). Null ⇒
//   row sorts to the end regardless of direction (avoids "" polluting the
//   top of asc sorts).
// align      — right for numbers, default for text
const COLUMNS: Array<{
  key: SortKey;
  label: string;
  accessor: (d: Doc) => string | number | null;
  sortAccessor: (d: Doc) => string | number | null;
  align?: 'left' | 'right';
  minWidth?: number;
  mono?: boolean;
}> = [
  {
    key: 'filename',
    label: 'Filename',
    accessor: (d) => d.filename,
    sortAccessor: (d) => (d.filename ?? '').toLowerCase(),
    minWidth: 280,
  },
  {
    key: 'doc_type',
    label: 'Type',
    accessor: (d) => d.doc_type ?? '',
    sortAccessor: (d) => (d.doc_type ?? '').toLowerCase() || null,
    minWidth: 120,
  },
  {
    key: 'system_type',
    label: 'System',
    accessor: (d) => (d as unknown as { system_type?: string | null }).system_type ?? '',
    sortAccessor: (d) => ((d as unknown as { system_type?: string | null }).system_type ?? '').toLowerCase() || null,
    minWidth: 120,
  },
  {
    key: 'oem',
    label: 'OEM',
    accessor: (d) => (d as unknown as { oem?: string | null }).oem ?? '',
    sortAccessor: (d) => ((d as unknown as { oem?: string | null }).oem ?? '').toLowerCase() || null,
    minWidth: 100,
  },
  {
    key: 'model',
    label: 'Model',
    accessor: (d) => (d as unknown as { model?: string | null }).model ?? '',
    sortAccessor: (d) => ((d as unknown as { model?: string | null }).model ?? '').toLowerCase() || null,
    mono: true,
    minWidth: 120,
  },
  {
    key: 'uploaded_by_name',
    label: 'Uploaded by',
    accessor: (d) => d.uploaded_by_name ?? '',
    sortAccessor: (d) => (d.uploaded_by_name ?? '').toLowerCase() || null,
    minWidth: 140,
  },
  {
    key: 'size_bytes',
    label: 'Size',
    accessor: (d) => formatSize(d.size_bytes),
    sortAccessor: (d) => d.size_bytes ?? null,
    align: 'right',
    mono: true,
    minWidth: 80,
  },
  {
    key: 'created_at',
    label: 'Created',
    accessor: (d) => formatDate(d.created_at),
    sortAccessor: (d) => d.created_at ?? null,
    mono: true,
    minWidth: 110,
  },
  {
    key: 'updated_at',
    label: 'Updated',
    accessor: (d) => formatDate(d.updated_at),
    sortAccessor: (d) => d.updated_at ?? null,
    mono: true,
    minWidth: 110,
  },
];

function formatSize(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '—';
    // YYYY-MM-DD (ISO date without time) — keeps the table dense and sortable
    return d.toISOString().slice(0, 10);
  } catch {
    return '—';
  }
}

function compareValues(a: string | number | null, b: string | number | null, dir: 'asc' | 'desc'): number {
  // nulls always sort to the end regardless of direction
  if (a === null && b === null) return 0;
  if (a === null) return 1;
  if (b === null) return -1;
  if (typeof a === 'number' && typeof b === 'number') {
    return dir === 'asc' ? a - b : b - a;
  }
  const sa = String(a);
  const sb = String(b);
  if (sa < sb) return dir === 'asc' ? -1 : 1;
  if (sa > sb) return dir === 'asc' ? 1 : -1;
  return 0;
}

const SORT_KEY = 'celeste:documents:sort';

function loadSort(): SortState {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.sessionStorage.getItem(SORT_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed.key === 'string' && (parsed.dir === 'asc' || parsed.dir === 'desc')) {
      return parsed as SortState;
    }
  } catch {
    /* ignore malformed storage */
  }
  return null;
}

function persistSort(sort: SortState): void {
  if (typeof window === 'undefined') return;
  try {
    if (sort) {
      window.sessionStorage.setItem(SORT_KEY, JSON.stringify(sort));
    } else {
      window.sessionStorage.removeItem(SORT_KEY);
    }
  } catch {
    /* quota / disabled storage — ignore */
  }
}

export default function DocumentsTableList({
  docs,
  onSelect,
  selectedDocId,
  isLoading,
}: DocumentsTableListProps) {
  const [sort, setSort] = React.useState<SortState>(() => loadSort());

  const toggleSort = React.useCallback((key: SortKey) => {
    setSort((prev) => {
      let next: SortState;
      if (!prev || prev.key !== key) next = { key, dir: 'asc' };
      else if (prev.dir === 'asc') next = { key, dir: 'desc' };
      else next = null;
      persistSort(next);
      return next;
    });
  }, []);

  const sorted = React.useMemo(() => {
    if (!sort) return docs;
    const col = COLUMNS.find((c) => c.key === sort.key);
    if (!col) return docs;
    return [...docs].sort((a, b) => compareValues(col.sortAccessor(a), col.sortAccessor(b), sort.dir));
  }, [docs, sort]);

  // ── Rendering ──
  const headerCellStyle: React.CSSProperties = {
    padding: 'var(--space-3) var(--space-4)',
    fontSize: 'var(--font-size-caption)',
    fontWeight: 'var(--font-weight-label)',
    color: 'var(--text-secondary)',
    letterSpacing: 'var(--letter-spacing-label)',
    textAlign: 'left',
    background: 'var(--surface)',
    borderBottom: '1px solid var(--border-sub)',
    position: 'sticky',
    top: 0,
    userSelect: 'none',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
  };

  const cellStyle: React.CSSProperties = {
    padding: 'var(--space-3) var(--space-4)',
    fontSize: 'var(--font-size-body)',
    color: 'var(--text-primary)',
    borderBottom: '1px solid var(--border-faint)',
    verticalAlign: 'top',
  };

  return (
    <div
      role="region"
      aria-label="Documents list"
      style={{
        flex: 1,
        overflow: 'auto',
        background: 'var(--surface-base)',
      }}
    >
      <table
        role="grid"
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontFamily: 'var(--font-sans)',
        }}
      >
        <thead>
          <tr>
            {COLUMNS.map((col) => {
              const active = sort?.key === col.key;
              const arrow = active ? (sort?.dir === 'asc' ? '▲' : '▼') : '';
              return (
                <th
                  key={col.key}
                  scope="col"
                  aria-sort={active ? (sort?.dir === 'asc' ? 'ascending' : 'descending') : 'none'}
                  onClick={() => toggleSort(col.key)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      toggleSort(col.key);
                    }
                  }}
                  tabIndex={0}
                  style={{
                    ...headerCellStyle,
                    textAlign: col.align ?? 'left',
                    minWidth: col.minWidth,
                    color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
                  }}
                >
                  <span style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
                    {col.label}
                    <span
                      aria-hidden
                      style={{
                        fontSize: 9,
                        width: 8,
                        color: active ? 'var(--brand-interactive)' : 'var(--text-tertiary)',
                        opacity: active ? 1 : 0.4,
                      }}
                    >
                      {arrow || '↕'}
                    </span>
                  </span>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {isLoading && docs.length === 0 ? (
            <tr>
              <td colSpan={COLUMNS.length} style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--text-secondary)' }}>
                Loading documents…
              </td>
            </tr>
          ) : sorted.length === 0 ? (
            <tr>
              <td colSpan={COLUMNS.length} style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--text-tertiary)' }}>
                No documents.
              </td>
            </tr>
          ) : (
            sorted.map((doc) => {
              const selected = doc.id === selectedDocId;
              return (
                <tr
                  key={doc.id}
                  onClick={() => onSelect(doc.id)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      onSelect(doc.id);
                    }
                  }}
                  tabIndex={0}
                  role="row"
                  aria-selected={selected}
                  style={{
                    cursor: 'pointer',
                    background: selected ? 'var(--teal-bg)' : 'transparent',
                    transition: 'background var(--duration-fast) var(--ease-out)',
                  }}
                  onMouseEnter={(e) => {
                    if (!selected) e.currentTarget.style.background = 'var(--surface-hover)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = selected ? 'var(--teal-bg)' : 'transparent';
                  }}
                >
                  {COLUMNS.map((col) => {
                    const value = col.accessor(doc);
                    return (
                      <td
                        key={col.key}
                        style={{
                          ...cellStyle,
                          textAlign: col.align ?? 'left',
                          fontFamily: col.mono ? 'var(--font-mono)' : undefined,
                          color: value === '' || value === '—' ? 'var(--text-tertiary)' : cellStyle.color,
                          whiteSpace: col.key === 'filename' ? 'normal' : 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          maxWidth: col.key === 'filename' ? 420 : undefined,
                        }}
                      >
                        {value === '' ? '—' : value}
                      </td>
                    );
                  })}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
