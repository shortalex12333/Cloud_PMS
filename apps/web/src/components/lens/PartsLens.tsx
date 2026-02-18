'use client';

/**
 * PartsLens - Full-screen entity lens for parts/inventory items.
 *
 * Per CLAUDE.md and UI_SPEC.md (WorkOrderLens pattern):
 * - Fixed LensHeader (56px): back button, entity type overline, close button
 * - Title block: part name, description
 * - VitalSignsRow: 5 indicators (stock level, location, unit, reorder point, supplier)
 * - Low stock warning: StatusPill with "warning" color when stock_level < reorder_point
 * - 5 sections:
 *   1. StockInfoSection - Current stock, min/max, reorder point, unit cost
 *   2. TransactionHistorySection - Inventory transaction ledger (pms_inventory_transactions)
 *   3. UsageLogSection - Part usage history with work order/equipment links (pms_part_usage)
 *   4. LinkedEquipmentSection - Equipment that uses this part
 *   5. DocumentsSection - Spec sheets, MSDS, manuals
 * - All semantic tokens, zero raw hex values
 * - Glass transition animation via LensContainer (300ms ease-out)
 * - Body scroll locked when open
 *
 * FE-02-03: Parts/Inventory Lens Rebuild
 */

import * as React from 'react';
import { useEffect } from 'react';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { LensContainer } from './LensContainer';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';

// Part-specific sections
import {
  StockInfoSection,
  TransactionHistorySection,
  LinkedEquipmentSection,
  DocumentsSection,
  UsageLogSection,
  type PartTransaction,
  type LinkedEquipment,
  type PartDocument,
  type PartUsageEntry,
} from './parts-sections';

// Action hook + permissions
import { usePartActions, usePartPermissions } from '@/hooks/usePartActions';
import { GhostButton } from '@/components/ui/GhostButton';
import { PrimaryButton } from '@/components/ui/PrimaryButton';

// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

export interface PartData {
  id: string;
  /** Human-readable part name — NEVER show raw id UUID */
  name: string;
  /** Part number for display (e.g. OEM reference) */
  part_number?: string;
  /** Description or notes */
  description?: string;
  /** Current stock quantity */
  stock_level: number;
  /** Reorder threshold — show warning when stock_level < reorder_point */
  reorder_point?: number;
  /** Minimum allowed stock quantity */
  min_stock?: number;
  /** Maximum stock capacity */
  max_stock?: number;
  /** Unit of measure (each, box, liter, kg, etc.) */
  unit?: string;
  /** Storage location string (e.g. "Engine Room - Shelf A3") */
  location?: string;
  /** Unit cost in USD */
  unit_cost?: number;
  /** Supplier / vendor name */
  supplier?: string;
  /** Whether stock is considered low (stock_level < reorder_point) */
  is_low_stock?: boolean;
  /** Linked equipment (direct FK or via work orders) */
  equipment_id?: string;
  equipment_name?: string;
  /** Transaction history: consume, receive, transfer, adjust, write-off */
  transactions?: PartTransaction[];
  /** Usage log: records of when parts were consumed with context (work order, equipment, reason) */
  usage_log?: PartUsageEntry[];
  /** Equipment that uses this part */
  linked_equipment?: LinkedEquipment[];
  /** Attached documents (spec sheets, MSDS) */
  documents?: PartDocument[];
}

export interface PartsLensProps {
  /** The part data to render */
  part: PartData;
  /** Handler for back navigation */
  onBack?: () => void;
  /** Handler for close */
  onClose?: () => void;
  /** Additional CSS classes for the lens container */
  className?: string;
  /** Callback to refresh data after an action succeeds */
  onRefresh?: () => void;
}

// ---------------------------------------------------------------------------
// Stock level display helpers (local to PartsLens — domain-specific)
// ---------------------------------------------------------------------------

/**
 * Format stock level as a display string.
 * "5 units" / "1 unit" — uses unit if provided.
 */
function formatStockLevel(stock: number, unit?: string): string {
  const unitLabel = unit ? ` ${unit}` : ` unit${stock === 1 ? '' : 's'}`;
  return `${stock}${unitLabel}`;
}

/**
 * Determine stock pill color based on is_low_stock or derived comparison.
 * - out of stock (0): critical
 * - low stock (< reorder_point): warning
 * - in stock: success
 */
function mapStockToColor(
  stockLevel: number,
  reorderPoint?: number,
  isLowStock?: boolean
): 'critical' | 'warning' | 'success' | undefined {
  if (stockLevel <= 0) return 'critical';
  if (isLowStock || (reorderPoint !== undefined && stockLevel < reorderPoint)) {
    return 'warning';
  }
  return 'success';
}

// ---------------------------------------------------------------------------
// PartsLens component
// ---------------------------------------------------------------------------

/**
 * PartsLens — Full-screen entity lens for parts/inventory.
 *
 * Usage:
 * ```tsx
 * <PartsLens
 *   part={data}
 *   onBack={() => router.back()}
 *   onClose={() => router.push('/app')}
 * />
 * ```
 */
export const PartsLens = React.forwardRef<
  HTMLDivElement,
  PartsLensProps
>(({ part, onBack, onClose, className, onRefresh }, ref) => {
  // Glass transition: lens mounts as closed then opens on first render
  const [isOpen, setIsOpen] = React.useState(false);

  // Modal visibility
  const [consumeOpen, setConsumeOpen] = React.useState(false);
  const [receiveOpen, setReceiveOpen] = React.useState(false);

  // Actions and permissions
  const actions = usePartActions(part.id);
  const perms = usePartPermissions();

  useEffect(() => {
    // Trigger glass enter animation on mount
    setIsOpen(true);
  }, []);

  // ---------------------------------------------------------------------------
  // Derived display values
  // ---------------------------------------------------------------------------

  // Part title: part_number prefix like WO uses wo_number
  const displayTitle = part.part_number
    ? `${part.part_number} — ${part.name}`
    : part.name;

  // Stock level color (StatusPill when low stock or out of stock)
  const stockColor = mapStockToColor(part.stock_level, part.reorder_point, part.is_low_stock);
  const stockLabel = formatStockLevel(part.stock_level, part.unit);

  // Build the 5 vital signs per plan spec
  const partVitalSigns: VitalSign[] = [
    {
      label: 'Stock',
      value: stockLabel,
      // StatusPill with warning/critical when low stock; success otherwise
      color: stockColor,
    },
    {
      label: 'Location',
      value: part.location ?? 'Unknown',
    },
    {
      label: 'Unit',
      value: part.unit ?? '—',
    },
    {
      label: 'Reorder at',
      value: part.reorder_point !== undefined
        ? formatStockLevel(part.reorder_point, part.unit)
        : '—',
    },
    {
      label: 'Supplier',
      value: part.supplier ?? 'None',
    },
  ];

  // Section data (safe fallbacks)
  const transactions = part.transactions ?? [];
  const usageLog = part.usage_log ?? [];
  const linkedEquipment = part.linked_equipment ?? [];
  const documents = part.documents ?? [];

  // ---------------------------------------------------------------------------
  // Action handlers — wrap hook methods with refresh callback
  // ---------------------------------------------------------------------------

  const handleConsume = React.useCallback(async (quantity: number, notes?: string) => {
    const result = await actions.consumePart(quantity, notes);
    if (result.success) onRefresh?.();
    return result;
  }, [actions, onRefresh]);

  const handleReceive = React.useCallback(async (quantity: number, notes?: string) => {
    const result = await actions.receivePart(quantity, notes);
    if (result.success) onRefresh?.();
    return result;
  }, [actions, onRefresh]);

  // Handle close with exit animation: flip isOpen → false, then call onClose after 200ms
  const handleClose = React.useCallback(() => {
    setIsOpen(false);
    if (onClose) {
      setTimeout(onClose, 210); // Wait for exit animation (200ms + buffer)
    }
  }, [onClose]);

  const handleBack = React.useCallback(() => {
    if (onBack) {
      onBack();
    } else {
      handleClose();
    }
  }, [onBack, handleClose]);

  return (
    <LensContainer
      ref={ref}
      isOpen={isOpen}
      onClose={handleClose}
      className={className}
    >
      {/* Fixed navigation header — 56px, at z-header */}
      <LensHeader
        entityType="Part"
        title={displayTitle}
        onBack={handleBack}
        onClose={handleClose}
      />

      {/* Main content — padded top to clear fixed header (56px = h-14) */}
      <main
        className={cn(
          // Clear the fixed header
          'pt-14',
          // Lens body padding: 40px desktop, responsive
          'px-10 md:px-6 sm:px-4',
          // Max content width: 800px centered per spec
          'max-w-[800px] mx-auto',
          // Bottom breathing room
          'pb-12'
        )}
      >
        {/* ---------------------------------------------------------------
            Title block: part name/number, description
            Gap from header: 24px (--space-6)
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <LensTitleBlock
            title={displayTitle}
            subtitle={part.description}
          />
        </div>

        {/* ---------------------------------------------------------------
            Vital Signs Row — 5 indicators
            Gap from title: 12px per UI_SPEC.md ("Title and vital signs: 12px")
            --------------------------------------------------------------- */}
        <div className="mt-3">
          <VitalSignsRow signs={partVitalSigns} />
        </div>

        {/* ---------------------------------------------------------------
            Low-stock warning banner — shown when stock_level < reorder_point
            Provides additional visual emphasis beyond the StatusPill
            --------------------------------------------------------------- */}
        {(part.is_low_stock || (part.reorder_point !== undefined && part.stock_level < part.reorder_point)) && part.stock_level > 0 && (
          <div
            className={cn(
              'mt-3 px-4 py-2 rounded-md',
              'bg-status-warning/10 border border-status-warning/30',
              'text-[13px] text-status-warning font-medium'
            )}
            role="alert"
          >
            Low stock — reorder point is {formatStockLevel(part.reorder_point ?? 0, part.unit)}.
            Consider adding to the shopping list.
          </div>
        )}

        {part.stock_level <= 0 && (
          <div
            className={cn(
              'mt-3 px-4 py-2 rounded-md',
              'bg-status-critical/10 border border-status-critical/30',
              'text-[13px] text-status-critical font-medium'
            )}
            role="alert"
          >
            Out of stock — this part is not available.
          </div>
        )}

        {/* ---------------------------------------------------------------
            Header action buttons (Consume, Receive)
            Visible only if user has relevant permissions — hidden, not disabled
            --------------------------------------------------------------- */}
        {(perms.canConsume || perms.canReceive) && (
          <div className="mt-4 flex items-center gap-2 flex-wrap">
            {perms.canConsume && (
              <PrimaryButton
                onClick={() => setConsumeOpen(true)}
                disabled={actions.isLoading || part.stock_level <= 0}
                className="text-[13px] min-h-[36px] px-4 py-2"
              >
                Consume
              </PrimaryButton>
            )}
            {perms.canReceive && (
              <GhostButton
                onClick={() => setReceiveOpen(true)}
                disabled={actions.isLoading}
                className="text-[13px] min-h-[36px] px-4 py-2"
              >
                Receive Stock
              </GhostButton>
            )}
            {perms.canAddToShoppingList && (
              <GhostButton
                onClick={() => actions.addToShoppingList()}
                disabled={actions.isLoading}
                className="text-[13px] min-h-[36px] px-4 py-2"
              >
                + Shopping List
              </GhostButton>
            )}
          </div>
        )}

        {/* ---------------------------------------------------------------
            Section divider
            Gap from vitals to first section: 24px per spec
            --------------------------------------------------------------- */}
        <div
          className="mt-6 border-t border-surface-border"
          aria-hidden="true"
        />

        {/* ---------------------------------------------------------------
            Stock Info Section — current stock, min/max, reorder point, unit cost
            stickyTop={56}: sticky headers clear the 56px fixed LensHeader
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <StockInfoSection
            stockLevel={part.stock_level}
            minStock={part.min_stock}
            maxStock={part.max_stock}
            reorderPoint={part.reorder_point}
            unitCost={part.unit_cost}
            unit={part.unit}
            stickyTop={56}
          />
        </div>

        {/* ---------------------------------------------------------------
            Transaction History Section — consume, receive, transfer, adjust events
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <TransactionHistorySection
            transactions={transactions}
            stickyTop={56}
          />
        </div>

        {/* ---------------------------------------------------------------
            Usage Log Section — detailed usage records with work order/equipment links
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <UsageLogSection
            usageLog={usageLog}
            stickyTop={56}
          />
        </div>

        {/* ---------------------------------------------------------------
            Linked Equipment Section — equipment using this part
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <LinkedEquipmentSection
            equipment={linkedEquipment}
            stickyTop={56}
          />
        </div>

        {/* ---------------------------------------------------------------
            Documents Section — spec sheets, MSDS
            --------------------------------------------------------------- */}
        <div className="mt-6">
          <DocumentsSection
            documents={documents}
            stickyTop={56}
          />
        </div>
      </main>

      {/* ---------------------------------------------------------------
          Action Modals — rendered at lens root for correct z-index stacking
          --------------------------------------------------------------- */}
      {consumeOpen && (
        <ConsumePartModal
          open={consumeOpen}
          onClose={() => setConsumeOpen(false)}
          onSubmit={handleConsume}
          isLoading={actions.isLoading}
          partName={part.name}
          maxQuantity={part.stock_level}
          unit={part.unit}
        />
      )}

      {receiveOpen && (
        <ReceivePartModal
          open={receiveOpen}
          onClose={() => setReceiveOpen(false)}
          onSubmit={handleReceive}
          isLoading={actions.isLoading}
          partName={part.name}
          unit={part.unit}
        />
      )}
    </LensContainer>
  );
});

PartsLens.displayName = 'PartsLens';

export default PartsLens;

// ---------------------------------------------------------------------------
// Inline action modals — simple, focused dialogs for consume/receive
// ---------------------------------------------------------------------------

interface ConsumePartModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (quantity: number, notes?: string) => Promise<{ success: boolean; error?: string }>;
  isLoading: boolean;
  partName: string;
  maxQuantity: number;
  unit?: string;
}

function ConsumePartModal({ open, onClose, onSubmit, isLoading, partName, maxQuantity, unit }: ConsumePartModalProps) {
  const [quantity, setQuantity] = React.useState(1);
  const [notes, setNotes] = React.useState('');
  const [error, setError] = React.useState<string | null>(null);

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (quantity < 1 || quantity > maxQuantity) {
      setError(`Quantity must be between 1 and ${maxQuantity}`);
      return;
    }
    setError(null);
    const result = await onSubmit(quantity, notes || undefined);
    if (result.success) {
      onClose();
    } else {
      setError(result.error ?? 'Failed to consume part');
    }
  };

  return (
    <div className="fixed inset-0 z-[var(--z-modal)] flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative bg-surface-primary rounded-md shadow-lg max-w-sm w-full p-6 z-10">
        <h2 className="text-[18px] font-semibold text-txt-primary mb-1">
          Consume Part
        </h2>
        <p className="text-[14px] text-txt-secondary mb-4">
          Record consumption from <span className="font-medium text-txt-primary">{partName}</span>
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="consume-quantity"
              className="block text-[13px] font-medium text-txt-secondary mb-1"
            >
              Quantity{unit ? ` (${unit})` : ''}
            </label>
            <input
              id="consume-quantity"
              type="number"
              min={1}
              max={maxQuantity}
              value={quantity}
              onChange={(e) => setQuantity(Number(e.target.value))}
              className={cn(
                'w-full px-3 py-2 rounded-md text-[14px]',
                'bg-surface-base border border-surface-border',
                'text-txt-primary',
                'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
                'transition-colors duration-[var(--duration-fast)]'
              )}
              required
            />
            <p className="mt-1 text-[12px] text-txt-tertiary">
              Available: {maxQuantity}{unit ? ` ${unit}` : ''}
            </p>
          </div>

          <div>
            <label
              htmlFor="consume-notes"
              className="block text-[13px] font-medium text-txt-secondary mb-1"
            >
              Notes <span className="text-txt-tertiary font-normal">(optional)</span>
            </label>
            <textarea
              id="consume-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="Work order number, reason for consumption..."
              className={cn(
                'w-full px-3 py-2 rounded-md text-[14px]',
                'bg-surface-base border border-surface-border',
                'text-txt-primary placeholder:text-txt-tertiary',
                'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
                'resize-none transition-colors duration-[var(--duration-fast)]'
              )}
            />
          </div>

          {error && (
            <p className="text-[13px] text-status-critical">{error}</p>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className={cn(
                'flex-1 px-4 py-2 rounded-md text-[14px] font-medium',
                'bg-surface-base border border-surface-border text-txt-primary',
                'hover:bg-surface-elevated transition-colors duration-[var(--duration-fast)]'
              )}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className={cn(
                'flex-1 px-4 py-2 rounded-md text-[14px] font-semibold',
                'bg-brand-interactive text-txt-inverse',
                'hover:bg-brand-hover transition-colors duration-[var(--duration-fast)]',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              {isLoading ? 'Consuming...' : 'Confirm Consume'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

interface ReceivePartModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (quantity: number, notes?: string) => Promise<{ success: boolean; error?: string }>;
  isLoading: boolean;
  partName: string;
  unit?: string;
}

function ReceivePartModal({ open, onClose, onSubmit, isLoading, partName, unit }: ReceivePartModalProps) {
  const [quantity, setQuantity] = React.useState(1);
  const [notes, setNotes] = React.useState('');
  const [error, setError] = React.useState<string | null>(null);

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (quantity < 1) {
      setError('Quantity must be at least 1');
      return;
    }
    setError(null);
    const result = await onSubmit(quantity, notes || undefined);
    if (result.success) {
      onClose();
    } else {
      setError(result.error ?? 'Failed to receive stock');
    }
  };

  return (
    <div className="fixed inset-0 z-[var(--z-modal)] flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative bg-surface-primary rounded-md shadow-lg max-w-sm w-full p-6 z-10">
        <h2 className="text-[18px] font-semibold text-txt-primary mb-1">
          Receive Stock
        </h2>
        <p className="text-[14px] text-txt-secondary mb-4">
          Add stock to <span className="font-medium text-txt-primary">{partName}</span>
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="receive-quantity"
              className="block text-[13px] font-medium text-txt-secondary mb-1"
            >
              Quantity received{unit ? ` (${unit})` : ''}
            </label>
            <input
              id="receive-quantity"
              type="number"
              min={1}
              value={quantity}
              onChange={(e) => setQuantity(Number(e.target.value))}
              className={cn(
                'w-full px-3 py-2 rounded-md text-[14px]',
                'bg-surface-base border border-surface-border',
                'text-txt-primary',
                'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
                'transition-colors duration-[var(--duration-fast)]'
              )}
              required
            />
          </div>

          <div>
            <label
              htmlFor="receive-notes"
              className="block text-[13px] font-medium text-txt-secondary mb-1"
            >
              Notes <span className="text-txt-tertiary font-normal">(optional)</span>
            </label>
            <textarea
              id="receive-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="PO number, delivery note, supplier reference..."
              className={cn(
                'w-full px-3 py-2 rounded-md text-[14px]',
                'bg-surface-base border border-surface-border',
                'text-txt-primary placeholder:text-txt-tertiary',
                'focus:outline-none focus:ring-2 focus:ring-brand-interactive',
                'resize-none transition-colors duration-[var(--duration-fast)]'
              )}
            />
          </div>

          {error && (
            <p className="text-[13px] text-status-critical">{error}</p>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className={cn(
                'flex-1 px-4 py-2 rounded-md text-[14px] font-medium',
                'bg-surface-base border border-surface-border text-txt-primary',
                'hover:bg-surface-elevated transition-colors duration-[var(--duration-fast)]'
              )}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className={cn(
                'flex-1 px-4 py-2 rounded-md text-[14px] font-semibold',
                'bg-brand-interactive text-txt-inverse',
                'hover:bg-brand-hover transition-colors duration-[var(--duration-fast)]',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              {isLoading ? 'Receiving...' : 'Confirm Receive'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
