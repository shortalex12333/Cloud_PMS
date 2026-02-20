import * as React from 'react';
import { cn } from '@/lib/utils';
import { StatusPill, type StatusPillProps } from './StatusPill';

/**
 * VitalSignsRow - Horizontal row of factual database values
 * Per UI_SPEC.md: 3-5 facts, horizontal flex with middle-dot separators
 *
 * Uses design tokens exclusively - zero raw hex values.
 *
 * @example
 * <VitalSignsRow signs={[
 *   { label: 'Status', value: 'Pending', color: 'neutral' },
 *   { label: 'Priority', value: 'High', color: 'warning' },
 *   { label: 'Parts', value: '3 parts' },
 *   { label: 'Age', value: '5 days ago' },
 *   { label: 'Equipment', value: 'Main Engine', href: '/equipment/123' }
 * ]} />
 */
export interface VitalSign {
  /** Label text (e.g., "Status", "Priority", "Parts") */
  label: string;
  /** Value to display */
  value: string | number;
  /** Status color - if provided, renders as StatusPill */
  color?: 'critical' | 'warning' | 'success' | 'neutral';
  /** URL for clickable entity links */
  href?: string;
  /** Custom click handler */
  onClick?: () => void;
}

export interface VitalSignsRowProps {
  /** Array of vital signs to display (3-5 recommended) */
  signs: VitalSign[];
  /** Additional CSS classes */
  className?: string;
}

/**
 * Individual vital sign item renderer
 */
const VitalSignItem = ({ sign }: { sign: VitalSign }) => {
  const { label, value, color, href, onClick } = sign;

  // Render value based on type
  const renderValue = () => {
    const displayValue = String(value);

    // If color is specified, render as StatusPill
    if (color) {
      return (
        <StatusPill
          status={color}
          label={displayValue}
        />
      );
    }

    // If href or onClick, render as clickable link
    if (href || onClick) {
      const handleClick = (e: React.MouseEvent) => {
        if (onClick) {
          e.preventDefault();
          onClick();
        }
        // If href but no onClick, let the link navigate naturally
      };

      return (
        <a
          href={href || '#'}
          onClick={handleClick}
          className={cn(
            // Typography: 14px / weight 500
            'text-body-strong leading-none',
            // Interactive color with hover
            'text-brand-interactive hover:text-brand-hover',
            // Cursor and transition
            'cursor-pointer transition-colors',
            // Duration from design tokens
            'duration-fast'
          )}
        >
          {displayValue}
        </a>
      );
    }

    // Plain text value
    return (
      <span className="text-body-strong leading-none text-txt-primary">
        {displayValue}
      </span>
    );
  };

  return (
    <div className="flex items-center gap-1.5">
      {/* Label: 13px / secondary color */}
      <span className="text-label leading-none text-txt-secondary">
        {label}:
      </span>
      {renderValue()}
    </div>
  );
};

/**
 * Middle dot separator component
 */
const Separator = () => (
  <span
    className="text-txt-tertiary text-body leading-none select-none"
    aria-hidden="true"
  >
    {'\u00B7'}
  </span>
);

export const VitalSignsRow = React.forwardRef<HTMLDivElement, VitalSignsRowProps>(
  ({ signs, className }, ref) => {
    if (!signs || signs.length === 0) {
      return null;
    }

    return (
      <div
        ref={ref}
        className={cn(
          // Layout: horizontal flex with 16px gap, wraps on mobile
          'flex flex-wrap items-center gap-x-4 gap-y-2',
          // Height: ~40px (min-height to allow wrapping)
          'min-h-10',
          className
        )}
      >
        {signs.map((sign, index) => (
          <React.Fragment key={`${sign.label}-${index}`}>
            <VitalSignItem sign={sign} />
            {/* Add separator between items, but not after the last one */}
            {index < signs.length - 1 && <Separator />}
          </React.Fragment>
        ))}
      </div>
    );
  }
);

VitalSignsRow.displayName = 'VitalSignsRow';

