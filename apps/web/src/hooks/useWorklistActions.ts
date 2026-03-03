'use client';

/**
 * useWorklistActions — Worklist action hook (FE-02-08)
 *
 * Wires worklist action registry calls to typed helper methods.
 * Uses the unified action API endpoint per the action router spec.
 *
 * Action IDs map 1:1 to registry.py keys:
 *   add_worklist_task, export_worklist
 *
 * Role-based access is enforced at the API level; visibility gates live in
 * WorklistLens (hide, not disable).
 */

import { useState, useCallback } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { executeAction } from '@/lib/actionClient';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface WorklistActionResult {
  success: boolean;
  message?: string;
  data?: Record<string, unknown>;
  error?: string;
}

export interface AddTaskParams {
  title: string;
  description?: string;
  priority?: string;
  due_date?: string;
}

export interface WorklistActionsState {
  isLoading: boolean;
  error: string | null;
}

// ---------------------------------------------------------------------------
// Role Configuration - DELEGATED TO CENTRALIZED SERVICE
// ---------------------------------------------------------------------------

// Note: Worklist uses work_order lens permissions in lens_matrix.json.
// Permissions are now derived from the centralized service.

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * useWorklistActions
 *
 * Returns typed action helpers for worklist operations.
 * Each helper calls POST /v1/actions/execute with action name and JWT auth.
 *
 * @param worklistId - UUID of the worklist in scope (optional)
 */
export function useWorklistActions(worklistId?: string) {
  const { user, session } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // Internal executor — wraps every action call
  // -------------------------------------------------------------------------

  const execute = useCallback(
    async (actionName: string, payload: Record<string, unknown>): Promise<WorklistActionResult> => {
      if (!session?.access_token) {
        return { success: false, error: 'Not authenticated' };
      }

      if (!user?.yachtId) {
        return { success: false, error: 'No yacht context available' };
      }

      setIsLoading(true);
      setError(null);

      try {
        const result = await executeAction(
          actionName,
          {
            yacht_id: user.yachtId,
            ...(worklistId && { worklist_id: worklistId }),
          },
          {
            ...(worklistId && { worklist_id: worklistId }),
            ...payload,
          }
        );

        if (result.status === 'error') {
          const msg = result.message || result.error_code || 'Action failed';
          setError(msg);
          return { success: false, error: msg };
        }

        return { success: true, data: result.result, message: result.message };
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Unknown error';
        setError(msg);
        return { success: false, error: msg };
      } finally {
        setIsLoading(false);
      }
    },
    [session, user, worklistId]
  );

  // -------------------------------------------------------------------------
  // Typed action helpers — one per registry action
  // -------------------------------------------------------------------------

  /**
   * add_worklist_task — Add a new task to the worklist
   *
   * Note: Backend expects 'task_description', frontend uses 'title'.
   * Mapping applied here for compatibility (fixed 2026-03-02).
   *
   * @param task - Task details (title, description, priority, due_date)
   */
  const addTask = useCallback(
    (task: AddTaskParams) =>
      execute('add_worklist_task', {
        task_description: task.title, // Backend expects task_description, not title
        description: task.description,
        priority: task.priority,
        due_date: task.due_date,
      }),
    [execute]
  );

  /**
   * export_worklist — Export the worklist to PDF or CSV format
   *
   * @param format - Export format ('pdf' or 'csv'), defaults to 'pdf'
   */
  const exportWorklist = useCallback(
    (format: 'pdf' | 'csv' = 'pdf') => execute('export_worklist', { format }),
    [execute]
  );

  return {
    addTask,
    exportWorklist,
    isLoading,
    error,
  };
}

// ---------------------------------------------------------------------------
// Permissions Hook - DELEGATED TO CENTRALIZED SERVICE
// ---------------------------------------------------------------------------

export interface WorklistPermissions {
  canAddTask: boolean;
  canExport: boolean;
}

import { useWorkOrderPermissions as useCentralizedWorkOrderPermissions } from '@/hooks/permissions/useWorkOrderPermissions';

/**
 * useWorklistPermissions
 *
 * Returns permission flags for worklist actions based on user role.
 * DELEGATED TO CENTRALIZED SERVICE - uses work_order lens from lens_matrix.json
 */
export function useWorklistPermissions(): WorklistPermissions {
  const central = useCentralizedWorkOrderPermissions();

  return {
    canAddTask: central.canAddNoteToWorkOrder, // Worklist tasks are similar to WO notes
    canExport: central.canViewRelatedEntities, // Export requires view access
  };
}
