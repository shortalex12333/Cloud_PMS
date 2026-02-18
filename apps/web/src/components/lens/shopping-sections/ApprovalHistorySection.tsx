'use client';

/**
 * ApprovalHistorySection - Audit log for shopping list approval actions.
 *
 * Used inside ShoppingListLens.
 *
 * Features:
 * - Chronological list of approve/reject/create/order actions
 * - Actor name, timestamp (relative/absolute per UI_SPEC.md)
 * - Item name shown for per-item actions
 * - Read-only — no action button
 * - Empty state: "No history yet" (spec note: always has creation entry in practice)
 *
 * FE-03-05: Shopping List Lens Rebuild
 */

import * as React from 'react';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { CheckCircle2, XCircle, PlusCircle, ShoppingCart, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ShoppingListAuditEntry } from '../types';

// ============================================================================
// TYPES
// ============================================================================

export interface ApprovalHistorySectionProps {
  history: ShoppingListAuditEntry[];
  /** Top offset for sticky header (56 when inside lens) */
  stickyTop?: number;
}

// ============================================================================
// HELPERS
// ============================================================================

/**
 * Format timestamp per UI_SPEC.md:
 * - Today: "Today at 14:32"
 * - Within 7 days: "Yesterday", "N days ago"
 * - Older: "Jan 23, 2026"
 */
function formatTimestamp(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

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
 * Map action name to icon and color.
 */
function getActionConfig(action: string): {
  icon: React.ReactNode;
  color: string;
  label: string;
} {
  switch (action) {
    case 'approve_item':
    case 'approve_shopping_list_item':
      return {
        icon: <CheckCircle2 className="w-4 h-4" />,
        color: 'text-status-success',
        label: 'Approved',
      };
    case 'reject_item':
    case 'reject_shopping_list_item':
      return {
        icon: <XCircle className="w-4 h-4" />,
        color: 'text-status-critical',
        label: 'Rejected',
      };
    case 'create_item':
    case 'create_shopping_list_item':
      return {
        icon: <PlusCircle className="w-4 h-4" />,
        color: 'text-brand-interactive',
        label: 'Added',
      };
    case 'mark_ordered':
      return {
        icon: <ShoppingCart className="w-4 h-4" />,
        color: 'text-status-success',
        label: 'Ordered',
      };
    default:
      return {
        icon: <Clock className="w-4 h-4" />,
        color: 'text-txt-secondary',
        label: action
          .split('_')
          .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
          .join(' '),
      };
  }
}

// ============================================================================
// COMPONENT
// ============================================================================

/**
 * ApprovalHistorySection — Read-only audit log for the shopping list.
 */
export function ApprovalHistorySection({
  history,
  stickyTop = 0,
}: ApprovalHistorySectionProps) {
  return (
    <SectionContainer
      title="Approval History"
      stickyTop={stickyTop}
      // Read-only — no action button per spec
    >
      {history.length === 0 ? (
        /* Defensive empty state — per decision: "HistorySection has defensive empty state" */
        <div className="py-8 text-center text-txt-secondary text-[14px]">
          No approval history yet
        </div>
      ) : (
        <ol className="space-y-0" aria-label="Approval history">
          {history.map((entry, index) => {
            const config = getActionConfig(entry.action);
            const isLast = index === history.length - 1;

            return (
              <li
                key={entry.id}
                className={cn(
                  'relative flex gap-3 pb-4',
                  // Timeline connector line (not on last item)
                  !isLast && [
                    'before:absolute before:left-[15px] before:top-7 before:bottom-0',
                    'before:w-px before:bg-surface-border before:content-[""]',
                  ]
                )}
              >
                {/* Action icon — colored circle */}
                <div
                  className={cn(
                    'mt-0.5 flex-shrink-0 w-8 h-8 rounded-full',
                    'flex items-center justify-center',
                    'bg-surface-secondary border border-surface-border',
                    config.color
                  )}
                  aria-hidden="true"
                >
                  {config.icon}
                </div>

                {/* Entry content */}
                <div className="flex-1 min-w-0 pt-1">
                  <div className="flex items-baseline gap-2 flex-wrap">
                    {/* Action label */}
                    <span
                      className={cn('text-[13px] font-semibold', config.color)}
                    >
                      {config.label}
                    </span>

                    {/* Item name (for per-item actions) */}
                    {entry.item_name && (
                      <span className="text-[13px] text-txt-primary font-medium">
                        {entry.item_name}
                      </span>
                    )}

                    {/* Actor */}
                    {entry.actor_name && (
                      <span className="text-[13px] text-txt-secondary">
                        by {entry.actor_name}
                      </span>
                    )}

                    {/* Timestamp */}
                    <time
                      dateTime={entry.timestamp}
                      className="text-[12px] text-txt-muted ml-auto"
                      title={new Date(entry.timestamp).toLocaleString()}
                    >
                      {formatTimestamp(entry.timestamp)}
                    </time>
                  </div>

                  {/* Details (e.g. rejection reason) */}
                  {entry.details && (
                    <p className="mt-1 text-[13px] text-txt-secondary">
                      {entry.details}
                    </p>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </SectionContainer>
  );
}
