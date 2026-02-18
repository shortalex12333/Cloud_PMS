'use client';

/**
 * useLensNavigation — Navigation stack management for entity lenses.
 *
 * Manages a linear navigation stack (max 9 entries, per view-stack.ts).
 *
 * Per FE-01-05 spec:
 * - Back button: returns to previous lens if stack has depth > 1, otherwise closes
 * - Close button: always returns to search/home (clears stack)
 * - Both actions log to ledger
 *
 * Usage:
 * ```tsx
 * const { navigationStack, push, back, close, canGoBack } = useLensNavigation({
 *   initialView: { mode: 'viewer', anchor_type: 'work_order', anchor_id: id },
 *   onClose: () => router.push('/app'),
 *   logEvent: (name, payload) => logNavigationEvent(name, payload),
 * });
 * ```
 */

import { useState, useCallback, useRef } from 'react';
import {
  pushView,
  goBack,
  clearStacks,
  canGoBack as canGoBackFn,
  type NavigationStack,
  type ViewState,
} from '@/lib/context-nav/view-stack';

export interface LensNavigationOptions {
  /** Initial view to push onto the stack when hook initialises */
  initialView: Omit<ViewState, 'timestamp'>;
  /** Called when navigation results in closing the lens (back from root or close) */
  onClose: () => void;
  /** Fire-and-forget ledger event logger */
  logEvent?: (eventName: string, payload: Record<string, unknown>) => void;
}

export interface LensNavigationResult {
  /** Current navigation stack state */
  navigationStack: NavigationStack;
  /** Current view (top of stack) */
  currentView: ViewState | null;
  /** Whether back navigation is possible */
  canGoBack: boolean;
  /** Push a new view onto the stack (cross-lens navigation) */
  push: (view: Omit<ViewState, 'timestamp'>) => void;
  /** Go back one step (or close if at root) */
  back: () => void;
  /** Close the lens and return to search */
  close: () => void;
}

export function useLensNavigation({
  initialView,
  onClose,
  logEvent,
}: LensNavigationOptions): LensNavigationResult {
  // Initialise stack with the first view
  const [navigationStack, setNavigationStack] = useState<NavigationStack>(() => {
    const initial: NavigationStack = { stack: [], forwardStack: [] };
    return pushView(initial, initialView);
  });

  // Track previous view for ledger logging
  const prevViewRef = useRef<ViewState | null>(null);

  // Push a new view onto the navigation stack
  const push = useCallback(
    (view: Omit<ViewState, 'timestamp'>) => {
      setNavigationStack((current) => {
        const currentTop = current.stack[current.stack.length - 1] ?? null;
        prevViewRef.current = currentTop;

        const next = pushView(current, view);

        // Log cross-lens navigation
        logEvent?.('navigate_to_lens', {
          from_type: currentTop?.anchor_type,
          from_id: currentTop?.anchor_id,
          to_type: view.anchor_type,
          to_id: view.anchor_id,
        });

        return next;
      });
    },
    [logEvent]
  );

  // Go back one step; if at root, close the lens
  const back = useCallback(() => {
    setNavigationStack((current) => {
      if (!canGoBackFn(current)) {
        // At root — close the lens
        logEvent?.('close_lens', {
          anchor_type: current.stack[0]?.anchor_type,
          anchor_id: current.stack[0]?.anchor_id,
          reason: 'back_from_root',
        });
        onClose();
        return current;
      }

      const { stack: newStack, view: previousView } = goBack(current);
      const currentView = current.stack[current.stack.length - 1];

      // Log navigate_back
      logEvent?.('navigate_back', {
        from_type: currentView?.anchor_type,
        from_id: currentView?.anchor_id,
        to_type: previousView?.anchor_type,
        to_id: previousView?.anchor_id,
      });

      return newStack;
    });
  }, [onClose, logEvent]);

  // Always close — returns to search/home
  const close = useCallback(() => {
    setNavigationStack((current) => {
      const currentView = current.stack[current.stack.length - 1];

      // Log close_lens
      logEvent?.('close_lens', {
        anchor_type: currentView?.anchor_type,
        anchor_id: currentView?.anchor_id,
        reason: 'user_close',
        stack_depth: current.stack.length,
      });

      return clearStacks();
    });

    onClose();
  }, [onClose, logEvent]);

  const currentView =
    navigationStack.stack.length > 0
      ? navigationStack.stack[navigationStack.stack.length - 1]
      : null;

  return {
    navigationStack,
    currentView,
    canGoBack: canGoBackFn(navigationStack),
    push,
    back,
    close,
  };
}
