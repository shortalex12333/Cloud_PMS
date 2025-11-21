// @ts-nocheck - Phase 3: Requires shadcn/ui components and action type updates
/**
 * FaultsListPage
 *
 * Complete faults list view with filtering, sorting, and pagination
 * Demonstrates Phase 3 Core filtering system in action
 */

'use client';

import { useEffect, useState } from 'react';
import { useFilters } from '@/hooks/useFilters';
import { useActionHandler } from '@/hooks/useActionHandler';
import { FilterBar } from '@/components/filters/FilterBar';
import { LocationFilter } from '@/components/filters/LocationFilter';
import { StatusFilter, type StatusOption } from '@/components/filters/StatusFilter';
import { TimeRangeFilter } from '@/components/filters/TimeRangeFilter';
import { Pagination } from '@/components/ui/Pagination';
import { SortControls, type SortField } from '@/components/ui/SortControls';
import { FaultCard } from '@/components/cards/FaultCard';
import { Button } from '@/components/ui/button';
import { Loader2, AlertCircle } from 'lucide-react';

// Fault status options
const STATUS_OPTIONS: StatusOption[] = [
  { value: 'open', label: 'Open', color: 'red' },
  { value: 'in_progress', label: 'In Progress', color: 'yellow' },
  { value: 'resolved', label: 'Resolved', color: 'green' },
  { value: 'closed', label: 'Closed', color: 'gray' },
];

// Sort field options
const SORT_FIELDS: SortField[] = [
  { value: 'created_at', label: 'Date Reported' },
  { value: 'severity', label: 'Severity' },
  { value: 'status', label: 'Status' },
  { value: 'resolved_at', label: 'Resolution Date' },
];

// Location options (would normally come from API)
const LOCATION_OPTIONS = {
  decks: ['Deck 1', 'Deck 2', 'Deck 3', 'Engine Room'],
  rooms: ['Bridge', 'Engine Room', 'Galley', 'Main Salon', 'Crew Mess'],
  storages: [], // Faults don't typically have storage locations
};

export default function FaultsListPage() {
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
  const [faults, setFaults] = useState<any[]>([]);
  const [totalCount, setTotalCount] = useState(0);

  // Fetch faults whenever filters change
  useEffect(() => {
    const fetchFaults = async () => {
      const response = await execute('view_faults_list', {
        parameters: queryParams,
      });

      if (response?.success && response.card) {
        setFaults(response.card.rows || []);
        setTotalCount(response.pagination?.total || 0);
      }
    };

    fetchFaults();
  }, [queryParams, execute]);

  // Loading state
  if (isLoading && faults.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Empty state
  if (!isLoading && faults.length === 0 && !hasActiveFilters) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
        <AlertCircle className="h-16 w-16 text-muted-foreground mb-4" />
        <h3 className="text-lg font-semibold mb-2">No faults reported</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Great news! There are currently no reported faults
        </p>
        <Button onClick={() => execute('report_fault', {})}>
          Report Fault
        </Button>
      </div>
    );
  }

  // Empty state with filters
  if (!isLoading && faults.length === 0 && hasActiveFilters) {
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
          <TimeRangeFilter
            value={filters.timeRange || null}
            onApply={(timeRange) => applyFilter('timeRange', timeRange)}
            onClear={() => clearFilter('timeRange')}
          />
          <SortControls
            sortBy={filters.sortBy || 'created_at'}
            sortOrder={filters.sortOrder || 'desc'}
            sortFields={SORT_FIELDS}
            onSortChange={setSort}
          />
        </FilterBar>

        <div className="flex flex-col items-center justify-center min-h-[300px] text-center">
          <AlertCircle className="h-12 w-12 text-muted-foreground mb-3" />
          <h3 className="text-lg font-semibold mb-2">No faults match your filters</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Try adjusting your filters or clearing them to see all faults
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
          <h1 className="text-3xl font-bold tracking-tight">Faults & Issues</h1>
          <p className="text-muted-foreground">
            Track and manage reported faults across the vessel
          </p>
        </div>
        <Button onClick={() => execute('report_fault', {})}>
          Report Fault
        </Button>
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
        <TimeRangeFilter
          value={filters.timeRange || null}
          onApply={(timeRange) => applyFilter('timeRange', timeRange)}
          onClear={() => clearFilter('timeRange')}
        />
        <SortControls
          sortBy={filters.sortBy || 'created_at'}
          sortOrder={filters.sortOrder || 'desc'}
          sortFields={SORT_FIELDS}
          onSortChange={setSort}
        />
      </FilterBar>

      {/* Faults List */}
      <div className="space-y-3">
        {faults.map((fault) => (
          <FaultCard
            key={fault.id}
            fault={fault}
            actions={[
              'view_fault_details',
              'diagnose_fault',
              'create_work_order',
              'resolve_fault',
            ]}
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
