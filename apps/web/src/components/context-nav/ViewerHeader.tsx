/**
 * ViewerHeader Component
 *
 * Back/Forward navigation buttons for artifact viewers.
 * Appears at the top of FaultCard, WorkOrderCard, DocumentViewer, etc.
 */

'use client';

import React from 'react';

interface ViewerHeaderProps {
  /** Current artifact type (for context) */
  artefactType: string;
  /** Current artifact ID */
  artefactId: string;
  /** Optional custom actions */
  actions?: React.ReactNode;
}

export function ViewerHeader({ artefactType, artefactId, actions }: ViewerHeaderProps) {
  // TODO: Implement in Phase 4
  // const { canGoBack, canGoForward, goBack, goForward } = useViewStack();
  // const { showRelated } = useRelatedPanel();

  return (
    <header className="viewer-header flex items-center justify-between p-4 border-b">
      <div className="navigation-controls flex gap-2">
        <button
          disabled={true} // TODO: Connect to useViewStack
          className="btn-secondary"
          aria-label="Go back"
        >
          ← Back
        </button>
        <button
          disabled={true} // TODO: Connect to useViewStack
          className="btn-secondary"
          aria-label="Go forward"
        >
          Forward →
        </button>
      </div>

      <div className="viewer-actions flex gap-2">
        <button
          className="btn-primary"
          onClick={() => {
            // TODO: Open RelatedPanel
            console.log('Show Related - Not implemented yet');
          }}
        >
          Show Related
        </button>
        {actions}
      </div>
    </header>
  );
}

// TODO: Implement full functionality in Phase 4
