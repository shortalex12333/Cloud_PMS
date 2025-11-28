'use client';

/**
 * InventoryStatusModule
 * Parts inventory health for Control Center
 */

import React from 'react';
import { Package, AlertTriangle, TrendingDown, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import ModuleContainer, { ModuleItem, StatCard, ProgressBar } from './ModuleContainer';
import { MicroactionButton } from '@/components/spotlight';

// ============================================================================
// MOCK DATA
// ============================================================================

const LOW_STOCK_ITEMS = [
  { id: 'P-3512', name: 'Coolant Temperature Sensor', current: 1, min: 3, location: 'A4-12' },
  { id: 'P-2847', name: 'Hydraulic Filter Element', current: 2, min: 4, location: 'B2-08' },
  { id: 'P-1923', name: 'O-Ring Kit (Generator)', current: 0, min: 2, location: 'A3-15' },
];

const STATS = {
  totalParts: 1248,
  inStock: 1195,
  lowStock: 38,
  outOfStock: 15,
  pendingOrders: 8,
};

// ============================================================================
// COMPONENT
// ============================================================================

interface InventoryStatusModuleProps {
  isExpanded: boolean;
  onToggle: () => void;
  className?: string;
}

export default function InventoryStatusModule({
  isExpanded,
  onToggle,
  className,
}: InventoryStatusModuleProps) {
  const overallStatus = STATS.outOfStock > 10 ? 'critical' : STATS.lowStock > 30 ? 'warning' : 'healthy';
  const stockHealth = Math.round((STATS.inStock / STATS.totalParts) * 100);

  return (
    <ModuleContainer
      title="Inventory"
      icon={<Package className="h-4.5 w-4.5 text-emerald-500" />}
      isExpanded={isExpanded}
      onToggle={onToggle}
      status={overallStatus}
      statusLabel={`${STATS.lowStock} items low stock`}
      badge={STATS.lowStock + STATS.outOfStock}
      collapsedContent={
        <div className="flex items-center gap-3">
          <ProgressBar value={stockHealth} status={overallStatus} />
          <span className="text-[11px] text-zinc-500">{stockHealth}% stocked</span>
        </div>
      }
      className={className}
    >
      {/* Stats */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <StatCard label="In Stock" value={STATS.inStock} status="healthy" />
        <StatCard label="Low Stock" value={STATS.lowStock} status="warning" />
        <StatCard label="Out of Stock" value={STATS.outOfStock} status={STATS.outOfStock > 0 ? 'critical' : 'neutral'} />
      </div>

      {/* Critical items */}
      <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500 mb-2">
        Requires Attention
      </p>
      <div className="space-y-1">
        {LOW_STOCK_ITEMS.map((item) => (
          <ModuleItem
            key={item.id}
            icon={
              item.current === 0 ? (
                <AlertTriangle className="h-4 w-4 text-red-500" />
              ) : (
                <TrendingDown className="h-4 w-4 text-amber-500" />
              )
            }
            title={item.name}
            subtitle={`${item.id} · ${item.location}`}
            status={item.current === 0 ? 'critical' : 'warning'}
            value={`${item.current}/${item.min}`}
            onClick={() => console.log('View part:', item.id)}
            actions={
              <MicroactionButton
                action="order_part"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  console.log('Order:', item.id);
                }}
              />
            }
          />
        ))}
      </div>

      {/* Pending orders note */}
      {STATS.pendingOrders > 0 && (
        <div className={cn(
          'mt-3 px-3 py-2 rounded-lg',
          'bg-blue-50 dark:bg-blue-900/20',
          'text-[12px] text-blue-600 dark:text-blue-400'
        )}>
          {STATS.pendingOrders} orders pending delivery
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 mt-4">
        <MicroactionButton
          action="add_part"
          size="md"
          showLabel
          onClick={() => console.log('Add part')}
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
    </ModuleContainer>
  );
}
