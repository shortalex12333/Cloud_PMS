/**
 * View Stack Unit Tests
 *
 * Tests for pure view stack navigation functions:
 * - Push with soft cap of 9
 * - Back/Forward navigation
 * - Stack clearing
 */

import { describe, it, expect } from 'vitest';
import {
  pushView,
  goBack,
  goForward,
  clearStacks,
  getCurrentView,
  canGoBack,
  canGoForward,
  type NavigationStack,
} from '@/lib/context-nav/view-stack';

describe('view-stack', () => {
  describe('pushView', () => {
    it('should push a view onto empty stack', () => {
      const stack: NavigationStack = { stack: [], forwardStack: [] };

      const result = pushView(stack, {
        mode: 'viewer',
        anchor_type: 'fault',
        anchor_id: 'fault-1',
      });

      expect(result.stack).toHaveLength(1);
      expect(result.stack[0].mode).toBe('viewer');
      expect(result.stack[0].anchor_type).toBe('fault');
      expect(result.stack[0].anchor_id).toBe('fault-1');
      expect(result.stack[0].timestamp).toBeGreaterThan(0);
      expect(result.forwardStack).toHaveLength(0);
    });

    it('should clear forward stack on push', () => {
      const stack: NavigationStack = {
        stack: [
          { mode: 'viewer', anchor_type: 'fault', anchor_id: 'fault-1', timestamp: 1 },
        ],
        forwardStack: [
          { mode: 'viewer', anchor_type: 'fault', anchor_id: 'fault-2', timestamp: 2 },
        ],
      };

      const result = pushView(stack, {
        mode: 'related',
        anchor_type: 'fault',
        anchor_id: 'fault-1',
      });

      expect(result.stack).toHaveLength(2);
      expect(result.forwardStack).toHaveLength(0); // Cleared
    });

    it('should enforce soft cap of 9 by dropping oldest', () => {
      const stack: NavigationStack = {
        stack: Array.from({ length: 9 }, (_, i) => ({
          mode: 'viewer' as const,
          anchor_type: 'fault',
          anchor_id: `fault-${i}`,
          timestamp: i,
        })),
        forwardStack: [],
      };

      const result = pushView(stack, {
        mode: 'viewer',
        anchor_type: 'fault',
        anchor_id: 'fault-9',
      });

      expect(result.stack).toHaveLength(9); // Still 9
      expect(result.stack[0].anchor_id).toBe('fault-1'); // fault-0 was dropped
      expect(result.stack[8].anchor_id).toBe('fault-9'); // New one at end
    });
  });

  describe('goBack', () => {
    it('should go back from current view', () => {
      const stack: NavigationStack = {
        stack: [
          { mode: 'viewer', anchor_type: 'fault', anchor_id: 'fault-1', timestamp: 1 },
          { mode: 'related', anchor_type: 'fault', anchor_id: 'fault-1', timestamp: 2 },
        ],
        forwardStack: [],
      };

      const result = goBack(stack);

      expect(result.view).not.toBeNull();
      expect(result.view?.anchor_id).toBe('fault-1');
      expect(result.view?.mode).toBe('viewer');
      expect(result.stack.stack).toHaveLength(1);
      expect(result.stack.forwardStack).toHaveLength(1); // Current moved to forward
    });

    it('should not go back when only one view in stack', () => {
      const stack: NavigationStack = {
        stack: [
          { mode: 'viewer', anchor_type: 'fault', anchor_id: 'fault-1', timestamp: 1 },
        ],
        forwardStack: [],
      };

      const result = goBack(stack);

      expect(result.view).toBeNull();
      expect(result.stack.stack).toHaveLength(1); // Unchanged
    });

    it('should not go back when stack is empty', () => {
      const stack: NavigationStack = { stack: [], forwardStack: [] };

      const result = goBack(stack);

      expect(result.view).toBeNull();
      expect(result.stack.stack).toHaveLength(0);
    });
  });

  describe('goForward', () => {
    it('should go forward when forward stack exists', () => {
      const stack: NavigationStack = {
        stack: [
          { mode: 'viewer', anchor_type: 'fault', anchor_id: 'fault-1', timestamp: 1 },
        ],
        forwardStack: [
          { mode: 'related', anchor_type: 'fault', anchor_id: 'fault-1', timestamp: 2 },
        ],
      };

      const result = goForward(stack);

      expect(result.view).not.toBeNull();
      expect(result.view?.mode).toBe('related');
      expect(result.stack.stack).toHaveLength(2);
      expect(result.stack.forwardStack).toHaveLength(0);
    });

    it('should not go forward when forward stack is empty', () => {
      const stack: NavigationStack = {
        stack: [
          { mode: 'viewer', anchor_type: 'fault', anchor_id: 'fault-1', timestamp: 1 },
        ],
        forwardStack: [],
      };

      const result = goForward(stack);

      expect(result.view).toBeNull();
      expect(result.stack.stack).toHaveLength(1); // Unchanged
    });
  });

  describe('clearStacks', () => {
    it('should clear both stacks', () => {
      const result = clearStacks();

      expect(result.stack).toHaveLength(0);
      expect(result.forwardStack).toHaveLength(0);
    });
  });

  describe('getCurrentView', () => {
    it('should return current view (top of stack)', () => {
      const stack: NavigationStack = {
        stack: [
          { mode: 'viewer', anchor_type: 'fault', anchor_id: 'fault-1', timestamp: 1 },
          { mode: 'related', anchor_type: 'fault', anchor_id: 'fault-1', timestamp: 2 },
        ],
        forwardStack: [],
      };

      const view = getCurrentView(stack);

      expect(view).not.toBeNull();
      expect(view?.mode).toBe('related');
      expect(view?.timestamp).toBe(2);
    });

    it('should return null when stack is empty', () => {
      const stack: NavigationStack = { stack: [], forwardStack: [] };

      const view = getCurrentView(stack);

      expect(view).toBeNull();
    });
  });

  describe('canGoBack', () => {
    it('should return true when stack has more than 1 view', () => {
      const stack: NavigationStack = {
        stack: [
          { mode: 'viewer', anchor_type: 'fault', anchor_id: 'fault-1', timestamp: 1 },
          { mode: 'related', anchor_type: 'fault', anchor_id: 'fault-1', timestamp: 2 },
        ],
        forwardStack: [],
      };

      expect(canGoBack(stack)).toBe(true);
    });

    it('should return false when stack has only 1 view', () => {
      const stack: NavigationStack = {
        stack: [
          { mode: 'viewer', anchor_type: 'fault', anchor_id: 'fault-1', timestamp: 1 },
        ],
        forwardStack: [],
      };

      expect(canGoBack(stack)).toBe(false);
    });

    it('should return false when stack is empty', () => {
      const stack: NavigationStack = { stack: [], forwardStack: [] };

      expect(canGoBack(stack)).toBe(false);
    });
  });

  describe('canGoForward', () => {
    it('should return true when forward stack has views', () => {
      const stack: NavigationStack = {
        stack: [
          { mode: 'viewer', anchor_type: 'fault', anchor_id: 'fault-1', timestamp: 1 },
        ],
        forwardStack: [
          { mode: 'related', anchor_type: 'fault', anchor_id: 'fault-1', timestamp: 2 },
        ],
      };

      expect(canGoForward(stack)).toBe(true);
    });

    it('should return false when forward stack is empty', () => {
      const stack: NavigationStack = {
        stack: [
          { mode: 'viewer', anchor_type: 'fault', anchor_id: 'fault-1', timestamp: 1 },
        ],
        forwardStack: [],
      };

      expect(canGoForward(stack)).toBe(false);
    });
  });

  describe('navigation flow', () => {
    it('should handle viewer → related → back → forward flow', () => {
      let stack: NavigationStack = { stack: [], forwardStack: [] };

      // Push viewer
      stack = pushView(stack, {
        mode: 'viewer',
        anchor_type: 'fault',
        anchor_id: 'fault-1',
      });

      expect(stack.stack).toHaveLength(1);
      expect(canGoBack(stack)).toBe(false);
      expect(canGoForward(stack)).toBe(false);

      // Push related
      stack = pushView(stack, {
        mode: 'related',
        anchor_type: 'fault',
        anchor_id: 'fault-1',
      });

      expect(stack.stack).toHaveLength(2);
      expect(canGoBack(stack)).toBe(true);
      expect(canGoForward(stack)).toBe(false);

      // Go back
      const backResult = goBack(stack);
      stack = backResult.stack;

      expect(backResult.view?.mode).toBe('viewer');
      expect(stack.stack).toHaveLength(1);
      expect(canGoBack(stack)).toBe(false);
      expect(canGoForward(stack)).toBe(true);

      // Go forward
      const forwardResult = goForward(stack);
      stack = forwardResult.stack;

      expect(forwardResult.view?.mode).toBe('related');
      expect(stack.stack).toHaveLength(2);
      expect(canGoBack(stack)).toBe(true);
      expect(canGoForward(stack)).toBe(false);
    });
  });
});
