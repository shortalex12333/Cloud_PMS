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
 * Each helper calls POST /v1/faults/{endpoint} with JWT auth.
 *
 * @param faultId - UUID of the fault in scope
 */
export function useFaultActions(faultId: string) {
  const { user, session } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // Internal executor — wraps every action call
  // Injects yacht_id + fault_id automatically (no repetition at call site)
  // -------------------------------------------------------------------------

  const execute = useCallback(
    async (endpoint: string, payload: Record<string, unknown>): Promise<ActionResult> => {
      if (!session?.access_token) {
        return { success: false, error: 'Not authenticated' };
      }

      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${session.access_token}`,
          },
          body: JSON.stringify({
            yacht_id: user?.yachtId,
            fault_id: faultId,
            ...payload,
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

  /** acknowledge_fault — HOD+ acknowledges the fault (sets acknowledged_at) */
  const acknowledgeFault = useCallback(
    () => execute('/v1/faults/acknowledge', {}),
    [execute]
  );

  /** close_fault — HOD+ closes/resolves the fault */
  const closeFault = useCallback(
    (resolutionNotes?: string) =>
      execute('/v1/faults/close', { resolution_notes: resolutionNotes }),
    [execute]
  );

  /** diagnose_fault — HOD+ records root cause analysis */
  const diagnoseFault = useCallback(
    (diagnosis: string, recommendedAction?: string) =>
      execute('/v1/faults/diagnose', { diagnosis, recommended_action: recommendedAction }),
    [execute]
  );

  /** reopen_fault — HOD+ reopens a previously closed fault */
  const reopenFault = useCallback(
    (reason?: string) => execute('/v1/faults/reopen', { reason }),
    [execute]
  );

  /** add_fault_photo — any crew member or HOD adds a photo */
  const addPhoto = useCallback(
    (photoUrl: string, caption?: string) =>
      execute('/v1/faults/add-photo', { photo_url: photoUrl, caption }),
    [execute]
  );

  /** add_fault_note — any crew member or HOD adds a text note */
  const addNote = useCallback(
    (noteText: string) => execute('/v1/faults/add-note', { text: noteText }),
    [execute]
  );

  // -------------------------------------------------------------------------
  // Return
  // -------------------------------------------------------------------------

  return {
    // State
    isLoading,
    error,

    // Status transitions
    acknowledgeFault,
    closeFault,
    reopenFault,

    // Diagnostic
    diagnoseFault,

    // Notes and media
    addNote,
    addPhoto,
  };
}

// ---------------------------------------------------------------------------
// Role permission helpers
// ---------------------------------------------------------------------------

/** Roles with HOD-level or above access (acknowledge, diagnose, close, reopen) */
const HOD_ROLES = ['chief_engineer', 'eto', 'chief_officer', 'captain', 'manager'];

/** Roles allowed to close / diagnose / acknowledge faults — registry: chief_engineer, chief_officer, captain */
const FAULT_ACTION_ROLES = ['chief_engineer', 'chief_officer', 'captain'];

/** Roles allowed to add notes/photos — registry: crew + HOD + captain */
const ADD_CONTENT_ROLES = ['crew', 'chief_engineer', 'chief_officer', 'captain'];

export interface FaultPermissions {
  /** Can acknowledge fault (HOD+) */
  canAcknowledge: boolean;
  /** Can close / resolve fault (chief_engineer, chief_officer, captain) */
  canClose: boolean;
  /** Can diagnose fault (chief_engineer, chief_officer, captain) */
  canDiagnose: boolean;
  /** Can reopen a closed fault (chief_engineer, chief_officer, captain) */
  canReopen: boolean;
  /** Can add notes (crew + HOD + captain) */
  canAddNote: boolean;
  /** Can add photos (crew + HOD + captain) */
  canAddPhoto: boolean;
}

/**
 * useFaultPermissions
 *
 * Derives boolean capability flags from the current user's role.
 * Used to conditionally show (not disable) action buttons in FaultLens.
 */
export function useFaultPermissions(): FaultPermissions {
  const { user } = useAuth();
  const role = user?.role ?? '';

  return {
    canAcknowledge: HOD_ROLES.includes(role),
    canClose: FAULT_ACTION_ROLES.includes(role),
    canDiagnose: FAULT_ACTION_ROLES.includes(role),
    canReopen: FAULT_ACTION_ROLES.includes(role),
    canAddNote: ADD_CONTENT_ROLES.includes(role),
    canAddPhoto: ADD_CONTENT_ROLES.includes(role),
  };
}
