import * as React from 'react';
import { SectionContainer } from '@/components/ui/SectionContainer';

// ============================================================================
// TYPES
// ============================================================================

export interface StockInfoSectionProps {
  /** Current stock quantity */
  stockLevel: number;
  /** Minimum stock level (alerts below this) */
  minStock?: number;
  /** Maximum stock capacity */
  maxStock?: number;
  /** Reorder threshold */
  reorderPoint?: number;
  /** Cost per unit in USD */
  unitCost?: number;
  /** Unit of measure */
  unit?: string;
  /** Top offset for sticky header (56 when inside lens to clear the fixed LensHeader) */
  stickyTop?: number;
}

// ============================================================================
// HELPERS
// ============================================================================

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

function formatQty(qty: number | undefined, unit?: string): string {
  if (qty === undefined || qty === null) return '—';
  const suffix = unit ? ` ${unit}` : '';
  return `${qty}${suffix}`;
}

// ============================================================================
// STOCK INFO ROW
// ============================================================================

interface StockInfoRowProps {
  label: string;
  value: string;
  /** Highlight value in warning color */
  warning?: boolean;
  /** Highlight value in critical color */
  critical?: boolean;
}

function StockInfoRow({ label, value, warning, critical }: StockInfoRowProps) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-surface-border-subtle last:border-b-0 min-h-[44px] px-5">
      <span className="text-[13px] font-normal text-txt-secondary leading-[1.4]">
        {label}
      </span>
      <span
        className={
          critical
            ? 'text-[14px] font-medium text-status-critical leading-[1.4]'
            : warning
              ? 'text-[14px] font-medium text-status-warning leading-[1.4]'
              : 'text-[14px] font-medium text-txt-primary leading-[1.4]'
        }
      >
        {value}
      </span>
    </div>
  );
}

// ============================================================================
// STOCK INFO SECTION
// ============================================================================

/**
 * StockInfoSection - Displays stock quantities, thresholds and cost.
 *
 * Rows:
 * - Current Stock (highlighted critical if 0, warning if low)
 * - Min Stock
 * - Max Stock
 * - Reorder Point
 * - Unit Cost
 *
 * Uses SectionContainer for sticky header behavior via IntersectionObserver.
 */
export function StockInfoSection({
  stockLevel,
  minStock,
  maxStock,
  reorderPoint,
  unitCost,
  unit,
  stickyTop,
}: StockInfoSectionProps) {
  const isOutOfStock = stockLevel <= 0;
  const isLowStock = !isOutOfStock && reorderPoint !== undefined && stockLevel < reorderPoint;

  return (
    <SectionContainer
      title="Stock Information"
      stickyTop={stickyTop}
    >
      <div className="-mx-4">
        <StockInfoRow
          label="Current Stock"
          value={formatQty(stockLevel, unit)}
          critical={isOutOfStock}
          warning={isLowStock}
        />
        {minStock !== undefined && (
          <StockInfoRow
            label="Minimum Stock"
            value={formatQty(minStock, unit)}
          />
        )}
        {maxStock !== undefined && (
          <StockInfoRow
            label="Maximum Stock"
            value={formatQty(maxStock, unit)}
          />
        )}
        {reorderPoint !== undefined && (
          <StockInfoRow
            label="Reorder Point"
            value={formatQty(reorderPoint, unit)}
          />
        )}
        {unitCost !== undefined && (
          <StockInfoRow
            label="Unit Cost"
            value={formatCurrency(unitCost)}
          />
        )}
        {unitCost !== undefined && stockLevel > 0 && (
          <StockInfoRow
            label="Total Value"
            value={formatCurrency(unitCost * stockLevel)}
          />
        )}
      </div>
    </SectionContainer>
  );
}

export default StockInfoSection;
