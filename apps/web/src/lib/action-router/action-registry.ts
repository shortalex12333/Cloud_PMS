/**
 * Action Router - Action Registry
 *
 * Single source of truth for all available actions in the system.
 * Maps action IDs to their definitions, endpoints, and permissions.
 */

import type { ActionDefinition, HandlerType } from './types';

// ============================================================================
// ACTION REGISTRY
// ============================================================================

export const ACTION_REGISTRY: Record<string, ActionDefinition> = {
  // ==========================================================================
  // NOTES ACTIONS
  // ==========================================================================
  add_note: {
    actionId: 'add_note',
    label: 'Add Note',
    endpoint: '/v1/notes/create',
    handlerType: 'internal',
    method: 'POST',
    allowedRoles: ['ETO', 'Engineer', 'HOD', 'Manager'],
    requiredFields: ['yacht_id', 'equipment_id', 'note_text'],
    schemaFile: 'add_note.json',
  },

  add_note_to_work_order: {
    actionId: 'add_note_to_work_order',
    label: 'Add Note to Work Order',
    endpoint: '/v1/work-orders/add-note',
    handlerType: 'internal',
    method: 'POST',
    allowedRoles: ['Engineer', 'HOD', 'Manager'],
    requiredFields: ['yacht_id', 'work_order_id', 'note_text'],
    schemaFile: 'add_note_to_work_order.json',
  },

  // ==========================================================================
  // WORK ORDER ACTIONS
  // ==========================================================================
  create_work_order: {
    actionId: 'create_work_order',
    label: 'Create Work Order',
    endpoint: '/v1/work-orders/create',
    handlerType: 'n8n',
    method: 'POST',
    allowedRoles: ['Engineer', 'HOD', 'Manager'],
    requiredFields: ['yacht_id', 'equipment_id', 'title', 'priority'],
    schemaFile: 'create_work_order.json',
  },

  create_work_order_fault: {
    actionId: 'create_work_order_fault',
    label: 'Create Work Order for Fault',
    endpoint: '/v1/work-orders/create',
    handlerType: 'n8n',
    method: 'POST',
    allowedRoles: ['Engineer', 'HOD', 'Manager'],
    requiredFields: ['yacht_id', 'equipment_id', 'fault_id', 'description'],
    schemaFile: 'create_work_order_fault.json',
  },

  close_work_order: {
    actionId: 'close_work_order',
    label: 'Close Work Order',
    endpoint: '/v1/work-orders/close',
    handlerType: 'internal',
    method: 'POST',
    allowedRoles: ['HOD', 'Manager'],
    requiredFields: ['yacht_id', 'work_order_id'],
    schemaFile: 'close_work_order.json',
  },

  // ==========================================================================
  // HANDOVER ACTIONS
  // ==========================================================================
  add_to_handover: {
    actionId: 'add_to_handover',
    label: 'Add to Handover',
    endpoint: '/v1/handover/add-item',
    handlerType: 'n8n',
    method: 'POST',
    allowedRoles: ['ETO', 'Engineer', 'HOD', 'Manager'],
    requiredFields: ['yacht_id', 'equipment_id', 'summary_text'],
    schemaFile: 'add_to_handover.json',
  },

  add_document_to_handover: {
    actionId: 'add_document_to_handover',
    label: 'Add Document to Handover',
    endpoint: '/v1/handover/add-document',
    handlerType: 'n8n',
    method: 'POST',
    allowedRoles: ['Engineer', 'HOD', 'Manager'],
    requiredFields: ['yacht_id', 'document_id'],
    schemaFile: 'add_document_to_handover.json',
  },

  add_part_to_handover: {
    actionId: 'add_part_to_handover',
    label: 'Add Part to Handover',
    endpoint: '/v1/handover/add-part',
    handlerType: 'n8n',
    method: 'POST',
    allowedRoles: ['Engineer', 'HOD', 'Manager'],
    requiredFields: ['yacht_id', 'part_id', 'reason'],
    schemaFile: 'add_part_to_handover.json',
  },

  add_predictive_to_handover: {
    actionId: 'add_predictive_to_handover',
    label: 'Add Predictive Insight to Handover',
    endpoint: '/v1/handover/add-predictive',
    handlerType: 'n8n',
    method: 'POST',
    allowedRoles: ['Engineer', 'HOD', 'Manager'],
    requiredFields: ['yacht_id', 'equipment_id', 'insight_id', 'summary'],
    schemaFile: 'add_predictive_to_handover.json',
  },

  edit_handover_section: {
    actionId: 'edit_handover_section',
    label: 'Edit Handover Section',
    endpoint: '/v1/handover/edit-section',
    handlerType: 'internal',
    method: 'POST',
    allowedRoles: ['HOD', 'Manager'],
    requiredFields: ['yacht_id', 'handover_id', 'section_name', 'new_text'],
    schemaFile: 'edit_handover_section.json',
  },

  export_handover: {
    actionId: 'export_handover',
    label: 'Export Handover',
    endpoint: '/v1/handover/export',
    handlerType: 'n8n',
    method: 'POST',
    allowedRoles: ['HOD', 'Manager'],
    requiredFields: ['yacht_id'],
    schemaFile: 'export_handover.json',
  },

  // ==========================================================================
  // DOCUMENT ACTIONS
  // ==========================================================================
  open_document: {
    actionId: 'open_document',
    label: 'Open Document',
    endpoint: '/v1/documents/open',
    handlerType: 'internal',
    method: 'POST',
    allowedRoles: ['Crew', 'ETO', 'Engineer', 'HOD', 'Manager'],
    requiredFields: ['storage_path'],
    schemaFile: 'open_document.json',
  },

  // ==========================================================================
  // INVENTORY ACTIONS
  // ==========================================================================
  order_part: {
    actionId: 'order_part',
    label: 'Order Part',
    endpoint: '/v1/inventory/order-part',
    handlerType: 'n8n',
    method: 'POST',
    allowedRoles: ['Engineer', 'HOD', 'Manager'],
    requiredFields: ['yacht_id', 'part_id', 'qty'],
    schemaFile: 'order_part.json',
  },
};

// ============================================================================
// REGISTRY FUNCTIONS
// ============================================================================

/**
 * Get action definition by ID
 *
 * @param actionId - Action ID to lookup
 * @returns ActionDefinition
 * @throws Error if action not found
 */
export function getAction(actionId: string): ActionDefinition {
  const action = ACTION_REGISTRY[actionId];
  if (!action) {
    throw new Error(`Action '${actionId}' not found in registry`);
  }
  return action;
}

/**
 * Check if action exists in registry
 *
 * @param actionId - Action ID to check
 * @returns true if action exists
 */
export function actionExists(actionId: string): boolean {
  return actionId in ACTION_REGISTRY;
}

/**
 * Get all registered actions
 *
 * @returns Copy of action registry
 */
export function listActions(): Record<string, ActionDefinition> {
  return { ...ACTION_REGISTRY };
}

/**
 * Get all actions available for a specific role
 *
 * @param role - User role to filter by
 * @returns Filtered action registry
 */
export function getActionsForRole(role: string): Record<string, ActionDefinition> {
  const result: Record<string, ActionDefinition> = {};
  for (const [actionId, action] of Object.entries(ACTION_REGISTRY)) {
    if (action.allowedRoles.includes(role)) {
      result[actionId] = action;
    }
  }
  return result;
}

/**
 * Get actions by handler type
 *
 * @param handlerType - Handler type to filter by
 * @returns Filtered action registry
 */
export function getActionsByHandler(
  handlerType: HandlerType
): Record<string, ActionDefinition> {
  const result: Record<string, ActionDefinition> = {};
  for (const [actionId, action] of Object.entries(ACTION_REGISTRY)) {
    if (action.handlerType === handlerType) {
      result[actionId] = action;
    }
  }
  return result;
}

/**
 * Get count of registered actions
 *
 * @returns Number of actions in registry
 */
export function getActionCount(): number {
  return Object.keys(ACTION_REGISTRY).length;
}
