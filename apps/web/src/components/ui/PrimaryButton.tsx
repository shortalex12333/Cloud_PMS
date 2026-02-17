import * as React from 'react';
import { cn } from '@/lib/utils';

/**
 * PrimaryButton - Main call-to-action button
 * Uses semantic design tokens exclusively - zero raw hex values.
 *
 * @example
 * <PrimaryButton>Save Changes</PrimaryButton>
 * <PrimaryButton loading>Saving...</PrimaryButton>
 */
export interface PrimaryButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  loading?: boolean;
}

export const PrimaryButton = React.forwardRef<
  HTMLButtonElement,
  PrimaryButtonProps
>(({ loading = false, className, children, disabled, ...props }, ref) => {
  const isDisabled = disabled || loading;

  return (
    <button
      ref={ref}
      disabled={isDisabled}
      className={cn(
        // Base layout
        'inline-flex items-center justify-center gap-2',
        // Size: min-height 40px, 12px 24px padding
        'min-h-[40px] px-6 py-3',
        // Typography: 14px font, weight 600
        'text-[14px] font-semibold',
        // Color: brand interactive bg, inverse text
        'bg-brand-interactive text-txt-inverse',
        // Hover: brand hover
        'hover:bg-brand-hover',
        // Transitions
        'transition-colors duration-150',
        // Border radius (using sm token = 8px)
        'rounded-sm',
        // Shadow for depth
        'shadow-sm',
        // Focus state
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-interactive focus-visible:ring-offset-2',
        // Disabled state
        'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-brand-interactive',
        className
      )}
      {...props}
    >
      {loading ? (
        <>
          <LoadingSpinner className="w-4 h-4" />
          <span>Loading...</span>
        </>
      ) : (
        children
      )}
    </button>
  );
});

PrimaryButton.displayName = 'PrimaryButton';

/**
 * Simple loading spinner using CSS animation
 */
function LoadingSpinner({ className }: { className?: string }) {
  return (
    <svg
      className={cn('animate-spin', className)}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

export default PrimaryButton;
