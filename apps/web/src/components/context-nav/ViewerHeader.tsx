/**
 * ViewerHeader Component
 *
 * Back/Forward navigation buttons for artifact viewers.
 * Appears at the top of FaultCard, WorkOrderCard, DocumentViewer, etc.
 */

'use client';

import React from 'react';
import { useNavigationContext } from '@/contexts/NavigationContext';

interface ViewerHeaderProps {
  /** Current artifact type (for context) */
  artefactType: string;
  /** Current artifact ID */
  artefactId: string;
  /** Optional custom actions */
  actions?: React.ReactNode;
}

export function ViewerHeader({ artefactType, artefactId, actions }: ViewerHeaderProps) {
  const { canGoBack, canGoForward, back, forward, pushRelated } = useNavigationContext();

  return (
    <header className="viewer-header flex items-center justify-between p-4 border-b">
      <div className="navigation-controls flex gap-2">
        <button
          disabled={!canGoBack}
          className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Go back"
          onClick={back}
        >
          ← Back
        </button>
        <button
          disabled={!canGoForward}
          className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Go forward"
          onClick={forward}
        >
          Forward →
        </button>
      </div>

      <div className="viewer-actions flex gap-2">
        <button className="btn-primary" onClick={pushRelated}>
          Show Related ▸
        </button>
        {actions}
      </div>
    </header>
  );
}
