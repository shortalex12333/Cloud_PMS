'use client';

/**
 * useRelatedPanel
 *
 * Encapsulates all UI state and data-fetching for the Show Related side panel.
 * Replaces the ~30-line boilerplate block that was duplicated across every
 * entity detail page (work-orders, faults, equipment, inventory).
 *
 * Usage:
 *   const panel = useRelatedPanel('work_order', workOrderId);
 *   // then use panel.open, panel.totalRelated, panel.primaryPanelProps, etc.
 */

import * as React from 'react';
import { useRelated } from '@/hooks/useRelated';
import { useAuth } from '@/hooks/useAuth';
import { isHOD } from '@/contexts/AuthContext';
import type { RelatedResponse } from '@/hooks/useRelated';

export interface RelatedPanelState {
  /** Whether the side panel is open */
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
  toggle: () => void;

  /** Whether the add-link modal is open (HOD/manager only) */
  showAddModal: boolean;
  setShowAddModal: React.Dispatch<React.SetStateAction<boolean>>;

  /** Current user can add explicit links */
  canAdd: boolean;

  /** Related data from GET /v1/related */
  data: RelatedResponse | undefined;
  isLoading: boolean;
  error: Error | null;

  /** Total items across all groups — drives badge count */
  totalRelated: number;
}

export function useRelatedPanel(
  entityType: string,
  entityId: string
): RelatedPanelState {
  const { user } = useAuth();
  const [open, setOpen] = React.useState(false);
  const [showAddModal, setShowAddModal] = React.useState(false);

  const {
    data,
    isLoading,
    error,
  } = useRelated(entityType, entityId);

  const totalRelated = data?.groups.reduce((sum, g) => sum + g.items.length, 0) ?? 0;
  const canAdd = isHOD(user);

  const toggle = React.useCallback(() => setOpen((v) => !v), []);

  return {
    open,
    setOpen,
    toggle,
    showAddModal,
    setShowAddModal,
    canAdd,
    data,
    isLoading: isLoading,
    error: error as Error | null,
    totalRelated,
  };
}
