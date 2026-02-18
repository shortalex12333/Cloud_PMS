'use client';

/**
 * SignaturePrompt
 * Ownership transfer - this is not "confirm", this is ownership.
 *
 * Rules (from UX spec):
 * - UI dims
 * - Preview remains visible
 * - Signature prompt is dominant
 * - No other actions visible
 *
 * This is the moment responsibility moves to the human.
 *
 * Brand tokens: bg-secondary, blue for commit, text colors
 */

import React from 'react';
import { cn } from '@/lib/utils';
import MutationPreview, { DiffItem } from './MutationPreview';

interface SignaturePromptProps {
  diffs: DiffItem[];
  userName: string;
  onSign: () => void;
  onCancel: () => void;
  isCommitting?: boolean;
  className?: string;
}

export default function SignaturePrompt({
  diffs,
  userName,
  onSign,
  onCancel,
  isCommitting = false,
  className,
}: SignaturePromptProps) {
  return (
    <div
      className={cn(
        'fixed inset-0 z-50 font-body',
        'flex items-center justify-center',
        className
      )}
    >
      {/* Dim background */}
      <div
        className="absolute inset-0 bg-black/80"
        onClick={onCancel}
      />

      {/* Prompt */}
      <div className="relative w-full max-w-celeste-modal mx-4">
        {/* Preview remains visible */}
        <MutationPreview diffs={diffs} className="mb-4" />

        {/* Signature area - dominant */}
        <div className="bg-surface-elevated rounded-celeste-md p-6">
          <div className="text-center">
            <div className="text-lg text-txt-primary mb-1">
              Sign as {userName}
            </div>
            <div className="text-sm text-txt-tertiary">
              This action will be recorded
            </div>
          </div>

          <div className="mt-6 flex gap-3">
            {/* Cancel - always visible, always immediate */}
            <button
              onClick={onCancel}
              disabled={isCommitting}
              className={cn(
                'flex-1 py-2.5',
                'text-base text-txt-tertiary',
                'bg-surface-hover hover:bg-surface-border',
                'rounded-celeste-md',
                'transition-colors',
                isCommitting && 'opacity-50 cursor-not-allowed'
              )}
            >
              Cancel
            </button>

            {/* Sign - commitment action */}
            <button
              onClick={onSign}
              disabled={isCommitting}
              className={cn(
                'flex-1 py-2.5',
                'text-base text-white font-medium',
                'bg-brand-interactive hover:bg-brand-interactive-hover',
                'rounded-celeste-md',
                'transition-colors',
                isCommitting && 'opacity-50 cursor-not-allowed'
              )}
            >
              {isCommitting ? 'Updating…' : 'Sign'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
