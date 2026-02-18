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
 *
 * Brand compliance:
 * - No decorative tooltips (using native title instead)
 * - Uses celeste brand tokens
 */

import React, { useState } from 'react';
import * as LucideIcons from 'lucide-react';
import { cn } from '@/lib/utils';
import { MicroAction, ACTION_REGISTRY } from '@/types/actions';

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
  sm: 'h-6 min-w-6 px-1.5 text-xs gap-1',
  md: 'h-7 min-w-7 px-2 text-sm gap-1.5',
  lg: 'h-8 min-w-8 px-2.5 text-base gap-1.5',
};

const iconSizes: Record<ButtonSize, number> = {
  sm: 12,
  md: 14,
  lg: 16,
};

// ============================================================================
// VARIANT CLASSES - Using celeste brand tokens
// ============================================================================

const variantClasses = {
  default: cn(
    'bg-surface-hover',
    'hover:bg-surface-active',
    'active:bg-surface-border',
    'text-txt-secondary',
    'border border-surface-border'
  ),
  primary: cn(
    'bg-brand-interactive hover:bg-brand-hover active:bg-brand-interactive',
    'text-white',
    'border border-brand-interactive'
  ),
  danger: cn(
    'bg-restricted-red/10 hover:bg-restricted-red/20 active:bg-restricted-red/30',
    'text-restricted-red',
    'border border-restricted-red/30'
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
  const metadata = ACTION_REGISTRY[action];
  if (!metadata) {
    console.warn(`Unknown action: ${action}`);
    return null;
  }

  // Get icon component
  const iconName = metadata.icon || 'Circle';
  const IconComponent = (LucideIcons as any)[iconName] || LucideIcons.Circle;
  const iconSize = iconSizes[size];

  // Determine variant based on side effect type
  const effectiveVariant = variant !== 'default' ? variant :
    metadata.side_effect_type === 'mutation_heavy' ? 'primary' : 'default';

  return (
    <button
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      disabled={disabled || loading}
      // Native title attribute for accessibility - no decorative tooltip (per brand spec)
      title={!showLabel ? metadata.label : undefined}
      className={cn(
        'inline-flex items-center justify-center font-body',
        'rounded-celeste-sm',
        'font-medium',
        'transition-all duration-celeste-fast',
        'shadow-celeste-sm',
        'hover:shadow-celeste-md',
        'active:shadow-none',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        'focus:outline-none focus:ring-2 focus:ring-brand-interactive/40',
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
              'rounded-celeste-sm',
              'transition-all duration-celeste-fast',
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
                'mt-1 p-1 rounded-celeste-md',
                'bg-surface-elevated',
                'border border-surface-border',
                'shadow-celeste-lg',
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
                      'px-2 py-1.5 rounded-celeste-sm',
                      'text-left text-base',
                      'text-txt-primary',
                      'hover:bg-surface-hover',
                      'transition-colors duration-celeste-fast'
                    )}
                  >
                    <Icon size={14} className="text-txt-tertiary" />
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
