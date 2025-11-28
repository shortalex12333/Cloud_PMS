'use client';

/**
 * SpotlightResultRow
 * Individual result row in the Spotlight search
 *
 * Anatomy:
 * [Icon] [Title/Subtitle] [Confidence Bar] [Microactions]
 */

import React, { useState, useCallback } from 'react';
import { ChevronRight, MoreHorizontal } from 'lucide-react';
import { cn } from '@/lib/utils';
import { MicroAction, ACTION_REGISTRY } from '@/types/actions';
import MicroactionButton from './MicroactionButton';

// ============================================================================
// TYPES
// ============================================================================

interface SearchResult {
  id: string;
  type: string;
  title: string;
  subtitle: string;
  confidence: number;
  actions: MicroAction[];
  metadata?: Record<string, any>;
}

interface SpotlightResultRowProps {
  result: SearchResult;
  isSelected: boolean;
  index: number;
  icon: React.ElementType;
  typeLabel: string;
  onClick?: () => void;
  onDoubleClick?: () => void;
}

// ============================================================================
// CONFIDENCE BAR
// ============================================================================

function ConfidenceBar({ value }: { value: number }) {
  const getColor = () => {
    if (value >= 80) return 'bg-emerald-500';
    if (value >= 50) return 'bg-amber-500';
    return 'bg-red-500';
  };

  return (
    <div className="flex items-center gap-1.5">
      <div className="w-10 h-1 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all duration-300', getColor())}
          style={{ width: `${value}%` }}
        />
      </div>
      <span className="text-[10px] text-zinc-400 dark:text-zinc-500 font-medium tabular-nums">
        {value}%
      </span>
    </div>
  );
}

// ============================================================================
// CARD TYPE COLORS
// ============================================================================

const CARD_TYPE_COLORS: Record<string, string> = {
  fault: 'bg-red-500',
  work_order: 'bg-blue-500',
  equipment: 'bg-violet-500',
  part: 'bg-emerald-500',
  handover: 'bg-amber-500',
  document: 'bg-indigo-500',
  hor_table: 'bg-pink-500',
  purchase: 'bg-teal-500',
  checklist: 'bg-lime-500',
  worklist: 'bg-orange-500',
  fleet_summary: 'bg-cyan-500',
  smart_summary: 'bg-purple-500',
};

// ============================================================================
// COMPONENT
// ============================================================================

export default function SpotlightResultRow({
  result,
  isSelected,
  index,
  icon: Icon,
  typeLabel,
  onClick,
  onDoubleClick,
}: SpotlightResultRowProps) {
  const [showAllActions, setShowAllActions] = useState(false);
  const [hoveredAction, setHoveredAction] = useState<string | null>(null);

  // Show max 3 actions by default, with overflow indicator
  const visibleActions = result.actions.slice(0, 3);
  const overflowCount = result.actions.length - 3;
  const hasOverflow = overflowCount > 0;

  const handleActionClick = useCallback((action: MicroAction, e: React.MouseEvent) => {
    e.stopPropagation();
    console.log('Execute action:', action, 'on:', result.id);
  }, [result.id]);

  const handleOverflowClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setShowAllActions(!showAllActions);
  }, [showAllActions]);

  return (
    <div
      data-index={index}
      onClick={onClick}
      onDoubleClick={onDoubleClick}
      className={cn(
        'group relative flex items-center gap-3',
        'px-4 py-2.5 min-h-[56px]',
        'cursor-pointer select-none',
        'transition-colors duration-100',
        isSelected
          ? 'bg-blue-500/10 dark:bg-blue-500/20'
          : 'hover:bg-zinc-100/80 dark:hover:bg-zinc-800/80'
      )}
    >
      {/* Selection indicator */}
      {isSelected && (
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-8 bg-blue-500 rounded-r-full" />
      )}

      {/* Icon */}
      <div
        className={cn(
          'flex-shrink-0 flex items-center justify-center',
          'w-8 h-8 rounded-lg',
          CARD_TYPE_COLORS[result.type] || 'bg-zinc-500',
          'shadow-sm'
        )}
      >
        <Icon className="h-4 w-4 text-white" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'text-[15px] font-medium truncate',
              'text-zinc-900 dark:text-zinc-100'
            )}
          >
            {result.title}
          </span>
          <span
            className={cn(
              'flex-shrink-0 px-1.5 py-0.5 rounded',
              'text-[10px] font-medium uppercase tracking-wide',
              'bg-zinc-200/80 dark:bg-zinc-700/80',
              'text-zinc-500 dark:text-zinc-400'
            )}
          >
            {typeLabel}
          </span>
        </div>
        <p
          className={cn(
            'text-[13px] truncate',
            'text-zinc-500 dark:text-zinc-400'
          )}
        >
          {result.subtitle}
        </p>
      </div>

      {/* Confidence bar */}
      <div className="flex-shrink-0 hidden sm:block">
        <ConfidenceBar value={result.confidence} />
      </div>

      {/* Microactions */}
      <div
        className={cn(
          'flex-shrink-0 flex items-center gap-1',
          'opacity-0 group-hover:opacity-100 transition-opacity duration-150',
          isSelected && 'opacity-100'
        )}
      >
        {visibleActions.map((action) => (
          <MicroactionButton
            key={action}
            action={action}
            size="sm"
            onClick={(e) => handleActionClick(action, e)}
            onMouseEnter={() => setHoveredAction(action)}
            onMouseLeave={() => setHoveredAction(null)}
          />
        ))}

        {/* Overflow button */}
        {hasOverflow && (
          <button
            onClick={handleOverflowClick}
            className={cn(
              'flex items-center justify-center',
              'h-6 w-6 rounded-md',
              'bg-zinc-100 dark:bg-zinc-800',
              'hover:bg-zinc-200 dark:hover:bg-zinc-700',
              'text-zinc-500 dark:text-zinc-400',
              'transition-colors duration-100'
            )}
            title={`${overflowCount} more actions`}
          >
            <MoreHorizontal className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {/* Chevron indicator */}
      <ChevronRight
        className={cn(
          'flex-shrink-0 h-4 w-4',
          'text-zinc-300 dark:text-zinc-600',
          'opacity-0 group-hover:opacity-100 transition-opacity duration-150',
          isSelected && 'opacity-100'
        )}
      />

      {/* Expanded actions dropdown */}
      {showAllActions && hasOverflow && (
        <div
          className={cn(
            'absolute right-4 top-full z-20',
            'mt-1 p-1.5 rounded-lg',
            'bg-white dark:bg-zinc-900',
            'border border-zinc-200 dark:border-zinc-700',
            'shadow-lg',
            'min-w-[160px]'
          )}
          onClick={(e) => e.stopPropagation()}
        >
          {result.actions.slice(3).map((action) => {
            const metadata = ACTION_REGISTRY[action];
            return (
              <button
                key={action}
                onClick={(e) => handleActionClick(action, e)}
                className={cn(
                  'w-full flex items-center gap-2',
                  'px-2 py-1.5 rounded-md',
                  'text-left text-[13px]',
                  'text-zinc-700 dark:text-zinc-300',
                  'hover:bg-zinc-100 dark:hover:bg-zinc-800',
                  'transition-colors duration-100'
                )}
              >
                <span className="text-zinc-500">{metadata?.label || action}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
