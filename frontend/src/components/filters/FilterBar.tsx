/**
 * FilterBar Component
 *
 * Container for filter controls and active filter badges
 * Shows applied filters and provides "Clear All" functionality
 */

'use client';

import { FilterBadge } from './FilterBadge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface FilterBarProps {
  activeFilters: Record<string, any>;
  onClearAll: () => void;
  children: React.ReactNode;
  className?: string;
}

/**
 * Formats filter value for display in badge
 */
function formatFilterValue(key: string, value: any): string {
  if (!value) return '';

  // Location filter
  if (key === 'location' && typeof value === 'object') {
    const parts = [];
    if (value.deck) parts.push(value.deck);
    if (value.room) parts.push(value.room);
    if (value.storage) parts.push(value.storage);
    return parts.join(', ') || '';
  }

  // Status filter (array)
  if (key === 'status' && Array.isArray(value)) {
    return value.join(', ');
  }

  // Time range filter
  if (key === 'timeRange' && typeof value === 'object') {
    return `${new Date(value.start).toLocaleDateString()} - ${new Date(value.end).toLocaleDateString()}`;
  }

  // Quantity filter
  if (key === 'quantity' && typeof value === 'object') {
    const op = value.operator === 'lt' ? '<' : value.operator === 'lte' ? '≤' :
               value.operator === 'gt' ? '>' : value.operator === 'gte' ? '≥' :
               value.operator === 'eq' ? '=' : '';
    if (value.operator === 'between' && Array.isArray(value.value)) {
      return `${value.value[0]} - ${value.value[1]}`;
    }
    return `${op} ${value.value}`;
  }

  // Default: stringify
  return String(value);
}

/**
 * Formats filter key for display label
 */
function formatFilterLabel(key: string): string {
  const labels: Record<string, string> = {
    location: 'Location',
    status: 'Status',
    timeRange: 'Date Range',
    quantity: 'Quantity',
    sortBy: 'Sort',
  };
  return labels[key] || key;
}

export function FilterBar({ activeFilters, onClearAll, children, className }: FilterBarProps) {
  // Filter out pagination/sorting from active filters display
  const displayFilters = Object.entries(activeFilters).filter(
    ([key]) => !['page', 'limit', 'sortBy', 'sortOrder'].includes(key)
  );

  const hasActiveFilters = displayFilters.length > 0;

  return (
    <div className={cn('border rounded-lg p-4 mb-4 bg-card', className)}>
      {/* Active Filter Badges */}
      {hasActiveFilters && (
        <div className="flex items-center gap-2 mb-3 flex-wrap">
          <span className="text-sm text-muted-foreground">Active filters:</span>
          {displayFilters.map(([key, value]) => {
            const displayValue = formatFilterValue(key, value);
            if (!displayValue) return null;

            return (
              <FilterBadge
                key={key}
                label={formatFilterLabel(key)}
                value={displayValue}
                onRemove={() => {
                  // This will be handled by parent via clearing individual filter
                  // For now, just clear all since we don't have granular control here
                }}
              />
            );
          })}
          <Button
            variant="ghost"
            size="sm"
            onClick={onClearAll}
            className="text-xs"
          >
            Clear All
          </Button>
        </div>
      )}

      {/* Filter Controls */}
      <div className="flex gap-2 flex-wrap">
        {children}
      </div>
    </div>
  );
}
