'use client';

/**
 * SuggestedActions Component
 *
 * Renders backend-provided action suggestions as buttons.
 * All actions, labels, and fields come from the backend - no UI authority.
 */

import React, { useState } from 'react';
import { cn } from '@/lib/utils';
import { PenLine } from 'lucide-react';
import type { ActionSuggestion } from '@/lib/actionClient';
import ActionModal from '@/components/actions/ActionModal';

interface SuggestedActionsProps {
  actions: ActionSuggestion[];
  yachtId: string | null;
  onActionComplete?: () => void;
  className?: string;
}

export default function SuggestedActions({
  actions,
  yachtId,
  onActionComplete,
  className,
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
        {actions.map((action) => (
          <button
            key={action.action_id}
            onClick={() => handleActionClick(action)}
            className={cn(
              'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg',
              'typo-meta font-medium',
              'bg-celeste-accent/20 text-celeste-accent',
              'hover:bg-celeste-accent/30 transition-colors',
              'border border-celeste-accent/30',
              action.variant === 'SIGNED' && 'border-amber-500/50 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20'
            )}
            data-testid={`action-btn-${action.action_id}`}
          >
            {action.label}
            {action.variant === 'SIGNED' && (
              <PenLine className="w-3.5 h-3.5" aria-label="Requires signature" />
            )}
          </button>
        ))}
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
