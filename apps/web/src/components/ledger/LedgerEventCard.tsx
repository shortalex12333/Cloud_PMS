'use client';

/**
 * LedgerEventCard
 * ================
 *
 * Renders a single ledger event as a clickable card.
 *
 * Supports navigation to entity lenses via handleLedgerClick().
 * For handover_export entities, routes to HandoverExportLens with:
 * - mode=edit  for export_ready_for_review events
 * - mode=review for requires_countersignature events
 */

import React from 'react';
import { useRouter } from 'next/navigation';
import { FileText, Pen, Circle, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatRelativeTime } from '@/lib/utils';
import { handleLedgerClick, ENTITY_ROUTES } from '@/lib/ledgerNavigation';

// ============================================================================
// TYPES
// ============================================================================

export interface LedgerEvent {
  id: string;
  yacht_id: string;
  user_id: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  action: string;
  change_summary?: string;
  user_role?: string;
  metadata: {
    domain?: string;
    user_name?: string;
    item_count?: number;
    status?: string;
    [key: string]: unknown;
  } | null;
  created_at: string;
}

// ============================================================================
// ICON MAPPING
// ============================================================================

const EVENT_ICONS: Record<string, React.ReactNode> = {
  handover_export_ready: <FileText className="w-4 h-4" />,
  handover_pending_countersign: <Pen className="w-4 h-4" />,
};

// ============================================================================
// COLOR MAPPING
// ============================================================================

const EVENT_COLORS: Record<string, string> = {
  handover_export_ready: 'text-brand-interactive',
  export_ready_for_review: 'text-brand-interactive',
  requires_countersignature: 'text-status-warning',
};

// ============================================================================
// COMPONENT
// ============================================================================

interface LedgerEventCardProps {
  event: LedgerEvent;
}

export function LedgerEventCard({ event }: LedgerEventCardProps) {
  const router = useRouter();

  const handleClick = () => {
    if (event.entity_type && event.entity_id) {
      handleLedgerClick(
        event.entity_type,
        event.entity_id,
        event.action,
        router
      );
    }
  };

  const isClickable = Boolean(
    event.entity_type &&
    event.entity_id &&
    ENTITY_ROUTES[event.entity_type]
  );

  // Resolve icon: try event_type first, then action, then fallback
  const iconColor = EVENT_COLORS[event.event_type] || EVENT_COLORS[event.action] || 'text-txt-secondary';
  const icon =
    EVENT_ICONS[event.event_type] ||
    EVENT_ICONS[event.action] ||
    <Circle className="w-4 h-4" />;

  return (
    <div
      className={cn(
        'p-3 rounded-lg bg-surface-secondary',
        isClickable && 'cursor-pointer hover:bg-surface-tertiary transition-colors'
      )}
      onClick={isClickable ? handleClick : undefined}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={isClickable ? (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleClick();
        }
      } : undefined}
    >
      <div className="flex items-start gap-3">
        <div className={cn('flex-shrink-0 mt-0.5', iconColor)}>
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-txt-primary">
            {event.change_summary || event.event_type}
          </p>
          <p className="text-xs text-txt-tertiary mt-1">
            {formatRelativeTime(event.created_at)}
          </p>
        </div>
        {isClickable && (
          <ChevronRight className="w-4 h-4 text-txt-tertiary flex-shrink-0" />
        )}
      </div>
    </div>
  );
}

export default LedgerEventCard;
