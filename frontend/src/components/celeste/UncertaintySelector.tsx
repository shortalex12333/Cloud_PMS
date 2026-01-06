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
        'px-4 py-3',
        className
      )}
      style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif' }}
    >
      <div className="text-[12px] text-[#86868b] mb-2">
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
              'text-[13px] text-[#f5f5f7]',
              'bg-[#2c2c2e] hover:bg-[#3d3d3f]',
              'rounded-lg',
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
