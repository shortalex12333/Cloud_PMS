'use client';

/**
 * useEquipmentActions — Equipment action hook (FE-02-02)
 *
 * Wires all equipment action registry calls to typed helper methods.
 * Uses the unified action API endpoint per the action router spec.
 *
 * Action IDs map 1:1 to registry.py keys:
 *   view_equipment, update_equipment, link_document,
 *   create_work_order (from equipment), report_fault (from equipment)
 *
 * Role-based access is enforced at the API level; visibility gates live in
 * EquipmentLens (hide, not disable).
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

export interface EquipmentActionsState {
  isLoading: boolean;
  error: string | null;
}

// API URL — same origin Next.js API route proxied to Render backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * useEquipmentActions
 *
 * Returns typed action helpers for all equipment operations.
 * Each helper calls POST /v1/actions/execute with action name and JWT auth.
 *
 * @param equipmentId - UUID of the equipment in scope
 */
export function useEquipmentActions(equipmentId: string) {
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
        // IMPORTANT: equipment_id must be in payload (backend validation checks payload, not context)
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
              equipment_id: equipmentId,
            },
            payload: {
              equipment_id: equipmentId,
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
    [session, user, equipmentId]
  );

  // -------------------------------------------------------------------------
  // Typed action helpers — one per registry action
  // -------------------------------------------------------------------------

  /** view_equipment — log a view event for this equipment */
  const viewEquipment = useCallback(
    () => execute('view_equipment', {}),
    [execute]
  );

  /** update_equipment — update editable fields (name, location, status, etc.) */
  const updateEquipment = useCallback(
    (changes: Record<string, unknown>) =>
      execute('update_equipment', changes),
    [execute]
  );

  /** link_document — attach a document (manual, certificate, etc.) */
  const linkDocument = useCallback(
    (documentUrl: string, title: string, documentType?: string) =>
      execute('link_document_to_equipment', {
        document_url: documentUrl,
        title,
        document_type: documentType,
      }),
    [execute]
  );

  /**
   * create_work_order — create a new work order originating from this equipment.
   * Returns new work order ID on success.
   */
  const createWorkOrder = useCallback(
    (equipId: string, overrides?: Record<string, unknown>) =>
      execute('create_work_order_from_equipment', {
        equipment_id: equipId,
        ...overrides,
      }),
    [execute]
  );

  /**
   * report_fault — report a new fault on this equipment.
   * Returns new fault ID on success.
   */
  const reportFault = useCallback(
    (equipId: string, overrides?: Record<string, unknown>) =>
      execute('report_fault', {
        equipment_id: equipId,
        ...overrides,
      }),
    [execute]
  );

  /**
   * log_hours — log a new running hours reading for this equipment.
   * Records to pms_equipment_hours_log table.
   */
  const logHours = useCallback(
    (equipId: string, hoursReading: number, readingType?: string, notes?: string) =>
      execute('log_equipment_hours', {
        equipment_id: equipId,
        hours_reading: hoursReading,
        reading_type: readingType ?? 'manual',
        notes,
      }),
    [execute]
  );

  // -------------------------------------------------------------------------
  // Return
  // -------------------------------------------------------------------------

  return {
    // State
    isLoading,
    error,

    // Actions
    viewEquipment,
    updateEquipment,
    linkDocument,
    createWorkOrder,
    reportFault,
    logHours,
  };
}

// ---------------------------------------------------------------------------
// Role permission helpers
// ---------------------------------------------------------------------------

/** All roles with HOD-level or above access */
const HOD_ROLES = ['chief_engineer', 'eto', 'chief_officer', 'captain', 'manager'];

/** Roles allowed to update equipment details */
const UPDATE_ROLES = ['chief_engineer', 'eto', 'captain', 'manager'];

/** Roles allowed to create work orders */
const CREATE_WO_ROLES = ['chief_engineer', 'eto', 'chief_officer', 'captain', 'manager'];

/** Roles allowed to link documents */
const LINK_DOC_ROLES = ['chief_engineer', 'eto', 'captain', 'manager'];

/** Roles allowed to log running hours */
const LOG_HOURS_ROLES = ['chief_engineer', 'eto', 'engineer', 'captain', 'manager'];

export interface EquipmentPermissions {
  /** Can view equipment details (all crew) */
  canView: boolean;
  /** Can update equipment fields (HOD+) */
  canUpdate: boolean;
  /** Can link a document to this equipment */
  canLinkDocument: boolean;
  /** Can create a work order from this equipment */
  canCreateWorkOrder: boolean;
  /** Can report a fault on this equipment */
  canReportFault: boolean;
  /** Can log running hours for this equipment */
  canLogHours: boolean;
}

/**
 * useEquipmentPermissions
 *
 * Derives a set of boolean capability flags from the current user's role.
 * These are used to conditionally show (not disable) action buttons.
 */
export function useEquipmentPermissions(): EquipmentPermissions {
  const { user } = useAuth();
  const role = user?.role ?? '';

  return {
    canView: true, // All authenticated users can view equipment
    canUpdate: UPDATE_ROLES.includes(role),
    canLinkDocument: LINK_DOC_ROLES.includes(role),
    canCreateWorkOrder: CREATE_WO_ROLES.includes(role),
    canReportFault: HOD_ROLES.includes(role),
    canLogHours: LOG_HOURS_ROLES.includes(role),
  };
}
