'use client';

/**
 * SpotlightResultRow
 * Apple Spotlight-inspired result row
 *
 * Design principles:
 * - No icons (typography carries hierarchy)
 * - Left accent bar for selection (OS feel, not SaaS)
 * - Subtle hover state
 * - Restraint and discipline
 */

import React from 'react';
import { cn } from '@/lib/utils';

// ============================================================================
// TYPES
// ============================================================================

interface SpotlightResult {
  id: string;
  type: string;
  title: string;
  subtitle: string;
  icon?: string;
  metadata?: Record<string, unknown>;
}

interface SpotlightResultRowProps {
  result: SpotlightResult;
  isSelected: boolean;
  index: number;
  onClick?: () => void;
  onDoubleClick?: () => void;
  /** Top Match gets slightly larger styling */
  isTopMatch?: boolean;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function SpotlightResultRow({
  result,
  isSelected,
  index,
  onClick,
  onDoubleClick,
  isTopMatch = false,
}: SpotlightResultRowProps) {
  return (
    <div
      data-index={index}
      data-testid="search-result-item"
      onClick={onClick}
      onDoubleClick={onDoubleClick}
      className={cn(
        // Base row styling
        'relative',
        'cursor-pointer select-none',
        'transition-colors duration-celeste-fast',
        // Height and padding
        'min-h-[52px] sm:min-h-[56px]',
        'py-2.5 px-5',
        // Hover: subtle background
        'hover:bg-celeste-accent-subtle',
        // Selected: slightly darker bg (not full teal block)
        isSelected && 'bg-celeste-accent-subtle',
        // Top match gets subtle distinction
        isTopMatch && !isSelected && 'bg-celeste-bg-tertiary/30'
      )}
    >
      {/* Left accent bar - appears on selection (OS feel) */}
      {isSelected && (
        <div
          className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-8 bg-celeste-accent rounded-r-sm"
          aria-hidden="true"
        />
      )}

      {/* Content - typography carries hierarchy, no icons */}
      <div className="flex flex-col gap-0.5">
        <p
          className={cn(
            // Title: text-celeste-base, weight 600
            'text-celeste-base font-semibold leading-tight',
            'truncate',
            isSelected
              ? 'text-celeste-text-title'
              : 'text-celeste-text-primary'
          )}
        >
          {result.title}
        </p>
        {result.subtitle && (
          <p
            className={cn(
              // Subline: text-celeste-sm, weight 400, muted
              'text-celeste-sm font-normal leading-tight',
              'truncate',
              'text-celeste-text-secondary'
            )}
          >
            {result.subtitle}
          </p>
        )}
      </div>
    </div>
  );
}
