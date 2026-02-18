/**
 * Navigation Context Provider
 *
 * Manages navigation stack and context lifecycle for situational continuity.
 *
 * State:
 * - situation_id: Backend navigation context ID
 * - active_anchor_type/id: Current anchor artifact
 * - stack[]: View history
 * - forwardStack[]: Forward navigation history
 *
 * Methods:
 * - pushViewer(): Navigate to artifact viewer
 * - pushRelated(): Navigate to related panel
 * - back(): Go back in stack
 * - forward(): Go forward in stack
 * - endContext(): End context and clear stacks
 */

'use client';

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import type { NavigationContext as NavContextType, RelatedResponse } from '@/lib/context-nav/api-client';
import { useAuth } from '@/hooks/useAuth';
import {
  createNavigationContext,
  updateActiveAnchor,
  getRelatedArtifacts,
  endNavigationContext,
} from '@/lib/context-nav/api-client';
import {
  pushView,
  goBack as stackGoBack,
  goForward as stackGoForward,
  clearStacks,
  getCurrentView,
  canGoBack as stackCanGoBack,
  canGoForward as stackCanGoForward,
  type NavigationStack,
  type ViewState,
} from '@/lib/context-nav/view-stack';

// ============================================================================
// TYPES
// ============================================================================

interface NavigationContextState {
  // Backend context
  contextId: string | null;
  activeAnchorType: string | null;
  activeAnchorId: string | null;

  // Navigation stacks
  stack: ViewState[];
  forwardStack: ViewState[];

  // Related data
  relatedGroups: RelatedResponse['groups'] | null;
  relatedLoading: boolean;
  relatedError: string | null;

  // User context
  yachtId: string | null;
  userId: string | null;
}

interface NavigationContextValue extends NavigationContextState {
  // Navigation methods
  pushViewer: (anchorType: string, anchorId: string, isInitial?: boolean) => Promise<void>;
  pushRelated: () => Promise<void>;
  back: () => void;
  forward: () => void;
  endContext: () => Promise<void>;

  // Helper methods
  canGoBack: boolean;
  canGoForward: boolean;
  currentView: ViewState | null;
  isRelatedView: boolean;
}

// ============================================================================
// CONTEXT
// ============================================================================

const NavigationContext = createContext<NavigationContextValue | null>(null);

export function useNavigationContext() {
  const context = useContext(NavigationContext);
  if (!context) {
    throw new Error('useNavigationContext must be used within NavigationProvider');
  }
  return context;
}

/**
 * Safe version of useNavigationContext that returns null instead of throwing.
 * Use this when NavigationProvider might not be available (e.g., in standalone renders).
 */
export function useNavigationContextSafe(): NavigationContextValue | null {
  return useContext(NavigationContext);
}

// ============================================================================
// PROVIDER
// ============================================================================

export function NavigationProvider({ children }: { children: React.ReactNode }) {
  // Get yacht_id and user_id from AuthContext - the ONLY source of truth
  const { user } = useAuth();

  const [state, setState] = useState<NavigationContextState>({
    contextId: null,
    activeAnchorType: null,
    activeAnchorId: null,
    stack: [],
    forwardStack: [],
    relatedGroups: null,
    relatedLoading: false,
    relatedError: null,
    yachtId: null,
    userId: null,
  });

  // Sync yachtId/userId from AuthContext when user changes
  useEffect(() => {
    if (user?.yachtId && user?.id) {
      setState(prev => ({
        ...prev,
        yachtId: user.yachtId,
        userId: user.id,
      }));
    }
  }, [user?.yachtId, user?.id]);

  // ========================================================================
  // PUSH VIEWER
  // ========================================================================

  const pushViewer = useCallback(
    async (anchorType: string, anchorId: string, isInitial: boolean = false) => {
      try {
        // If initial viewer from search, create context
        if (isInitial && !state.contextId) {
          // Get yacht_id and user_id from state (synced from AuthContext)
          // CRITICAL: Do NOT fall back to placeholders - fail visibly if auth not ready
          const yachtId = state.yachtId || user?.yachtId;
          const userId = state.userId || user?.id;

          if (!yachtId || !userId) {
            console.error('[NavigationContext] Cannot create context: missing yacht_id or user_id');
            return;
          }

          const context = await createNavigationContext({
            yacht_id: yachtId,
            user_id: userId,
            artefact_type: anchorType,
            artefact_id: anchorId,
          });

          // Initialize state with first view
          const navStack: NavigationStack = {
            stack: [],
            forwardStack: [],
          };

          const newStack = pushView(navStack, {
            mode: 'viewer',
            anchor_type: anchorType,
            anchor_id: anchorId,
          });

          setState({
            ...state,
            contextId: context.id,
            activeAnchorType: anchorType,
            activeAnchorId: anchorId,
            stack: newStack.stack,
            forwardStack: newStack.forwardStack,
            yachtId,
            userId,
          });
        } else if (state.contextId) {
          // Update anchor for existing context
          const yachtId = state.yachtId!;
          const userId = state.userId!;

          await updateActiveAnchor({
            context_id: state.contextId,
            anchor_type: anchorType,
            anchor_id: anchorId,
            yacht_id: yachtId,
            user_id: userId,
          });

          // Push viewer to stack
          const navStack: NavigationStack = {
            stack: state.stack,
            forwardStack: state.forwardStack,
          };

          const newStack = pushView(navStack, {
            mode: 'viewer',
            anchor_type: anchorType,
            anchor_id: anchorId,
          });

          setState({
            ...state,
            activeAnchorType: anchorType,
            activeAnchorId: anchorId,
            stack: newStack.stack,
            forwardStack: newStack.forwardStack,
          });
        }
      } catch (error) {
        console.error('[NavigationContext] Failed to push viewer:', error);
      }
    },
    [state, user]
  );

  // ========================================================================
  // PUSH RELATED
  // ========================================================================

  const pushRelated = useCallback(async () => {
    if (!state.contextId || !state.activeAnchorType || !state.activeAnchorId) {
      console.warn('[NavigationContext] Cannot show related: no active context');
      return;
    }

    try {
      // Push related view to stack
      const navStack: NavigationStack = {
        stack: state.stack,
        forwardStack: state.forwardStack,
      };

      const newStack = pushView(navStack, {
        mode: 'related',
        anchor_type: state.activeAnchorType,
        anchor_id: state.activeAnchorId,
      });

      setState({
        ...state,
        stack: newStack.stack,
        forwardStack: newStack.forwardStack,
        relatedLoading: true,
        relatedError: null,
      });

      // Fetch related artifacts
      const response = await getRelatedArtifacts({
        situation_id: state.contextId,
        anchor_type: state.activeAnchorType,
        anchor_id: state.activeAnchorId,
        tenant_id: state.yachtId!,
        user_id: state.userId!,
        allowed_domains: [
          'inventory',
          'work_orders',
          'faults',
          'shopping',
          'documents',
          'manuals',
          'emails',
          'certificates',
          'history',
        ],
      });

      setState((prev) => ({
        ...prev,
        relatedGroups: response.groups,
        relatedLoading: false,
      }));
    } catch (error) {
      console.error('[NavigationContext] Failed to fetch related:', error);
      setState((prev) => ({
        ...prev,
        relatedLoading: false,
        relatedError: error instanceof Error ? error.message : 'Unknown error',
      }));
    }
  }, [state]);

  // ========================================================================
  // BACK
  // ========================================================================

  const back = useCallback(() => {
    const navStack: NavigationStack = {
      stack: state.stack,
      forwardStack: state.forwardStack,
    };

    const result = stackGoBack(navStack);

    if (result.view) {
      setState({
        ...state,
        stack: result.stack.stack,
        forwardStack: result.stack.forwardStack,
        activeAnchorType: result.view.anchor_type,
        activeAnchorId: result.view.anchor_id,
      });
    }
  }, [state]);

  // ========================================================================
  // FORWARD
  // ========================================================================

  const forward = useCallback(() => {
    const navStack: NavigationStack = {
      stack: state.stack,
      forwardStack: state.forwardStack,
    };

    const result = stackGoForward(navStack);

    if (result.view) {
      setState({
        ...state,
        stack: result.stack.stack,
        forwardStack: result.stack.forwardStack,
        activeAnchorType: result.view.anchor_type,
        activeAnchorId: result.view.anchor_id,
      });
    }
  }, [state]);

  // ========================================================================
  // END CONTEXT
  // ========================================================================

  const endContext = useCallback(async () => {
    if (state.contextId) {
      try {
        await endNavigationContext({
          context_id: state.contextId,
          yacht_id: state.yachtId!,
          user_id: state.userId!,
        });
      } catch (error) {
        console.error('[NavigationContext] Failed to end context:', error);
      }
    }

    // Clear all state
    const emptyStack = clearStacks();
    setState({
      contextId: null,
      activeAnchorType: null,
      activeAnchorId: null,
      stack: emptyStack.stack,
      forwardStack: emptyStack.forwardStack,
      relatedGroups: null,
      relatedLoading: false,
      relatedError: null,
      yachtId: null,
      userId: null,
    });
  }, [state]);

  // ========================================================================
  // COMPUTED VALUES
  // ========================================================================

  const navStack: NavigationStack = {
    stack: state.stack,
    forwardStack: state.forwardStack,
  };

  const currentView = getCurrentView(navStack);
  const canGoBackValue = stackCanGoBack(navStack);
  const canGoForwardValue = stackCanGoForward(navStack);
  const isRelatedView = currentView?.mode === 'related';

  // ========================================================================
  // RENDER
  // ========================================================================

  const value: NavigationContextValue = {
    ...state,
    pushViewer,
    pushRelated,
    back,
    forward,
    endContext,
    canGoBack: canGoBackValue,
    canGoForward: canGoForwardValue,
    currentView,
    isRelatedView,
  };

  return <NavigationContext.Provider value={value}>{children}</NavigationContext.Provider>;
}
