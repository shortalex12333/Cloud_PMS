import * as React from 'react';
import { cn } from '@/lib/utils';
import { GhostButton } from '@/components/ui/GhostButton';
import { StatusPill } from '@/components/ui/StatusPill';

/**
 * LensHeader - Fixed navigation header for all entity lenses.
 * Per UI_SPEC.md NAVIGATION HEADER spec:
 * - 56px height, fixed at top, surface-base background, border-bottom
 * - Left: Back button (← icon)
 * - Center: Entity type overline (uppercase, tertiary text)
 * - Right: Close button (× icon)
 *
 * Reference implementation — all other lenses inherit this pattern.
 */
export interface LensHeaderProps {
  /** Entity type label e.g. "Work Order", "Fault", "Certificate" */
  entityType: string;
  /** Human-readable title (not UUID) */
  title: string;
  /** Optional subtitle / description (max 2 lines, truncated) */
  subtitle?: string;
  /** Optional status pill */
  status?: {
    label: string;
    color: 'critical' | 'warning' | 'success' | 'neutral';
  };
  /** Optional priority pill */
  priority?: {
    label: string;
    color: 'critical' | 'warning' | 'success' | 'neutral';
  };
  /** Handler for back navigation */
  onBack?: () => void;
  /** Handler for close / dismiss */
  onClose?: () => void;
  /** Additional CSS classes for the header bar */
  className?: string;
}

/** Arrow-left SVG icon (18px) */
const ArrowLeftIcon = () => (
  <svg
    width="18"
    height="18"
    viewBox="0 0 18 18"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <path
      d="M15 9H3M3 9L8 4M3 9L8 14"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

/** X / Close SVG icon (18px) */
const CloseIcon = () => (
  <svg
    width="18"
    height="18"
    viewBox="0 0 18 18"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <path
      d="M13.5 4.5L4.5 13.5M4.5 4.5L13.5 13.5"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
    />
  </svg>
);

/**
 * LensHeader — Fixed top bar used by all entity lenses.
 */
export const LensHeader = React.forwardRef<HTMLElement, LensHeaderProps>(
  (
    {
      entityType,
      title,
      subtitle,
      status,
      priority,
      onBack,
      onClose,
      className,
    },
    ref
  ) => {
    return (
      <header
        ref={ref}
        className={cn(
          // Positioning: fixed at top, full width
          'fixed top-0 left-0 right-0',
          // Height: 56px per spec
          'h-14',
          // Background and border
          'bg-surface-base border-b border-surface-border',
          // Z-index: header layer
          'z-[var(--z-header)]',
          // Layout: flex, space-between, vertically centered
          'flex items-center justify-between',
          // Horizontal padding: 24px per spec
          'px-6',
          className
        )}
      >
        {/* Left cluster: Back button */}
        <div className="flex items-center gap-1">
          {onBack && (
            <button
              onClick={onBack}
              aria-label="Go back"
              className={cn(
                // Icon-only button: 36x36, radius-sm
                'w-9 h-9 flex items-center justify-center',
                'rounded-sm',
                // Colors: secondary text at rest
                'text-txt-secondary bg-transparent',
                // Hover: surface-hover bg, primary text
                'hover:bg-surface-hover hover:text-txt-primary',
                // Transition: 120ms
                'transition-colors duration-[120ms] ease-out',
                // Focus ring
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-interactive',
                // Touch target
                'cursor-pointer'
              )}
            >
              <ArrowLeftIcon />
            </button>
          )}
        </div>

        {/* Center: Entity type overline */}
        {/*
          Overline spec: 11px / weight 500 / tracking 0.08em / uppercase / text-tertiary
          Vertically centered in the 56px header.
        */}
        <span
          className={cn(
            'text-[11px] font-medium tracking-[0.08em] uppercase',
            'text-txt-tertiary',
            'select-none'
          )}
        >
          {entityType}
        </span>

        {/* Right cluster: Close button */}
        <div className="flex items-center gap-2">
          {onClose && (
            <button
              onClick={onClose}
              aria-label="Close"
              className={cn(
                // Icon-only button: 36x36, radius-sm
                'w-9 h-9 flex items-center justify-center',
                'rounded-sm',
                // Colors
                'text-txt-secondary bg-transparent',
                // Hover
                'hover:bg-surface-hover hover:text-txt-primary',
                // Transition
                'transition-colors duration-[120ms] ease-out',
                // Focus ring
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-interactive',
                'cursor-pointer'
              )}
            >
              <CloseIcon />
            </button>
          )}
        </div>
      </header>
    );
  }
);

LensHeader.displayName = 'LensHeader';

/**
 * LensTitleBlock — Title + subtitle + status/priority pills.
 * Placed directly below LensHeader (with pt-14 to clear the fixed header).
 *
 * Per UI_SPEC.md:
 * - Title: text-txt-primary, 28px (Display), font-semibold (700)
 * - Subtitle: text-txt-secondary, 16px, max 2 lines, truncated
 * - Pills inline with title area, 4px gap from overline to title, 12px gap from title to vitals
 */
export interface LensTitleBlockProps {
  title: string;
  subtitle?: string;
  status?: {
    label: string;
    color: 'critical' | 'warning' | 'success' | 'neutral';
  };
  priority?: {
    label: string;
    color: 'critical' | 'warning' | 'success' | 'neutral';
  };
  className?: string;
}

export const LensTitleBlock = React.forwardRef<
  HTMLDivElement,
  LensTitleBlockProps
>(({ title, subtitle, status, priority, className }, ref) => {
  return (
    <div ref={ref} className={cn('flex flex-col gap-1', className)}>
      {/* Pills row — shown above title if both status and priority present */}
      {(status || priority) && (
        <div className="flex items-center gap-2 mb-1">
          {status && (
            <StatusPill status={status.color} label={status.label} showDot />
          )}
          {priority && (
            <StatusPill status={priority.color} label={priority.label} showDot />
          )}
        </div>
      )}

      {/* Title: 28px Display, semibold */}
      <h1
        className={cn(
          'text-[28px] font-semibold leading-[1.15] tracking-[-0.02em]',
          'text-txt-primary',
          // Prevent UUID-like text from wrapping awkwardly
          'break-words'
        )}
      >
        {title}
      </h1>

      {/* Subtitle: 16px, secondary color, max 2 lines */}
      {subtitle && (
        <p
          className={cn(
            'text-[16px] font-normal leading-[1.5]',
            'text-txt-secondary',
            // Max 2 lines with ellipsis
            'overflow-hidden',
            'line-clamp-2'
          )}
        >
          {subtitle}
        </p>
      )}
    </div>
  );
});

LensTitleBlock.displayName = 'LensTitleBlock';

export default LensHeader;
