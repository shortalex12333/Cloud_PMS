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
        // Height and padding - tokenized
        'min-h-[var(--celeste-spotlight-row-min-height)]',
        'py-[var(--celeste-spotlight-row-padding-y)] px-[var(--celeste-spotlight-row-padding-x)]',
        // Hover: very subtle
        'hover:bg-celeste-bg-tertiary/40',
        // Selected: subtle, not bold
        isSelected && 'bg-celeste-bg-tertiary/60',
        // Top match gets minimal distinction
        isTopMatch && !isSelected && 'bg-celeste-bg-tertiary/20'
      )}
    >
      {/* Left accent bar - subtle, appears on selection (OS feel) */}
      {isSelected && (
        <div
          className="absolute left-0 top-1/2 -translate-y-1/2 w-[var(--celeste-spotlight-accent-bar-width)] h-5 bg-celeste-accent rounded-r-sm"
          aria-hidden="true"
        />
      )}

      {/* Content - typography carries hierarchy, no icons */}
      <div className="flex flex-col gap-1">
        <p
          className={cn(
            // Title: slightly larger, medium weight for clarity
            'text-celeste-base font-medium leading-snug',
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
              // Subtitle: smaller, muted - clear hierarchy
              'text-celeste-sm font-normal leading-snug',
              'truncate',
              'text-celeste-text-muted'
            )}
          >
            {result.subtitle}
          </p>
        )}
      </div>
    </div>
  );
}
