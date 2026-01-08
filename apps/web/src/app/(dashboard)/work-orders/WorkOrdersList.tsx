// @ts-nocheck - Phase 3: Requires shadcn/ui components
/**
 * WorkOrdersList Client Component
 *
 * Complete work orders list view with filtering, sorting, and pagination
 * Demonstrates Phase 3 Core filtering system with React Query
 */

'use client';

import { useFilters } from '@/hooks/useFilters';
import { useWorkOrdersList } from '@/hooks/useListViews';
import { useActionHandler } from '@/hooks/useActionHandler';
import { FilterBar } from '@/components/filters/FilterBar';
import { StatusFilter, type StatusOption } from '@/components/filters/StatusFilter';
import { TimeRangeFilter } from '@/components/filters/TimeRangeFilter';
import { Pagination } from '@/components/ui/Pagination';
import { SortControls, type SortField } from '@/components/ui/SortControls';
import { WorkOrderCard } from '@/components/cards/WorkOrderCard';
import { Button } from '@/components/ui/button';
import { Loader2, ClipboardList } from 'lucide-react';

// Work order status options
const STATUS_OPTIONS: StatusOption[] = [
  { value: 'pending', label: 'Pending', color: 'gray' },
  { value: 'in_progress', label: 'In Progress', color: 'blue' },
  { value: 'completed', label: 'Completed', color: 'green' },
  { value: 'cancelled', label: 'Cancelled', color: 'red' },
];

// Sort field options
const SORT_FIELDS: SortField[] = [
  { value: 'created_at', label: 'Date Created' },
  { value: 'priority', label: 'Priority' },
  { value: 'status', label: 'Status' },
  { value: 'completed_at', label: 'Completion Date' },
];

export default function WorkOrdersList() {
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

  // Use React Query for data fetching with automatic caching
  const { data, isLoading, error } = useWorkOrdersList(queryParams);

  // Extract work orders and pagination from response
  const workOrders = data?.card?.rows || [];
  const totalCount = data?.pagination?.total || 0;

  // Still need useActionHandler for button actions (create_work_order, etc.)
  const { execute } = useActionHandler();

  // Loading state
  if (isLoading && workOrders.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Empty state
  if (!isLoading && workOrders.length === 0 && !hasActiveFilters) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
        <ClipboardList className="h-16 w-16 text-muted-foreground mb-4" />
        <h3 className="text-lg font-semibold mb-2">No work orders found</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Get started by creating your first work order
        </p>
        <Button onClick={() => execute('create_work_order', {})}>
          Create Work Order
        </Button>
      </div>
    );
  }

  // Empty state with filters
  if (!isLoading && workOrders.length === 0 && hasActiveFilters) {
    return (
      <div className="space-y-4">
        <FilterBar
          activeFilters={filters}
          onClearAll={clearAllFilters}
          className="mb-4"
        >
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
          <ClipboardList className="h-12 w-12 text-muted-foreground mb-3" />
          <h3 className="text-lg font-semibold mb-2">
            No work orders match your filters
          </h3>
          <p className="text-sm text-muted-foreground mb-4">
            Try adjusting your filters or clearing them to see all work orders
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
          <h1 className="text-3xl font-bold tracking-tight">Work Orders</h1>
          <p className="text-muted-foreground">
            Track maintenance tasks and repairs across the vessel
          </p>
        </div>
        <Button onClick={() => execute('create_work_order', {})}>
          Create Work Order
        </Button>
      </div>

      {/* Filters */}
      <FilterBar
        activeFilters={filters}
        onClearAll={clearAllFilters}
        className="mb-4"
      >
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

      {/* Work Orders List */}
      <div className="space-y-3">
        {workOrders.map((wo) => (
          <WorkOrderCard
            key={wo.id}
            workOrder={wo}
            actions={[
              'view_work_order_details',
              'update_work_order_status',
              'assign_work_order',
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
