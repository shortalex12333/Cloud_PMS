import * as React from 'react';
import { cn } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { GhostButton } from '@/components/ui/GhostButton';
import { StatusPill } from '@/components/ui/StatusPill';

// ============================================================================
// TYPES
// ============================================================================

/**
 * Transaction types per pms_inventory_transactions schema.
 * Maps to CHECK constraint in database.
 */
export type TransactionType =
  | 'received'         // Parts received from supplier
  | 'consumed'         // Parts consumed for work/maintenance
  | 'adjusted'         // Manual stock adjustment (SIGNED action)
  | 'transferred_in'   // Received from transfer
  | 'transferred_out'  // Sent via transfer
  | 'write_off'        // Written off (SIGNED action)
  | 'returned'         // Returned to supplier
  | 'initial'          // Initial stock count
  // Legacy types for backward compatibility
  | 'consume'
  | 'receive'
  | 'transfer'
  | 'adjust';

export interface PartTransaction {
  id: string;
  /** Transaction type per pms_inventory_transactions schema */
  type: TransactionType;
  /** Positive = stock added (received), negative = stock removed (consumed/write_off) */
  quantity_change: number;
  /** Stock level after this transaction */
  stock_after?: number;
  /** Actor who performed the transaction — NEVER show raw UUID */
  actor: string;
  actor_id?: string;
  /** ISO timestamp */
  created_at: string;
  /** Linked work order id if applicable */
  work_order_id?: string;
  work_order_number?: string;
  /** Reason for adjustment or write-off (required for adjusted/write_off types) */
  reason?: string;
  /** Free-text notes */
  notes?: string;
}

export interface TransactionHistorySectionProps {
  transactions: PartTransaction[];
  pageSize?: number;
  /** Top offset for sticky header (56 when inside lens to clear the fixed LensHeader) */
  stickyTop?: number;
}

// ============================================================================
// CONSTANTS
// ============================================================================

const DEFAULT_PAGE_SIZE = 20;

// ============================================================================
// HELPERS
// ============================================================================

function formatTimestamp(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    const hh = date.getHours().toString().padStart(2, '0');
    const mm = date.getMinutes().toString().padStart(2, '0');
    return `Today at ${hh}:${mm}`;
  }
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  return date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

/**
 * Map transaction type to human-readable label and StatusPill color.
 * consumed/write_off = stock removed → warning/critical
 * received/returned = stock change → success/neutral
 * transferred_in/out = transfer → neutral
 * adjusted = manual correction → neutral
 * initial = opening balance → neutral
 */
function mapTransactionType(type: TransactionType): {
  label: string;
  color: 'critical' | 'warning' | 'success' | 'neutral';
} {
  switch (type) {
    // New canonical types from pms_inventory_transactions
    case 'received':
      return { label: 'Received', color: 'success' };
    case 'consumed':
      return { label: 'Consumed', color: 'warning' };
    case 'adjusted':
      return { label: 'Adjusted', color: 'neutral' };
    case 'transferred_in':
      return { label: 'Transferred In', color: 'success' };
    case 'transferred_out':
      return { label: 'Transferred Out', color: 'warning' };
    case 'write_off':
      return { label: 'Written Off', color: 'critical' };
    case 'returned':
      return { label: 'Returned', color: 'neutral' };
    case 'initial':
      return { label: 'Initial Count', color: 'neutral' };
    // Legacy types for backward compatibility
    case 'consume':
      return { label: 'Consumed', color: 'warning' };
    case 'receive':
      return { label: 'Received', color: 'success' };
    case 'transfer':
      return { label: 'Transferred', color: 'neutral' };
    case 'adjust':
      return { label: 'Adjusted', color: 'neutral' };
    default:
      return { label: String(type).replace(/_/g, ' '), color: 'neutral' };
  }
}

function formatQuantityChange(change: number): string {
  if (change > 0) return `+${change}`;
  return String(change);
}

// ============================================================================
// TRANSACTION ROW
// ============================================================================

interface TransactionRowProps {
  tx: PartTransaction;
}

function TransactionRow({ tx }: TransactionRowProps) {
  const [isExpanded, setIsExpanded] = React.useState(false);
  const { label, color } = mapTransactionType(tx.type);
  const hasDetails = !!tx.notes || !!tx.reason || !!tx.work_order_number || tx.stock_after !== undefined;

  return (
    <div
      className={cn(
        'px-5 py-3 min-h-[44px]',
        'border-b border-surface-border-subtle last:border-b-0'
      )}
    >
      {/* Primary row: type pill + quantity change + actor + timestamp */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap flex-1 min-w-0">
          <StatusPill status={color} label={label} />
          <span
            className={cn(
              'text-[14px] font-semibold leading-none tabular-nums',
              tx.quantity_change > 0 ? 'text-status-success' : 'text-status-warning'
            )}
          >
            {formatQuantityChange(tx.quantity_change)}
          </span>
          <span className="text-[13px] text-txt-secondary leading-none">
            by {tx.actor}
          </span>
        </div>
        <span
          className="text-[12px] text-txt-tertiary leading-[1.4] flex-shrink-0"
          title={new Date(tx.created_at).toLocaleString()}
        >
          {formatTimestamp(tx.created_at)}
        </span>
      </div>

      {/* Expand/collapse for details */}
      {hasDetails && (
        <>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className={cn(
              'mt-1 text-[12px] font-medium text-txt-tertiary',
              'hover:text-txt-secondary transition-colors duration-fast',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-interactive rounded-lg'
            )}
            aria-expanded={isExpanded}
          >
            {isExpanded ? 'Hide details' : 'Show details'}
          </button>

          {isExpanded && (
            <div className="mt-2 space-y-1">
              {tx.work_order_number && (
                <p className="text-[13px] text-txt-secondary leading-[1.6]">
                  Work order:{' '}
                  <a
                    href={`/work-orders/${tx.work_order_id}`}
                    className="font-medium text-brand-interactive hover:underline underline-offset-2 transition-colors"
                  >
                    {tx.work_order_number}
                  </a>
                </p>
              )}
              {tx.reason && (
                <p className="text-[13px] text-txt-secondary leading-[1.6]">
                  Reason: <span className="font-medium text-txt-primary">{tx.reason}</span>
                </p>
              )}
              {tx.stock_after !== undefined && (
                <p className="text-[13px] text-txt-tertiary leading-[1.6]">
                  Balance after: {tx.stock_after}
                </p>
              )}
              {tx.notes && (
                <p className="text-[13px] text-txt-secondary leading-[1.6]">
                  {tx.notes}
                </p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ============================================================================
// TRANSACTION HISTORY SECTION
// ============================================================================

/**
 * TransactionHistorySection - Paginated read-only ledger of stock movements.
 *
 * Transaction types per pms_inventory_transactions schema:
 * - received: Parts received from supplier
 * - consumed: Parts consumed for work/maintenance
 * - adjusted: Manual stock adjustment (SIGNED action)
 * - transferred_in/transferred_out: Transfer between locations
 * - write_off: Written off (SIGNED action)
 * - returned: Returned to supplier
 * - initial: Opening balance
 *
 * Most recent first (caller responsible for sort order).
 * Paginated with "Load more" for > pageSize entries.
 *
 * Uses SectionContainer for sticky header behavior via IntersectionObserver.
 */
export function TransactionHistorySection({
  transactions,
  pageSize = DEFAULT_PAGE_SIZE,
  stickyTop,
}: TransactionHistorySectionProps) {
  const [visibleCount, setVisibleCount] = React.useState(pageSize);

  React.useEffect(() => {
    setVisibleCount(pageSize);
  }, [transactions.length, pageSize]);

  const visibleTx = transactions.slice(0, visibleCount);
  const hasMore = transactions.length > visibleCount;
  const remainingCount = transactions.length - visibleCount;

  return (
    <SectionContainer
      title="Transaction History"
      count={transactions.length > 0 ? transactions.length : undefined}
      stickyTop={stickyTop}
    >
      {transactions.length === 0 ? (
        <div className="py-8 text-center">
          <p className="text-[14px] text-txt-secondary leading-[1.6]">
            No transactions recorded yet.
          </p>
        </div>
      ) : (
        <>
          <div className="-mx-4">
            {visibleTx.map((tx) => (
              <TransactionRow key={tx.id} tx={tx} />
            ))}
          </div>

          {hasMore && (
            <div className="pt-3 pb-1 text-center">
              <GhostButton
                onClick={() => setVisibleCount((prev) => prev + pageSize)}
              >
                Load {Math.min(remainingCount, pageSize)} more
                {remainingCount > pageSize && ` (${remainingCount} remaining)`}
              </GhostButton>
            </div>
          )}
        </>
      )}
    </SectionContainer>
  );
}

export default TransactionHistorySection;
