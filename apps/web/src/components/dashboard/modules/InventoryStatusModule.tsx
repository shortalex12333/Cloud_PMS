'use client';

/**
 * InventoryStatusModule
 * Parts inventory health for Control Center
 * Connected to real dashboard data via useDashboardData hook
 */

import React from 'react';
import { Package, AlertTriangle, TrendingDown, CheckCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import ModuleContainer, { ModuleItem, StatCard, ProgressBar } from './ModuleContainer';
import { ActionButton } from '@/components/actions/ActionButton';
import { useInventoryData, InventoryItem, InventoryStats } from '@/hooks/useDashboardData';

// ============================================================================
// TYPES
// ============================================================================

interface InventoryStatusModuleProps {
  isExpanded: boolean;
  onToggle: () => void;
  className?: string;
  items?: InventoryItem[];
  stats?: InventoryStats;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function InventoryStatusModule({
  isExpanded,
  onToggle,
  className,
  items: propItems,
  stats: propStats,
}: InventoryStatusModuleProps) {
  // Use hook data unless props are provided
  const hookData = useInventoryData();

  const items = propItems ?? hookData.items;
  const stats = propStats ?? hookData.stats;
  const isLoading = !propItems && hookData.isLoading;

  // Filter to only show items that need attention
  const lowStockItems = items.filter(item => item.status === 'low' || item.status === 'out_of_stock' || item.status === 'critical');
  const inStock = stats.totalParts - stats.lowStock - stats.outOfStock;

  const overallStatus = stats.outOfStock > 10 ? 'critical' : stats.lowStock > 30 ? 'warning' : 'healthy';
  const stockHealth = stats.totalParts > 0 ? Math.round((inStock / stats.totalParts) * 100) : 0;

  return (
    <ModuleContainer
      title="Inventory"
      icon={<Package className="h-4.5 w-4.5 text-emerald-500" />}
      isExpanded={isExpanded}
      onToggle={onToggle}
      status={overallStatus}
      statusLabel={`${stats.lowStock} items low stock`}
      badge={stats.lowStock + stats.outOfStock}
      collapsedContent={
        <div className="flex items-center gap-3">
          <ProgressBar value={stockHealth} status={overallStatus} />
          <span className="text-[11px] text-zinc-500">{stockHealth}% stocked</span>
        </div>
      }
      className={className}
    >
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-5 w-5 text-zinc-400 animate-spin" />
        </div>
      ) : (
        <>
          {/* Stats */}
          <div className="grid grid-cols-3 gap-2 mb-4">
            <StatCard label="In Stock" value={inStock} status="healthy" />
            <StatCard label="Low Stock" value={stats.lowStock} status="warning" />
            <StatCard label="Out of Stock" value={stats.outOfStock} status={stats.outOfStock > 0 ? 'critical' : 'neutral'} />
          </div>

          {/* Critical items */}
          <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500 mb-2">
            Requires Attention
          </p>
          <div className="space-y-1">
            {lowStockItems.map((item) => (
              <ModuleItem
                key={item.id}
                icon={
                  item.status === 'out_of_stock' ? (
                    <AlertTriangle className="h-4 w-4 text-red-500" />
                  ) : (
                    <TrendingDown className="h-4 w-4 text-amber-500" />
                  )
                }
                title={item.name}
                subtitle={`${item.partNumber} · ${item.location}`}
                status={item.status === 'out_of_stock' ? 'critical' : 'warning'}
                value={`${item.quantity}/${item.minStock}`}
                onClick={() => console.log('View part:', item.id)}
                actions={
                  <ActionButton
                    action="order_part"
                    context={{ part_id: item.id }}
                    size="sm"
                    iconOnly
                    onSuccess={() => hookData.refresh?.()}
                  />
                }
              />
            ))}
          </div>

          {/* Pending orders note */}
          {stats.pendingOrders > 0 && (
            <div className={cn(
              'mt-3 px-3 py-2 rounded-lg',
              'bg-blue-50 dark:bg-blue-900/20',
              'text-[12px] text-blue-600 dark:text-blue-400'
            )}>
              {stats.pendingOrders} orders pending delivery
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-2 mt-4">
            <ActionButton
              action="add_part"
              size="sm"
              onSuccess={() => hookData.refresh?.()}
            />
            <button className={cn(
              'px-3 py-1.5 rounded-lg',
              'text-[12px] font-medium',
              'text-blue-500 hover:text-blue-600',
              'hover:bg-blue-50 dark:hover:bg-blue-900/20',
              'transition-colors'
            )}>
              View inventory →
            </button>
          </div>
        </>
      )}
    </ModuleContainer>
  );
}
