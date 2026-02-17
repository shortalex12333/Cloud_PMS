import * as React from 'react';
import { cn } from '@/lib/utils';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { GhostButton } from '@/components/ui/GhostButton';
import { StatusPill } from '@/components/ui/StatusPill';

// ============================================================================
// TYPES
// ============================================================================

export type TransactionType =
  | 'consume'
  | 'receive'
  | 'transfer'
  | 'adjust'
  | 'write_off';

export interface PartTransaction {
  id: string;
  /** Transaction type: consume, receive, transfer, adjust, write_off */
  type: TransactionType;
  /** Positive = stock added (receive), negative = stock removed (consume/write_off) */
  quantity_change: number;
  /** Stock level after this transaction */
  stock_after?: number;
  /** Actor who performed the transaction */
  actor: string;
  actor_id?: string;
  /** ISO timestamp */
  created_at: string;
  /** Linked work order id if applicable */
  work_order_id?: string;
  work_order_number?: string;
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
 * consume/write_off = stock removed → warning/critical
 * receive = stock added → success
 * transfer/adjust = neutral
 */
function mapTransactionType(type: TransactionType): {
  label: string;
  color: 'critical' | 'warning' | 'success' | 'neutral';
} {
  switch (type) {
    case 'consume':
      return { label: 'Consumed', color: 'warning' };
    case 'receive':
      return { label: 'Received', color: 'success' };
    case 'transfer':
      return { label: 'Transferred', color: 'neutral' };
    case 'adjust':
      return { label: 'Adjusted', color: 'neutral' };
    case 'write_off':
      return { label: 'Written Off', color: 'critical' };
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
  const hasDetails = !!tx.notes || !!tx.work_order_number || tx.stock_after !== undefined;

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
              'hover:text-txt-secondary transition-colors duration-150',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-interactive rounded-sm'
            )}
            aria-expanded={isExpanded}
          >
            {isExpanded ? 'Hide details' : 'Show details'}
          </button>

          {isExpanded && (
            <div className="mt-2 space-y-1">
              {tx.work_order_number && (
                <p className="text-[13px] text-txt-secondary leading-[1.6]">
                  Work order: <span className="font-medium text-txt-primary">{tx.work_order_number}</span>
                </p>
              )}
              {tx.stock_after !== undefined && (
                <p className="text-[13px] text-txt-tertiary leading-[1.6]">
                  Stock after: {tx.stock_after}
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
 * Transaction types: consume, receive, transfer, adjust, write_off
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
