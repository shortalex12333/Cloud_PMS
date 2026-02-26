'use client';

/**
 * useEquipmentActions — Equipment action hook (FE-02-02)
 *
 * Wires all equipment action registry calls to typed helper methods.
 * Uses the unified action API endpoint per the action router spec.
 *
 * SPEC ACTIONS (equipment_lens_v2_PHASE_4_ACTIONS.md):
 * 1. update_equipment_status - Change status (engineer+)
 * 2. add_equipment_note - Add note (all crew)
 * 3. attach_file_to_equipment - Upload photo/doc (all crew)
 * 4. create_work_order_for_equipment - Create WO (engineer+)
 * 5. link_part_to_equipment - Add to BOM (engineer+)
 * 6. flag_equipment_attention - Set/clear attention flag (engineer+)
 * 7. decommission_equipment - Terminal state (captain/manager, SIGNED)
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

/** Equipment status values */
export type EquipmentStatus = 'operational' | 'maintenance' | 'faulty' | 'offline' | 'decommissioned';

/** Signature data for signed actions */
export interface SignatureData {
  signature_base64: string;
  signed_at: string;
  signer_name: string;
  signer_role: string;
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
  // SPEC ACTION 1: update_equipment_status
  // Change equipment status (engineer+)
  // -------------------------------------------------------------------------

  /**
   * update_equipment_status — Change equipment operational status
   * @param newStatus - Target status (operational, maintenance, faulty, offline)
   * @param reason - Optional reason for status change
   */
  const updateEquipmentStatus = useCallback(
    (newStatus: EquipmentStatus, reason?: string) =>
      execute('update_equipment_status', {
        status: newStatus,
        reason,
      }),
    [execute]
  );

  // -------------------------------------------------------------------------
  // SPEC ACTION 2: add_equipment_note
  // Add note (all crew)
  // -------------------------------------------------------------------------

  /**
   * add_equipment_note — Add observation or note to equipment record
   * @param noteText - The note content
   * @param noteType - Optional note type (observation, issue, maintenance, etc.)
   */
  const addEquipmentNote = useCallback(
    (noteText: string, noteType?: string) =>
      execute('add_equipment_note', {
        note_text: noteText,
        note_type: noteType,
      }),
    [execute]
  );

  // -------------------------------------------------------------------------
  // SPEC ACTION 3: attach_file_to_equipment
  // Upload photo/doc (all crew)
  // -------------------------------------------------------------------------

  /**
   * attach_file_to_equipment — Attach a photo or document to equipment
   * @param fileUrl - Storage URL of the uploaded file
   * @param fileName - Original file name
   * @param fileType - MIME type or category (image, document, manual, etc.)
   * @param caption - Optional caption or description
   */
  const attachFileToEquipment = useCallback(
    (fileUrl: string, fileName: string, fileType?: string, caption?: string) =>
      execute('attach_file_to_equipment', {
        file_url: fileUrl,
        file_name: fileName,
        file_type: fileType,
        caption,
      }),
    [execute]
  );

  // -------------------------------------------------------------------------
  // SPEC ACTION 4: create_work_order_for_equipment
  // Create WO (engineer+)
  // -------------------------------------------------------------------------

  /**
   * create_work_order_for_equipment — Create a new work order for this equipment
   * @param title - Work order title
   * @param description - Work order description
   * @param priority - Priority level (routine, important, critical)
   * @param type - Work order type (scheduled, corrective, unplanned)
   * @param dueDate - Optional due date (ISO string)
   * @param assignedTo - Optional assignee user ID
   */
  const createWorkOrderForEquipment = useCallback(
    (
      title: string,
      description: string,
      priority: 'routine' | 'important' | 'critical' = 'routine',
      type: 'scheduled' | 'corrective' | 'unplanned' = 'corrective',
      dueDate?: string,
      assignedTo?: string
    ) =>
      execute('create_work_order_for_equipment', {
        title,
        description,
        priority,
        type,
        due_date: dueDate,
        assigned_to: assignedTo,
      }),
    [execute]
  );

  // -------------------------------------------------------------------------
  // SPEC ACTION 5: link_part_to_equipment
  // Add to BOM (engineer+)
  // -------------------------------------------------------------------------

  /**
   * link_part_to_equipment — Link a spare part to equipment's BOM
   * @param partId - UUID of the part to link
   * @param quantity - Quantity required (default 1)
   * @param notes - Optional notes about the part relationship
   */
  const linkPartToEquipment = useCallback(
    (partId: string, quantity: number = 1, notes?: string) =>
      execute('link_part_to_equipment', {
        part_id: partId,
        quantity,
        notes,
      }),
    [execute]
  );

  // -------------------------------------------------------------------------
  // SPEC ACTION 6: flag_equipment_attention
  // Set/clear attention flag (engineer+)
  // -------------------------------------------------------------------------

  /**
   * flag_equipment_attention — Set or clear attention flag on equipment
   * @param flagged - true to set flag, false to clear
   * @param reason - Reason for flagging (required when setting)
   */
  const flagEquipmentAttention = useCallback(
    (flagged: boolean, reason?: string) =>
      execute('flag_equipment_attention', {
        flagged,
        reason,
      }),
    [execute]
  );

  // -------------------------------------------------------------------------
  // SPEC ACTION 7: decommission_equipment
  // Terminal state (captain/manager, SIGNED)
  // -------------------------------------------------------------------------

  /**
   * decommission_equipment — Mark equipment as decommissioned (terminal state)
   * Requires signature capture for audit trail.
   *
   * @param reason - Reason for decommissioning
   * @param signature - Signature data (base64, timestamp, signer info)
   */
  const decommissionEquipment = useCallback(
    (reason: string, signature: SignatureData) =>
      execute('decommission_equipment', {
        reason,
        signature,
      }),
    [execute]
  );

  // -------------------------------------------------------------------------
  // Legacy actions (kept for backward compatibility)
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
   * @deprecated Use createWorkOrderForEquipment instead
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

    // SPEC ACTIONS (7 required per equipment_lens_v2_PHASE_4_ACTIONS.md)
    updateEquipmentStatus,      // 1. Change status (engineer+)
    addEquipmentNote,           // 2. Add note (all crew)
    attachFileToEquipment,      // 3. Upload photo/doc (all crew)
    createWorkOrderForEquipment, // 4. Create WO (engineer+)
    linkPartToEquipment,        // 5. Add to BOM (engineer+)
    flagEquipmentAttention,     // 6. Set/clear attention flag (engineer+)
    decommissionEquipment,      // 7. Terminal state (captain/manager, SIGNED)

    // Legacy actions (backward compatibility)
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

/** Engineer+ roles (can update status, create WOs, link parts, flag attention) */
const ENGINEER_PLUS_ROLES = ['engineer', 'chief_engineer', 'eto', 'captain', 'manager'];

/** Roles allowed to decommission equipment (captain/manager only - requires signature) */
const DECOMMISSION_ROLES = ['captain', 'manager'];

/** All crew can add notes and attach files */
const ALL_CREW_ROLES = ['crew', 'deck', 'interior', 'engineer', 'chief_engineer', 'eto', 'chief_officer', 'captain', 'manager'];

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

  // SPEC ACTION PERMISSIONS
  /** Can update equipment status (engineer+) */
  canUpdateStatus: boolean;
  /** Can add notes (all crew) */
  canAddNote: boolean;
  /** Can attach files (all crew) */
  canAttachFile: boolean;
  /** Can create work order for equipment (engineer+) */
  canCreateWorkOrderForEquipment: boolean;
  /** Can link part to equipment BOM (engineer+) */
  canLinkPart: boolean;
  /** Can flag equipment for attention (engineer+) */
  canFlagAttention: boolean;
  /** Can decommission equipment (captain/manager, requires signature) */
  canDecommission: boolean;
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
    // Legacy permissions
    canView: true, // All authenticated users can view equipment
    canUpdate: UPDATE_ROLES.includes(role),
    canLinkDocument: LINK_DOC_ROLES.includes(role),
    canCreateWorkOrder: CREATE_WO_ROLES.includes(role),
    canReportFault: HOD_ROLES.includes(role),
    canLogHours: LOG_HOURS_ROLES.includes(role),

    // SPEC ACTION PERMISSIONS (7 required)
    canUpdateStatus: ENGINEER_PLUS_ROLES.includes(role),      // 1. engineer+
    canAddNote: ALL_CREW_ROLES.includes(role),                // 2. all crew
    canAttachFile: ALL_CREW_ROLES.includes(role),             // 3. all crew
    canCreateWorkOrderForEquipment: ENGINEER_PLUS_ROLES.includes(role), // 4. engineer+
    canLinkPart: ENGINEER_PLUS_ROLES.includes(role),          // 5. engineer+
    canFlagAttention: ENGINEER_PLUS_ROLES.includes(role),     // 6. engineer+
    canDecommission: DECOMMISSION_ROLES.includes(role),       // 7. captain/manager (signed)
  };
}
