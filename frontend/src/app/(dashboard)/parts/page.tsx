/**
 * PartsListPage
 *
 * Complete parts list view with filtering, sorting, and pagination
 * Demonstrates Phase 3 Core filtering system in action
 */

'use client';

import { useEffect, useState } from 'react';
import { useFilters } from '@/hooks/useFilters';
import { useActionHandler } from '@/hooks/useActionHandler';
import { FilterBar } from '@/components/filters/FilterBar';
import { LocationFilter } from '@/components/filters/LocationFilter';
import { StatusFilter, type StatusOption } from '@/components/filters/StatusFilter';
import { QuantityFilter } from '@/components/filters/QuantityFilter';
import { Pagination } from '@/components/ui/Pagination';
import { SortControls, type SortField } from '@/components/ui/SortControls';
import { PartCard } from '@/components/cards/PartCard';
import { Button } from '@/components/ui/button';
import { Loader2, PackageSearch } from 'lucide-react';

// Part status options
const STATUS_OPTIONS: StatusOption[] = [
  { value: 'in_stock', label: 'In Stock', color: 'green' },
  { value: 'low_stock', label: 'Low Stock', color: 'yellow' },
  { value: 'out_of_stock', label: 'Out of Stock', color: 'red' },
  { value: 'on_order', label: 'On Order', color: 'blue' },
];

// Sort field options
const SORT_FIELDS: SortField[] = [
  { value: 'created_at', label: 'Date Added' },
  { value: 'part_name', label: 'Part Name' },
  { value: 'stock_quantity', label: 'Stock Quantity' },
  { value: 'unit_cost', label: 'Unit Cost' },
];

// Location options (would normally come from API)
const LOCATION_OPTIONS = {
  decks: ['Deck 1', 'Deck 2', 'Deck 3', 'Engine Room'],
  rooms: ['Storage A', 'Storage B', 'Workshop', 'Lazarette'],
  storages: ['Cabinet 1', 'Cabinet 2', 'Shelf A', 'Shelf B'],
};

export default function PartsListPage() {
  const {
    filters,
    queryParams,
    hasActiveFilters,
    applyFilter,
    clearFilter,
    clearAllFilters,
    setPage,
    setLimit,
    setSort,
  } = useFilters({
    defaultLimit: 50,
    defaultSortBy: 'created_at',
    defaultSortOrder: 'desc',
  });

  const { execute, isLoading } = useActionHandler();
  const [parts, setParts] = useState<any[]>([]);
  const [totalCount, setTotalCount] = useState(0);

  // Fetch parts whenever filters change
  useEffect(() => {
    const fetchParts = async () => {
      const response = await execute('view_parts_list', {
        parameters: queryParams,
      });

      if (response?.success && response.card) {
        setParts(response.card.rows || []);
        setTotalCount(response.pagination?.total || 0);
      }
    };

    fetchParts();
  }, [queryParams, execute]);

  // Loading state
  if (isLoading && parts.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Empty state
  if (!isLoading && parts.length === 0 && !hasActiveFilters) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
        <PackageSearch className="h-16 w-16 text-muted-foreground mb-4" />
        <h3 className="text-lg font-semibold mb-2">No parts found</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Get started by adding your first part to the inventory
        </p>
        <Button onClick={() => execute('add_part', {})}>Add Part</Button>
      </div>
    );
  }

  // Empty state with filters
  if (!isLoading && parts.length === 0 && hasActiveFilters) {
    return (
      <div className="space-y-4">
        <FilterBar
          activeFilters={filters}
          onClearAll={clearAllFilters}
          className="mb-4"
        >
          <LocationFilter
            options={LOCATION_OPTIONS}
            value={filters.location || {}}
            onApply={(location) => applyFilter('location', location)}
            onClear={() => clearFilter('location')}
          />
          <StatusFilter
            options={STATUS_OPTIONS}
            value={filters.status || []}
            onApply={(status) => applyFilter('status', status)}
            onClear={() => clearFilter('status')}
          />
          <QuantityFilter
            label="Stock Quantity"
            value={filters.quantity || null}
            min={0}
            step={1}
            onApply={(quantity) => applyFilter('quantity', quantity)}
            onClear={() => clearFilter('quantity')}
          />
          <SortControls
            sortBy={filters.sortBy || 'created_at'}
            sortOrder={filters.sortOrder || 'desc'}
            sortFields={SORT_FIELDS}
            onSortChange={setSort}
          />
        </FilterBar>

        <div className="flex flex-col items-center justify-center min-h-[300px] text-center">
          <PackageSearch className="h-12 w-12 text-muted-foreground mb-3" />
          <h3 className="text-lg font-semibold mb-2">No parts match your filters</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Try adjusting your filters or clearing them to see all parts
          </p>
          <Button variant="outline" onClick={clearAllFilters}>
            Clear All Filters
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Parts Inventory</h1>
          <p className="text-muted-foreground">
            Manage and track all spare parts across the vessel
          </p>
        </div>
        <Button onClick={() => execute('add_part', {})}>Add Part</Button>
      </div>

      {/* Filters */}
      <FilterBar
        activeFilters={filters}
        onClearAll={clearAllFilters}
        className="mb-4"
      >
        <LocationFilter
          options={LOCATION_OPTIONS}
          value={filters.location || {}}
          onApply={(location) => applyFilter('location', location)}
          onClear={() => clearFilter('location')}
        />
        <StatusFilter
          options={STATUS_OPTIONS}
          value={filters.status || []}
          onApply={(status) => applyFilter('status', status)}
          onClear={() => clearFilter('status')}
        />
        <QuantityFilter
          label="Stock Quantity"
          value={filters.quantity || null}
          min={0}
          step={1}
          onApply={(quantity) => applyFilter('quantity', quantity)}
          onClear={() => clearFilter('quantity')}
        />
        <SortControls
          sortBy={filters.sortBy || 'created_at'}
          sortOrder={filters.sortOrder || 'desc'}
          sortFields={SORT_FIELDS}
          onSortChange={setSort}
        />
      </FilterBar>

      {/* Parts Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {parts.map((part) => (
          <PartCard
            key={part.id}
            part={part}
            actions={['view_part_stock', 'order_part', 'log_part_usage']}
          />
        ))}
      </div>

      {/* Loading overlay */}
      {isLoading && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Pagination */}
      <Pagination
        currentPage={filters.page}
        totalItems={totalCount}
        itemsPerPage={filters.limit}
        onPageChange={setPage}
        onItemsPerPageChange={setLimit}
      />
    </div>
  );
}
