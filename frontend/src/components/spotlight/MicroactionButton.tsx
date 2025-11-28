'use client';

/**
 * MicroactionButton
 * Compact action button for Spotlight results and cards
 *
 * Sizes:
 * - sm: 24px height, for inline result rows
 * - md: 28px height, for cards
 * - lg: 32px height, for detail views
 *
 * States:
 * - default, hover, active, disabled, loading
 */

import React, { useState, useCallback } from 'react';
import * as LucideIcons from 'lucide-react';
import { cn } from '@/lib/utils';
import { MicroAction, ACTION_REGISTRY, ActionMetadata } from '@/types/actions';

// ============================================================================
// TYPES
// ============================================================================

type ButtonSize = 'sm' | 'md' | 'lg';

interface MicroactionButtonProps {
  action: MicroAction;
  size?: ButtonSize;
  showLabel?: boolean;
  disabled?: boolean;
  loading?: boolean;
  variant?: 'default' | 'primary' | 'danger';
  onClick?: (e: React.MouseEvent) => void;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
  className?: string;
}

// ============================================================================
// SIZE SPECIFICATIONS
// ============================================================================

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'h-6 min-w-6 px-1.5 text-[11px] gap-1',
  md: 'h-7 min-w-7 px-2 text-[12px] gap-1.5',
  lg: 'h-8 min-w-8 px-2.5 text-[13px] gap-1.5',
};

const iconSizes: Record<ButtonSize, number> = {
  sm: 12,
  md: 14,
  lg: 16,
};

// ============================================================================
// VARIANT CLASSES
// ============================================================================

const variantClasses = {
  default: cn(
    'bg-zinc-100 dark:bg-zinc-800',
    'hover:bg-zinc-200 dark:hover:bg-zinc-700',
    'active:bg-zinc-300 dark:active:bg-zinc-600',
    'text-zinc-600 dark:text-zinc-300',
    'border border-zinc-200/60 dark:border-zinc-700/60'
  ),
  primary: cn(
    'bg-blue-500 hover:bg-blue-600 active:bg-blue-700',
    'text-white',
    'border border-blue-600'
  ),
  danger: cn(
    'bg-red-500/10 hover:bg-red-500/20 active:bg-red-500/30',
    'text-red-600 dark:text-red-400',
    'border border-red-500/30'
  ),
};

// ============================================================================
// COMPONENT
// ============================================================================

export default function MicroactionButton({
  action,
  size = 'md',
  showLabel = false,
  disabled = false,
  loading = false,
  variant = 'default',
  onClick,
  onMouseEnter,
  onMouseLeave,
  className,
}: MicroactionButtonProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  const metadata = ACTION_REGISTRY[action];
  if (!metadata) {
    console.warn(`Unknown action: ${action}`);
    return null;
  }

  // Get icon component
  const iconName = metadata.icon || 'Circle';
  const IconComponent = (LucideIcons as any)[iconName] || LucideIcons.Circle;
  const iconSize = iconSizes[size];

  // Handle tooltip
  const handleMouseEnter = useCallback(() => {
    setShowTooltip(true);
    onMouseEnter?.();
  }, [onMouseEnter]);

  const handleMouseLeave = useCallback(() => {
    setShowTooltip(false);
    onMouseLeave?.();
  }, [onMouseLeave]);

  // Determine variant based on side effect type
  const effectiveVariant = variant !== 'default' ? variant :
    metadata.side_effect_type === 'mutation_heavy' ? 'primary' : 'default';

  return (
    <div className="relative">
      <button
        onClick={onClick}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        disabled={disabled || loading}
        className={cn(
          'inline-flex items-center justify-center',
          'rounded-md',
          'font-medium',
          'transition-all duration-100',
          'shadow-[0_1px_2px_rgba(0,0,0,0.05)]',
          'hover:shadow-[0_2px_6px_rgba(0,0,0,0.10)]',
          'active:shadow-[inset_0_1px_2px_rgba(0,0,0,0.08)]',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          'focus:outline-none focus:ring-2 focus:ring-blue-500/40',
          sizeClasses[size],
          variantClasses[effectiveVariant],
          className
        )}
        aria-label={metadata.label}
      >
        {loading ? (
          <LucideIcons.Loader2
            className="animate-spin"
            size={iconSize}
          />
        ) : (
          <IconComponent size={iconSize} />
        )}
        {showLabel && (
          <span className="truncate">{metadata.label}</span>
        )}
      </button>

      {/* Tooltip */}
      {showTooltip && !showLabel && (
        <div
          className={cn(
            'absolute z-50',
            'left-1/2 -translate-x-1/2',
            'bottom-full mb-1.5',
            'px-2 py-1 rounded-md',
            'bg-zinc-900 dark:bg-zinc-100',
            'text-white dark:text-zinc-900',
            'text-[11px] font-medium',
            'whitespace-nowrap',
            'shadow-lg',
            'pointer-events-none',
            'animate-in fade-in-0 zoom-in-95 duration-100'
          )}
        >
          {metadata.label}
          {/* Arrow */}
          <div
            className={cn(
              'absolute left-1/2 -translate-x-1/2',
              'top-full',
              'w-0 h-0',
              'border-l-[5px] border-l-transparent',
              'border-r-[5px] border-r-transparent',
              'border-t-[5px] border-t-zinc-900 dark:border-t-zinc-100'
            )}
          />
        </div>
      )}
    </div>
  );
}

// ============================================================================
// MICROACTION GROUP
// ============================================================================

interface MicroactionGroupProps {
  actions: MicroAction[];
  size?: ButtonSize;
  maxVisible?: number;
  showLabels?: boolean;
  onAction?: (action: MicroAction) => void;
  className?: string;
}

export function MicroactionGroup({
  actions,
  size = 'md',
  maxVisible = 3,
  showLabels = false,
  onAction,
  className,
}: MicroactionGroupProps) {
  const [showOverflow, setShowOverflow] = useState(false);

  const visibleActions = actions.slice(0, maxVisible);
  const overflowActions = actions.slice(maxVisible);
  const hasOverflow = overflowActions.length > 0;

  return (
    <div className={cn('flex items-center gap-1', className)}>
      {visibleActions.map((action) => (
        <MicroactionButton
          key={action}
          action={action}
          size={size}
          showLabel={showLabels}
          onClick={() => onAction?.(action)}
        />
      ))}

      {hasOverflow && (
        <div className="relative">
          <button
            onClick={() => setShowOverflow(!showOverflow)}
            className={cn(
              'inline-flex items-center justify-center',
              'rounded-md',
              'transition-all duration-100',
              sizeClasses[size],
              variantClasses.default
            )}
          >
            <LucideIcons.MoreHorizontal size={iconSizes[size]} />
          </button>

          {showOverflow && (
            <div
              className={cn(
                'absolute right-0 top-full z-50',
                'mt-1 p-1 rounded-lg',
                'bg-white dark:bg-zinc-900',
                'border border-zinc-200 dark:border-zinc-700',
                'shadow-lg',
                'min-w-[140px]'
              )}
            >
              {overflowActions.map((action) => {
                const meta = ACTION_REGISTRY[action];
                const Icon = (LucideIcons as any)[meta?.icon || 'Circle'] || LucideIcons.Circle;

                return (
                  <button
                    key={action}
                    onClick={() => {
                      onAction?.(action);
                      setShowOverflow(false);
                    }}
                    className={cn(
                      'w-full flex items-center gap-2',
                      'px-2 py-1.5 rounded-md',
                      'text-left text-[13px]',
                      'text-zinc-700 dark:text-zinc-300',
                      'hover:bg-zinc-100 dark:hover:bg-zinc-800',
                      'transition-colors duration-100'
                    )}
                  >
                    <Icon size={14} className="text-zinc-400" />
                    <span>{meta?.label || action}</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
