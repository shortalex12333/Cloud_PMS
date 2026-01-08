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
 *
 * Brand tokens: bg-primary, text colors, font-mono for diffs
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
        'p-4 font-body',
        'bg-celeste-bg-primary',
        'rounded-celeste-md',
        className
      )}
    >
      <div className="space-y-3">
        {diffs.map((diff, i) => (
          <div key={i}>
            <div className="text-celeste-xs text-celeste-text-muted mb-1">
              {diff.field}
            </div>
            <div className="text-celeste-md font-mono">
              <span className="text-celeste-text-secondary">{String(diff.before)}</span>
              <span className="text-celeste-text-disabled mx-2">→</span>
              <span className="text-celeste-text-primary">{String(diff.after)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
