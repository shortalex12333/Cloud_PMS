'use client';

/**
 * SuggestedActions Component
 *
 * Renders backend-provided action suggestions as buttons.
 * All actions, labels, and fields come from the backend - no UI authority.
 */

import React, { useState, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { PenLine, Check, Circle, Lock, X } from 'lucide-react';
import type { ActionSuggestion } from '@/lib/actionClient';
import type { IntentFilter } from '@/hooks/useCelesteSearch';
import ActionModal from '@/components/actions/ActionModal';

/**
 * FilterChips Component
 *
 * Displays route segments as visual filter chips.
 * Each chip represents a filter that affects the current view.
 *
 * Example: For route /work-orders/status/open
 * Renders: [status: open] chip
 */
interface FilterChipsProps {
  filters: IntentFilter[];
  onRemove?: (filter: IntentFilter) => void;
  className?: string;
}

function FilterChips({ filters, onRemove, className }: FilterChipsProps) {
  if (!filters || filters.length === 0) {
    return null;
  }

  return (
    <div
      className={cn(
        'flex flex-wrap gap-1.5 px-4 py-1.5',
        className
      )}
      data-testid="filter-chips"
    >
      {filters.map((filter, idx) => (
        <span
          key={`${filter.field}-${filter.value}-${idx}`}
          className={cn(
            'inline-flex items-center gap-1 px-2 py-0.5 rounded-md',
            'typo-meta',
            'bg-celeste-accent/10 text-celeste-accent border border-celeste-accent/20'
          )}
          data-testid={`filter-chip-${filter.field}`}
        >
          <span className="text-txt-secondary">{filter.field}:</span>
          <span className="font-medium">{filter.value}</span>
          {onRemove && (
            <button
              type="button"
              onClick={() => onRemove(filter)}
              className="ml-0.5 hover:text-txt-primary transition-colors"
              aria-label={`Remove ${filter.field} filter`}
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </span>
      ))}
    </div>
  );
}

interface SuggestedActionsProps {
  actions: ActionSuggestion[];
  yachtId: string | null;
  onActionComplete?: () => void;
  className?: string;
  // NEW: Map of action_id to readiness state
  readinessStates?: Record<string, 'READY' | 'NEEDS_INPUT' | 'BLOCKED'>;
  // NEW: Prefill data for deriving readiness
  prefillData?: Record<string, any> | null;
  // NEW: Filter chips for READ navigation
  filters?: IntentFilter[];
  canonicalRoute?: string;
  onFilterRemove?: (filter: IntentFilter) => void;
  onNavigate?: (route: string) => void;
}

/**
 * Get visual indicator for action readiness state
 * Per READY-04: green checkmark (READY), amber dot (NEEDS_INPUT), lock (BLOCKED)
 */
function ReadinessIndicator({ state }: { state: 'READY' | 'NEEDS_INPUT' | 'BLOCKED' | undefined }) {
  switch (state) {
    case 'READY':
      return (
        <Check
          className="w-3.5 h-3.5 text-emerald-400"
          aria-label="Ready to execute"
        />
      );
    case 'NEEDS_INPUT':
      return (
        <Circle
          className="w-2.5 h-2.5 fill-amber-400 text-amber-400"
          aria-label="Requires input"
        />
      );
    case 'BLOCKED':
      return (
        <Lock
          className="w-3.5 h-3.5 text-red-400"
          aria-label="Permission required"
        />
      );
    default:
      // Unknown state - show amber dot as default (needs input)
      return (
        <Circle
          className="w-2.5 h-2.5 fill-amber-400/50 text-amber-400/50"
          aria-label="Checking..."
        />
      );
  }
}

export default function SuggestedActions({
  actions,
  yachtId,
  onActionComplete,
  className,
  readinessStates = {},
  prefillData,
  filters = [],
  canonicalRoute,
  onFilterRemove,
  onNavigate,
}: SuggestedActionsProps) {
  const [selectedAction, setSelectedAction] = useState<ActionSuggestion | null>(null);

  // Navigation handler for READ mode
  const handleNavigate = useCallback(() => {
    if (canonicalRoute && onNavigate) {
      onNavigate(canonicalRoute);
    }
  }, [canonicalRoute, onNavigate]);

  const handleActionClick = (action: ActionSuggestion) => {
    setSelectedAction(action);
  };

  const handleModalClose = () => {
    setSelectedAction(null);
  };

  const handleActionSuccess = () => {
    setSelectedAction(null);
    onActionComplete?.();
  };

  return (
    <>
      {/* Filter Chips for READ navigation */}
      {filters.length > 0 && (
        <FilterChips
          filters={filters}
          onRemove={onFilterRemove}
          className="border-b border-surface-border/30"
        />
      )}

      {/* Navigate button for READ mode with filters */}
      {canonicalRoute && filters.length > 0 && onNavigate && (
        <div className="flex items-center gap-2 px-4 py-2 border-b border-surface-border/30">
          <button
            onClick={handleNavigate}
            className={cn(
              'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg',
              'typo-meta font-medium',
              'bg-brand-interactive/20 text-brand-interactive border border-brand-interactive/30',
              'hover:bg-brand-interactive/30 transition-colors'
            )}
            data-testid="navigate-btn"
          >
            Navigate to {canonicalRoute.split('?')[0]}
          </button>
        </div>
      )}

      {/* Existing actions rendering */}
      {actions && actions.length > 0 && (
        <div
          className={cn(
            'flex flex-wrap gap-2 px-4 py-2 border-b border-surface-border/30',
            className
          )}
          data-testid="suggested-actions"
        >
          <span className="typo-meta text-txt-secondary self-center mr-1">
            Actions:
          </span>
          {actions.map((action) => {
          const readiness = readinessStates[action.action_id];
          const isBlocked = readiness === 'BLOCKED';

          return (
            <button
              key={action.action_id}
              onClick={() => !isBlocked && handleActionClick(action)}
              disabled={isBlocked}
              className={cn(
                'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg',
                'typo-meta font-medium',
                'transition-colors',
                'border',
                // Readiness-based styling
                readiness === 'READY' && 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/30',
                readiness === 'NEEDS_INPUT' && 'bg-celeste-accent/20 text-celeste-accent border-celeste-accent/30 hover:bg-celeste-accent/30',
                readiness === 'BLOCKED' && 'bg-red-500/10 text-red-400/70 border-red-500/20 cursor-not-allowed opacity-75',
                // Default styling when no readiness state yet
                !readiness && 'bg-celeste-accent/20 text-celeste-accent border-celeste-accent/30 hover:bg-celeste-accent/30',
                // SIGNED variant override (signature pen icon takes precedence)
                action.variant === 'SIGNED' && !isBlocked && 'border-amber-500/50 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20'
              )}
              data-testid={`action-btn-${action.action_id}`}
              title={isBlocked ? 'You do not have permission for this action' : undefined}
            >
              {/* Readiness indicator */}
              <ReadinessIndicator state={readiness} />

              {/* Action label */}
              {action.label}

              {/* Signature indicator (SIGNED variant) */}
              {action.variant === 'SIGNED' && !isBlocked && (
                <PenLine className="w-3.5 h-3.5" aria-label="Requires signature" />
              )}
            </button>
          );
        })}
        </div>
      )}

      {/* Action Modal */}
      {selectedAction && (
        <ActionModal
          action={selectedAction}
          yachtId={yachtId}
          onClose={handleModalClose}
          onSuccess={handleActionSuccess}
        />
      )}
    </>
  );
}
