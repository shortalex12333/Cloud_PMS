/**
 * Receiving Results List
 *
 * Displays receiving/delivery search results with:
 * - Status filter chips (Draft, Accepted, Rejected, In Review)
 * - Table/list view with vendor, reference, status, date, total
 * - Item contains search filter
 * - Click to view details in ContextPanel
 */

'use client';

import { useState, useMemo } from 'react';
import { Package, Calendar, DollarSign, Filter, Search, Eye, List } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ReceivingResult {
  id: string;
  vendor_name?: string;
  vendor_reference?: string;
  status: 'draft' | 'in_review' | 'accepted' | 'rejected';
  received_date?: string;
  total?: number;
  currency?: string;
  item_names?: string[];  // Line item descriptions
  linked_work_order_id?: string;
  // From raw_data/metadata
  notes?: string;
  received_by?: string;
}

interface ReceivingResultsListProps {
  results: ReceivingResult[];
  onResultClick?: (result: ReceivingResult) => void;
  onViewItems?: (receivingId: string) => void;
}

export function ReceivingResultsList({
  results,
  onResultClick,
  onViewItems,
}: ReceivingResultsListProps) {
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [itemSearchFilter, setItemSearchFilter] = useState('');

  // Filter results by status and item search
  const filteredResults = useMemo(() => {
    let filtered = results;

    // Apply status filter
    if (statusFilter) {
      filtered = filtered.filter((r) => r.status === statusFilter);
    }

    // Apply item search filter
    if (itemSearchFilter) {
      const search = itemSearchFilter.toLowerCase();
      filtered = filtered.filter((r) =>
        r.item_names?.some((item) => item.toLowerCase().includes(search))
      );
    }

    return filtered;
  }, [results, statusFilter, itemSearchFilter]);

  // Count by status
  const statusCounts = useMemo(() => {
    const counts = {
      draft: 0,
      in_review: 0,
      accepted: 0,
      rejected: 0,
    };

    results.forEach((r) => {
      counts[r.status] = (counts[r.status] || 0) + 1;
    });

    return counts;
  }, [results]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'accepted':
        return 'bg-restricted-green-100 text-restricted-green-800 border-restricted-green-200';
      case 'rejected':
        return 'bg-restricted-red-100 text-restricted-red-800 border-restricted-red-200';
      case 'in_review':
        return 'bg-restricted-yellow-100 text-restricted-yellow-800 border-restricted-yellow-200';
      case 'draft':
      default:
        return 'bg-celeste-bg-secondary text-celeste-bg-tertiary border-celeste-border';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'in_review':
        return 'In Review';
      case 'accepted':
        return 'Accepted';
      case 'rejected':
        return 'Rejected';
      case 'draft':
      default:
        return 'Draft';
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  const formatCurrency = (amount?: number, currency?: string) => {
    if (amount === undefined || amount === null) return null;
    const formatted = amount.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
    return currency ? `${currency} ${formatted}` : `$${formatted}`;
  };

  return (
    <div className="w-full space-y-4">
      {/* Banner: Status Filters */}
      <div className="flex items-center gap-2 flex-wrap p-3 bg-muted/50 rounded-lg border border-border">
        <Filter className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm font-medium text-foreground">Filter:</span>

        <button
          onClick={() => setStatusFilter(null)}
          className={cn(
            'px-3 py-1 text-xs rounded-full border transition-colors',
            statusFilter === null
              ? 'bg-primary text-primary-foreground border-primary'
              : 'bg-background text-muted-foreground border-border hover:bg-accent'
          )}
        >
          All ({results.length})
        </button>

        <button
          onClick={() => setStatusFilter('draft')}
          className={cn(
            'px-3 py-1 text-xs rounded-full border transition-colors',
            statusFilter === 'draft'
              ? 'bg-celeste-text-secondary text-celeste-text-title border-celeste-text-secondary'
              : 'bg-celeste-bg-secondary text-celeste-text-secondary border-celeste-border hover:bg-celeste-border'
          )}
        >
          Draft ({statusCounts.draft})
        </button>

        <button
          onClick={() => setStatusFilter('in_review')}
          className={cn(
            'px-3 py-1 text-xs rounded-full border transition-colors',
            statusFilter === 'in_review'
              ? 'bg-restricted-yellow-600 text-celeste-text-title border-restricted-yellow-700'
              : 'bg-restricted-yellow-100 text-restricted-yellow-700 border-restricted-yellow-200 hover:bg-restricted-yellow-200'
          )}
        >
          In Review ({statusCounts.in_review})
        </button>

        <button
          onClick={() => setStatusFilter('accepted')}
          className={cn(
            'px-3 py-1 text-xs rounded-full border transition-colors',
            statusFilter === 'accepted'
              ? 'bg-restricted-green-600 text-celeste-text-title border-restricted-green-700'
              : 'bg-restricted-green-100 text-restricted-green-700 border-restricted-green-200 hover:bg-restricted-green-200'
          )}
        >
          Accepted ({statusCounts.accepted})
        </button>

        <button
          onClick={() => setStatusFilter('rejected')}
          className={cn(
            'px-3 py-1 text-xs rounded-full border transition-colors',
            statusFilter === 'rejected'
              ? 'bg-restricted-red-600 text-celeste-text-title border-restricted-red-700'
              : 'bg-restricted-red-100 text-restricted-red-700 border-restricted-red-200 hover:bg-restricted-red-200'
          )}
        >
          Rejected ({statusCounts.rejected})
        </button>
      </div>

      {/* Item Contains Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Filter by item name (e.g., fuel filter)..."
          value={itemSearchFilter}
          onChange={(e) => setItemSearchFilter(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        />
      </div>

      {/* Results Table */}
      <div className="border border-border rounded-lg overflow-hidden">
        {filteredResults.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            <Package className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">No deliveries match your filters</p>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {filteredResults.map((result) => (
              <div
                key={result.id}
                className="p-4 hover:bg-accent/50 transition-colors cursor-pointer"
                onClick={() => onResultClick?.(result)}
              >
                <div className="flex items-start justify-between gap-4">
                  {/* Left: Vendor & Reference */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Package className="h-4 w-4 text-primary flex-shrink-0" />
                      <h4 className="font-medium text-foreground truncate">
                        {result.vendor_name || 'Unknown Vendor'}
                      </h4>
                    </div>

                    {result.vendor_reference && (
                      <p className="text-sm text-muted-foreground mb-2">
                        Ref: {result.vendor_reference}
                      </p>
                    )}

                    {/* Item Names Preview */}
                    {result.item_names && result.item_names.length > 0 && (
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <List className="h-3 w-3" />
                        <span>
                          {result.item_names.slice(0, 2).join(', ')}
                          {result.item_names.length > 2 && ` +${result.item_names.length - 2} more`}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Middle: Status & Date */}
                  <div className="flex flex-col items-end gap-2">
                    <span
                      className={cn(
                        'px-2 py-1 text-xs font-medium rounded-full border',
                        getStatusBadge(result.status)
                      )}
                    >
                      {getStatusLabel(result.status)}
                    </span>

                    {result.received_date && (
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Calendar className="h-3 w-3" />
                        {formatDate(result.received_date)}
                      </div>
                    )}
                  </div>

                  {/* Right: Total & Actions */}
                  <div className="flex flex-col items-end gap-2">
                    {result.total !== undefined && result.total !== null && (
                      <div className="flex items-center gap-1 text-sm font-medium text-foreground">
                        <DollarSign className="h-4 w-4 text-restricted-green-600" />
                        {formatCurrency(result.total, result.currency)}
                      </div>
                    )}

                    <div className="flex gap-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onResultClick?.(result);
                        }}
                        className="px-2 py-1 text-xs bg-primary text-primary-foreground rounded hover:bg-primary/90 transition-colors flex items-center gap-1"
                      >
                        <Eye className="h-3 w-3" />
                        View
                      </button>

                      {result.item_names && result.item_names.length > 0 && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onViewItems?.(result.id);
                          }}
                          className="px-2 py-1 text-xs bg-secondary text-secondary-foreground rounded hover:bg-secondary/90 transition-colors flex items-center gap-1"
                        >
                          <List className="h-3 w-3" />
                          Items
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Results Summary */}
      <div className="text-xs text-muted-foreground text-center">
        Showing {filteredResults.length} of {results.length} deliveries
      </div>
    </div>
  );
}
