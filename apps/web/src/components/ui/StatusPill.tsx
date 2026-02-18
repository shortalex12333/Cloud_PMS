import * as React from 'react';
import { cn } from '@/lib/utils';

/**
 * StatusPill - Semantic status indicator
 * Uses design tokens exclusively - zero raw hex values.
 *
 * @example
 * <StatusPill status="critical" label="Overdue" showDot />
 * <StatusPill status="success" label="Completed" />
 */
export interface StatusPillProps {
  status: 'critical' | 'warning' | 'success' | 'neutral';
  label: string;
  showDot?: boolean;
  className?: string;
}

const statusStyles = {
  critical: 'bg-status-critical-bg text-status-critical',
  warning: 'bg-status-warning-bg text-status-warning',
  success: 'bg-status-success-bg text-status-success',
  neutral: 'bg-status-neutral-bg text-status-neutral',
} as const;

export const StatusPill = React.forwardRef<HTMLSpanElement, StatusPillProps>(
  ({ status, label, showDot = false, className }, ref) => {
    return (
      <span
        ref={ref}
        className={cn(
          // Base styles: 24px height, 4px 12px padding, full radius
          'inline-flex items-center h-6 px-3 py-1 rounded-full',
          // Typography: 12px / weight 500
          'text-[12px] font-medium leading-none',
          // Status-specific colors
          statusStyles[status],
          className
        )}
      >
        {showDot && (
          <span
            className={cn(
              // 6px dot with matching status color
              'w-1.5 h-1.5 rounded-full mr-2',
              status === 'critical' && 'bg-status-critical',
              status === 'warning' && 'bg-status-warning',
              status === 'success' && 'bg-status-success',
              status === 'neutral' && 'bg-status-neutral'
            )}
          />
        )}
        {label}
      </span>
    );
  }
);

StatusPill.displayName = 'StatusPill';

export default StatusPill;
