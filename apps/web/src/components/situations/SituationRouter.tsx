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
 */

import React from 'react';
import type { SituationContext, EntityType } from '@/types/situation';
import DocumentViewer from './DocumentSituationView';

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
// ROUTER
// ============================================================================

export default function SituationRouter({
  situation,
  onClose,
  onAction,
}: SituationRouterProps) {
  if (!situation || situation.state === 'IDLE') {
    return null;
  }

  // Only render viewer when ACTIVE
  if (situation.state !== 'ACTIVE') {
    return null;
  }

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
