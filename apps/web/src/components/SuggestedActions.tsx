'use client';

/**
 * SuggestedActions Component
 *
 * Renders backend-provided action suggestions as buttons.
 * All actions, labels, and fields come from the backend - no UI authority.
 */

import React, { useState } from 'react';
import { cn } from '@/lib/utils';
import { PenLine, Check, Circle, Lock } from 'lucide-react';
import type { ActionSuggestion } from '@/lib/actionClient';
import ActionModal from '@/components/actions/ActionModal';

interface SuggestedActionsProps {
  actions: ActionSuggestion[];
  yachtId: string | null;
  onActionComplete?: () => void;
  className?: string;
  // NEW: Map of action_id to readiness state
  readinessStates?: Record<string, 'READY' | 'NEEDS_INPUT' | 'BLOCKED'>;
  // NEW: Prefill data for deriving readiness
  prefillData?: Record<string, any> | null;
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
}: SuggestedActionsProps) {
  const [selectedAction, setSelectedAction] = useState<ActionSuggestion | null>(null);

  if (!actions || actions.length === 0) {
    return null;
  }

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
