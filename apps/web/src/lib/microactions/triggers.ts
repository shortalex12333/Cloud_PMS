/**
 * CelesteOS Trigger Rules
 *
 * Deterministic rules for when each microaction should appear.
 * Based on ACTION_OFFERING_RULES.md specifications.
 */

import type { TriggerRule, TriggerContext } from './types';

// HOD roles that have elevated permissions
const HOD_ROLES = ['chief_engineer', 'eto', 'captain', 'manager'];

/**
 * Check if user has HOD (Head of Department) permissions
 */
function isHOD(role?: string): boolean {
  return role ? HOD_ROLES.includes(role) : false;
}

/**
 * Cluster 1: fix_something - Fault Actions
 * Reference: ACTION_OFFERING_RULES.md lines 55-96
 */
const FAULT_TRIGGERS: TriggerRule[] = [
  {
    action_name: 'diagnose_fault',
    // Always available on fault cards, auto-runs when card mounts
    condition: (ctx) => !!ctx.fault?.id,
    auto_run: true,
  },
  {
    action_name: 'show_manual_section',
    // Always available if equipment is identified
    condition: (ctx) => !!ctx.fault?.id && !!ctx.fault?.equipment_id,
  },
  {
    action_name: 'view_fault_history',
    // Always available on fault cards
    condition: (ctx) => !!ctx.fault?.id,
  },
  {
    action_name: 'suggest_parts',
    // Only if fault is recognized/known by AI
    condition: (ctx) =>
      !!ctx.fault?.id && ctx.fault?.ai_diagnosis?.is_known === true,
  },
  {
    action_name: 'create_work_order_from_fault',
    // Always available unless WO already exists
    condition: (ctx) => !!ctx.fault?.id && !ctx.fault?.has_work_order,
  },
  {
    action_name: 'add_fault_note',
    // Always available on fault cards
    condition: (ctx) => !!ctx.fault?.id,
  },
  {
    action_name: 'add_fault_photo',
    // Always available on fault cards
    condition: (ctx) => !!ctx.fault?.id,
  },
];

/**
 * Cluster 2: do_maintenance - Work Order Actions
 * Reference: ACTION_OFFERING_RULES.md lines 108-178
 */
const WORK_ORDER_TRIGGERS: TriggerRule[] = [
  {
    action_name: 'create_work_order',
    // Available when equipment is identified but no WO exists
    condition: (ctx) => !!ctx.equipment?.id,
  },
  {
    action_name: 'view_work_order_history',
    // Always available on work order cards
    condition: (ctx) => !!ctx.work_order?.id,
  },
  {
    action_name: 'mark_work_order_complete',
    // Only if WO is open or in_progress
    condition: (ctx) =>
      !!ctx.work_order?.id &&
      (ctx.work_order?.status === 'open' ||
        ctx.work_order?.status === 'in_progress'),
  },
  {
    action_name: 'add_work_order_note',
    // Always available on work order cards
    condition: (ctx) => !!ctx.work_order?.id,
  },
  {
    action_name: 'add_work_order_photo',
    // Always available on work order cards
    condition: (ctx) => !!ctx.work_order?.id,
  },
  {
    action_name: 'add_parts_to_work_order',
    // Always available on work order cards
    condition: (ctx) => !!ctx.work_order?.id,
  },
  {
    action_name: 'view_work_order_checklist',
    // Only if WO has a checklist
    condition: (ctx) =>
      !!ctx.work_order?.id && ctx.work_order?.has_checklist === true,
  },
  {
    action_name: 'assign_work_order',
    // HOD only
    condition: (ctx) => !!ctx.work_order?.id && isHOD(ctx.user_role),
  },
  {
    action_name: 'view_checklist',
    // Alias for view_work_order_checklist
    condition: (ctx) =>
      !!ctx.work_order?.id && ctx.work_order?.has_checklist === true,
  },
  {
    action_name: 'mark_checklist_item_complete',
    // Always available on checklist items
    condition: (ctx) => !!ctx.work_order?.id,
  },
  {
    action_name: 'add_checklist_note',
    // Always available
    condition: (ctx) => !!ctx.work_order?.id,
  },
  {
    action_name: 'add_checklist_photo',
    // Always available
    condition: (ctx) => !!ctx.work_order?.id,
  },
  {
    action_name: 'view_worklist',
    // Available in shipyard context or when worklist exists
    condition: (ctx) =>
      ctx.environment === 'shipyard' || !!ctx.work_order?.id,
  },
  {
    action_name: 'add_worklist_task',
    // Available in shipyard context
    condition: (ctx) => ctx.environment === 'shipyard',
  },
  {
    action_name: 'update_worklist_progress',
    // Available when worklist task exists
    condition: (ctx) => ctx.environment === 'shipyard',
  },
  {
    action_name: 'export_worklist',
    // HOD only
    condition: (ctx) => ctx.environment === 'shipyard' && isHOD(ctx.user_role),
  },
];

/**
 * Cluster 3: manage_equipment - Equipment Actions
 * Reference: ACTION_OFFERING_RULES.md lines 184-237
 */
const EQUIPMENT_TRIGGERS: TriggerRule[] = [
  {
    action_name: 'view_equipment_details',
    // Always available on equipment cards
    condition: (ctx) => !!ctx.equipment?.id,
    auto_run: true,
  },
  {
    action_name: 'view_equipment_history',
    // Always available on equipment cards
    condition: (ctx) => !!ctx.equipment?.id,
  },
  {
    action_name: 'view_equipment_parts',
    // Always available on equipment cards
    condition: (ctx) => !!ctx.equipment?.id,
  },
  {
    action_name: 'view_linked_faults',
    // Always available on equipment cards
    condition: (ctx) => !!ctx.equipment?.id,
  },
  {
    action_name: 'view_equipment_manual',
    // Only if manual exists
    condition: (ctx) => !!ctx.equipment?.id && ctx.equipment?.has_manual === true,
  },
  {
    action_name: 'add_equipment_note',
    // Always available
    condition: (ctx) => !!ctx.equipment?.id,
  },
];

/**
 * Cluster 4: control_inventory - Inventory Actions
 * Reference: ACTION_OFFERING_RULES.md lines 241-304
 */
const INVENTORY_TRIGGERS: TriggerRule[] = [
  {
    action_name: 'view_part_stock',
    // Always available on part cards
    condition: (ctx) => !!ctx.part?.id,
    auto_run: true,
  },
  {
    action_name: 'order_part',
    // Only if stock is low or out
    condition: (ctx) =>
      !!ctx.part?.id &&
      (ctx.part?.is_out_of_stock === true ||
        (ctx.part?.stock_level !== undefined &&
          ctx.part?.reorder_threshold !== undefined &&
          ctx.part.stock_level <= ctx.part.reorder_threshold)),
  },
  {
    action_name: 'view_part_location',
    // Always available on part cards
    condition: (ctx) => !!ctx.part?.id,
  },
  {
    action_name: 'view_part_usage',
    // Always available on part cards
    condition: (ctx) => !!ctx.part?.id,
  },
  {
    action_name: 'log_part_usage',
    // Always available on part cards
    condition: (ctx) => !!ctx.part?.id,
  },
  {
    action_name: 'scan_part_barcode',
    // Always available
    condition: () => true,
  },
  {
    action_name: 'view_linked_equipment',
    // Always available on part cards
    condition: (ctx) => !!ctx.part?.id,
  },
];

/**
 * Cluster 5: communicate_status - Handover Actions
 * Reference: ACTION_OFFERING_RULES.md lines 309-360
 */
const HANDOVER_TRIGGERS: TriggerRule[] = [
  {
    action_name: 'add_to_handover',
    // Always available when context exists
    condition: (ctx) =>
      !!ctx.fault?.id ||
      !!ctx.work_order?.id ||
      !!ctx.equipment?.id ||
      !!ctx.part?.id,
  },
  {
    action_name: 'add_document_to_handover',
    // Always available
    condition: () => true,
  },
  {
    action_name: 'add_predictive_insight_to_handover',
    // Only if predictive maintenance is enabled
    condition: (ctx) => ctx.equipment?.predictive_maintenance_enabled === true,
  },
  {
    action_name: 'edit_handover_section',
    // Only if handover exists
    condition: (ctx) => ctx.handover?.exists === true,
  },
  {
    action_name: 'export_handover',
    // Only if handover exists, HOD only
    condition: (ctx) =>
      ctx.handover?.exists === true && isHOD(ctx.user_role),
  },
  {
    action_name: 'regenerate_handover_summary',
    // Only if handover exists
    condition: (ctx) => ctx.handover?.exists === true,
  },
  {
    action_name: 'view_document',
    // Always available
    condition: () => true,
  },
  {
    action_name: 'view_related_documents',
    // Always available when equipment context exists
    condition: (ctx) => !!ctx.equipment?.id,
  },
  {
    action_name: 'view_document_section',
    // Always available
    condition: () => true,
  },
];

/**
 * Cluster 6: comply_audit - Compliance Actions
 * Reference: ACTION_OFFERING_RULES.md lines 366-422
 */
const COMPLIANCE_TRIGGERS: TriggerRule[] = [
  {
    action_name: 'view_hours_of_rest',
    // Always available
    condition: () => true,
  },
  {
    action_name: 'update_hours_of_rest',
    // Always available for own records
    condition: () => true,
  },
  {
    action_name: 'export_hours_of_rest',
    // HOD only
    condition: (ctx) => isHOD(ctx.user_role),
  },
  {
    action_name: 'view_compliance_status',
    // Always available
    condition: () => true,
  },
  {
    action_name: 'tag_for_survey',
    // HOD only
    condition: (ctx) =>
      isHOD(ctx.user_role) &&
      (!!ctx.equipment?.id || !!ctx.fault?.id || !!ctx.work_order?.id),
  },
];

/**
 * Cluster 7: procure_suppliers - Procurement Actions
 * Reference: ACTION_OFFERING_RULES.md lines 478-549
 */
const PROCUREMENT_TRIGGERS: TriggerRule[] = [
  {
    action_name: 'create_purchase_request',
    // Always available when part needs ordering
    condition: (ctx) =>
      !!ctx.part?.id &&
      (ctx.part?.is_out_of_stock === true ||
        (ctx.part?.stock_level !== undefined &&
          ctx.part?.reorder_threshold !== undefined &&
          ctx.part.stock_level <= ctx.part.reorder_threshold)),
  },
  {
    action_name: 'add_item_to_purchase',
    // When purchase is in draft
    condition: (ctx) => ctx.purchase?.status === 'draft',
  },
  {
    action_name: 'approve_purchase',
    // HOD only, when pending approval
    condition: (ctx) =>
      isHOD(ctx.user_role) && ctx.purchase?.status === 'pending_approval',
  },
  {
    action_name: 'upload_invoice',
    // When purchase is received
    condition: (ctx) => ctx.purchase?.status === 'received',
  },
  {
    action_name: 'track_delivery',
    // When purchase is ordered or in transit
    condition: (ctx) =>
      ctx.purchase?.status === 'ordered' ||
      ctx.purchase?.status === 'in_transit',
  },
  {
    action_name: 'log_delivery_received',
    // When purchase is in transit
    condition: (ctx) => ctx.purchase?.status === 'in_transit',
  },
  {
    action_name: 'update_purchase_status',
    // Always available when purchase exists
    condition: (ctx) => !!ctx.purchase?.id,
  },
];

/**
 * All trigger rules combined
 */
export const TRIGGER_RULES: TriggerRule[] = [
  ...FAULT_TRIGGERS,
  ...WORK_ORDER_TRIGGERS,
  ...EQUIPMENT_TRIGGERS,
  ...INVENTORY_TRIGGERS,
  ...HANDOVER_TRIGGERS,
  ...COMPLIANCE_TRIGGERS,
  ...PROCUREMENT_TRIGGERS,
];

/**
 * Get trigger rule for a specific action
 */
export function getTriggerRule(actionName: string): TriggerRule | undefined {
  return TRIGGER_RULES.find((rule) => rule.action_name === actionName);
}

/**
 * Check if an action should be visible given the context
 */
export function shouldShowAction(
  actionName: string,
  context: TriggerContext
): boolean {
  const rule = getTriggerRule(actionName);
  // If no rule exists, default to showing (backward compatibility)
  if (!rule) return true;
  return rule.condition(context);
}

/**
 * Check if an action should auto-run when the card mounts
 */
export function shouldAutoRun(actionName: string): boolean {
  const rule = getTriggerRule(actionName);
  return rule?.auto_run === true;
}

/**
 * Get all visible actions for a given context
 */
export function getVisibleActions(
  actionNames: string[],
  context: TriggerContext
): string[] {
  return actionNames.filter((name) => shouldShowAction(name, context));
}

/**
 * Get auto-run actions from a list
 */
export function getAutoRunActions(actionNames: string[]): string[] {
  return actionNames.filter((name) => shouldAutoRun(name));
}

export default TRIGGER_RULES;
