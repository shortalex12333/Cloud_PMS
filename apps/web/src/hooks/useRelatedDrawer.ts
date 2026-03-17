'use client';

/**
 * useRelatedDrawer
 *
 * Encapsulates all UI state and data-fetching for the RelatedDrawer.
 * Replaces the ~30-line boilerplate block that was duplicated across every
 * entity detail page (work-orders, faults, equipment, inventory).
 *
 * Usage:
 *   const drawer = useRelatedDrawer('work_order', workOrderId);
 *   // then use drawer.open, drawer.totalRelated, etc.
 */

import * as React from 'react';
import { useRelated } from '@/hooks/useRelated';
import { useAuth } from '@/hooks/useAuth';
import { isHOD } from '@/contexts/AuthContext';
import type { RelatedResponse } from '@/hooks/useRelated';

export interface RelatedDrawerState {
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

export function useRelatedDrawer(
  entityType: string,
  entityId: string
): RelatedDrawerState {
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
