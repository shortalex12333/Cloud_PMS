import * as React from 'react';
import { cn } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { EntityLink } from '@/components/ui/EntityLink';
import { GhostButton } from '@/components/ui/GhostButton';
import { StatusPill } from '@/components/ui/StatusPill';

// ============================================================================
// TYPES
// ============================================================================

export interface ReceivingLineItem {
  /** Line item UUID (backend only - do not render) */
  id: string;
  /** Yacht UUID (backend only - do not render) */
  yacht_id?: string;
  /** Receiving header UUID (backend only - do not render) */
  receiving_id?: string;
  /** Part UUID for linking (backend only - used for navigation) */
  part_id?: string;
  /** Part name or description (FRONTEND - render this) */
  description?: string;
  /** Expected quantity from PO/order (FRONTEND) */
  quantity_expected?: number | null;
  /** Actual quantity received (FRONTEND) */
  quantity_received: number;
  /** Unit price (FRONTEND) */
  unit_price?: number | null;
  /** Currency code (FRONTEND) */
  currency?: string | null;
  /** Additional metadata */
  properties?: Record<string, unknown> | null;
  /** Called when user clicks the part entity link */
  onPartClick?: () => void;
}

export interface ReceivingLineItemsSectionProps {
  items: ReceivingLineItem[];
  onAddItem?: () => void;
  canAddItem: boolean;
  /** Top offset for sticky header (56 when inside lens to clear the fixed LensHeader) */
  stickyTop?: number;
}

// ============================================================================
// HELPERS
// ============================================================================

/**
 * Determine if there's a quantity discrepancy between expected and received.
 * Returns 'match' if quantities match or expected is null (ad-hoc item).
 * Returns 'short' if received < expected.
 * Returns 'over' if received > expected.
 */
function getDiscrepancyStatus(
  expected: number | null | undefined,
  received: number
): 'match' | 'short' | 'over' {
  if (expected === null || expected === undefined) {
    // Ad-hoc item, no expected quantity
    return 'match';
  }
  if (received < expected) return 'short';
  if (received > expected) return 'over';
  return 'match';
}

/**
 * Map discrepancy status to StatusPill variant.
 * short (under-delivery) → warning (needs attention)
 * over (over-delivery) → neutral (informational, may be bonus)
 * match → success (all good)
 */
function getDiscrepancyVariant(
  status: 'match' | 'short' | 'over'
): 'success' | 'warning' | 'neutral' {
  switch (status) {
    case 'short':
      return 'warning';
    case 'over':
      return 'neutral';
    case 'match':
    default:
      return 'success';
  }
}

/**
 * Format quantity display with expected vs received.
 */
function formatQuantities(
  expected: number | null | undefined,
  received: number
): string {
  if (expected === null || expected === undefined) {
    return `${received}`;
  }
  return `${received} / ${expected}`;
}

/**
 * Format currency amount.
 */
function formatPrice(amount: number | null | undefined, currency?: string | null): string {
  if (amount === null || amount === undefined) return '';
  const formatted = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(amount);
  return currency ? `${currency} ${formatted}` : formatted;
}

// ============================================================================
// LINE ITEM ROW
// ============================================================================

interface LineItemRowProps {
  item: ReceivingLineItem;
}

function LineItemRow({ item }: LineItemRowProps) {
  const discrepancyStatus = getDiscrepancyStatus(item.quantity_expected, item.quantity_received);
  const discrepancyVariant = getDiscrepancyVariant(discrepancyStatus);
  const quantityLabel = formatQuantities(item.quantity_expected, item.quantity_received);
  const priceLabel = formatPrice(item.unit_price, item.currency);

  // Determine the discrepancy label
  const getDiscrepancyLabel = () => {
    if (discrepancyStatus === 'short') {
      const diff = (item.quantity_expected ?? 0) - item.quantity_received;
      return `Short ${diff}`;
    }
    if (discrepancyStatus === 'over') {
      const diff = item.quantity_received - (item.quantity_expected ?? 0);
      return `Over ${diff}`;
    }
    return 'Complete';
  };

  return (
    <div
      className={cn(
        // Entity card layout: 20px horizontal, 12px vertical per UI_SPEC.md
        'flex items-center justify-between',
        'px-5 py-3 min-h-12',
        // Subtle internal divider between rows
        'border-b border-surface-border-subtle last:border-b-0',
        // Hover state for interactive rows
        'transition-colors duration-fast hover:bg-surface-hover',
        // Highlight discrepancy rows with subtle background
        discrepancyStatus === 'short' && 'bg-status-warning-bg/30'
      )}
    >
      {/* Left: Item description/name + price */}
      <div className="flex-1 min-w-0 mr-3">
        <div className="flex items-center gap-2">
          {item.part_id ? (
            <EntityLink
              entityType="part"
              entityId={item.part_id}
              label={item.description || 'Unnamed Part'}
              onClick={item.onPartClick}
              className="text-[14px] font-medium truncate"
            />
          ) : (
            <span className="text-[14px] font-medium text-txt-primary truncate">
              {item.description || 'Unnamed Item'}
            </span>
          )}
        </div>
        {priceLabel && (
          <p className="text-[12px] text-txt-tertiary mt-0.5">
            {priceLabel} / unit
          </p>
        )}
      </div>

      {/* Center: Quantity display */}
      <div className="flex items-center gap-3 flex-shrink-0">
        <span className="text-[13px] text-txt-secondary tabular-nums">
          {quantityLabel}
        </span>
      </div>

      {/* Right: Discrepancy status pill */}
      {item.quantity_expected !== null && item.quantity_expected !== undefined && (
        <StatusPill
          status={discrepancyVariant}
          label={getDiscrepancyLabel()}
          showDot={discrepancyStatus === 'short'}
          className="flex-shrink-0 ml-3"
        />
      )}
    </div>
  );
}

// ============================================================================
// RECEIVING LINE ITEMS SECTION
// ============================================================================

/**
 * ReceivingLineItemsSection - Displays line items for a receiving record.
 *
 * Each item row includes:
 * - Item description/name (EntityLink if linked to part)
 * - Quantity received vs expected
 * - Unit price (if available)
 * - Discrepancy indicator (Short/Over/Complete)
 *
 * Discrepancies are highlighted:
 * - Short deliveries show warning status with subtle yellow background
 * - Over deliveries show neutral status (informational)
 * - Complete items show success status
 *
 * Empty state: contextual, actionable.
 */
export function ReceivingLineItemsSection({
  items,
  onAddItem,
  canAddItem,
  stickyTop,
}: ReceivingLineItemsSectionProps) {
  // Calculate summary stats
  const totalItems = items.length;
  const shortCount = items.filter(
    (item) => getDiscrepancyStatus(item.quantity_expected, item.quantity_received) === 'short'
  ).length;

  return (
    <SectionContainer
      title="Line Items"
      count={totalItems > 0 ? totalItems : undefined}
      action={
        canAddItem
          ? { label: '+ Add Item', onClick: onAddItem ?? (() => {}) }
          : undefined
      }
      stickyTop={stickyTop}
    >
      {items.length === 0 ? (
        // Contextual empty state: specific + actionable per UI_SPEC.md language rules
        <div className="py-8 text-center">
          <p className="text-[14px] text-txt-secondary leading-[1.6]">
            No items recorded. Add items to track received goods.
          </p>
          {canAddItem && onAddItem && (
            <GhostButton onClick={onAddItem} className="mt-3">
              + Add Item
            </GhostButton>
          )}
        </div>
      ) : (
        <div className="-mx-4">
          {items.map((item) => (
            <LineItemRow key={item.id} item={item} />
          ))}
        </div>
      )}
    </SectionContainer>
  );
}

export default ReceivingLineItemsSection;
