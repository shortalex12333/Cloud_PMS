/**
 * CelesteOS Workflow Archetype Mapping
 *
 * Maps all 67 micro-actions to 6 master workflow archetypes
 * This eliminates the need for 67 separate n8n workflows
 *
 * Architecture: 6 master workflows with switch nodes
 *
 * Version: 1.0
 * Date: 2025-11-21
 */

import { MicroAction } from './actions';

// ============================================================================
// WORKFLOW ARCHETYPE TYPES
// ============================================================================

export type WorkflowArchetype =
  | 'VIEW'      // Read-only actions (query DB → return card)
  | 'UPDATE'    // Mutation actions (update DB → return updated card)
  | 'CREATE'    // Creation actions (insert DB → return new card)
  | 'EXPORT'    // Export/generate files (collect data → generate PDF/CSV)
  | 'RAG'       // AI/semantic search (embed → vector search → LLM → card)
  | 'LINKING';  // Relational linking (insert link table → return updated card)

// ============================================================================
// ARCHETYPE CATEGORIZATION
// ============================================================================

/**
 * VIEW WORKFLOW ACTIONS (25 actions)
 * All read-only micro-actions that query and display data
 * Endpoint: /workflows/view
 */
export const VIEW_ACTIONS: MicroAction[] = [
  // Equipment
  'view_equipment_details',
  'view_equipment_history',
  'view_equipment_parts',
  'view_equipment_manual',
  'view_linked_faults',
  'view_linked_equipment',

  // Work Orders
  'view_work_order_history',
  'view_work_order_checklist',

  // Parts/Inventory
  'view_part_stock',
  'view_part_location',
  'view_part_usage',

  // Faults
  'view_fault_history',

  // Documents
  'view_document',
  'view_document_section',
  'view_related_documents',
  'show_manual_section',

  // Hours of Rest
  'view_hours_of_rest',
  'view_compliance_status',

  // Checklists
  'view_checklist',

  // Shipyard
  'view_worklist',

  // Fleet
  'view_fleet_summary',
  'open_vessel',

  // Predictive
  'view_smart_summary',
];

/**
 * UPDATE WORKFLOW ACTIONS (18 actions)
 * All mutation actions that update existing records
 * Endpoint: /workflows/update
 */
export const UPDATE_ACTIONS: MicroAction[] = [
  // Work Orders
  'mark_work_order_complete',
  'assign_work_order',
  'approve_work_order',

  // Hours of Rest
  'update_hours_of_rest',

  // Purchasing
  'approve_purchase',
  'track_delivery',
  'log_delivery_received',
  'update_purchase_status',

  // Checklists
  'mark_checklist_item_complete',

  // Shipyard
  'update_worklist_progress',
  'tag_for_survey',

  // Parts
  'log_part_usage',

  // EDIT ACTIONS (Audit-sensitive mutations)
  'edit_work_order_details',
  'edit_equipment_details',
  'edit_part_details',
  'edit_purchase_details',
  'edit_invoice_amount',
  'edit_fault_details',
  'edit_note',
];

/**
 * CREATE WORKFLOW ACTIONS (14 actions)
 * All creation actions that insert new records
 * Endpoint: /workflows/create
 */
export const CREATE_ACTIONS: MicroAction[] = [
  // Work Orders
  'create_work_order',
  'create_work_order_from_fault',

  // Purchasing
  'create_purchase_request',
  'add_item_to_purchase',

  // Shipyard
  'add_worklist_task',

  // Notes (creation-style actions)
  'add_fault_note',
  'add_work_order_note',
  'add_equipment_note',
  'add_checklist_note',

  // Parts
  'add_parts_to_work_order',
  'order_part',

  // Media uploads
  'upload_photo',
  'upload_invoice',

  // Scanning
  'scan_part_barcode',
  'scan_equipment_barcode',
];

/**
 * EXPORT WORKFLOW ACTIONS (6 actions)
 * All actions that generate files/PDFs/summaries
 * Endpoint: /workflows/export
 */
export const EXPORT_ACTIONS: MicroAction[] = [
  'export_handover',
  'export_hours_of_rest',
  'export_worklist',
  'export_fleet_summary',
  'regenerate_handover_summary',
  'record_voice_note', // Transcription export
];

/**
 * RAG WORKFLOW ACTIONS (4 actions)
 * All AI-powered actions requiring semantic search/LLM
 * Endpoint: /workflows/rag
 */
export const RAG_ACTIONS: MicroAction[] = [
  'diagnose_fault',                    // LLM diagnosis based on manual + history
  'suggest_parts',                     // RAG to find parts from manual/history
  'request_predictive_insight',        // AI prediction based on data
  'add_predictive_insight_to_handover', // LLM-generated insights
];

/**
 * LINKING WORKFLOW ACTIONS (6 actions)
 * All actions that create relationships between entities
 * Endpoint: /workflows/linking
 */
export const LINKING_ACTIONS: MicroAction[] = [
  'add_to_handover',
  'add_document_to_handover',
  'add_fault_photo',
  'add_work_order_photo',
  'add_checklist_photo',
  'edit_handover_section', // Modifies link metadata
];

/**
 * DELETE WORKFLOW ACTION (1 action)
 * Soft delete (update deleted_at timestamp)
 * Could be merged into UPDATE, but kept separate for clarity
 */
export const DELETE_ACTIONS: MicroAction[] = [
  'delete_item', // Generic soft delete
];

// ============================================================================
// ARCHETYPE MAPPING REGISTRY
// ============================================================================

/**
 * Master mapping: action_name → workflow archetype
 * Used by action handler to route to correct n8n endpoint
 */
export const ACTION_TO_ARCHETYPE_MAP: Record<MicroAction, WorkflowArchetype> = {
  // VIEW (25)
  view_equipment_details: 'VIEW',
  view_equipment_history: 'VIEW',
  view_equipment_parts: 'VIEW',
  view_equipment_manual: 'VIEW',
  view_linked_faults: 'VIEW',
  view_linked_equipment: 'VIEW',
  view_work_order_history: 'VIEW',
  view_work_order_checklist: 'VIEW',
  view_part_stock: 'VIEW',
  view_part_location: 'VIEW',
  view_part_usage: 'VIEW',
  view_fault_history: 'VIEW',
  view_document: 'VIEW',
  view_document_section: 'VIEW',
  view_related_documents: 'VIEW',
  show_manual_section: 'VIEW',
  view_hours_of_rest: 'VIEW',
  view_compliance_status: 'VIEW',
  view_checklist: 'VIEW',
  view_worklist: 'VIEW',
  view_fleet_summary: 'VIEW',
  open_vessel: 'VIEW',
  view_smart_summary: 'VIEW',
  view_fault_detail: 'VIEW',

  // UPDATE (24)
  mark_work_order_complete: 'UPDATE',
  complete_work_order: 'UPDATE',
  edit_part_quantity: 'UPDATE',
  assign_work_order: 'UPDATE',
  approve_work_order: 'UPDATE',
  update_hours_of_rest: 'UPDATE',
  approve_purchase: 'UPDATE',
  track_delivery: 'UPDATE',
  log_delivery_received: 'UPDATE',
  update_purchase_status: 'UPDATE',
  mark_checklist_item_complete: 'UPDATE',
  update_worklist_progress: 'UPDATE',
  tag_for_survey: 'UPDATE',
  log_part_usage: 'UPDATE',
  edit_work_order_details: 'UPDATE',
  edit_equipment_details: 'UPDATE',
  edit_part_details: 'UPDATE',
  edit_purchase_details: 'UPDATE',
  edit_invoice_amount: 'UPDATE',
  edit_fault_details: 'UPDATE',
  edit_note: 'UPDATE',
  acknowledge_fault: 'UPDATE',
  update_fault: 'UPDATE',

  // CREATE (16)
  create_work_order: 'CREATE',
  create_work_order_from_fault: 'CREATE',
  report_fault: 'CREATE',
  add_part: 'CREATE',
  create_purchase_request: 'CREATE',
  add_item_to_purchase: 'CREATE',
  add_worklist_task: 'CREATE',
  add_fault_note: 'CREATE',
  add_work_order_note: 'CREATE',
  add_equipment_note: 'CREATE',
  add_checklist_note: 'CREATE',
  add_parts_to_work_order: 'CREATE',
  order_part: 'CREATE',
  upload_photo: 'CREATE',
  upload_invoice: 'CREATE',
  scan_part_barcode: 'CREATE',
  scan_equipment_barcode: 'CREATE',

  // EXPORT (6)
  export_handover: 'EXPORT',
  export_hours_of_rest: 'EXPORT',
  export_worklist: 'EXPORT',
  export_fleet_summary: 'EXPORT',
  regenerate_handover_summary: 'EXPORT',
  record_voice_note: 'EXPORT',

  // RAG (4)
  diagnose_fault: 'RAG',
  suggest_parts: 'RAG',
  request_predictive_insight: 'RAG',
  add_predictive_insight_to_handover: 'RAG',

  // LINKING (8)
  add_to_handover: 'LINKING',
  add_document_to_handover: 'LINKING',
  add_fault_photo: 'LINKING',
  add_work_order_photo: 'LINKING',
  add_checklist_photo: 'LINKING',
  edit_handover_section: 'LINKING',
  link_equipment_to_fault: 'LINKING',
  link_parts_to_work_order: 'LINKING',

  // DELETE (1) - Treated as UPDATE in practice
  delete_item: 'UPDATE',
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Get the workflow archetype for a given action
 */
export function getWorkflowArchetype(action: MicroAction): WorkflowArchetype {
  return ACTION_TO_ARCHETYPE_MAP[action];
}

/**
 * Get the n8n endpoint for a given action
 */
export function getWorkflowEndpoint(action: MicroAction): string {
  const archetype = getWorkflowArchetype(action);
  return `/workflows/${archetype.toLowerCase()}`;
}

/**
 * Get all actions for a specific archetype
 */
export function getActionsByArchetype(archetype: WorkflowArchetype): MicroAction[] {
  return Object.entries(ACTION_TO_ARCHETYPE_MAP)
    .filter(([_, archetypeValue]) => archetypeValue === archetype)
    .map(([action]) => action as MicroAction);
}

/**
 * Check if an action belongs to a specific archetype
 */
export function isActionOfType(action: MicroAction, archetype: WorkflowArchetype): boolean {
  return getWorkflowArchetype(action) === archetype;
}

// ============================================================================
// ARCHETYPE STATISTICS
// ============================================================================

export const ARCHETYPE_STATS = {
  VIEW: VIEW_ACTIONS.length,      // 23
  UPDATE: UPDATE_ACTIONS.length,  // 18
  CREATE: CREATE_ACTIONS.length,  // 14
  EXPORT: EXPORT_ACTIONS.length,  // 6
  RAG: RAG_ACTIONS.length,        // 4
  LINKING: LINKING_ACTIONS.length, // 6
  DELETE: DELETE_ACTIONS.length,  // 1
  TOTAL: 67,
};

// Validation: Ensure all 67 actions are accounted for
const totalMapped = Object.keys(ACTION_TO_ARCHETYPE_MAP).length;
if (totalMapped !== 67) {
  console.warn(`⚠️ Action count mismatch: ${totalMapped}/67 actions mapped`);
}
