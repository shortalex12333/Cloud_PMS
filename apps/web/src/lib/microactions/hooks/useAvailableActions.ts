'use client';

/**
 * useAvailableActions Hook
 *
 * React hook for getting available actions based on the current context
 * (card type, entity, user role).
 */

import { useMemo } from 'react';
import { getActionsForCardType, getAction } from '../registry';
import { hasHandler, canExecuteAction } from '../executor';
import type {
  MicroAction,
  CardType,
  ActionContext,
  AvailableAction,
  SideEffectType,
  TriggerContext,
} from '../types';
import { shouldShowAction, shouldAutoRun, getAutoRunActions } from '../triggers';

interface UseAvailableActionsOptions {
  /** Card type to get actions for */
  cardType: CardType;
  /** Optional entity ID */
  entityId?: string;
  /** User's role for permission filtering */
  userRole?: string;
  /** Yacht ID for context */
  yachtId?: string;
  /** User ID for context */
  userId?: string;
  /** Filter by side effect type */
  sideEffectFilter?: SideEffectType[];
  /** Only show actions with registered handlers */
  requireHandler?: boolean;
  /** Maximum number of actions to return */
  limit?: number;
  /** Trigger context for conditional visibility */
  triggerContext?: TriggerContext;
}

interface UseAvailableActionsReturn {
  /** All available actions for the context */
  actions: MicroAction[];
  /** Primary action (first mutation_heavy or most relevant) */
  primaryAction: MicroAction | null;
  /** Read-only actions */
  readActions: MicroAction[];
  /** Mutation actions */
  mutationActions: MicroAction[];
  /** Formatted for UI display */
  formattedActions: AvailableAction[];
  /** Check if a specific action is available */
  isActionAvailable: (actionName: string) => boolean;
  /** Get action by name from available set */
  getActionByName: (actionName: string) => MicroAction | undefined;
  /** Actions that should auto-run when card mounts */
  autoRunActions: MicroAction[];
}

/**
 * Get icon for an action based on its cluster
 */
function getActionIcon(action: MicroAction): string {
  const iconMap: Record<string, string> = {
    // fix_something
    diagnose_fault: 'search',
    show_manual_section: 'book-open',
    view_fault_history: 'history',
    suggest_parts: 'package',
    create_work_order_from_fault: 'plus-circle',
    add_fault_note: 'message-square',
    add_fault_photo: 'camera',

    // do_maintenance
    create_work_order: 'plus',
    view_work_order_history: 'clock',
    mark_work_order_complete: 'check-circle',
    add_work_order_note: 'edit',
    add_work_order_photo: 'image',
    assign_work_order: 'user-plus',

    // manage_equipment
    view_equipment_details: 'settings',
    view_equipment_history: 'activity',
    view_equipment_parts: 'layers',
    view_linked_faults: 'alert-triangle',
    view_equipment_manual: 'file-text',

    // control_inventory
    view_part_stock: 'package',
    order_part: 'shopping-cart',
    view_part_location: 'map-pin',
    log_part_usage: 'minus-circle',

    // communicate_status
    add_to_handover: 'arrow-right',
    export_handover: 'download',
    view_document: 'file',

    // comply_audit
    view_hours_of_rest: 'clock',
    export_hours_of_rest: 'download',
    view_compliance_status: 'shield',

    // procure_suppliers
    create_purchase_request: 'shopping-bag',
    approve_purchase: 'check',
    track_delivery: 'truck',
  };

  return iconMap[action.action_name] || 'circle';
}

/**
 * Determine the variant for an action
 */
function getActionVariant(
  action: MicroAction
): 'READ' | 'MUTATE' | 'NAVIGATE' {
  if (action.side_effect === 'read_only') {
    return 'READ';
  }
  if (action.action_name.startsWith('view_') || action.action_name.startsWith('open_')) {
    return 'NAVIGATE';
  }
  return 'MUTATE';
}

export function useAvailableActions(
  options: UseAvailableActionsOptions
): UseAvailableActionsReturn {
  const {
    cardType,
    entityId,
    userRole,
    yachtId,
    userId,
    sideEffectFilter,
    requireHandler = true,
    limit,
    triggerContext,
  } = options;

  const context: ActionContext = useMemo(
    () => ({
      yacht_id: yachtId || '',
      user_id: userId || '',
      user_role: userRole || '',
      entity_id: entityId,
      source_card: cardType,
    }),
    [yachtId, userId, userRole, entityId, cardType]
  );

  // Merge user role into trigger context if provided
  const effectiveTriggerContext: TriggerContext = useMemo(
    () => ({
      ...triggerContext,
      user_role: triggerContext?.user_role || userRole,
    }),
    [triggerContext, userRole]
  );

  const actions = useMemo(() => {
    let availableActions = getActionsForCardType(cardType);

    // Filter by side effect if specified
    if (sideEffectFilter && sideEffectFilter.length > 0) {
      availableActions = availableActions.filter((action) =>
        sideEffectFilter.includes(action.side_effect)
      );
    }

    // Filter by handler availability if required
    if (requireHandler) {
      availableActions = availableActions.filter((action) =>
        hasHandler(action.action_name)
      );
    }

    // Filter by trigger context (conditional visibility)
    if (triggerContext) {
      availableActions = availableActions.filter((action) =>
        shouldShowAction(action.action_name, effectiveTriggerContext)
      );
    }

    // Apply limit
    if (limit && limit > 0) {
      availableActions = availableActions.slice(0, limit);
    }

    return availableActions;
  }, [cardType, sideEffectFilter, requireHandler, limit, triggerContext, effectiveTriggerContext]);

  const primaryAction = useMemo(() => {
    // Prefer mutation_heavy actions as primary
    const heavy = actions.find((a) => a.side_effect === 'mutation_heavy');
    if (heavy) return heavy;

    // Then mutation_light
    const light = actions.find((a) => a.side_effect === 'mutation_light');
    if (light) return light;

    // Then first read_only
    return actions[0] || null;
  }, [actions]);

  const readActions = useMemo(
    () => actions.filter((a) => a.side_effect === 'read_only'),
    [actions]
  );

  const mutationActions = useMemo(
    () => actions.filter((a) => a.side_effect !== 'read_only'),
    [actions]
  );

  const formattedActions = useMemo((): AvailableAction[] => {
    return actions.map((action) => {
      const canExecute = canExecuteAction(action.action_name, context);
      const isPrimary = primaryAction?.action_name === action.action_name;

      return {
        action_name: action.action_name,
        label: action.label,
        variant: getActionVariant(action),
        icon: getActionIcon(action),
        is_primary: isPrimary,
        requires_signature: action.requires_confirmation,
        disabled: !canExecute.allowed,
        disabled_reason: canExecute.reason,
      };
    });
  }, [actions, context, primaryAction]);

  const isActionAvailable = useMemo(
    () => (actionName: string) => {
      return actions.some((a) => a.action_name === actionName);
    },
    [actions]
  );

  const getActionByName = useMemo(
    () => (actionName: string) => {
      return actions.find((a) => a.action_name === actionName);
    },
    [actions]
  );

  // Actions that should auto-run when card mounts
  const autoRunActions = useMemo(
    () => actions.filter((action) => shouldAutoRun(action.action_name)),
    [actions]
  );

  return {
    actions,
    primaryAction,
    readActions,
    mutationActions,
    formattedActions,
    isActionAvailable,
    getActionByName,
    autoRunActions,
  };
}

export default useAvailableActions;
