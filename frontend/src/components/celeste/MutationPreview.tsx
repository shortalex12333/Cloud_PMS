'use client';

/**
 * MutationPreview
 * The most important screen in the system.
 * Shows only what will change as a diff.
 *
 * Rules (from UX spec):
 * - Show only what will change
 * - Use before → after
 * - No prose
 * - No justification
 * - No warnings
 *
 * If you cannot express the change as a diff, the action is invalid.
 */

import React from 'react';
import { cn } from '@/lib/utils';

export interface DiffItem {
  field: string;
  before: string | number;
  after: string | number;
}

interface MutationPreviewProps {
  diffs: DiffItem[];
  className?: string;
}

export default function MutationPreview({
  diffs,
  className,
}: MutationPreviewProps) {
  if (!diffs || diffs.length === 0) return null;

  return (
    <div
      className={cn(
        'p-4',
        'bg-[#1c1c1e]',
        'rounded-lg',
        className
      )}
      style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif' }}
    >
      <div className="space-y-3">
        {diffs.map((diff, i) => (
          <div key={i}>
            <div className="text-[11px] text-[#86868b] mb-1">
              {diff.field}
            </div>
            <div className="text-[14px] font-mono">
              <span className="text-[#98989f]">{String(diff.before)}</span>
              <span className="text-[#636366] mx-2">→</span>
              <span className="text-[#f5f5f7]">{String(diff.after)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
