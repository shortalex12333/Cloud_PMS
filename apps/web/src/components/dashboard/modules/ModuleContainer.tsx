'use client';

/**
 * ModuleContainer
 * Reusable container for Control Center modules
 *
 * Features:
 * - Glassmorphic styling
 * - Collapse/expand animation
 * - Status badge
 * - Microaction integration
 */

import React, { ReactNode } from 'react';
import { ChevronDown, ChevronUp, MoreHorizontal } from 'lucide-react';
import { cn } from '@/lib/utils';

// ============================================================================
// TYPES
// ============================================================================

type StatusType = 'healthy' | 'warning' | 'critical' | 'neutral';

interface ModuleContainerProps {
  title: string;
  icon: React.ReactNode;
  isExpanded: boolean;
  onToggle: () => void;
  status?: StatusType;
  statusLabel?: string;
  badge?: string | number;
  children: ReactNode;
  collapsedContent?: ReactNode;
  actions?: ReactNode;
  className?: string;
}

// ============================================================================
// STATUS STYLES
// ============================================================================

const statusStyles: Record<StatusType, { dot: string; text: string; bg: string }> = {
  healthy: {
    dot: 'bg-restricted-green-500',
    text: 'text-restricted-green-600 dark:text-restricted-green-400',
    bg: 'bg-restricted-green-500/10',
  },
  warning: {
    dot: 'bg-amber-500',
    text: 'text-amber-600 dark:text-amber-400',
    bg: 'bg-amber-500/10',
  },
  critical: {
    dot: 'bg-red-500',
    text: 'text-red-600 dark:text-red-400',
    bg: 'bg-red-500/10',
  },
  neutral: {
    dot: 'bg-zinc-400',
    text: 'text-zinc-500 dark:text-zinc-400',
    bg: 'bg-zinc-500/10',
  },
};

// ============================================================================
// COMPONENT
// ============================================================================

export default function ModuleContainer({
  title,
  icon,
  isExpanded,
  onToggle,
  status = 'neutral',
  statusLabel,
  badge,
  children,
  collapsedContent,
  actions,
  className,
}: ModuleContainerProps) {
  const styles = statusStyles[status];

  return (
    <div
      className={cn(
        'relative overflow-hidden',
        'bg-white dark:bg-zinc-900',
        'border border-zinc-200/60 dark:border-zinc-700/60',
        'rounded-xl',
        'transition-all duration-slow ease-out',
        className
      )}
    >
      {/* Header */}
      <button
        onClick={onToggle}
        className={cn(
          'w-full flex items-center gap-3',
          'px-4 py-3',
          'text-left',
          'hover:bg-surface-hover',
          'transition-colors duration-fast'
        )}
      >
        {/* Icon */}
        <div className={cn(
          'flex items-center justify-center',
          'w-9 h-9 rounded-md',
          styles.bg
        )}>
          {icon}
        </div>

        {/* Title & Status */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="typo-body font-semibold text-zinc-900 dark:text-zinc-100 truncate">
              {title}
            </h3>
            {badge !== undefined && (
              <span className={cn(
                'px-1.5 py-0.5 rounded-md',
                'typo-meta font-semibold',
                styles.bg,
                styles.text
              )}>
                {badge}
              </span>
            )}
          </div>
          {statusLabel && (
            <p className={cn('typo-meta mt-0.5', styles.text)}>
              {statusLabel}
            </p>
          )}
        </div>

        {/* Status dot */}
        <div className={cn(
          'w-2 h-2 rounded-full',
          styles.dot,
          status === 'critical' && 'animate-pulse'
        )} />

        {/* Expand/Collapse icon */}
        <div className="text-zinc-400 dark:text-zinc-500">
          {isExpanded ? (
            <ChevronUp className="h-5 w-5" />
          ) : (
            <ChevronDown className="h-5 w-5" />
          )}
        </div>
      </button>

      {/* Collapsed preview content */}
      {!isExpanded && collapsedContent && (
        <div className="px-4 pb-3 -mt-1">
          {collapsedContent}
        </div>
      )}

      {/* Expanded content */}
      <div
        className={cn(
          'overflow-hidden transition-all duration-slow ease-out',
          isExpanded ? 'max-h-[600px] opacity-100' : 'max-h-0 opacity-0'
        )}
      >
        <div className="px-4 pb-4 pt-1">
          {/* Divider */}
          <div className="h-px bg-zinc-200/60 dark:bg-zinc-700/60 mb-3" />

          {/* Module content */}
          {children}

          {/* Actions */}
          {actions && (
            <div className="mt-4 pt-3 border-t border-zinc-200/60 dark:border-zinc-700/60">
              {actions}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// MODULE ITEM COMPONENT
// ============================================================================

interface ModuleItemProps {
  icon?: React.ReactNode;
  title: string;
  subtitle?: string;
  status?: StatusType;
  value?: string | number;
  onClick?: () => void;
  actions?: React.ReactNode;
  className?: string;
}

export function ModuleItem({
  icon,
  title,
  subtitle,
  status = 'neutral',
  value,
  onClick,
  actions,
  className,
}: ModuleItemProps) {
  const styles = statusStyles[status];

  return (
    <div
      onClick={onClick}
      className={cn(
        'flex items-center gap-3',
        'px-3 py-2 -mx-3 rounded-md',
        onClick && 'cursor-pointer hover:bg-surface-active',
        'transition-colors duration-fast',
        'group',
        className
      )}
    >
      {icon && (
        <div className={cn(
          'flex items-center justify-center',
          'w-8 h-8 rounded-md',
          styles.bg
        )}>
          {icon}
        </div>
      )}

      <div className="flex-1 min-w-0">
        <p className="typo-meta font-medium text-zinc-700 dark:text-zinc-200 truncate">
          {title}
        </p>
        {subtitle && (
          <p className="typo-meta text-zinc-500 dark:text-zinc-400 truncate">
            {subtitle}
          </p>
        )}
      </div>

      {value !== undefined && (
        <span className={cn(
          'typo-meta font-semibold tabular-nums',
          styles.text
        )}>
          {value}
        </span>
      )}

      {actions && (
        <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-fast">
          {actions}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// PROGRESS BAR
// ============================================================================

interface ProgressBarProps {
  value: number;
  max?: number;
  status?: StatusType;
  showLabel?: boolean;
  size?: 'sm' | 'md';
  className?: string;
}

export function ProgressBar({
  value,
  max = 100,
  status = 'neutral',
  showLabel = false,
  size = 'sm',
  className,
}: ProgressBarProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));
  const styles = statusStyles[status];

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className={cn(
        'flex-1 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden',
        size === 'sm' ? 'h-1.5' : 'h-2'
      )}>
        <div
          className={cn(
            'h-full rounded-full transition-all duration-500',
            styles.dot
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <span className={cn(
          'typo-meta font-medium tabular-nums',
          styles.text
        )}>
          {Math.round(percentage)}%
        </span>
      )}
    </div>
  );
}

// ============================================================================
// STAT CARD
// ============================================================================

interface StatCardProps {
  label: string;
  value: string | number;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  status?: StatusType;
  className?: string;
}

export function StatCard({
  label,
  value,
  trend,
  trendValue,
  status = 'neutral',
  className,
}: StatCardProps) {
  const styles = statusStyles[status];

  return (
    <div className={cn(
      'px-3 py-2 rounded-md',
      'bg-surface-active',
      className
    )}>
      <p className="typo-meta text-zinc-500 dark:text-zinc-400">
        {label}
      </p>
      <div className="flex items-end gap-1.5 mt-0.5">
        <span className={cn(
          'typo-title font-semibold tabular-nums',
          styles.text.replace('text-', 'text-zinc-900 dark:text-zinc-100')
        )}>
          {value}
        </span>
        {trendValue && (
          <span className={cn(
            'typo-meta font-medium mb-0.5',
            trend === 'up' && 'text-restricted-green-500',
            trend === 'down' && 'text-red-500',
            trend === 'neutral' && 'text-zinc-400'
          )}>
            {trend === 'up' && '↑'}
            {trend === 'down' && '↓'}
            {trendValue}
          </span>
        )}
      </div>
    </div>
  );
}
