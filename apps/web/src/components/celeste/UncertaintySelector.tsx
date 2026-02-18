'use client';

/**
 * UncertaintySelector
 * Shows parallel options when Celeste is uncertain.
 *
 * Rules (from UX spec):
 * - Equal visual weight
 * - Ordered by confidence
 * - No recommendation copy
 * - No "Did you mean"
 * - Once selected, the rest disappear
 * - No "you chose" messaging
 *
 * Brand tokens: bg-secondary, bg-tertiary, text colors
 */

import React from 'react';
import { cn } from '@/lib/utils';

export interface UncertainOption {
  id: string;
  type: string;
  value: string;
  confidence?: number; // For ordering, not display
}

interface UncertaintySelectorProps {
  options: UncertainOption[];
  onSelect: (option: UncertainOption) => void;
  className?: string;
}

export default function UncertaintySelector({
  options,
  onSelect,
  className,
}: UncertaintySelectorProps) {
  if (!options || options.length === 0) return null;

  // Sort by confidence if provided (descending)
  const sortedOptions = [...options].sort(
    (a, b) => (b.confidence ?? 0) - (a.confidence ?? 0)
  );

  return (
    <div
      className={cn(
        'px-4 py-3 font-body',
        className
      )}
    >
      <div className="text-sm text-txt-tertiary mb-2">
        Which did you mean?
      </div>

      <div className="space-y-1">
        {sortedOptions.map((option) => (
          <button
            key={option.id}
            onClick={() => onSelect(option)}
            className={cn(
              'w-full text-left',
              'px-3 py-2',
              'text-base text-txt-primary',
              'bg-surface-elevated hover:bg-surface-hover',
              'rounded-celeste-md',
              'transition-colors'
            )}
          >
            • {option.type}: {option.value}
          </button>
        ))}
      </div>
    </div>
  );
}
