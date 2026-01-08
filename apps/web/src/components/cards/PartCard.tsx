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
  };
  actions?: MicroAction[];
}

export function PartCard({ part, actions = [] }: PartCardProps) {
  const isLowStock = part.stock_quantity <= part.min_stock_level;
  const isOutOfStock = part.stock_quantity === 0;

  const getStockStatus = () => {
    if (isOutOfStock) {
      return { label: 'Out of Stock', color: 'text-red-700 bg-red-50 border-red-200' };
    }
    if (isLowStock) {
      return { label: 'Low Stock', color: 'text-orange-700 bg-orange-50 border-orange-200' };
    }
    return { label: 'In Stock', color: 'text-green-700 bg-green-50 border-green-200' };
  };

  const stockStatus = getStockStatus();

  return (
    <div className="bg-card border border-border rounded-lg p-4 hover:bg-accent/50 transition-colors">
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
            <span
              className={cn(
                'text-xs px-2 py-0.5 rounded-full border font-medium uppercase',
                stockStatus.color
              )}
            >
              {stockStatus.label}
            </span>
          </div>

          {/* Part Number */}
          <p className="text-sm text-muted-foreground mb-1">
            <span className="font-medium">P/N:</span> {part.part_number}
          </p>

          {/* Category */}
          {part.category && (
            <p className="text-sm text-muted-foreground mb-2">
              <span className="font-medium">Category:</span> {part.category}
            </p>
          )}

          {/* Stock Quantity */}
          <div className="flex items-center gap-4 mb-2">
            <div className="text-sm">
              <span className="font-medium">Stock:</span>{' '}
              <span className={cn(isLowStock && 'text-orange-600 font-bold')}>
                {part.stock_quantity}
              </span>{' '}
              <span className="text-muted-foreground">
                (min: {part.min_stock_level})
              </span>
            </div>
          </div>

          {/* Location */}
          <div className="flex items-center gap-1.5 text-sm text-muted-foreground mb-2">
            <MapPin className="h-4 w-4" />
            <span>{part.location}</span>
          </div>

          {/* Cost & Supplier */}
          <div className="flex items-center gap-4 text-xs text-muted-foreground mb-3">
            {part.unit_cost && (
              <span className="font-medium">${part.unit_cost.toFixed(2)}/unit</span>
            )}
            {part.supplier && <span>Supplier: {part.supplier}</span>}
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-2">
            {isLowStock && !actions.includes('order_part') && (
              <ActionButton
                action="order_part"
                context={{ part_id: part.id }}
                variant="default"
                size="sm"
                showIcon={true}
              />
            )}
            {actions.map((action) => (
              <ActionButton
                key={action}
                action={action}
                context={{ part_id: part.id }}
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
