'use client';

/**
 * LensContainer - Full-screen wrapper for all entity lenses.
 *
 * Per UI_SPEC.md and CLAUDE.md:
 * - Position: fixed, inset: 0 (100vw × 100vh)
 * - Background: surface-base
 * - Z-index: z-modal (40 per --z-modal token)
 * - Overflow-y: auto for independent lens scrolling
 * - Body scroll locked when open (prevents background scroll)
 * - Glass transition animation: 300ms ease-out on enter, 200ms ease-in on exit
 *
 * FE-01-05: Full-Screen Lens Layout + Glass Transitions
 */

import * as React from 'react';
import { useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';

export interface LensContainerProps {
  /** Controls visibility — drives enter/exit animation */
  isOpen: boolean;
  /** Called when lens should close (× button or Escape key) */
  onClose: () => void;
  /** Lens content */
  children: React.ReactNode;
  /** Additional CSS classes for the container */
  className?: string;
}

/**
 * LensContainer — Fixed full-screen wrapper with glass transition animation.
 *
 * Usage:
 * ```tsx
 * <LensContainer isOpen={isOpen} onClose={handleClose}>
 *   <WorkOrderLens workOrder={data} onClose={handleClose} />
 * </LensContainer>
 * ```
 */
export const LensContainer = React.forwardRef<
  HTMLDivElement,
  LensContainerProps
>(({ isOpen, onClose, children, className }, ref) => {
  // Track mounted state so we can apply exit animation before unmounting.
  // We keep the element in the DOM during exit transition (200ms).
  const [visible, setVisible] = React.useState(isOpen);
  const [animClass, setAnimClass] = React.useState<'entering' | 'entered' | 'exiting' | 'exited'>(
    isOpen ? 'entering' : 'exited'
  );
  const animTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Synchronise animation state with isOpen prop
  useEffect(() => {
    if (animTimer.current) clearTimeout(animTimer.current);

    if (isOpen) {
      // Mount → trigger enter
      setVisible(true);
      // Defer one tick so browser paints the entering class before entered
      animTimer.current = setTimeout(() => {
        setAnimClass('entering');
        animTimer.current = setTimeout(() => {
          setAnimClass('entered');
        }, 10);
      }, 10);
    } else {
      // Trigger exit animation, then unmount
      setAnimClass('exiting');
      animTimer.current = setTimeout(() => {
        setAnimClass('exited');
        setVisible(false);
      }, 210); // 200ms exit + 10ms buffer
    }

    return () => {
      if (animTimer.current) clearTimeout(animTimer.current);
    };
  }, [isOpen]);

  // Body scroll lock: prevents background scroll when lens is open
  useEffect(() => {
    if (isOpen) {
      // Lock body scroll
      document.body.style.overflow = 'hidden';
      // Compensate for scrollbar width to prevent layout shift
      const scrollbarWidth =
        window.innerWidth - document.documentElement.clientWidth;
      if (scrollbarWidth > 0) {
        document.body.style.paddingRight = `${scrollbarWidth}px`;
      }
    }
    return () => {
      // Always restore scroll on cleanup
      document.body.style.overflow = '';
      document.body.style.paddingRight = '';
    };
  }, [isOpen]);

  // Escape key closes the lens
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!visible) return null;

  return (
    <div
      ref={ref}
      role="dialog"
      aria-modal="true"
      className={cn(
        // Full viewport coverage — fixed, inset 0 = 100vw × 100vh
        'fixed inset-0',
        // Surface: darkest app background
        'bg-surface-base',
        // Z-index: modal layer (40 per --z-modal token)
        'z-modal',
        // Independent scroll — lens content scrolls, body does not
        'overflow-y-auto overflow-x-hidden',
        // Overscroll bounce prevention (iOS Safari)
        'overscroll-contain',
        // Glass transition classes
        animClass === 'entering' && 'lens-entering',
        animClass === 'entered' && 'lens-entered',
        animClass === 'exiting' && 'lens-exiting',
        animClass === 'exited' && 'lens-exited',
        className
      )}
    >
      {children}
    </div>
  );
});

LensContainer.displayName = 'LensContainer';

