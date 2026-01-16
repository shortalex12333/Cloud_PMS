'use client';

/**
 * Situation Router
 *
 * Central dispatcher for all situation types:
 * - Document Situation (read-only + capture)
 * - Equipment Situation (maintenance)
 * - Work Order Situation (execution + signature)
 * - Inventory Situation (stock management)
 * - Hours of Rest Situation (compliance ledger)
 *
 * Routes to appropriate viewer based on entity type
 *
 * INTEGRATION WITH CONTEXT NAVIGATION:
 * - Wraps with NavigationProvider
 * - Creates context on initial viewer open from search
 * - Renders ViewerHeader on all viewers
 * - Renders RelatedPanel when view_mode == 'related'
 * - Ends context when returning to search home
 */

import React, { useEffect } from 'react';
import type { SituationContext, EntityType } from '@/types/situation';
import DocumentViewer from './DocumentSituationView';
import { NavigationProvider, useNavigationContext } from '@/contexts/NavigationContext';
import { ViewerHeader } from '@/components/context-nav/ViewerHeader';
import { RelatedPanel } from '@/components/context-nav/RelatedPanel';

// ============================================================================
// TYPES
// ============================================================================

export interface SituationRouterProps {
  situation: SituationContext | null;
  onClose: () => void;
  onAction?: (action: string, payload: any) => void;
}

export interface SituationViewerData {
  id: string;
  title: string;
  subtitle?: string;
  metadata?: Record<string, any>;
}

// ============================================================================
// INNER ROUTER (with access to NavigationContext)
// ============================================================================

function SituationRouterInner({
  situation,
  onClose,
  onAction,
}: SituationRouterProps) {
  const {
    pushViewer,
    endContext,
    isRelatedView,
    contextId,
    activeAnchorType,
    activeAnchorId,
  } = useNavigationContext();

  // End context when situation becomes IDLE (user returned to search home)
  useEffect(() => {
    if (situation?.state === 'IDLE' && contextId) {
      endContext();
    }
  }, [situation?.state, contextId, endContext]);

  // Create context on initial viewer open from search
  useEffect(() => {
    if (
      situation &&
      situation.state === 'ACTIVE' &&
      !contextId &&
      situation.primary_entity_id
    ) {
      // Initial viewer open from search
      pushViewer(situation.primary_entity_type, situation.primary_entity_id, true);
    }
  }, [situation, contextId, pushViewer]);

  if (!situation || situation.state === 'IDLE') {
    return null;
  }

  // Only render viewer when ACTIVE
  if (situation.state !== 'ACTIVE') {
    return null;
  }

  // If in related view, show RelatedPanel instead of viewer
  if (isRelatedView && contextId && activeAnchorType && activeAnchorId) {
    return (
      <div className="situation-container">
        <ViewerHeader
          artefactType={activeAnchorType}
          artefactId={activeAnchorId}
        />
        <RelatedPanel
          anchorType={activeAnchorType}
          anchorId={activeAnchorId}
          contextId={contextId}
        />
      </div>
    );
  }

  // Render viewer with header
  const viewer = renderViewer(situation, onClose, onAction);

  if (!viewer) return null;

  return (
    <div className="situation-container">
      <ViewerHeader
        artefactType={situation.primary_entity_type}
        artefactId={situation.primary_entity_id}
      />
      {viewer}
    </div>
  );
}

// ============================================================================
// VIEWER RENDERING
// ============================================================================

function renderViewer(
  situation: SituationContext,
  onClose: () => void,
  onAction?: (action: string, payload: any) => void
) {
  // Route to appropriate viewer based on entity type
  switch (situation.primary_entity_type) {
    case 'document':
      return (
        <DocumentViewer
          situation={situation}
          onClose={onClose}
          onAction={onAction}
        />
      );

    case 'equipment':
      // TODO: Implement EquipmentSituationView
      console.log('[SituationRouter] Equipment viewer not yet implemented');
      return null;

    case 'work_order':
      // TODO: Implement WorkOrderSituationView
      console.log('[SituationRouter] Work Order viewer not yet implemented');
      return null;

    case 'inventory':
    case 'part':
      // TODO: Implement InventorySituationView
      console.log('[SituationRouter] Inventory viewer not yet implemented');
      return null;

    case 'fault':
      // TODO: Implement FaultSituationView
      console.log('[SituationRouter] Fault viewer not yet implemented');
      return null;

    default:
      console.warn('[SituationRouter] Unknown entity type:', situation.primary_entity_type);
      return null;
  }
}

// ============================================================================
// OUTER ROUTER (with NavigationProvider)
// ============================================================================

export default function SituationRouter(props: SituationRouterProps) {
  return (
    <NavigationProvider>
      <SituationRouterInner {...props} />
    </NavigationProvider>
  );
}
