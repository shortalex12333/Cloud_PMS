'use client';

/**
 * useAvailableActions Hook
 *
 * Phase 12: Refactored to use server-driven decisions via useActionDecisions.
 * UI renders decisions - UI does NOT make decisions (E020).
 *
 * This hook maintains backward compatibility with existing consumers while
 * delegating all visibility decisions to the Decision Engine server.
 */

import { useMemo } from 'react';
import { getActionsForCardType, getAction } from '../registry';
import { hasHandler, canExecuteAction } from '../executor';
import { useActionDecisions, type EntityInput } from './useActionDecisions';
import type {
  MicroAction,
  CardType,
  ActionContext,
  AvailableAction,
  SideEffectType,
  TriggerContext,
} from '../types';

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
  /** Trigger context for conditional visibility (converted to entities for server) */
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
  /** Loading state from decisions endpoint */
  isLoading: boolean;
  /** Error state from decisions endpoint */
  error: string | null;
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

/**
 * Convert TriggerContext to EntityInput[] for the decisions API
 */
function triggerContextToEntities(ctx?: TriggerContext): EntityInput[] {
  if (!ctx) return [];

  const entities: EntityInput[] = [];

  if (ctx.fault?.id) {
    entities.push({
      type: 'fault',
      id: ctx.fault.id,
      status: ctx.fault.status,
      has_work_order: ctx.fault.has_work_order,
      acknowledged: ctx.fault.acknowledged,
    });
  }

  if (ctx.work_order?.id) {
    entities.push({
      type: 'work_order',
      id: ctx.work_order.id,
      status: ctx.work_order.status,
      has_checklist: ctx.work_order.has_checklist,
    });
  }

  if (ctx.equipment?.id) {
    entities.push({
      type: 'equipment',
      id: ctx.equipment.id,
      name: ctx.equipment.name,
      has_manual: ctx.equipment.has_manual,
    });
  }

  if (ctx.part?.id) {
    entities.push({
      type: 'part',
      id: ctx.part.id,
      name: ctx.part.name,
    });
  }

  return entities;
}

/**
 * Map card type to likely intents for decision API
 */
function cardTypeToIntents(cardType: CardType): string[] {
  switch (cardType) {
    case 'fault':
      return ['diagnose', 'view', 'repair'];
    case 'work_order':
      return ['view', 'complete_work', 'update'];
    case 'equipment':
      return ['view', 'maintain'];
    case 'part':
      return ['view', 'order'];
    case 'document':
      return ['view'];
    case 'handover':
      return ['handover', 'view'];
    default:
      return ['view'];
  }
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

  // Phase 12: Get decisions from server
  const entities = useMemo(
    () => triggerContextToEntities(triggerContext),
    [triggerContext]
  );

  const detectedIntents = useMemo(
    () => cardTypeToIntents(cardType),
    [cardType]
  );

  const {
    isAllowed,
    getDecision,
    isLoading,
    error,
  } = useActionDecisions({
    detected_intents: detectedIntents,
    entities,
    skip: entities.length === 0, // Skip if no entity context
  });

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

  // FAIL-CLOSED: If decisions error, return empty arrays
  const failClosed = error !== null;

  const actions = useMemo(() => {
    // Fail closed: return empty if decisions endpoint failed
    if (failClosed) return [];

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

    // Phase 12: Filter by SERVER decisions (replaces shouldShowAction)
    // Only include actions that the server says are allowed
    availableActions = availableActions.filter((action) =>
      isAllowed(action.action_name)
    );

    // Apply limit
    if (limit && limit > 0) {
      availableActions = availableActions.slice(0, limit);
    }

    return availableActions;
  }, [cardType, sideEffectFilter, requireHandler, limit, isAllowed, failClosed]);

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
      const decision = getDecision(action.action_name);

      return {
        action_name: action.action_name,
        label: action.label,
        variant: getActionVariant(action),
        icon: getActionIcon(action),
        is_primary: isPrimary,
        requires_signature: action.requires_confirmation,
        disabled: !canExecute.allowed,
        disabled_reason: canExecute.reason || decision?.blocked_by?.detail,
      };
    });
  }, [actions, context, primaryAction, getDecision]);

  const isActionAvailable = useMemo(
    () => (actionName: string) => {
      if (failClosed) return false;
      return actions.some((a) => a.action_name === actionName);
    },
    [actions, failClosed]
  );

  const getActionByName = useMemo(
    () => (actionName: string) => {
      return actions.find((a) => a.action_name === actionName);
    },
    [actions]
  );

  // Auto-run actions: check server decision for auto_run flag
  // For now, diagnose_fault is the only auto-run action per E017
  const autoRunActions = useMemo(
    () => actions.filter((action) => {
      // diagnose_fault has auto_run_on_card_mount: true in E017
      if (action.action_name === 'diagnose_fault') {
        return isAllowed('diagnose_fault');
      }
      return false;
    }),
    [actions, isAllowed]
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
    isLoading,
    error,
  };
}

export default useAvailableActions;
