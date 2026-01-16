/**
 * View Stack - Pure Functions
 *
 * Linear stack navigation with soft cap of 9 view states.
 * Drop oldest silently when cap is exceeded.
 *
 * View types:
 * - 'viewer': Artifact viewer (equipment, fault, work order, etc.)
 * - 'related': Related panel showing grouped artifacts
 */

export type ViewMode = 'viewer' | 'related';

export interface ViewState {
  mode: ViewMode;
  anchor_type: string;
  anchor_id: string;
  timestamp: number;
}

export interface NavigationStack {
  stack: ViewState[];
  forwardStack: ViewState[];
}

const MAX_STACK_SIZE = 9;

/**
 * Push a new view state onto the stack.
 * Enforces soft cap of 9 states by dropping oldest.
 * Clears forward stack on push.
 */
export function pushView(
  current: NavigationStack,
  view: Omit<ViewState, 'timestamp'>
): NavigationStack {
  const newView: ViewState = {
    ...view,
    timestamp: Date.now(),
  };

  let newStack = [...current.stack, newView];

  // Soft cap: drop oldest if exceeds 9
  if (newStack.length > MAX_STACK_SIZE) {
    newStack = newStack.slice(newStack.length - MAX_STACK_SIZE);
  }

  return {
    stack: newStack,
    forwardStack: [], // Clear forward on new push
  };
}

/**
 * Pop the current view and go back.
 * Returns updated stack and the view to navigate to (or null if can't go back).
 */
export function goBack(current: NavigationStack): {
  stack: NavigationStack;
  view: ViewState | null;
} {
  if (current.stack.length <= 1) {
    // Can't go back from first view
    return { stack: current, view: null };
  }

  const newStack = [...current.stack];
  const poppedView = newStack.pop()!; // Remove current view
  const previousView = newStack[newStack.length - 1]; // Peek at new current

  return {
    stack: {
      stack: newStack,
      forwardStack: [poppedView, ...current.forwardStack],
    },
    view: previousView,
  };
}

/**
 * Go forward to next view (if exists in forward stack).
 * Returns updated stack and the view to navigate to (or null if can't go forward).
 */
export function goForward(current: NavigationStack): {
  stack: NavigationStack;
  view: ViewState | null;
} {
  if (current.forwardStack.length === 0) {
    // No forward history
    return { stack: current, view: null };
  }

  const newForwardStack = [...current.forwardStack];
  const nextView = newForwardStack.shift()!; // Remove from forward

  return {
    stack: {
      stack: [...current.stack, nextView],
      forwardStack: newForwardStack,
    },
    view: nextView,
  };
}

/**
 * Clear all stacks (used when ending context).
 */
export function clearStacks(): NavigationStack {
  return {
    stack: [],
    forwardStack: [],
  };
}

/**
 * Get current view (top of stack).
 */
export function getCurrentView(stack: NavigationStack): ViewState | null {
  if (stack.stack.length === 0) return null;
  return stack.stack[stack.stack.length - 1];
}

/**
 * Check if can go back.
 */
export function canGoBack(stack: NavigationStack): boolean {
  return stack.stack.length > 1;
}

/**
 * Check if can go forward.
 */
export function canGoForward(stack: NavigationStack): boolean {
  return stack.forwardStack.length > 0;
}
