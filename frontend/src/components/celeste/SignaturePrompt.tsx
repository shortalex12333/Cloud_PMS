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
        'fixed inset-0 z-50',
        'flex items-center justify-center',
        className
      )}
      style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif' }}
    >
      {/* Dim background */}
      <div
        className="absolute inset-0 bg-black/80"
        onClick={onCancel}
      />

      {/* Prompt */}
      <div className="relative w-full max-w-[400px] mx-4">
        {/* Preview remains visible */}
        <MutationPreview diffs={diffs} className="mb-4" />

        {/* Signature area - dominant */}
        <div className="bg-[#2c2c2e] rounded-lg p-6">
          <div className="text-center">
            <div className="text-[15px] text-[#f5f5f7] mb-1">
              Sign as {userName}
            </div>
            <div className="text-[12px] text-[#636366]">
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
                'text-[14px] text-[#86868b]',
                'bg-[#3d3d3f] hover:bg-[#48484a]',
                'rounded-lg',
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
                'text-[14px] text-white font-medium',
                'bg-[#0A84FF] hover:bg-[#409cff]',
                'rounded-lg',
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
