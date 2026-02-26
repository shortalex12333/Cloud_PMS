'use client';

/**
 * useFaultActions — Fault action hook (FE-02-01)
 *
 * Wires all fault action registry calls to typed helper methods.
 * Uses the unified action API endpoint per the action router spec.
 *
 * Action IDs map 1:1 to registry.py keys:
 *   report_fault, acknowledge_fault, close_fault, diagnose_fault,
 *   reopen_fault, add_fault_photo, add_fault_note
 *
 * Role-based access is enforced at the API level; visibility gates live in
 * FaultLens (hide, not disable — per UI_SPEC.md).
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

export interface FaultActionsState {
  isLoading: boolean;
  error: string | null;
}

// API URL — same origin Next.js API route proxied to Render backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * useFaultActions
 *
 * Returns typed action helpers for all fault operations.
 * Each helper calls POST /v1/actions/execute with action name and JWT auth.
 *
 * @param faultId - UUID of the fault in scope
 */
export function useFaultActions(faultId: string) {
  const { user, session } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // Internal executor — wraps every action call
  // Injects yacht_id + fault_id automatically via context
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
        // IMPORTANT: fault_id must be in payload (backend validation checks payload, not context)
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
              fault_id: faultId,
            },
            payload: {
              fault_id: faultId,
              ...payload,
            },
          }),
        });

        const json = await response.json().catch(() => ({}));

        if (!response.ok) {
          const msg =
            (json as { error?: string; detail?: string }).error ||
            (json as { error?: string; detail?: string }).detail ||
            `Request failed (${response.status})`;
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
    [session, user, faultId]
  );

  // -------------------------------------------------------------------------
  // Typed action helpers — one per registry action
  // -------------------------------------------------------------------------

  /** report_fault — all crew can report a new fault */
  const reportFault = useCallback(
    (params: {
      equipment_id: string;
      title: string;
      description?: string;
      severity?: 'cosmetic' | 'minor' | 'major' | 'critical' | 'safety';
    }) =>
      execute('report_fault', {
        equipment_id: params.equipment_id,
        title: params.title,
        description: params.description,
        severity: params.severity ?? 'minor',
      }),
    [execute]
  );

  /** acknowledge_fault — Engineer+ acknowledges the fault (sets status=investigating) */
  const acknowledgeFault = useCallback(
    () => execute('acknowledge_fault', {}),
    [execute]
  );

  /** close_fault — Engineer+ closes/resolves the fault (sets status=closed) */
  const closeFault = useCallback(
    (resolutionNotes?: string) =>
      execute('close_fault', { resolution_notes: resolutionNotes }),
    [execute]
  );

  /** update_fault — Engineer+ updates severity/description */
  const updateFault = useCallback(
    (params: {
      severity?: 'cosmetic' | 'minor' | 'major' | 'critical' | 'safety';
      description?: string;
      title?: string;
    }) =>
      execute('update_fault', {
        severity: params.severity,
        description: params.description,
        title: params.title,
      }),
    [execute]
  );

  /** reopen_fault — Engineer+ reopens a previously closed fault (sets status=open) */
  const reopenFault = useCallback(
    (reason?: string) => execute('reopen_fault', { reason }),
    [execute]
  );

  /** diagnose_fault — Engineer+ adds diagnosis notes (sets status=diagnosed) */
  const diagnoseFault = useCallback(
    (diagnosis: string, recommendedAction?: string) =>
      execute('diagnose_fault', { diagnosis, recommended_action: recommendedAction }),
    [execute]
  );

  /** mark_fault_false_alarm — Engineer+ marks fault as false alarm (sets status=false_alarm) */
  const markFalseAlarm = useCallback(
    (reason?: string) => execute('mark_fault_false_alarm', { reason }),
    [execute]
  );

  /** add_fault_photo — any crew member or HOD adds a photo */
  const addPhoto = useCallback(
    (photoUrl: string, caption?: string) =>
      execute('add_fault_photo', { photo_url: photoUrl, caption }),
    [execute]
  );

  /** add_fault_note — any crew member or HOD adds a text note */
  const addNote = useCallback(
    (noteText: string) => execute('add_fault_note', { text: noteText }),
    [execute]
  );

  // -------------------------------------------------------------------------
  // Return
  // -------------------------------------------------------------------------

  return {
    // State
    isLoading,
    error,

    // Create
    reportFault,

    // Status transitions
    acknowledgeFault,
    closeFault,
    reopenFault,
    markFalseAlarm,
    diagnoseFault,

    // Update
    updateFault,

    // Notes and media
    addNote,
    addPhoto,
  };
}

// ---------------------------------------------------------------------------
// Role permission helpers
// ---------------------------------------------------------------------------

/** All crew roles (can report faults, add notes/photos) */
const ALL_CREW_ROLES = ['crew', 'deckhand', 'steward', 'chef', 'eto', 'engineer', 'chief_engineer', 'chief_officer', 'captain', 'manager'];

/** Engineer+ roles (acknowledge, close, update, reopen, mark false alarm) */
const ENGINEER_PLUS_ROLES = ['eto', 'engineer', 'chief_engineer', 'chief_officer', 'captain', 'manager'];

/** Roles allowed to add notes/photos — all crew per LENS.md */
const ADD_CONTENT_ROLES = ['crew', 'deckhand', 'steward', 'chef', 'eto', 'engineer', 'chief_engineer', 'chief_officer', 'captain', 'manager'];

export interface FaultPermissions {
  /** Can report a new fault (all crew) */
  canReport: boolean;
  /** Can acknowledge fault (engineer+) */
  canAcknowledge: boolean;
  /** Can close / resolve fault (engineer+) */
  canClose: boolean;
  /** Can update fault severity/description (engineer+) */
  canUpdate: boolean;
  /** Can reopen a closed fault (engineer+) */
  canReopen: boolean;
  /** Can mark fault as false alarm (engineer+) */
  canMarkFalseAlarm: boolean;
  /** Can diagnose fault (engineer+) */
  canDiagnose: boolean;
  /** Can add notes (all crew) */
  canAddNote: boolean;
  /** Can add photos (all crew) */
  canAddPhoto: boolean;
}

/**
 * useFaultPermissions
 *
 * Derives boolean capability flags from the current user's role.
 * Used to conditionally show (not disable) action buttons in FaultLens.
 * Per UI_SPEC.md: hide, not disable for role gates.
 *
 * Role matrix per LENS.md:
 * - report_fault:            all crew
 * - acknowledge_fault:       engineer+ (eto, engineer, chief_engineer, chief_officer, captain, manager)
 * - close_fault:             engineer+
 * - update_fault:            engineer+
 * - reopen_fault:            engineer+
 * - mark_fault_false_alarm:  engineer+
 * - add_fault_note:          all crew
 * - add_fault_photo:         all crew
 */
export function useFaultPermissions(): FaultPermissions {
  const { user } = useAuth();
  const role = user?.role ?? '';

  return {
    canReport: ALL_CREW_ROLES.includes(role),
    canAcknowledge: ENGINEER_PLUS_ROLES.includes(role),
    canClose: ENGINEER_PLUS_ROLES.includes(role),
    canUpdate: ENGINEER_PLUS_ROLES.includes(role),
    canReopen: ENGINEER_PLUS_ROLES.includes(role),
    canMarkFalseAlarm: ENGINEER_PLUS_ROLES.includes(role),
    canDiagnose: ENGINEER_PLUS_ROLES.includes(role),
    canAddNote: ADD_CONTENT_ROLES.includes(role),
    canAddPhoto: ADD_CONTENT_ROLES.includes(role),
  };
}
