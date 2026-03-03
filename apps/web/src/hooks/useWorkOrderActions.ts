'use client';

/**
 * useWorkOrderActions — Work Order action hook (FE-01-03)
 *
 * Wires all work order action registry calls to typed helper methods.
 * Uses the unified action API endpoint per the action router spec.
 *
 * Action IDs map 1:1 to registry.py keys:
 *   add_wo_note, close_work_order, start_work_order, cancel_work_order,
 *   add_wo_part, add_parts_to_work_order, add_work_order_photo,
 *   assign_work_order, reassign_work_order, update_work_order,
 *   archive_work_order, add_wo_hours, view_work_order_checklist,
 *   create_work_order_from_fault, view_my_work_orders, view_related_entities
 *
 * Role-based access is enforced at the API level; visibility gates live in
 * WorkOrderLens (hide, not disable).
 */

import { useState, useCallback } from 'react';
import { useAuth } from '@/hooks/useAuth';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ActionResult {
  success: boolean;
  message?: string;
  data?: Record<string, unknown>;
  error?: string;
}

export interface WorkOrderActionsState {
  isLoading: boolean;
  error: string | null;
}

// API URL — same origin Next.js API route proxied to Render backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * useWorkOrderActions
 *
 * Returns typed action helpers for all work order operations.
 * Each helper calls POST /v1/actions/execute with action name and JWT auth.
 *
 * @param workOrderId - UUID of the work order in scope
 */
export function useWorkOrderActions(workOrderId: string) {
  const { user, session } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // Internal executor — wraps every action call
  // -------------------------------------------------------------------------

  const execute = useCallback(
    async (actionName: string, payload: Record<string, unknown>): Promise<ActionResult> => {
      if (!session?.access_token) {
        return { success: false, error: 'Not authenticated' };
      }

      setIsLoading(true);
      setError(null);

      try {
        // Use unified action router endpoint - /v1/actions/execute
        // IMPORTANT: work_order_id must be in payload (backend validation checks payload, not context)
        const response = await fetch(`${API_BASE}/v1/actions/execute`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${session.access_token}`,
          },
          body: JSON.stringify({
            action: actionName,
            context: {
              yacht_id: user?.yachtId,
              work_order_id: workOrderId,
            },
            payload: {
              work_order_id: workOrderId,
              ...payload,
            },
          }),
        });

        const json = await response.json().catch(() => ({}));

        if (!response.ok) {
          const msg = (json as { error?: string; detail?: string }).error
            || (json as { error?: string; detail?: string }).detail
            || `Request failed (${response.status})`;
          setError(msg);
          return { success: false, error: msg };
        }

        return { success: true, ...(json as object) };
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Unknown error';
        setError(msg);
        return { success: false, error: msg };
      } finally {
        setIsLoading(false);
      }
    },
    [session, user, workOrderId]
  );

  // -------------------------------------------------------------------------
  // Typed action helpers — one per registry action
  // -------------------------------------------------------------------------

  /** add_wo_note — add a text note to the work order */
  const addNote = useCallback(
    (noteText: string) =>
      execute('add_wo_note', { note_text: noteText }),
    [execute]
  );

  /** close_work_order — mark the WO as closed (HOD+) */
  const closeWorkOrder = useCallback(
    (completionNotes?: string) =>
      execute('mark_work_order_complete', { completion_notes: completionNotes }),
    [execute]
  );

  /** start_work_order — transition from open → in_progress */
  const startWorkOrder = useCallback(
    () => execute('start_work_order', {}),
    [execute]
  );

  /** cancel_work_order — cancel the work order (HOD+) */
  const cancelWorkOrder = useCallback(
    (reason?: string) => execute('cancel_work_order', { reason }),
    [execute]
  );

  /** add_wo_part — attach a part to the work order */
  const addPart = useCallback(
    (partId: string, quantity: number, unit?: string) =>
      execute('add_part_to_work_order', { part_id: partId, quantity, unit }),
    [execute]
  );

  /** add_parts_to_work_order — bulk add parts */
  const addParts = useCallback(
    (parts: Array<{ part_id: string; quantity: number }>) =>
      execute('add_parts_to_work_order', { parts }),
    [execute]
  );

  /** add_work_order_photo — attach a photo (signed storage URL) */
  const addPhoto = useCallback(
    (photoUrl: string, caption?: string) =>
      execute('add_work_order_photo', { photo_url: photoUrl, caption }),
    [execute]
  );

  /** assign_work_order — assign to a crew member */
  const assignWorkOrder = useCallback(
    (assignedTo: string) =>
      execute('assign_work_order', { assigned_to: assignedTo }),
    [execute]
  );

  /** reassign_work_order — signed reassignment with reason */
  const reassignWorkOrder = useCallback(
    (assigneeId: string, reason: string, signature: Record<string, unknown>) =>
      execute('reassign_work_order', { assignee_id: assigneeId, reason, signature }),
    [execute]
  );

  /** update_work_order — update editable fields (title, priority, due_date, etc.) */
  const updateWorkOrder = useCallback(
    (changes: Record<string, unknown>) =>
      execute('update_work_order', changes),
    [execute]
  );

  /** archive_work_order — signed archive with deletion reason */
  const archiveWorkOrder = useCallback(
    (deletionReason: string, signature: Record<string, unknown>) =>
      execute('archive_work_order', { deletion_reason: deletionReason, signature }),
    [execute]
  );

  /** add_wo_hours — log hours worked on the work order */
  const addHours = useCallback(
    (hours: number, notes?: string) =>
      execute('add_wo_hours', { hours, notes }),
    [execute]
  );

  /** view_work_order_checklist — fetch checklist items (read-only) */
  const viewChecklist = useCallback(
    () => execute('view_work_order_checklist', {}),
    [execute]
  );

  /** view_my_work_orders — fetch work orders assigned to current user (read-only) */
  const viewMyWorkOrders = useCallback(
    (params?: {
      status_filter?: string[];
      date_range?: { start: string; end: string };
      group_by?: 'status' | 'priority' | 'equipment';
    }) =>
      execute('view_my_work_orders', {
        status_filter: params?.status_filter,
        date_range: params?.date_range,
        group_by: params?.group_by,
      }),
    [execute]
  );

  /** view_related_entities — fetch context links (parts, manuals, handovers, faults, certificates) */
  const viewRelatedEntities = useCallback(
    (entityTypes?: ('part' | 'manual' | 'handover' | 'fault' | 'certificate')[]) =>
      execute('view_related_entities', { entity_types: entityTypes }),
    [execute]
  );

  // -------------------------------------------------------------------------
  // Return
  // -------------------------------------------------------------------------

  return {
    // State
    isLoading,
    error,

    // Note actions
    addNote,

    // Status transitions
    startWorkOrder,
    closeWorkOrder,
    cancelWorkOrder,

    // Parts
    addPart,
    addParts,

    // Attachments
    addPhoto,

    // Assignment
    assignWorkOrder,
    reassignWorkOrder,

    // Updates
    updateWorkOrder,

    // Privileged
    archiveWorkOrder,

    // Hours
    addHours,

    // Read-only
    viewChecklist,
    viewMyWorkOrders,
    viewRelatedEntities,
  };
}

// ---------------------------------------------------------------------------
// Role permission helpers - DELEGATED TO CENTRALIZED SERVICE
// ---------------------------------------------------------------------------

import { useWorkOrderPermissions as useCentralizedWorkOrderPermissions } from '@/hooks/permissions/useWorkOrderPermissions';

export interface WorkOrderPermissions {
  /** Can add a note (all roles per lens_matrix) */
  canAddNote: boolean;
  /** Can close/complete (chief_engineer, captain, manager) */
  canClose: boolean;
  /** Can start the work order (all roles) */
  canStart: boolean;
  /** Can cancel (chief_engineer, captain, manager) */
  canCancel: boolean;
  /** Can add parts (all roles per lens_matrix) */
  canAddPart: boolean;
  /** Can add photos (all roles per lens_matrix) */
  canAddPhoto: boolean;
  /** Can assign/reassign (chief_engineer, captain, manager) */
  canAssign: boolean;
  /** Can archive (chief_engineer, captain, manager) */
  canArchive: boolean;
  /** Can update WO details (all roles per lens_matrix) */
  canUpdate: boolean;
  /** Can log hours (all roles) */
  canAddHours: boolean;
  /** Can view related entities */
  canViewRelated: boolean;
}

/**
 * useWorkOrderPermissions
 *
 * Derives a set of boolean capability flags from the current user's role.
 * DELEGATED TO CENTRALIZED SERVICE - reads from lens_matrix.json
 */
export function useWorkOrderPermissions(): WorkOrderPermissions {
  const central = useCentralizedWorkOrderPermissions();

  return {
    // From lens_matrix.json work_order lens
    canAddNote: central.canAddNoteToWorkOrder,
    canClose: central.canCloseWorkOrder,
    canStart: central.canUpdateWorkOrder, // Starting is an update action
    canCancel: central.canCloseWorkOrder, // Cancel requires same permissions as close
    canAddPart: central.canAddPartToWorkOrder,
    canAddPhoto: central.canAttachPhotoToWorkOrder,
    canAssign: central.canAssignWorkOrder,
    canArchive: central.canCloseWorkOrder, // Archive requires close permissions
    canUpdate: central.canUpdateWorkOrder,
    canAddHours: central.canUpdateWorkOrder, // Hours update is a WO update
    canViewRelated: true, // All authenticated users can view related entities
  };
}
