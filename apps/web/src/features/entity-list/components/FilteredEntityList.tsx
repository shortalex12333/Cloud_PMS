'use client';

/**
 * FilteredEntityList — Composite component combining FilterBar + entity list.
 * Queries Supabase directly with server-side filters.
 * Replaces EntityList for pages that need rich filtering.
 */

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useSearchParams } from 'next/navigation';
import { FilterPanel } from './FilterPanel';
import SpotlightResultRow from '@/components/spotlight/SpotlightResultRow';
import { EntityRecordRow, type RecordRowData } from './EntityRecordRow';
import { EmptyState } from './EmptyState';
import { useFilteredEntityList } from '../hooks/useFilteredEntityList';
import type { FilterFieldConfig, ActiveFilters } from '../types/filter-config';
import { isDateRange } from '../types/filter-config';
import { mapLegacyFilter } from '@/lib/filters/mapLegacyFilter';
import type { EntityAdapter, EntityListResult } from '../types';
import { groupByUrgency, SectionHeader } from './UrgencyGroupHeaders';
import { useShellContext } from '@/components/shell/ShellContext';

/** Sort column mapping per domain */
const SORT_PRIORITY_COLUMN: Record<string, string> = {
  'work-orders': 'priority',
  faults: 'severity',
  equipment: 'criticality',
  'shopping-list': 'urgency',
};

const SORT_ALPHA_COLUMN: Record<string, string> = {
  inventory: 'name',
  equipment: 'name',
  'shopping-list': 'part_name',
};

interface FilteredEntityListProps<T extends { id: string }> {
  /** React Query key */
  queryKey: string[];
  /** Supabase table name */
  table: string;
  /** Columns to select */
  columns: string;
  /** Row → list result adapter */
  adapter: EntityAdapter<T>;
  /** Available filter fields */
  filterConfig: FilterFieldConfig[];
  /** Called when user selects an item. yachtId present in overview mode for cross-vessel navigation. */
  onSelect: (id: string, yachtId?: string) => void;
  /** Currently selected item ID */
  selectedId: string | null;
  /** Message when no items exist */
  emptyMessage?: string;
  /** Default sort column */
  sortBy?: string;
  /** Domain slug for FilterPanel (drives domain pills + presets) */
  domain?: string;
}

export function FilteredEntityList<T extends { id: string }>({
  queryKey,
  table,
  columns,
  adapter,
  filterConfig,
  onSelect,
  selectedId,
  emptyMessage,
  sortBy = 'created_at',
  domain,
}: FilteredEntityListProps<T>) {
  const searchParams = useSearchParams();

  // Initialize filters from URL search params
  const [activeFilters, setActiveFilters] = useState<ActiveFilters>(() => {
    const initial: ActiveFilters = {};
    filterConfig.forEach(field => {
      const val = searchParams.get(field.key);
      if (val) {
        if (field.type === 'date-range') {
          const to = searchParams.get(`${field.key}_to`);
          if (to) initial[field.key] = { from: val, to };
        } else {
          initial[field.key] = val;
        }
      }
    });
    // Support legacy ?filter= param from QuickFilter system
    const legacyFilter = searchParams.get('filter');
    if (legacyFilter) {
      const mapped = mapLegacyFilter(legacyFilter);
      if (mapped) Object.assign(initial, mapped);
    }
    return initial;
  });

  // Sort state
  const [currentSortBy, setCurrentSortBy] = useState(sortBy);
  const [currentSortDir, setCurrentSortDir] = useState<'asc' | 'desc'>('desc');

  // Shell context: Subbar search + chip filters
  const shell = useShellContext();

  // Merge Subbar filters into active filters for the query
  const mergedFilters = useMemo(() => {
    const merged = { ...activeFilters };

    // Subbar search → ilike on title (text search)
    if (shell.debouncedQuery) {
      merged['title'] = shell.debouncedQuery;
    }

    // Subbar chip → map to filter field
    if (shell.activeChip && shell.activeChip !== 'All') {
      const chipFilter = mapChipToFilter(shell.activeChip, domain);
      if (chipFilter) {
        merged[chipFilter.key] = chipFilter.value;
      }
    }

    return merged;
  }, [activeFilters, shell.debouncedQuery, shell.activeChip, domain]);

  // Apply shell sort to query sort
  const effectiveSortBy = useMemo(() => {
    if (!shell.activeSort) return currentSortBy;
    return mapSortToColumn(shell.activeSort, domain) || currentSortBy;
  }, [shell.activeSort, currentSortBy, domain]);

  const effectiveSortDir = useMemo((): 'asc' | 'desc' => {
    if (!shell.activeSort) return currentSortDir;
    const s = shell.activeSort.toLowerCase();
    if (s === 'newest') return 'desc';
    if (s === 'name' || s === 'assigned' || s === 'due date' || s === 'expiry date') return 'asc';
    return 'desc';
  }, [shell.activeSort, currentSortDir]);

  // Mobile state
  const [panelOpen, setPanelOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 899px)');
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  const activeDomain = domain || queryKey[0] || '';

  // Derive text fields from filterConfig so the hook uses ilike instead of eq
  // Always include 'title' for Subbar search
  const textFields = useMemo(
    () => {
      const fields = new Set(filterConfig.filter(f => f.type === 'text').map(f => f.key));
      fields.add('title');
      return fields;
    },
    [filterConfig],
  );

  const {
    items,
    total,
    isLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
    error,
  } = useFilteredEntityList({
    queryKey,
    table,
    columns,
    adapter,
    filters: mergedFilters,
    sortBy: effectiveSortBy,
    sortDir: effectiveSortDir,
    textFields,
  });

  // Infinite scroll observer
  const observerRef = useRef<IntersectionObserver | null>(null);
  const loadMoreRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (observerRef.current) observerRef.current.disconnect();
    observerRef.current = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      },
      { threshold: 0.1 }
    );
    if (loadMoreRef.current) observerRef.current.observe(loadMoreRef.current);
    return () => { observerRef.current?.disconnect(); };
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  const handleSelect = useCallback((id: string, yachtId?: string) => { onSelect(id, yachtId); }, [onSelect]);

  // Sort handler
  const handleSortChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    switch (val) {
      case 'newest': setCurrentSortBy('created_at'); setCurrentSortDir('desc'); break;
      case 'oldest': setCurrentSortBy('created_at'); setCurrentSortDir('asc'); break;
      case 'priority': {
        const col = SORT_PRIORITY_COLUMN[activeDomain] || 'created_at';
        setCurrentSortBy(col); setCurrentSortDir('asc'); break;
      }
      case 'alpha': {
        const col = SORT_ALPHA_COLUMN[activeDomain] || 'title';
        setCurrentSortBy(col); setCurrentSortDir('asc'); break;
      }
    }
  }, [activeDomain]);

  // Determine current sort value for select
  const sortValue = useMemo(() => {
    if (currentSortBy === 'created_at' && currentSortDir === 'desc') return 'newest';
    if (currentSortBy === 'created_at' && currentSortDir === 'asc') return 'oldest';
    if (Object.values(SORT_PRIORITY_COLUMN).includes(currentSortBy)) return 'priority';
    return 'alpha';
  }, [currentSortBy, currentSortDir]);

  // Results content
  let resultsContent: React.ReactNode;

  if (isLoading) {
    resultsContent = (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1 }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
          <div style={{ width: 32, height: 32, border: '2px solid var(--border-sub)', borderTopColor: 'var(--txt)', borderRadius: '50%' }} className="animate-spin" />
          <p style={{ fontSize: 13, color: 'var(--txt2)' }}>Loading...</p>
        </div>
      </div>
    );
  } else if (error) {
    resultsContent = (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1 }}>
        <p style={{ color: 'var(--red)', fontSize: 13 }}>Failed to load items</p>
      </div>
    );
  } else if (items.length === 0 && Object.keys(activeFilters).length === 0) {
    resultsContent = <EmptyState message={emptyMessage} />;
  } else if (items.length === 0) {
    resultsContent = (
      <div data-testid="empty-state" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', flex: 1, padding: 40, textAlign: 'center' }}>
        <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--txt3)', marginBottom: 4 }}>No {domain?.replace(/-/g, ' ') || 'records'} match</p>
        <button
          onClick={() => setActiveFilters({})}
          style={{ fontSize: 11, color: 'var(--mark)', background: 'none', border: 'none', cursor: 'pointer', marginTop: 8 }}
        >
          Clear filters
        </button>
      </div>
    );
  } else {
    const renderRow = (item: EntityListResult, index: number) =>
      item.entityRef ? (
        <EntityRecordRow
          key={item.id}
          data={{
            id: item.id,
            entityRef: item.entityRef,
            title: item.title,
            equipmentRef: item.equipmentRef,
            equipmentName: item.equipmentName,
            assignedTo: item.assignedTo,
            meta: item.subtitle,
            status: item.status || '',
            statusVariant: (item.statusVariant || 'open') as RecordRowData['statusVariant'],
            severity: (item.severity || null) as RecordRowData['severity'],
            age: item.age,
            entityType: item.type?.replace('pms_', '') || '',
            vesselName: item.vesselName,
          }}
          onClick={() => handleSelect(item.id, item.yachtId)}
        />
      ) : (
        <SpotlightResultRow
          key={item.id}
          result={item}
          isSelected={item.id === selectedId}
          index={index}
          onClick={() => handleSelect(item.id, item.yachtId)}
        />
      );

    const groups = groupByUrgency(items, domain);

    resultsContent = (
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {groups ? (
          <GroupedList groups={groups} renderRow={renderRow} forceExpand={!!shell.debouncedQuery} />
        ) : (
          items.map(renderRow)
        )}
        <div ref={loadMoreRef} style={{ height: 16 }} />
        {isFetchingNextPage && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
            <div style={{ width: 20, height: 20, border: '2px solid var(--border-sub)', borderTopColor: 'var(--txt2)', borderRadius: '50%' }} className="animate-spin" />
          </div>
        )}
      </div>
    );
  }

  // Mobile overlay backdrop
  const backdrop = isMobile && panelOpen ? (
    <div
      onClick={() => setPanelOpen(false)}
      style={{
        position: 'fixed', inset: 0,
        background: 'var(--overlay-bg, rgba(0,0,0,0.5))', zIndex: 99,
      }}
    />
  ) : null;

  // FilterPanel wrapper — bottom sheet on mobile, side panel on desktop
  const filterPanelWrapper = (
    <div style={isMobile ? {
      position: 'fixed', left: 0, right: 0, bottom: 0,
      maxHeight: '60vh', zIndex: 100,
      borderTopLeftRadius: 8, borderTopRightRadius: 8,
      transform: panelOpen ? 'translateY(0)' : 'translateY(100%)',
      transition: 'transform 200ms ease',
      boxShadow: panelOpen ? '0 -4px 24px rgba(0,0,0,0.3)' : 'none',
      overflowY: 'auto',
    } : undefined}>
      <FilterPanel
        filters={filterConfig}
        activeFilters={activeFilters}
        onChange={setActiveFilters}
        activeDomain={activeDomain}
        totalCount={total}
        isOpen={panelOpen}
        onClose={() => setPanelOpen(false)}
      />
    </div>
  );

  return (
    <div style={{ display: 'flex', height: '100%' }}>
      {backdrop}
      {filterPanelWrapper}

      {/* Results area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--surface-base)' }}>
        {/* Results header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '14px 20px', borderBottom: '1px solid var(--border-faint)', flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {isMobile && (
              <button
                onClick={() => setPanelOpen(true)}
                style={{
                  minHeight: 44, minWidth: 44, display: 'flex',
                  alignItems: 'center', justifyContent: 'center',
                  borderRadius: 8, background: 'none', border: 'none', cursor: 'pointer',
                  color: 'var(--txt2)',
                }}
                aria-label="Toggle filters"
              >
                <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><path d="M3 4h18M7 9h10M10 14h4"/></svg>
              </button>
            )}
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--txt2)' }}>
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--txt)', fontWeight: 700 }}>{total}</span> result{total !== 1 ? 's' : ''}
            </span>
          </div>
          <select
            value={sortValue}
            onChange={handleSortChange}
            style={{
              minHeight: 44, padding: '0 28px 0 12px', borderRadius: 6,
              fontSize: 12, fontWeight: 500,
              background: 'var(--neutral-bg)', color: 'var(--txt2)',
              border: '1px solid var(--border-sub)', cursor: 'pointer',
              WebkitAppearance: 'none', appearance: 'none' as const,
              backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='rgba(255,255,255,0.4)' viewBox='0 0 16 16'%3E%3Cpath d='M4 6l4 4 4-4'/%3E%3C/svg%3E\")",
              backgroundRepeat: 'no-repeat',
              backgroundPosition: 'right 10px center',
            }}
          >
            <option value="newest">Newest</option>
            <option value="oldest">Oldest</option>
            <option value="alpha">Alphabetical</option>
          </select>
        </div>

        {resultsContent}
      </div>
    </div>
  );
}

/** Renders items grouped by urgency tier with collapsible section headers */
function GroupedList({
  groups,
  renderRow,
  forceExpand,
}: {
  groups: ReturnType<typeof groupByUrgency>;
  renderRow: (item: EntityListResult, index: number) => React.ReactNode;
  forceExpand?: boolean;
}) {
  const [collapsed, setCollapsed] = React.useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {};
    groups?.forEach((g) => { if (g.group.collapsed) init[g.group.key] = true; });
    return init;
  });

  if (!groups) return null;

  return (
    <>
      {groups.map((g) => (
        <React.Fragment key={g.group.key}>
          <SectionHeader
            label={g.group.label}
            count={g.items.length}
            colour={g.group.colour}
            collapsed={g.group.collapsed !== undefined ? collapsed[g.group.key] : undefined}
            onToggle={g.group.collapsed !== undefined ? () => setCollapsed((prev) => ({ ...prev, [g.group.key]: !prev[g.group.key] })) : undefined}
          />
          {(forceExpand || !collapsed[g.group.key]) && g.items.map(renderRow)}
        </React.Fragment>
      ))}
    </>
  );
}

/** Map sort dropdown label to Supabase column name */
function mapSortToColumn(sort: string, domain?: string): string | null {
  const s = sort.toLowerCase();
  if (s === 'newest') return 'created_at';
  if (s === 'urgency') return domain === 'faults' ? 'severity' : 'status';
  if (s === 'severity') return 'severity';
  if (s === 'due date') return 'due_date';
  if (s === 'expiry date') return 'expiry_date';
  if (s === 'assigned') return 'assigned_to';
  if (s === 'name') return 'name';
  if (s === 'equipment') return 'equipment_name';
  if (s === 'location') return 'location';
  if (s === 'stock level') return 'quantity_on_hand';
  return null;
}

/** Map Subbar chip label to a Supabase filter field + value */
function mapChipToFilter(
  chip: string,
  domain?: string
): { key: string; value: string } | null {
  const c = chip.toLowerCase();

  // Status chips (work for most domains)
  if (c === 'open') return { key: 'status', value: 'open' };
  if (c === 'overdue') return { key: 'status', value: 'overdue' };
  if (c === 'in progress') return { key: 'status', value: 'in_progress' };
  if (c === 'completed') return { key: 'status', value: 'completed' };
  if (c === 'cancelled') return { key: 'status', value: 'cancelled' };
  if (c === 'pending') return { key: 'status', value: 'pending' };
  if (c === 'draft') return { key: 'status', value: 'draft' };
  if (c === 'signed') return { key: 'status', value: 'signed' };
  if (c === 'investigating') return { key: 'status', value: 'investigating' };
  if (c === 'resolved') return { key: 'status', value: 'resolved' };

  // Severity chips (faults)
  if (c === 'critical') return { key: 'severity', value: 'critical' };
  if (c === 'high') return { key: 'severity', value: 'high' };
  if (c === 'medium') return { key: 'severity', value: 'medium' };
  if (c === 'low') return { key: 'severity', value: 'low' };

  // Priority chips (work orders)
  if (c === 'emergency') return { key: 'priority', value: 'emergency' };
  if (c === 'routine') return { key: 'priority', value: 'routine' };

  // Assignment chips
  if (c === 'unassigned') return { key: 'assigned_to', value: '' };
  if (c === 'my tasks') return null; // Would need current user ID — skip for now

  // Stock chips (parts)
  if (c === 'zero stock') return { key: '_stock_status', value: 'out' };
  if (c === 'low stock') return { key: '_stock_status', value: 'low' };

  // Domain-specific text search chips
  if (c === 'engine' || c === 'pending parts') return { key: 'title', value: chip };

  return null;
}
