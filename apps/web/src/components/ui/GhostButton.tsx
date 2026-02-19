import * as React from 'react';
import { cn } from '@/lib/utils';

/**
 * GhostButton - Transparent interactive button
 * Uses semantic design tokens exclusively - zero raw hex values.
 *
 * @example
 * <GhostButton>Cancel</GhostButton>
 * <GhostButton icon={<PlusIcon />}>Add Item</GhostButton>
 * <GhostButton loading>Saving...</GhostButton>
 */
export interface GhostButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: React.ReactNode;
  loading?: boolean;
}

export const GhostButton = React.forwardRef<HTMLButtonElement, GhostButtonProps>(
  ({ icon, loading = false, className, children, disabled, ...props }, ref) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={cn(
          'btn-ghost',
          className
        )}
        {...props}
      >
        {loading ? (
          <LoadingSpinner className="w-4 h-4" />
        ) : (
          icon && <span className="flex-shrink-0">{icon}</span>
        )}
        {children}
      </button>
    );
  }
);

GhostButton.displayName = 'GhostButton';

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

export default GhostButton;
