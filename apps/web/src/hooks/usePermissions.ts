'use client';

/**
 * usePermissions - Universal Permission Hook
 *
 * Provides role-based permission checks using the centralized PermissionService.
 * Replaces 13 domain-specific hooks with hardcoded role arrays.
 *
 * Usage:
 *   const { can, permittedActions, userRole } = usePermissions('fault');
 *   if (can('update_fault')) { // Show button }
 *
 * This hook automatically reads the user's role from AuthContext
 * and checks permissions against lens_matrix.json (single source of truth).
 */

import { useMemo } from 'react';
import { useAuth } from '@/hooks/useAuth';
import {
  canPerformAction,
  getPermittedActions,
  getActionMetadata,
  requiresSignature,
  requiresConfirmation,
  type Lens,
  type ActionId,
  type ActionPermission,
} from '@/services/permissions';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PermissionResult {
  /**
   * Check if user can perform a specific action
   * @param actionId - The action to check (e.g., 'update_fault')
   * @returns true if the user can perform the action
   */
  can: (actionId: ActionId) => boolean;

  /**
   * All permitted actions for this lens given the user's role
   */
  permittedActions: ActionId[];

  /**
   * User's current role (for display/debugging)
   */
  userRole: string;

  /**
   * Whether auth is still loading
   */
  isLoading: boolean;

  /**
   * Get metadata for an action (required fields, signature requirements, etc.)
   */
  getMetadata: (actionId: ActionId) => ActionPermission | null;

  /**
   * Check if action requires digital signature
   */
  needsSignature: (actionId: ActionId) => boolean;

  /**
   * Check if action requires confirmation dialog
   */
  needsConfirmation: (actionId: ActionId) => boolean;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Universal permission hook - replaces all 13 domain-specific hooks
 *
 * @param lens - The lens context (e.g., 'fault', 'equipment', 'work_order')
 * @returns Permission utilities for the specified lens
 *
 * Example:
 * ```tsx
 * function FaultActions({ faultId }: { faultId: string }) {
 *   const { can, isLoading } = usePermissions('fault');
 *
 *   if (isLoading) return <Spinner />;
 *
 *   return (
 *     <>
 *       {can('update_fault') && <Button>Update</Button>}
 *       {can('close_fault') && <Button>Close</Button>}
 *       {can('add_fault_note') && <Button>Add Note</Button>}
 *     </>
 *   );
 * }
 * ```
 */
export function usePermissions(lens: Lens): PermissionResult {
  const { user } = useAuth();
  const isLoading = !user;
  const userRole = user?.role ?? 'crew'; // Default to most restricted if no user

  // Memoize permitted actions calculation
  const permittedActions = useMemo(() => {
    if (!user) return [];
    return getPermittedActions(userRole, lens);
  }, [userRole, lens, user]);

  // Memoize the can function
  const can = useMemo(() => {
    return (actionId: ActionId): boolean => {
      if (!user) return false;
      return canPerformAction(userRole, actionId, lens);
    };
  }, [userRole, lens, user]);

  // Memoize metadata getter
  const getMetadata = useMemo(() => {
    return (actionId: ActionId): ActionPermission | null => {
      return getActionMetadata(actionId, lens);
    };
  }, [lens]);

  // Memoize signature check
  const needsSignature = useMemo(() => {
    return (actionId: ActionId): boolean => {
      return requiresSignature(actionId, lens);
    };
  }, [lens]);

  // Memoize confirmation check
  const needsConfirmation = useMemo(() => {
    return (actionId: ActionId): boolean => {
      return requiresConfirmation(actionId, lens);
    };
  }, [lens]);

  return {
    can,
    permittedActions,
    userRole,
    isLoading,
    getMetadata,
    needsSignature,
    needsConfirmation,
  };
}

/**
 * Convenience hook for checking multiple lenses at once
 *
 * @param lenses - Array of lens contexts to check
 * @returns Map of lens -> permission result
 *
 * Example:
 * ```tsx
 * const perms = useMultiLensPermissions(['fault', 'work_order', 'equipment']);
 * perms.fault.can('update_fault');
 * perms.work_order.can('close_work_order');
 * ```
 */
export function useMultiLensPermissions<T extends Lens>(lenses: T[]): Record<T, PermissionResult> {
  const { user } = useAuth();
  const isLoading = !user;
  const userRole = user?.role ?? 'crew';

  return useMemo(() => {
    const result = {} as Record<T, PermissionResult>;

    for (const lens of lenses) {
      const permittedActions = user ? getPermittedActions(userRole, lens) : [];

      result[lens] = {
        can: (actionId: ActionId) => user ? canPerformAction(userRole, actionId, lens) : false,
        permittedActions,
        userRole,
        isLoading,
        getMetadata: (actionId: ActionId) => getActionMetadata(actionId, lens),
        needsSignature: (actionId: ActionId) => requiresSignature(actionId, lens),
        needsConfirmation: (actionId: ActionId) => requiresConfirmation(actionId, lens),
      };
    }

    return result;
  }, [lenses, userRole, user, isLoading]);
}
