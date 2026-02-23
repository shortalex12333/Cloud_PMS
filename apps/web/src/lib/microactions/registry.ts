/**
 * CelesteOS Microaction Registry
 *
 * Complete registry of all 57 microactions organized by purpose cluster.
 * This is the canonical source of truth for action definitions.
 */

import type { MicroAction, CardType } from './types';

// ============================================================================
// CLUSTER 1: FIX_SOMETHING (7 actions)
// Diagnose and resolve faults, breakdowns, alarms
// ============================================================================

const FIX_SOMETHING_ACTIONS: Record<string, MicroAction> = {
  diagnose_fault: {
    action_name: 'diagnose_fault',
    label: 'Diagnose Fault',
    cluster: 'fix_something',
    card_types: ['fault'],
    side_effect: 'read_only',
    description: 'Analyze fault code and provide diagnostic guidance',
    handler: 'fault_handlers.diagnose_fault',
    requires_confirmation: false,
  },
  view_fault: {
    action_name: 'view_fault',
    label: 'View Fault Details',
    cluster: 'fix_something',
    card_types: ['fault', 'equipment'],
    side_effect: 'read_only',
    description: 'View detailed fault information',
    handler: 'fault_handlers.view_fault',
    requires_confirmation: false,
  },
  show_manual_section: {
    action_name: 'show_manual_section',
    label: 'View Manual',
    cluster: 'fix_something',
    card_types: ['fault', 'equipment', 'work_order'],
    side_effect: 'read_only',
    description: 'Open relevant manual section for current context',
    handler: 'manual_handlers.show_manual_section',
    requires_confirmation: false,
  },
  view_fault_history: {
    action_name: 'view_fault_history',
    label: 'View History',
    cluster: 'fix_something',
    card_types: ['fault', 'equipment'],
    side_effect: 'read_only',
    description: 'Show historical occurrences of similar faults',
    handler: 'fault_handlers.view_fault_history',
    requires_confirmation: false,
  },
  suggest_parts: {
    action_name: 'suggest_parts',
    label: 'Suggest Parts',
    cluster: 'fix_something',
    card_types: ['fault'],
    side_effect: 'read_only',
    description: 'Recommend likely parts needed for this fault',
    handler: 'fault_handlers.suggest_parts',
    requires_confirmation: false,
  },
  create_work_order_from_fault: {
    action_name: 'create_work_order_from_fault',
    label: 'Create Work Order',
    cluster: 'fix_something',
    card_types: ['fault'],
    side_effect: 'mutation_heavy',
    description: 'Generate work order pre-filled from fault context',
    handler: 'fault_handlers.create_work_order_from_fault',
    requires_confirmation: true,
  },
  add_fault_note: {
    action_name: 'add_fault_note',
    label: 'Add Note',
    cluster: 'fix_something',
    card_types: ['fault'],
    side_effect: 'mutation_light',
    description: 'Attach observation or comment to fault record',
    handler: 'fault_handlers.add_fault_note',
    requires_confirmation: false,
  },
  add_fault_photo: {
    action_name: 'add_fault_photo',
    label: 'Add Photo',
    cluster: 'fix_something',
    card_types: ['fault'],
    side_effect: 'mutation_light',
    description: 'Upload photo evidence of fault condition',
    handler: 'fault_handlers.add_fault_photo',
    requires_confirmation: false,
  },
};

// ============================================================================
// CLUSTER 2: DO_MAINTENANCE (16 actions)
// Execute planned maintenance and PMS tasks
// ============================================================================

const DO_MAINTENANCE_ACTIONS: Record<string, MicroAction> = {
  create_work_order: {
    action_name: 'create_work_order',
    label: 'Create Work Order',
    cluster: 'do_maintenance',
    card_types: ['smart_summary', 'equipment'],
    side_effect: 'mutation_heavy',
    description: 'Create new work order with manual equipment selection',
    handler: 'work_order_handlers.create_work_order',
    requires_confirmation: true,
  },
  view_work_order_history: {
    action_name: 'view_work_order_history',
    label: 'View History',
    cluster: 'do_maintenance',
    card_types: ['work_order', 'equipment'],
    side_effect: 'read_only',
    description: 'Show completion history for this work order type',
    handler: 'work_order_handlers.view_work_order_history',
    requires_confirmation: false,
  },
  view_work_order: {
    action_name: 'view_work_order',
    label: 'View Work Order',
    cluster: 'do_maintenance',
    card_types: ['work_order', 'smart_summary'],
    side_effect: 'read_only',
    description: 'View work order details',
    handler: 'work_order_handlers.view_work_order',
    requires_confirmation: false,
  },
  mark_work_order_complete: {
    action_name: 'mark_work_order_complete',
    label: 'Mark Done',
    cluster: 'do_maintenance',
    card_types: ['work_order'],
    side_effect: 'mutation_heavy',
    description: 'Close work order and log completion',
    handler: 'work_order_handlers.mark_work_order_complete',
    requires_confirmation: true,
  },
  add_work_order_note: {
    action_name: 'add_work_order_note',
    label: 'Add Note',
    cluster: 'do_maintenance',
    card_types: ['work_order'],
    side_effect: 'mutation_light',
    description: 'Add progress note or findings to work order',
    handler: 'work_order_handlers.add_work_order_note',
    requires_confirmation: false,
  },
  add_work_order_photo: {
    action_name: 'add_work_order_photo',
    label: 'Add Photo',
    cluster: 'do_maintenance',
    card_types: ['work_order'],
    side_effect: 'mutation_light',
    description: 'Attach photo to work order (before/after, evidence)',
    handler: 'work_order_handlers.add_work_order_photo',
    requires_confirmation: false,
  },
  add_parts_to_work_order: {
    action_name: 'add_parts_to_work_order',
    label: 'Add Parts',
    cluster: 'do_maintenance',
    card_types: ['work_order'],
    side_effect: 'mutation_light',
    description: 'Link consumed parts to this work order',
    handler: 'work_order_handlers.add_parts_to_work_order',
    requires_confirmation: false,
  },
  view_work_order_checklist: {
    action_name: 'view_work_order_checklist',
    label: 'Show Checklist',
    cluster: 'do_maintenance',
    card_types: ['work_order'],
    side_effect: 'read_only',
    description: 'Display procedural checklist for this task',
    handler: 'work_order_handlers.view_work_order_checklist',
    requires_confirmation: false,
  },
  assign_work_order: {
    action_name: 'assign_work_order',
    label: 'Assign Task',
    cluster: 'do_maintenance',
    card_types: ['work_order'],
    side_effect: 'mutation_light',
    description: 'Assign work order to crew member or contractor',
    handler: 'work_order_handlers.assign_work_order',
    requires_confirmation: false,
  },
  view_checklist: {
    action_name: 'view_checklist',
    label: 'View Checklist',
    cluster: 'do_maintenance',
    card_types: ['checklist'],
    side_effect: 'read_only',
    description: 'Display operational checklist (arrival, departure, etc.)',
    handler: 'checklist_handlers.view_checklist',
    requires_confirmation: false,
  },
  mark_checklist_item_complete: {
    action_name: 'mark_checklist_item_complete',
    label: 'Mark Complete',
    cluster: 'do_maintenance',
    card_types: ['checklist'],
    side_effect: 'mutation_light',
    description: 'Tick off checklist item',
    handler: 'checklist_handlers.mark_checklist_item_complete',
    requires_confirmation: false,
  },
  add_checklist_note: {
    action_name: 'add_checklist_note',
    label: 'Add Note',
    cluster: 'do_maintenance',
    card_types: ['checklist'],
    side_effect: 'mutation_light',
    description: 'Add note or observation to checklist item',
    handler: 'checklist_handlers.add_checklist_note',
    requires_confirmation: false,
  },
  add_checklist_photo: {
    action_name: 'add_checklist_photo',
    label: 'Add Photo',
    cluster: 'do_maintenance',
    card_types: ['checklist'],
    side_effect: 'mutation_light',
    description: 'Attach photo to checklist item',
    handler: 'checklist_handlers.add_checklist_photo',
    requires_confirmation: false,
  },
  view_worklist: {
    action_name: 'view_worklist',
    label: 'View Worklist',
    cluster: 'do_maintenance',
    card_types: ['worklist'],
    side_effect: 'read_only',
    description: 'Display shipyard work items and snags',
    handler: 'worklist_handlers.view_worklist',
    requires_confirmation: false,
  },
  add_worklist_task: {
    action_name: 'add_worklist_task',
    label: 'Add Task',
    cluster: 'do_maintenance',
    card_types: ['worklist'],
    side_effect: 'mutation_heavy',
    description: 'Create new shipyard work item',
    handler: 'worklist_handlers.add_worklist_task',
    requires_confirmation: true,
  },
  update_worklist_progress: {
    action_name: 'update_worklist_progress',
    label: 'Update Progress',
    cluster: 'do_maintenance',
    card_types: ['worklist'],
    side_effect: 'mutation_light',
    description: 'Update completion status of yard task',
    handler: 'worklist_handlers.update_worklist_progress',
    requires_confirmation: false,
  },
  export_worklist: {
    action_name: 'export_worklist',
    label: 'Export Worklist',
    cluster: 'do_maintenance',
    card_types: ['worklist'],
    side_effect: 'read_only',
    description: 'Generate worklist document for yard/contractors',
    handler: 'worklist_handlers.export_worklist',
    requires_confirmation: false,
  },
};

// ============================================================================
// CLUSTER 3: MANAGE_EQUIPMENT (6 actions)
// Understand equipment state, history, and context
// ============================================================================

const MANAGE_EQUIPMENT_ACTIONS: Record<string, MicroAction> = {
  view_equipment_details: {
    action_name: 'view_equipment_details',
    label: 'View Equipment',
    cluster: 'manage_equipment',
    card_types: ['equipment', 'fault', 'smart_summary'],
    side_effect: 'read_only',
    description: 'Display full equipment profile (model, serial, location)',
    handler: 'equipment_handlers.view_equipment_details',
    requires_confirmation: false,
  },
  run_diagnostic: {
    action_name: 'run_diagnostic',
    label: 'Run Diagnostic',
    cluster: 'manage_equipment',
    card_types: ['equipment'],
    side_effect: 'read_only',
    description: 'Run equipment diagnostic check',
    handler: 'equipment_handlers.run_diagnostic',
    requires_confirmation: false,
  },
  view_equipment_history: {
    action_name: 'view_equipment_history',
    label: 'View History',
    cluster: 'manage_equipment',
    card_types: ['equipment'],
    side_effect: 'read_only',
    description: 'Show maintenance timeline for this equipment',
    handler: 'equipment_handlers.view_equipment_history',
    requires_confirmation: false,
  },
  view_equipment_parts: {
    action_name: 'view_equipment_parts',
    label: 'View Parts',
    cluster: 'manage_equipment',
    card_types: ['equipment'],
    side_effect: 'read_only',
    description: 'List compatible parts for this equipment',
    handler: 'equipment_handlers.view_equipment_parts',
    requires_confirmation: false,
  },
  view_linked_faults: {
    action_name: 'view_linked_faults',
    label: 'View Faults',
    cluster: 'manage_equipment',
    card_types: ['equipment'],
    side_effect: 'read_only',
    description: 'Show fault history for this equipment',
    handler: 'equipment_handlers.view_linked_faults',
    requires_confirmation: false,
  },
  view_equipment_manual: {
    action_name: 'view_equipment_manual',
    label: 'Open Manual',
    cluster: 'manage_equipment',
    card_types: ['equipment'],
    side_effect: 'read_only',
    description: 'Access equipment-specific manual or documentation',
    handler: 'equipment_handlers.view_equipment_manual',
    requires_confirmation: false,
  },
  add_equipment_note: {
    action_name: 'add_equipment_note',
    label: 'Add Note',
    cluster: 'manage_equipment',
    card_types: ['equipment'],
    side_effect: 'mutation_light',
    description: 'Add observation about equipment condition',
    handler: 'equipment_handlers.add_equipment_note',
    requires_confirmation: false,
  },
};

// ============================================================================
// CLUSTER 4: CONTROL_INVENTORY (7 actions)
// Track, order, and manage spare parts
// ============================================================================

const CONTROL_INVENTORY_ACTIONS: Record<string, MicroAction> = {
  view_part_stock: {
    action_name: 'view_part_stock',
    label: 'Check Stock',
    cluster: 'control_inventory',
    card_types: ['part', 'fault', 'work_order'],
    side_effect: 'read_only',
    description: 'Display current stock level and location',
    handler: 'inventory_handlers.view_part_stock',
    requires_confirmation: false,
  },
  order_part: {
    action_name: 'order_part',
    label: 'Order Part',
    cluster: 'control_inventory',
    card_types: ['part', 'fault'],
    side_effect: 'mutation_heavy',
    description: 'Create purchase request for this part',
    handler: 'inventory_handlers.order_part',
    requires_confirmation: true,
  },
  view_part_location: {
    action_name: 'view_part_location',
    label: 'View Storage Location',
    cluster: 'control_inventory',
    card_types: ['part'],
    side_effect: 'read_only',
    description: 'Show physical storage location (deck, locker, bin)',
    handler: 'inventory_handlers.view_part_location',
    requires_confirmation: false,
  },
  view_part_usage: {
    action_name: 'view_part_usage',
    label: 'View Usage History',
    cluster: 'control_inventory',
    card_types: ['part'],
    side_effect: 'read_only',
    description: 'Show when/where this part was consumed',
    handler: 'inventory_handlers.view_part_usage',
    requires_confirmation: false,
  },
  log_part_usage: {
    action_name: 'log_part_usage',
    label: 'Log Usage',
    cluster: 'control_inventory',
    card_types: ['part', 'work_order'],
    side_effect: 'mutation_light',
    description: 'Record part consumption against work order',
    handler: 'inventory_handlers.log_part_usage',
    requires_confirmation: false,
  },
  scan_part_barcode: {
    action_name: 'scan_part_barcode',
    label: 'Scan Barcode',
    cluster: 'control_inventory',
    card_types: ['part'],
    side_effect: 'read_only',
    description: 'Identify part via barcode/QR code scan',
    handler: 'inventory_handlers.scan_part_barcode',
    requires_confirmation: false,
  },
  view_linked_equipment: {
    action_name: 'view_linked_equipment',
    label: 'View Equipment',
    cluster: 'control_inventory',
    card_types: ['part'],
    side_effect: 'read_only',
    description: 'Show which equipment uses this part',
    handler: 'inventory_handlers.view_linked_equipment',
    requires_confirmation: false,
  },
};

// ============================================================================
// CLUSTER 5: COMMUNICATE_STATUS (9 actions)
// Transfer knowledge via handovers, notes, reports
// ============================================================================

const COMMUNICATE_STATUS_ACTIONS: Record<string, MicroAction> = {
  add_to_handover: {
    action_name: 'add_to_handover',
    label: 'Add to Handover',
    cluster: 'communicate_status',
    card_types: ['fault', 'work_order', 'equipment', 'part', 'document'],
    side_effect: 'mutation_light',
    description: 'Add this item to active handover draft',
    handler: 'handover_handlers.add_to_handover',
    requires_confirmation: false,
  },
  add_document_to_handover: {
    action_name: 'add_document_to_handover',
    label: 'Add Document',
    cluster: 'communicate_status',
    card_types: ['document', 'handover'],
    side_effect: 'mutation_light',
    description: 'Attach document/manual to handover section',
    handler: 'handover_handlers.add_document_to_handover',
    requires_confirmation: false,
  },
  add_predictive_insight_to_handover: {
    action_name: 'add_predictive_insight_to_handover',
    label: 'Add Insight',
    cluster: 'communicate_status',
    card_types: ['equipment', 'smart_summary'],
    side_effect: 'mutation_light',
    description: 'Include predictive maintenance insight in handover',
    handler: 'handover_handlers.add_predictive_insight_to_handover',
    requires_confirmation: false,
  },
  edit_handover_section: {
    action_name: 'edit_handover_section',
    label: 'Edit Section',
    cluster: 'communicate_status',
    card_types: ['handover'],
    side_effect: 'mutation_light',
    description: 'Modify handover section content',
    handler: 'handover_handlers.edit_handover_section',
    requires_confirmation: false,
  },
  export_handover: {
    action_name: 'export_handover',
    label: 'Export PDF',
    cluster: 'communicate_status',
    card_types: ['handover'],
    side_effect: 'read_only',
    description: 'Generate downloadable handover document',
    handler: 'handover_handlers.export_handover',
    requires_confirmation: false,
  },
  regenerate_handover_summary: {
    action_name: 'regenerate_handover_summary',
    label: 'Regenerate Summary',
    cluster: 'communicate_status',
    card_types: ['handover'],
    side_effect: 'mutation_light',
    description: 'Auto-generate summary from recent activity',
    handler: 'handover_handlers.regenerate_handover_summary',
    requires_confirmation: false,
  },
  view_document: {
    action_name: 'view_document',
    label: 'Open Document',
    cluster: 'communicate_status',
    card_types: ['document'],
    side_effect: 'read_only',
    description: 'Display full document or manual',
    handler: 'document_handlers.view_document',
    requires_confirmation: false,
  },
  view_related_documents: {
    action_name: 'view_related_documents',
    label: 'Related Docs',
    cluster: 'communicate_status',
    card_types: ['fault', 'equipment'],
    side_effect: 'read_only',
    description: 'Find documents linked to current context',
    handler: 'document_handlers.view_related_documents',
    requires_confirmation: false,
  },
  view_document_section: {
    action_name: 'view_document_section',
    label: 'View Section',
    cluster: 'communicate_status',
    card_types: ['fault', 'work_order'],
    side_effect: 'read_only',
    description: 'Jump to specific section within document',
    handler: 'document_handlers.view_document_section',
    requires_confirmation: false,
  },
};

// ============================================================================
// CLUSTER 6: COMPLY_AUDIT (5 actions)
// Maintain compliance with regulations and standards
// ============================================================================

const COMPLY_AUDIT_ACTIONS: Record<string, MicroAction> = {
  view_hours_of_rest: {
    action_name: 'view_hours_of_rest',
    label: 'View Hours of Rest',
    cluster: 'comply_audit',
    card_types: ['hor_table'],
    side_effect: 'read_only',
    description: 'Display hours of rest summary for selected period',
    handler: 'compliance_handlers.view_hours_of_rest',
    requires_confirmation: false,
  },
  update_hours_of_rest: {
    action_name: 'update_hours_of_rest',
    label: 'Update Hours',
    cluster: 'comply_audit',
    card_types: ['hor_table'],
    side_effect: 'mutation_heavy',
    description: 'Edit or correct hours of rest entries',
    handler: 'compliance_handlers.update_hours_of_rest',
    requires_confirmation: true,
  },
  export_hours_of_rest: {
    action_name: 'export_hours_of_rest',
    label: 'Export Logs',
    cluster: 'comply_audit',
    card_types: ['hor_table'],
    side_effect: 'read_only',
    description: 'Download hours of rest report (PDF/Excel)',
    handler: 'compliance_handlers.export_hours_of_rest',
    requires_confirmation: false,
  },
  view_compliance_status: {
    action_name: 'view_compliance_status',
    label: 'Check Compliance',
    cluster: 'comply_audit',
    card_types: ['hor_table'],
    side_effect: 'read_only',
    description: 'Show MLC compliance warnings/violations',
    handler: 'compliance_handlers.view_compliance_status',
    requires_confirmation: false,
  },
  tag_for_survey: {
    action_name: 'tag_for_survey',
    label: 'Tag for Survey',
    cluster: 'comply_audit',
    card_types: ['worklist'],
    side_effect: 'mutation_light',
    description: 'Flag item for class/flag survey prep',
    handler: 'compliance_handlers.tag_for_survey',
    requires_confirmation: false,
  },
};

// ============================================================================
// CLUSTER 7: PROCURE_SUPPLIERS (7 actions)
// Acquire parts and manage supplier relationships
// ============================================================================

const PROCURE_SUPPLIERS_ACTIONS: Record<string, MicroAction> = {
  create_purchase_request: {
    action_name: 'create_purchase_request',
    label: 'Create Purchase',
    cluster: 'procure_suppliers',
    card_types: ['part', 'smart_summary'],
    side_effect: 'mutation_heavy',
    description: 'Initiate purchase order for parts or services',
    handler: 'purchasing_handlers.create_purchase_request',
    requires_confirmation: true,
  },
  add_item_to_purchase: {
    action_name: 'add_item_to_purchase',
    label: 'Add Item',
    cluster: 'procure_suppliers',
    card_types: ['purchase'],
    side_effect: 'mutation_light',
    description: 'Add part to existing purchase request',
    handler: 'purchasing_handlers.add_item_to_purchase',
    requires_confirmation: false,
  },
  approve_purchase: {
    action_name: 'approve_purchase',
    label: 'Approve',
    cluster: 'procure_suppliers',
    card_types: ['purchase'],
    side_effect: 'mutation_heavy',
    description: 'Approve purchase request (role-based)',
    handler: 'purchasing_handlers.approve_purchase',
    requires_confirmation: true,
  },
  upload_invoice: {
    action_name: 'upload_invoice',
    label: 'Upload Invoice',
    cluster: 'procure_suppliers',
    card_types: ['purchase'],
    side_effect: 'mutation_light',
    description: 'Attach supplier invoice to purchase order',
    handler: 'purchasing_handlers.upload_invoice',
    requires_confirmation: false,
  },
  track_delivery: {
    action_name: 'track_delivery',
    label: 'Track Delivery',
    cluster: 'procure_suppliers',
    card_types: ['purchase'],
    side_effect: 'read_only',
    description: 'View delivery status and ETA',
    handler: 'purchasing_handlers.track_delivery',
    requires_confirmation: false,
  },
  log_delivery_received: {
    action_name: 'log_delivery_received',
    label: 'Log Delivery',
    cluster: 'procure_suppliers',
    card_types: ['purchase'],
    side_effect: 'mutation_heavy',
    description: 'Mark items as received and update inventory',
    handler: 'purchasing_handlers.log_delivery_received',
    requires_confirmation: true,
  },
  update_purchase_status: {
    action_name: 'update_purchase_status',
    label: 'Update Status',
    cluster: 'procure_suppliers',
    card_types: ['purchase'],
    side_effect: 'mutation_light',
    description: 'Change purchase order status',
    handler: 'purchasing_handlers.update_purchase_status',
    requires_confirmation: false,
  },
};

// ============================================================================
// ADDITIONAL ACTIONS (Fleet, Predictive, Mobile)
// ============================================================================

const ADDITIONAL_ACTIONS: Record<string, MicroAction> = {
  view_fleet_summary: {
    action_name: 'view_fleet_summary',
    label: 'View Fleet',
    cluster: 'manage_equipment',
    card_types: ['fleet_summary'],
    side_effect: 'read_only',
    description: 'Display multi-vessel overview',
    handler: 'fleet_handlers.view_fleet_summary',
    requires_confirmation: false,
  },
  open_vessel: {
    action_name: 'open_vessel',
    label: 'Open Vessel',
    cluster: 'manage_equipment',
    card_types: ['fleet_summary'],
    side_effect: 'read_only',
    description: 'Switch context to specific vessel',
    handler: 'fleet_handlers.open_vessel',
    requires_confirmation: false,
  },
  export_fleet_summary: {
    action_name: 'export_fleet_summary',
    label: 'Export Summary',
    cluster: 'communicate_status',
    card_types: ['fleet_summary'],
    side_effect: 'read_only',
    description: 'Download fleet status report',
    handler: 'fleet_handlers.export_fleet_summary',
    requires_confirmation: false,
  },
  request_predictive_insight: {
    action_name: 'request_predictive_insight',
    label: 'Predictive Insight',
    cluster: 'manage_equipment',
    card_types: ['equipment', 'smart_summary'],
    side_effect: 'read_only',
    description: 'Request AI-driven maintenance predictions',
    handler: 'predictive_handlers.request_predictive_insight',
    requires_confirmation: false,
  },
  view_smart_summary: {
    action_name: 'view_smart_summary',
    label: 'View Summary',
    cluster: 'communicate_status',
    card_types: ['smart_summary'],
    side_effect: 'read_only',
    description: 'Generate situational briefing (daily, pre-departure)',
    handler: 'summary_handlers.view_smart_summary',
    requires_confirmation: false,
  },
  upload_photo: {
    action_name: 'upload_photo',
    label: 'Upload Photo',
    cluster: 'communicate_status',
    card_types: ['work_order', 'fault', 'checklist', 'equipment'],
    side_effect: 'mutation_light',
    description: 'Upload photo from mobile device',
    handler: 'mobile_handlers.upload_photo',
    requires_confirmation: false,
  },
  record_voice_note: {
    action_name: 'record_voice_note',
    label: 'Voice Note',
    cluster: 'communicate_status',
    card_types: ['work_order', 'fault'],
    side_effect: 'mutation_light',
    description: 'Record audio note and transcribe',
    handler: 'mobile_handlers.record_voice_note',
    requires_confirmation: false,
  },
};

// ============================================================================
// COMPLETE REGISTRY (57 actions)
// ============================================================================

export const MICROACTION_REGISTRY: Record<string, MicroAction> = {
  ...FIX_SOMETHING_ACTIONS,
  ...DO_MAINTENANCE_ACTIONS,
  ...MANAGE_EQUIPMENT_ACTIONS,
  ...CONTROL_INVENTORY_ACTIONS,
  ...COMMUNICATE_STATUS_ACTIONS,
  ...COMPLY_AUDIT_ACTIONS,
  ...PROCURE_SUPPLIERS_ACTIONS,
  ...ADDITIONAL_ACTIONS,
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Get all actions for a specific card type
 */
function getActionsForCardType(cardType: CardType): MicroAction[] {
  return Object.values(MICROACTION_REGISTRY).filter((action) =>
    action.card_types.includes(cardType)
  );
}

/**
 * Get all actions in a specific cluster
 */
function getActionsInCluster(cluster: MicroAction['cluster']): MicroAction[] {
  return Object.values(MICROACTION_REGISTRY).filter(
    (action) => action.cluster === cluster
  );
}

/**
 * Get action by name
 */
export function getAction(actionName: string): MicroAction | undefined {
  return MICROACTION_REGISTRY[actionName];
}

/**
 * Get all read-only actions
 */
function getReadOnlyActions(): MicroAction[] {
  return Object.values(MICROACTION_REGISTRY).filter(
    (action) => action.side_effect === 'read_only'
  );
}

/**
 * Get all mutation actions (light + heavy)
 */
function getMutationActions(): MicroAction[] {
  return Object.values(MICROACTION_REGISTRY).filter(
    (action) => action.side_effect !== 'read_only'
  );
}

/**
 * Get all actions requiring confirmation
 */
function getConfirmationRequiredActions(): MicroAction[] {
  return Object.values(MICROACTION_REGISTRY).filter(
    (action) => action.requires_confirmation
  );
}

/**
 * Count actions by side effect type
 */
function countBySideEffect(): Record<MicroAction['side_effect'], number> {
  const counts: Record<MicroAction['side_effect'], number> = {
    read_only: 0,
    mutation_light: 0,
    mutation_heavy: 0,
  };

  Object.values(MICROACTION_REGISTRY).forEach((action) => {
    counts[action.side_effect]++;
  });

  return counts;
}

/**
 * Count actions by cluster
 */
function countByCluster(): Record<MicroAction['cluster'], number> {
  const counts: Record<MicroAction['cluster'], number> = {
    fix_something: 0,
    do_maintenance: 0,
    manage_equipment: 0,
    control_inventory: 0,
    communicate_status: 0,
    comply_audit: 0,
    procure_suppliers: 0,
  };

  Object.values(MICROACTION_REGISTRY).forEach((action) => {
    counts[action.cluster]++;
  });

  return counts;
}

// Export total count for verification
const TOTAL_ACTIONS = Object.keys(MICROACTION_REGISTRY).length;
