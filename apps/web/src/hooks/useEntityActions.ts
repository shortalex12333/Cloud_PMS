'use client';

/**
 * useEntityActions — Generic action hook factory
 *
 * One hook to rule them all. Every domain-specific action hook
 * (useReceivingActions, useHoursOfRestActions, useHandoverActions, etc.)
 * follows the exact same pattern:
 *
 *   1. Get auth context (user, yacht_id)
 *   2. Call executeAction(actionName, context, payload)
 *   3. Fire onSuccess/onError callbacks
 *   4. Return permission booleans
 *
 * Instead of writing N × 150-line files that are 90% identical,
 * this factory takes a declarative config and returns typed methods.
 *
 * Usage:
 *   const actions = useEntityActions('receiving', receivingId, {
 *     actions: {
 *       addItem:    'add_receiving_item',
 *       accept:     'accept_receiving',
 *       reject:     'reject_receiving',
 *     },
 *     permissions: {
 *       canAccept: (role) => HOD_ROLES.includes(role),
 *       canReject: (role) => HOD_ROLES.includes(role),
 *     },
 *     onSuccess: () => refetch(),
 *   });
 *
 *   // Typed: actions.addItem({ part_id: '...', quantity: 1 })
 *   // Typed: actions.canAccept → boolean
 */

import { useCallback, useMemo } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { executeAction, type ActionResult } from '@/lib/actionClient';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Role predicate — receives current user role, returns boolean */
type RoleCheck = (role: string) => boolean;

/** Hook configuration */
export interface EntityActionsConfig {
  /** Map of method names → action IDs */
  actions: Record<string, string>;
  /** Map of permission names → role predicates */
  permissions?: Record<string, RoleCheck>;
  /** Extra context keys beyond yacht_id + entity_id (e.g., { user_id: ... }) */
  extraContext?: Record<string, string>;
  /** Called after any successful action */
  onSuccess?: () => void;
  /** Called after any failed action */
  onError?: (error: Error) => void;
}

/** Return type: action methods + permission booleans + execute */
export type EntityActionsReturn<T extends EntityActionsConfig> = {
  /** Direct executor for ad-hoc actions not in the config */
  execute: (actionName: string, payload?: Record<string, unknown>) => Promise<ActionResult>;
} & {
  [K in keyof T['actions']]: (payload?: Record<string, unknown>) => Promise<ActionResult>;
} & {
  [K in keyof T['permissions']]: boolean;
};

// ---------------------------------------------------------------------------
// Common role sets (reusable across configs)
// ---------------------------------------------------------------------------

const HOD_ROLES = ['chief_engineer', 'eto', 'chief_officer', 'captain', 'manager'];
const OFFICER_ROLES = ['chief_engineer', 'chief_officer', 'captain', 'manager'];
const ENGINEER_ROLES = ['chief_engineer', 'eto', 'engineer', 'manager'];
const CAPTAIN_ROLES = ['captain', 'manager'];

export const Roles = {
  isHOD:      (role: string) => HOD_ROLES.includes(role),
  isOfficer:  (role: string) => OFFICER_ROLES.includes(role),
  isEngineer: (role: string) => ENGINEER_ROLES.includes(role),
  isCaptain:  (role: string) => CAPTAIN_ROLES.includes(role),
  isAnyCrew:  () => true,
} as const;

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * useEntityActions
 *
 * @param entityType - e.g. 'receiving', 'hours_of_rest' (used for context key: `${entityType}_id`)
 * @param entityId - UUID of the entity in scope
 * @param config - actions, permissions, callbacks
 */
export function useEntityActions<T extends EntityActionsConfig>(
  entityType: string,
  entityId: string,
  config: T
): EntityActionsReturn<T> {
  const { user } = useAuth();
  const role = user?.role ?? '';
  const yachtId = user?.yachtId;

  // Build context once
  const context = useMemo(() => ({
    yacht_id: yachtId ?? '',
    [`${entityType}_id`]: entityId,
    ...(config.extraContext ?? {}),
  }), [yachtId, entityType, entityId, config.extraContext]);

  // Core executor
  const execute = useCallback(
    async (actionName: string, payload: Record<string, unknown> = {}): Promise<ActionResult> => {
      if (!yachtId) {
        const err = new Error('No yacht context available');
        config.onError?.(err);
        throw err;
      }
      try {
        const result = await executeAction(actionName, context, payload);
        config.onSuccess?.();
        return result;
      } catch (error) {
        config.onError?.(error as Error);
        throw error;
      }
    },
    [yachtId, context, config]
  );

  // Build action methods dynamically
  const actionMethods = useMemo(() => {
    const methods: Record<string, (payload?: Record<string, unknown>) => Promise<ActionResult>> = {};
    for (const [methodName, actionId] of Object.entries(config.actions)) {
      methods[methodName] = (payload?: Record<string, unknown>) => execute(actionId, payload ?? {});
    }
    return methods;
  }, [config.actions, execute]);

  // Evaluate permissions
  const permissions = useMemo(() => {
    const perms: Record<string, boolean> = {};
    if (config.permissions) {
      for (const [permName, check] of Object.entries(config.permissions)) {
        perms[permName] = check(role);
      }
    }
    return perms;
  }, [config.permissions, role]);

  return { execute, ...actionMethods, ...permissions } as EntityActionsReturn<T>;
}

// ---------------------------------------------------------------------------
// Pre-built configs for each domain
// ---------------------------------------------------------------------------

export const RECEIVING_ACTIONS = {
  actions: {
    addItem:          'add_receiving_item',
    acceptReceiving:  'accept_receiving',
    rejectReceiving:  'reject_receiving',
    adjustItem:       'adjust_receiving_item',
    linkInvoice:      'link_invoice_document',
  },
  permissions: {
    canAccept:  Roles.isHOD,
    canReject:  Roles.isHOD,
    canAddItem: Roles.isAnyCrew,
  },
} as const;

export const HOURS_OF_REST_ACTIONS = {
  actions: {
    upsertRecord:   'upsert_hours_of_rest',
    createSignoff:  'create_monthly_signoff',
  },
  permissions: {
    canVerify: Roles.isHOD,
    canEdit:   Roles.isAnyCrew,
  },
} as const;

export const HANDOVER_ACTIONS = {
  actions: {
    addToHandover: 'add_to_handover',
    editSection:   'edit_handover_section',
    exportHandover: 'export_handover',
  },
  permissions: {
    canExport: Roles.isOfficer,
  },
} as const;

export const CERTIFICATE_ACTIONS = {
  actions: {
    renewCertificate:   'update_certificate',
    linkDocument:       'link_document_to_certificate',
  },
  permissions: {
    canRenew: Roles.isHOD,
  },
} as const;

export const PARTS_ACTIONS = {
  actions: {
    logUsage:    'consume_part',
    countStock:  'adjust_stock_quantity',
  },
  permissions: {
    canLogUsage:   Roles.isEngineer,
    canCountStock: Roles.isHOD,
  },
} as const;

export const WARRANTY_ACTIONS = {
  actions: {
    fileClaim: 'report_fault',
  },
  permissions: {
    canFileClaim: Roles.isHOD,
  },
} as const;
