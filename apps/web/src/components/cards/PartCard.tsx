/**
 * PartCard Component
 *
 * Displays part/inventory information with stock levels and actions
 */

'use client';

import { Package, MapPin, ShoppingCart, AlertTriangle } from 'lucide-react';
import { ActionButton } from '@/components/actions/ActionButton';
import { cn } from '@/lib/utils';
import type { MicroAction } from '@/types/actions';

interface PartCardProps {
  part: {
    id: string;
    part_name: string;
    part_number: string;
    stock_quantity: number;
    min_stock_level: number;
    location: string;
    unit_cost?: number;
    supplier?: string;
    category?: string;
    last_counted_at?: string;
    last_counted_by?: string;
    unit?: string;
  };
  actions?: MicroAction[];
  entityType?: 'part' | 'inventory';
}

export function PartCard({ part, actions = [] as MicroAction[], entityType = 'part' }: PartCardProps) {
  const isLowStock = part.stock_quantity <= part.min_stock_level;
  const isOutOfStock = part.stock_quantity === 0;

  const getStockStatus = () => {
    if (isOutOfStock) {
      return { label: 'Out of Stock', pillClass: 'status-pill status-pill-critical' };
    }
    if (isLowStock) {
      return { label: 'Low Stock', pillClass: 'status-pill status-pill-warning' };
    }
    return { label: 'In Stock', pillClass: 'status-pill status-pill-success' };
  };

  const stockStatus = getStockStatus();

  return (
    <div
      className="entity-card"
      data-testid={entityType === 'inventory' ? 'inventory-card' : 'part-card'}
      data-entity-type={entityType}
      data-entity-id={part.id}
    >
      <div className="flex items-start gap-3">
        {/* Part Icon */}
        <div className={cn('mt-1', isOutOfStock ? 'text-red-600' : 'text-primary')}>
          {isOutOfStock ? (
            <AlertTriangle className="h-5 w-5" />
          ) : (
            <Package className="h-5 w-5" />
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Name & Stock Status */}
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <h3 className="font-medium text-foreground">{part.part_name}</h3>
            <span className={stockStatus.pillClass}>
              {stockStatus.label}
            </span>
          </div>

          {/* Part Number */}
          <p className="typo-body text-muted-foreground mb-1">
            <span className="font-medium">P/N:</span> {part.part_number}
          </p>

          {/* Category */}
          {part.category && (
            <p className="typo-body text-muted-foreground mb-2">
              <span className="font-medium">Category:</span> {part.category}
            </p>
          )}

          {/* Stock Quantity */}
          <div className="flex items-center gap-4 mb-2">
            <div className="typo-body">
              <span className="font-medium">Stock:</span>{' '}
              <span className={cn(
                isLowStock && 'text-orange-600 font-bold',
                isOutOfStock && 'text-red-600 font-bold'
              )}>
                {part.stock_quantity}
              </span>
              {part.unit && <span className="text-muted-foreground ml-1">{part.unit}</span>}
              {' '}
              <span className="text-muted-foreground">
                (min: {part.min_stock_level})
              </span>
            </div>
          </div>

          {/* Last Counted (Inventory-specific info) */}
          {part.last_counted_at && (
            <div className="typo-meta text-muted-foreground mb-2">
              <span className="font-medium">Last counted:</span>{' '}
              {new Date(part.last_counted_at).toLocaleDateString()}{' '}
              {part.last_counted_by && <span>by {part.last_counted_by}</span>}
            </div>
          )}

          {/* Location */}
          <div className="flex items-center gap-1.5 typo-body text-muted-foreground mb-2">
            <MapPin className="h-4 w-4" />
            <span>{part.location}</span>
          </div>

          {/* Cost & Supplier */}
          <div className="flex items-center gap-4 typo-meta text-muted-foreground mb-3">
            {part.unit_cost && (
              <span className="font-medium">${part.unit_cost.toFixed(2)}/unit</span>
            )}
            {part.supplier && <span>Supplier: {part.supplier}</span>}
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-2">
            {/* Auto-suggest shopping list action for low stock */}
            {isLowStock && !actions.includes('order_part' as MicroAction) && (
              <ActionButton
                action="order_part"
                context={{ part_id: part.id }}
                variant="default"
                size="sm"
                showIcon={true}
              />
            )}
            {/* Render backend-provided actions */}
            {actions.map((action) => (
              <ActionButton
                key={action}
                action={action}
                context={{ part_id: part.id, entity_type: entityType }}
                variant="secondary"
                size="sm"
                showIcon={true}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
