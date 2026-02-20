import * as React from 'react';
import { cn } from '@/lib/utils';

/**
 * Toast - Notification message component
 * Uses semantic design tokens exclusively - zero raw hex values.
 *
 * @example
 * <Toast type="success" message="Changes saved successfully" onDismiss={() => {}} />
 * <Toast type="error" message="Failed to save changes" />
 */
export interface ToastProps {
  type: 'success' | 'warning' | 'error';
  message: string;
  onDismiss?: () => void;
  className?: string;
}

const AUTO_DISMISS_MS = 4000;

export const Toast = React.forwardRef<HTMLDivElement, ToastProps>(
  ({ type, message, onDismiss, className }, ref) => {
    const [isVisible, setIsVisible] = React.useState(true);

    // Auto-dismiss after 4 seconds
    React.useEffect(() => {
      const timer = setTimeout(() => {
        setIsVisible(false);
        // Wait for animation to complete before calling onDismiss
        setTimeout(() => onDismiss?.(), 200);
      }, AUTO_DISMISS_MS);

      return () => clearTimeout(timer);
    }, [onDismiss]);

    // Early exit if not visible (during fade out)
    if (!isVisible) {
      return (
        <div
          ref={ref}
          className={cn(
            // Fixed position at bottom center
            'fixed bottom-6 left-1/2 -translate-x-1/2',
            // Z-index for toast layer
            'z-toast',
            // Fade out animation
            'opacity-0 transform translate-y-2 transition-all duration-normal',
            className
          )}
        >
          <ToastContent type={type} message={message} onDismiss={onDismiss} />
        </div>
      );
    }

    return (
      <div
        ref={ref}
        className={cn(
          // Fixed position at bottom center
          'fixed bottom-6 left-1/2 -translate-x-1/2',
          // Z-index for toast layer
          'z-toast',
          // Slide up + fade in animation
          'animate-toast-in',
          className
        )}
      >
        <ToastContent type={type} message={message} onDismiss={onDismiss} />
      </div>
    );
  }
);

Toast.displayName = 'Toast';

/**
 * Internal toast content component
 */
function ToastContent({
  type,
  message,
  onDismiss,
}: {
  type: ToastProps['type'];
  message: string;
  onDismiss?: () => void;
}) {
  return (
    <div
      className={cn(
        // Container styling
        'flex items-center gap-3',
        'px-4 py-3 min-w-[280px] max-w-[400px]',
        // Surface styling
        'bg-surface-elevated border border-surface-border',
        'rounded-md',
        // Text
        'text-label text-txt-primary'
      )}
      role="alert"
    >
      <ToastIcon type={type} />
      <span className="flex-1">{message}</span>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="btn-icon h-8 w-8"
          aria-label="Dismiss"
        >
          <CloseIcon className="w-[18px] h-[18px]" />
        </button>
      )}
    </div>
  );
}

/**
 * Icon based on toast type
 */
function ToastIcon({ type }: { type: ToastProps['type'] }) {
  const iconClass = cn('w-5 h-5 flex-shrink-0', {
    'text-status-success': type === 'success',
    'text-status-warning': type === 'warning',
    'text-status-critical': type === 'error',
  });

  if (type === 'success') {
    return (
      <svg
        className={iconClass}
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    );
  }

  if (type === 'warning') {
    return (
      <svg
        className={iconClass}
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
    );
  }

  // error
  return (
    <svg
      className={iconClass}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

/**
 * Close icon
 */
function CloseIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M6 18L18 6M6 6l12 12"
      />
    </svg>
  );
}

