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

const statusPillVariants = {
  critical: 'status-pill-critical',
  warning: 'status-pill-warning',
  success: 'status-pill-success',
  neutral: 'status-pill-neutral',
} as const;

const statusDotVariants = {
  critical: 'status-dot-critical',
  warning: 'status-dot-warning',
  success: 'status-dot-success',
  neutral: 'status-dot-neutral',
} as const;

export const StatusPill = React.forwardRef<HTMLSpanElement, StatusPillProps>(
  ({ status, label, showDot = false, className }, ref) => {
    return (
      <span
        ref={ref}
        className={cn(
          'status-pill',
          statusPillVariants[status],
          className
        )}
      >
        {showDot && (
          <span
            className={cn(
              'status-dot',
              statusDotVariants[status]
            )}
          />
        )}
        {label}
      </span>
    );
  }
);

StatusPill.displayName = 'StatusPill';

