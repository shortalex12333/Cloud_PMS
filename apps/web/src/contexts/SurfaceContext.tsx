'use client';

/**
 * SurfaceContext - Single Surface State Management
 *
 * Manages the state machine for the single-surface UX:
 * - search-dominant (default): Spotlight centered, no panels
 * - email-present: Email panel slides in from left
 * - context-open: Context panel slides in from right
 *
 * No URL changes - all state-based with CSS transitions.
 */

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  ReactNode,
} from 'react';

// ============================================================================
// TYPES
// ============================================================================

export type SurfaceState = 'search-dominant' | 'email-present' | 'context-open';

export interface EmailPanelState {
  visible: boolean;
  threadId?: string;
  folder?: 'inbox' | 'sent';
}

export interface ContextPanelState {
  visible: boolean;
  expanded: boolean;
  entityType?: string;
  entityId?: string;
  entityData?: Record<string, unknown>;
}

export interface SurfaceContextValue {
  // Current state
  state: SurfaceState;
  emailPanel: EmailPanelState;
  contextPanel: ContextPanelState;

  // Actions
  showEmail: (options?: { threadId?: string; folder?: 'inbox' | 'sent' }) => void;
  hideEmail: () => void;
  showContext: (entityType: string, entityId: string, data?: Record<string, unknown>) => void;
  hideContext: () => void;
  expandContext: () => void;
  collapseContext: () => void;
  reset: () => void;

  // Utilities
  isSearchDominant: boolean;
  hasAnyPanel: boolean;
}

// ============================================================================
// CONTEXT
// ============================================================================

const SurfaceContext = createContext<SurfaceContextValue | null>(null);

// ============================================================================
// PROVIDER
// ============================================================================

interface SurfaceProviderProps {
  children: ReactNode;
}

export function SurfaceProvider({ children }: SurfaceProviderProps) {
  const [state, setState] = useState<SurfaceState>('search-dominant');

  const [emailPanel, setEmailPanel] = useState<EmailPanelState>({
    visible: false,
  });

  const [contextPanel, setContextPanel] = useState<ContextPanelState>({
    visible: false,
    expanded: false,
  });

  // Show email panel (slides from left)
  const showEmail = useCallback(
    (options?: { threadId?: string; folder?: 'inbox' | 'sent' }) => {
      setEmailPanel({
        visible: true,
        threadId: options?.threadId,
        folder: options?.folder || 'inbox',
      });
      setState('email-present');

      // Hide context panel if open
      setContextPanel((prev) => ({ ...prev, visible: false }));
    },
    []
  );

  // Hide email panel
  const hideEmail = useCallback(() => {
    setEmailPanel({ visible: false });
    setState(contextPanel.visible ? 'context-open' : 'search-dominant');
  }, [contextPanel.visible]);

  // Show context panel (slides from right) - Opens FULL-SCREEN immediately
  // Per user requirement: no sidebar step, go directly to expanded view
  const showContext = useCallback(
    (entityType: string, entityId: string, data?: Record<string, unknown>) => {
      setContextPanel({
        visible: true,
        expanded: true, // Open full-screen immediately
        entityType,
        entityId,
        entityData: data,
      });
      setState('context-open');

      // Hide email panel if open
      setEmailPanel((prev) => ({ ...prev, visible: false }));
    },
    []
  );

  // Hide context panel
  const hideContext = useCallback(() => {
    console.log('[SurfaceContext] 🚪 hideContext called');
    setContextPanel((prev) => {
      console.log('[SurfaceContext] Panel state before:', prev.visible, '→ false');
      return { visible: false, expanded: false };
    });
    // Access emailPanel from outer scope - it's stable in this closure
    const newState = emailPanel.visible ? 'email-present' : 'search-dominant';
    console.log('[SurfaceContext] State transition: →', newState);
    setState(newState);
  }, []); // Empty deps to stabilize reference - emailPanel access is intentional

  // Expand context panel to full-screen
  const expandContext = useCallback(() => {
    setContextPanel((prev) => ({ ...prev, expanded: true }));
  }, []);

  // Collapse context panel back to sidebar
  const collapseContext = useCallback(() => {
    setContextPanel((prev) => ({ ...prev, expanded: false }));
  }, []);

  // Reset to default state
  const reset = useCallback(() => {
    setEmailPanel({ visible: false });
    setContextPanel({ visible: false, expanded: false });
    setState('search-dominant');
  }, []);

  const value: SurfaceContextValue = {
    state,
    emailPanel,
    contextPanel,
    showEmail,
    hideEmail,
    showContext,
    hideContext,
    expandContext,
    collapseContext,
    reset,
    isSearchDominant: state === 'search-dominant',
    hasAnyPanel: emailPanel.visible || contextPanel.visible,
  };

  return (
    <SurfaceContext.Provider value={value}>{children}</SurfaceContext.Provider>
  );
}

// ============================================================================
// HOOK
// ============================================================================

export function useSurface(): SurfaceContextValue {
  const context = useContext(SurfaceContext);
  if (!context) {
    throw new Error('useSurface must be used within a SurfaceProvider');
  }
  return context;
}

/**
 * Safe version of useSurface that returns null if not in SurfaceProvider
 * Use this when the component may be rendered outside the SurfaceProvider
 */
export function useSurfaceSafe(): SurfaceContextValue | null {
  return useContext(SurfaceContext);
}

