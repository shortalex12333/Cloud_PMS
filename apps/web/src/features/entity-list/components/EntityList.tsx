'use client';

import { useEffect, useRef, useCallback, useMemo } from 'react';
import { X } from 'lucide-react';
import SpotlightResultRow from '@/components/spotlight/SpotlightResultRow';
import { useEntityList } from '../hooks/useEntityList';
import { EmptyState } from './EmptyState';
import { applyFilter, getFilterLabel } from '@/lib/filters/execute';
import type { EntityListProps, EntityListResult } from '../types';

// Active filter banner component
function ActiveFilterBanner({
  filterId,
  onClear,
}: {
  filterId: string;
  onClear: () => void;
}) {
  const label = getFilterLabel(filterId);
  if (!label) return null;

  return (
    <div
      className="flex items-center justify-between px-6 py-3 bg-brand-interactive/10 border-b border-brand-interactive/20 shrink-0"
      data-testid="active-filter-banner"
    >
      <div className="flex items-center gap-2">
        <span className="text-xs text-white/60">Filtered by:</span>
        <span className="text-sm font-medium text-brand-interactive">{label}</span>
      </div>
      <button
        onClick={onClear}
        className="flex items-center gap-1 px-2 py-1 text-xs text-white/60 hover:text-white hover:bg-white/5 rounded transition-colors"
        aria-label="Clear filter"
        data-testid="clear-filter-button"
      >
        <X className="w-3 h-3" />
        Clear
      </button>
    </div>
  );
}

// Empty filter state component
function EmptyFilterState({ onClear }: { onClear: () => void }) {
  return (
    <div
      className="flex flex-col items-center justify-center h-full text-center px-6"
      data-testid="empty-filter-state"
    >
      <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4">
        <svg
          width="32"
          height="32"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="text-white/40"
        >
          <path d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-white mb-2">No matching items</h3>
      <p className="text-sm text-white/60 max-w-sm mb-4">
        No items match the current filter criteria.
      </p>
      <button
        onClick={onClear}
        className="px-4 py-2 text-sm text-brand-interactive hover:bg-brand-interactive/10 rounded-lg transition-colors"
      >
        Clear filter
      </button>
    </div>
  );
}

export function EntityList<T extends { id: string }>({
  queryKey,
  fetchFn,
  adapter,
  onSelect,
  selectedId,
  emptyMessage,
  filter,
  filterDomain,
  onClearFilter,
}: EntityListProps<T>) {
  const {
    items,
    rawItems,
    total,
    isLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
    error,
  } = useEntityList({ queryKey, fetchFn, adapter });

  // Apply client-side filtering if filter is specified
  const filteredItems = useMemo(() => {
    if (!filter || !filterDomain || !rawItems) return items;
    // Apply filter to raw items, then adapt
    const filtered = applyFilter(rawItems, filter, filterDomain);
    return filtered.map(adapter);
  }, [items, rawItems, filter, filterDomain, adapter]);

  // Infinite scroll observer
  const observerRef = useRef<IntersectionObserver | null>(null);
  const loadMoreRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (observerRef.current) {
      observerRef.current.disconnect();
    }

    observerRef.current = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      },
      { threshold: 0.1 }
    );

    if (loadMoreRef.current) {
      observerRef.current.observe(loadMoreRef.current);
    }

    return () => {
      observerRef.current?.disconnect();
    };
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  const handleSelect = useCallback((id: string) => {
    onSelect(id);
  }, [onSelect]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
          <p className="text-sm text-white/60">Loading...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-red-400">Failed to load items</p>
      </div>
    );
  }

  // Empty state (no items at all)
  if (items.length === 0) {
    return <EmptyState message={emptyMessage} />;
  }

  // Empty filter state (filter applied but no matches)
  if (filter && filteredItems.length === 0 && onClearFilter) {
    return (
      <div className="flex flex-col h-full">
        <ActiveFilterBanner filterId={filter} onClear={onClearFilter} />
        <EmptyFilterState onClear={onClearFilter} />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Active filter banner */}
      {filter && onClearFilter && (
        <ActiveFilterBanner filterId={filter} onClear={onClearFilter} />
      )}

      {/* Results list */}
      <div className="flex-1 overflow-y-auto">
        {filteredItems.map((item, index) => (
          <SpotlightResultRow
            key={item.id}
            result={item}
            isSelected={item.id === selectedId}
            index={index}
            onClick={() => handleSelect(item.id)}
          />
        ))}

        {/* Infinite scroll trigger */}
        <div ref={loadMoreRef} className="h-4" />

        {/* Loading more indicator */}
        {isFetchingNextPage && (
          <div className="flex items-center justify-center py-4">
            <div className="w-5 h-5 border-2 border-white/20 border-t-white/60 rounded-full animate-spin" />
          </div>
        )}
      </div>
    </div>
  );
}
