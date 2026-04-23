'use client';

/**
 * EntityTableList — shared tabulated list view used by every domain lens.
 *
 * Replaces the SpotlightResultRow-style card lists per CEO directive
 * 2026-04-23. Every entity lens drops in a column spec and gets:
 *   - Column headers as click-to-sort (asc → desc → unset cycle)
 *   - aria-sort + keyboard nav (Enter/Space on headers, Enter on rows)
 *   - Null values sort to the end regardless of direction (avoids empty
 *     cells polluting the top of asc sorts)
 *   - Per-domain sort state persisted to sessionStorage (survives tab-local
 *     refreshes, cleared on close)
 *   - Sticky header row
 *   - Selected row highlighted via the canonical teal-bg token
 *   - Token-only styling — zero raw hex / raw rgba / raw px colours
 *
 * The component is generic over the row type `T`. Per-lens column specs
 * live alongside each lens's adapter / filter-config (e.g.
 * `apps/web/src/features/entity-list/types/table-config.ts` is the parallel
 * to `filter-config.ts` for column specs).
 *
 * Extracted from DocumentsTableList (2026-04-23) to normalise the pattern
 * across cert / work-orders / receiving / shopping / purchase-orders /
 * warranty / hours-of-rest / handover.
 *
 * See: `docs/ongoing_work/documents/ENTITY_TABLE_LIST_SPEC_2026-04-23.md`
 */

import * as React from 'react';

// ── Types ───────────────────────────────────────────────────────────────────

export interface EntityTableColumn<T> {
  /** Stable key — used for sort state + React list keys. */
  key: string;

  /** Header-cell label. */
  label: string;

  /**
   * How to compute the displayed cell value. Return null or empty string
   * for "no data" and the table will render the em-dash placeholder.
   */
  accessor: (row: T) => string | number | null;

  /**
   * How to compute the sortable value. Defaults to `accessor`. Return null
   * to sort the row to the END regardless of direction — use this for rows
   * where the filter value is missing so they never pollute the top of an
   * ascending sort.
   */
  sortAccessor?: (row: T) => string | number | null;

  /** Optional custom cell renderer. If present, overrides accessor for display. */
  render?: (row: T) => React.ReactNode;

  /** Column horizontal alignment. Default left for text, right for numbers. */
  align?: 'left' | 'right';

  /** Minimum column width in px. */
  minWidth?: number;

  /**
   * If true, the cell is rendered in mono font — use for IDs, codes,
   * timestamps, file sizes, any column where fixed-width glyphs improve
   * scanability.
   */
  mono?: boolean;

  /**
   * If true, the cell allows natural word-wrap rather than truncating with
   * ellipsis. Usually only set on the primary title column.
   */
  wrap?: boolean;

  /** Optional max width for ellipsis truncation when wrap = false. */
  maxWidth?: number;
}

export interface EntityTableListProps<T extends { id: string }> {
  /** Row data — already fetched & adapted. */
  rows: T[];

  /** Per-lens column specification. */
  columns: EntityTableColumn<T>[];

  /**
   * Fired when a row is clicked or Enter-pressed. `yachtId` is passed
   * through for fleet-overview (multi-vessel) list modes.
   */
  onSelect: (id: string, yachtId?: string) => void;

  /** UUID of the currently-selected row (highlighted with --teal-bg). */
  selectedId?: string | null;

  /**
   * Domain key used to namespace the sort state in sessionStorage. Should
   * match the frontend domain slug (e.g. 'documents', 'work-orders',
   * 'certificates'). Two lenses using the same domain key would share sort
   * state — don't.
   */
  domain: string;

  /** Optional loading state — shows a centered message when rows is empty. */
  isLoading?: boolean;

  /** Optional override for the "no rows" empty-state copy. */
  emptyMessage?: string;

  /** Optional override for the loading copy. */
  loadingMessage?: string;
}

type SortState = { key: string; dir: 'asc' | 'desc' } | null;

// ── Pure helpers (exported for unit tests) ──────────────────────────────────

/**
 * Compare two sort values with direction. Null/undefined always sort to the
 * end regardless of direction. Numbers compared numerically; everything else
 * lexicographically as strings.
 */
export function compareValues(
  a: string | number | null | undefined,
  b: string | number | null | undefined,
  dir: 'asc' | 'desc',
): number {
  const aNil = a === null || a === undefined;
  const bNil = b === null || b === undefined;
  if (aNil && bNil) return 0;
  if (aNil) return 1;
  if (bNil) return -1;
  if (typeof a === 'number' && typeof b === 'number') {
    return dir === 'asc' ? a - b : b - a;
  }
  const sa = String(a);
  const sb = String(b);
  if (sa < sb) return dir === 'asc' ? -1 : 1;
  if (sa > sb) return dir === 'asc' ? 1 : -1;
  return 0;
}

function sortStateKey(domain: string): string {
  return `celeste:${domain}:sort`;
}

function loadSort(domain: string): SortState {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.sessionStorage.getItem(sortStateKey(domain));
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed.key === 'string' && (parsed.dir === 'asc' || parsed.dir === 'desc')) {
      return parsed as SortState;
    }
  } catch {
    /* malformed — ignore */
  }
  return null;
}

function persistSort(domain: string, sort: SortState): void {
  if (typeof window === 'undefined') return;
  try {
    const key = sortStateKey(domain);
    if (sort) {
      window.sessionStorage.setItem(key, JSON.stringify(sort));
    } else {
      window.sessionStorage.removeItem(key);
    }
  } catch {
    /* quota / disabled — ignore */
  }
}

// ── Component ───────────────────────────────────────────────────────────────

export function EntityTableList<T extends { id: string; yachtId?: string }>({
  rows,
  columns,
  onSelect,
  selectedId,
  domain,
  isLoading = false,
  emptyMessage = 'No results.',
  loadingMessage = 'Loading…',
}: EntityTableListProps<T>) {
  const [sort, setSort] = React.useState<SortState>(() => loadSort(domain));

  const toggleSort = React.useCallback(
    (key: string) => {
      setSort((prev) => {
        let next: SortState;
        if (!prev || prev.key !== key) next = { key, dir: 'asc' };
        else if (prev.dir === 'asc') next = { key, dir: 'desc' };
        else next = null;
        persistSort(domain, next);
        return next;
      });
    },
    [domain],
  );

  const sorted = React.useMemo(() => {
    if (!sort) return rows;
    const col = columns.find((c) => c.key === sort.key);
    if (!col) return rows;
    const sortAccessor = col.sortAccessor ?? col.accessor;
    return [...rows].sort((a, b) => compareValues(sortAccessor(a), sortAccessor(b), sort.dir));
  }, [rows, columns, sort]);

  // ── Token-driven style constants ──
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

  const cellStyleBase: React.CSSProperties = {
    padding: 'var(--space-3) var(--space-4)',
    fontSize: 'var(--font-size-body)',
    color: 'var(--text-primary)',
    borderBottom: '1px solid var(--border-faint)',
    verticalAlign: 'top',
  };

  return (
    <div
      role="region"
      aria-label={`${domain} list`}
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
            {columns.map((col) => {
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
          {isLoading && rows.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                style={{
                  padding: 'var(--space-6)',
                  textAlign: 'center',
                  color: 'var(--text-secondary)',
                }}
              >
                {loadingMessage}
              </td>
            </tr>
          ) : sorted.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                style={{
                  padding: 'var(--space-6)',
                  textAlign: 'center',
                  color: 'var(--text-tertiary)',
                }}
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            sorted.map((row) => {
              const selected = row.id === selectedId;
              return (
                <tr
                  key={row.id}
                  onClick={() => onSelect(row.id, row.yachtId)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      onSelect(row.id, row.yachtId);
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
                  {columns.map((col) => {
                    const displayed = col.render ? col.render(row) : col.accessor(row);
                    const isEmpty =
                      displayed === null || displayed === undefined || displayed === '';
                    return (
                      <td
                        key={col.key}
                        style={{
                          ...cellStyleBase,
                          textAlign: col.align ?? 'left',
                          fontFamily: col.mono ? 'var(--font-mono)' : undefined,
                          color: isEmpty ? 'var(--text-tertiary)' : cellStyleBase.color,
                          whiteSpace: col.wrap ? 'normal' : 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          maxWidth: col.maxWidth,
                        }}
                      >
                        {isEmpty ? '—' : displayed}
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
