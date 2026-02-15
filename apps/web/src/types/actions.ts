/**
 * CelesteOS Micro-Actions Type System
 * Complete registry of all 83 canonical micro-actions
 *
 * Version: 1.1
 * Last Updated: 2026-01-26
 */

// ============================================================================
// MICRO-ACTION TYPES (All 67 Actions)
// ============================================================================

export type MicroAction =
  // FAULT & DIAGNOSIS (12 actions)
  | 'diagnose_fault'
  | 'report_fault'
  | 'show_manual_section'
  | 'view_fault_history'
  | 'suggest_parts'
  | 'create_work_order_from_fault'
  | 'add_fault_note'
  | 'add_fault_photo'
  | 'link_equipment_to_fault'
  | 'acknowledge_fault'
  | 'update_fault'
  | 'view_fault_detail'

  // WORK ORDER / PMS (11 actions)
  | 'create_work_order'
  | 'view_work_order_history'
  | 'mark_work_order_complete'
  | 'complete_work_order'
  | 'add_work_order_note'
  | 'add_work_order_photo'
  | 'add_parts_to_work_order'
  | 'link_parts_to_work_order'
  | 'view_work_order_checklist'
  | 'assign_work_order'

  // EQUIPMENT (6 actions)
  | 'view_equipment_details'
  | 'view_equipment_history'
  | 'view_equipment_parts'
  | 'view_linked_faults'
  | 'view_equipment_manual'
  | 'add_equipment_note'

  // INVENTORY / PARTS (9 actions)
  | 'view_part_stock'
  | 'add_part'
  | 'order_part'
  | 'view_part_location'
  | 'view_part_usage'
  | 'log_part_usage'
  | 'edit_part_quantity'
  | 'scan_part_barcode'
  | 'view_linked_equipment'

  // HANDOVER (6 actions)
  | 'add_to_handover'
  | 'add_document_to_handover'
  | 'add_predictive_insight_to_handover'
  | 'edit_handover_section'
  | 'export_handover'
  | 'regenerate_handover_summary'

  // DOCUMENT (3 actions)
  | 'view_document'
  | 'view_related_documents'
  | 'view_document_section'

  // HOURS OF REST / COMPLIANCE (4 actions)
  | 'view_hours_of_rest'
  | 'update_hours_of_rest'
  | 'export_hours_of_rest'
  | 'view_compliance_status'

  // PURCHASING / SUPPLIER (7 actions)
  | 'create_purchase_request'
  | 'add_item_to_purchase'
  | 'approve_purchase'
  | 'upload_invoice'
  | 'track_delivery'
  | 'log_delivery_received'
  | 'update_purchase_status'

  // RECEIVING (10 actions)
  | 'create_receiving'
  | 'view_receiving_history'
  | 'add_receiving_item'
  | 'adjust_receiving_item'
  | 'update_receiving'
  | 'attach_receiving_image_with_comment'
  | 'extract_receiving_candidates'
  | 'accept_receiving'
  | 'reject_receiving'
  | 'link_receiving_to_invoice'

  // OPERATIONAL CHECKLISTS (5 actions)
  | 'view_checklist'
  | 'mark_checklist_item_complete'
  | 'add_checklist_item'
  | 'add_checklist_note'
  | 'add_checklist_photo'

  // SHIPYARD / REFIT (5 actions)
  | 'view_worklist'
  | 'add_worklist_task'
  | 'update_worklist_progress'
  | 'export_worklist'
  | 'tag_for_survey'

  // FLEET / MANAGEMENT (3 actions)
  | 'view_fleet_summary'
  | 'open_vessel'
  | 'export_fleet_summary'

  // PREDICTIVE / SMART SUMMARY (2 actions)
  | 'request_predictive_insight'
  | 'view_smart_summary'

  // MOBILE-SPECIFIC (2 actions)
  | 'upload_photo'
  | 'record_voice_note'

  // EDIT ACTIONS - ADDENDUM (10 actions)
  | 'edit_work_order_details'
  | 'edit_equipment_details'
  | 'edit_part_details'
  | 'edit_purchase_details'
  | 'edit_invoice_amount'
  | 'edit_fault_details'
  | 'edit_note'
  | 'delete_item'
  | 'approve_work_order'
  | 'scan_equipment_barcode';

// ============================================================================
// ACTION METADATA
// ============================================================================

export type SideEffectType = 'read_only' | 'mutation_light' | 'mutation_heavy';

export type PurposeCluster =
  | 'fix_something'
  | 'do_maintenance'
  | 'manage_equipment'
  | 'control_inventory'
  | 'communicate_status'
  | 'comply_audit'
  | 'procure_suppliers';

export interface ActionMetadata {
  action_name: MicroAction;
  label: string; // UI button label
  cluster: PurposeCluster;
  side_effect_type: SideEffectType;
  requires_confirmation?: boolean; // For mutation_heavy actions
  requires_reason?: boolean; // For audit-sensitive actions like edit_invoice_amount
  role_restricted?: ('chief_engineer' | 'eto' | 'captain' | 'manager' | 'chief_officer' | 'chief_steward' | 'purser' | 'vendor' | 'crew' | 'deck' | 'interior')[]; // If role-based
  icon?: string; // lucide-react icon name
  description: string;
}

// ============================================================================
// CARD TYPES (All 12 Card Types)
// ============================================================================

export type CardType =
  | 'fault'
  | 'work_order'
  | 'equipment'
  | 'part'
  | 'handover'
  | 'document'
  | 'hor_table'
  | 'purchase'
  | 'checklist'
  | 'worklist'
  | 'fleet_summary'
  | 'smart_summary';

// Backward compatibility alias
export type ResultCardType = CardType;

// ============================================================================
// ACTION PAYLOAD INTERFACES
// ============================================================================

/**
 * Payload sent to backend when action is triggered
 */
export interface ActionPayload {
  action_name: MicroAction;
  user_id: string;
  yacht_id: string;
  context: Record<string, any>; // Entity-specific context
  timestamp: string;
}

/**
 * Response from backend after action execution
 */
export interface ActionResponse {
  success: boolean;
  message?: string;
  data?: any;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
}

// ============================================================================
// SPECIFIC ACTION PAYLOADS
// ============================================================================

export interface CreateWorkOrderPayload {
  equipment_id?: string;
  title: string;
  description: string;
  type: 'scheduled' | 'corrective' | 'unplanned';
  priority: 'routine' | 'important' | 'critical';
  due_date?: string;
  assigned_to?: string;
}

export interface EditInvoiceAmountPayload {
  purchase_id: string;
  invoice_id: string;
  old_amount: number;
  new_amount: number;
  reason: string; // Required for audit
}

export interface AddToHandoverPayload {
  handover_id?: string; // If null, add to active draft
  source_type: 'fault' | 'work_order' | 'equipment' | 'part' | 'document' | 'note';
  source_id: string;
  summary?: string; // Optional custom summary
  importance?: 'low' | 'normal' | 'high';
}

export interface EditWorkOrderDetailsPayload {
  work_order_id: string;
  changes: {
    title?: string;
    description?: string;
    priority?: 'routine' | 'important' | 'critical';
    due_date?: string;
    assigned_to?: string;
  };
}

export interface MarkWorkOrderCompletePayload {
  work_order_id: string;
  completion_notes?: string;
  parts_used?: Array<{
    part_id: string;
    quantity: number;
  }>;
}

export interface OrderPartPayload {
  part_id: string;
  quantity: number;
  supplier?: string;
  delivery_date?: string;
  notes?: string;
}

export interface AddNotePayload {
  entity_type: 'fault' | 'work_order' | 'equipment' | 'checklist';
  entity_id: string;
  note_text: string;
}

export interface UploadPhotoPayload {
  entity_type: 'fault' | 'work_order' | 'equipment' | 'checklist';
  entity_id: string;
  photo: File;
  caption?: string;
}

export interface EditEquipmentDetailsPayload {
  equipment_id: string;
  changes: {
    name?: string;
    model?: string;
    serial_number?: string;
    location?: string;
    install_date?: string;
    manufacturer?: string;
    notes?: string;
  };
}

export interface EditPartDetailsPayload {
  part_id: string;
  changes: {
    part_name?: string;
    part_number?: string;
    storage_location?: string;
    min_stock_level?: number;
    max_stock_level?: number;
    reorder_quantity?: number;
    preferred_supplier?: string;
    notes?: string;
  };
}

export interface DeleteItemPayload {
  item_type: 'note' | 'photo' | 'work_order' | 'handover_item';
  item_id: string;
  reason?: string; // Optional delete reason
}

export interface ApproveWorkOrderPayload {
  work_order_id: string;
  approved: boolean; // true = approve, false = reject
  approver_notes?: string;
}

// ============================================================================
// ACTION REGISTRY (Metadata for all actions)
// ============================================================================

export const ACTION_REGISTRY: Record<MicroAction, ActionMetadata> = {
  // FAULT & DIAGNOSIS
  diagnose_fault: {
    action_name: 'diagnose_fault',
    label: 'Diagnose Fault',
    cluster: 'fix_something',
    side_effect_type: 'read_only',
    icon: 'AlertTriangle',
    description: 'Analyze fault code and provide diagnostic guidance',
  },
  show_manual_section: {
    action_name: 'show_manual_section',
    label: 'View Manual',
    cluster: 'fix_something',
    side_effect_type: 'read_only',
    icon: 'BookOpen',
    description: 'Open relevant manual section for current context',
  },
  view_fault_history: {
    action_name: 'view_fault_history',
    label: 'View History',
    cluster: 'fix_something',
    side_effect_type: 'read_only',
    icon: 'History',
    description: 'Show historical occurrences of similar faults',
  },
  suggest_parts: {
    action_name: 'suggest_parts',
    label: 'Suggest Parts',
    cluster: 'fix_something',
    side_effect_type: 'read_only',
    icon: 'Package',
    description: 'Recommend likely parts needed for this fault',
  },
  create_work_order_from_fault: {
    action_name: 'create_work_order_from_fault',
    label: 'Create Work Order',
    cluster: 'fix_something',
    side_effect_type: 'mutation_heavy',
    requires_confirmation: true,
    icon: 'Wrench',
    description: 'Generate work order pre-filled from fault context',
  },
  add_fault_note: {
    action_name: 'add_fault_note',
    label: 'Add Note',
    cluster: 'fix_something',
    side_effect_type: 'mutation_light',
    icon: 'StickyNote',
    description: 'Attach observation or comment to fault record',
  },
  add_fault_photo: {
    action_name: 'add_fault_photo',
    label: 'Add Photo',
    cluster: 'fix_something',
    side_effect_type: 'mutation_light',
    icon: 'Camera',
    description: 'Upload photo evidence of fault condition',
  },
  acknowledge_fault: {
    action_name: 'acknowledge_fault',
    label: 'Acknowledge',
    cluster: 'fix_something',
    side_effect_type: 'mutation_light',
    icon: 'CheckCircle',
    description: 'Acknowledge fault and take responsibility',
  },
  update_fault: {
    action_name: 'update_fault',
    label: 'Update',
    cluster: 'fix_something',
    side_effect_type: 'mutation_light',
    icon: 'Edit',
    description: 'Update fault details (severity, description, etc.)',
  },
  view_fault_detail: {
    action_name: 'view_fault_detail',
    label: 'View Details',
    cluster: 'fix_something',
    side_effect_type: 'read_only',
    icon: 'Eye',
    description: 'View full fault details',
  },
  report_fault: {
    action_name: 'report_fault',
    label: 'Report Fault',
    cluster: 'fix_something',
    side_effect_type: 'mutation_heavy',
    requires_confirmation: true,
    icon: 'AlertCircle',
    description: 'Report a new fault on equipment',
  },
  link_equipment_to_fault: {
    action_name: 'link_equipment_to_fault',
    label: 'Link Equipment',
    cluster: 'fix_something',
    side_effect_type: 'mutation_light',
    icon: 'Link',
    description: 'Link equipment to an existing fault',
  },

  // WORK ORDER / PMS
  create_work_order: {
    action_name: 'create_work_order',
    label: 'Create Work Order',
    cluster: 'do_maintenance',
    side_effect_type: 'mutation_heavy',
    requires_confirmation: true,
    icon: 'Wrench',
    description: 'Create new work order with manual equipment selection',
  },
  view_work_order_history: {
    action_name: 'view_work_order_history',
    label: 'View History',
    cluster: 'do_maintenance',
    side_effect_type: 'read_only',
    icon: 'History',
    description: 'Show completion history for this work order type',
  },
  mark_work_order_complete: {
    action_name: 'mark_work_order_complete',
    label: 'Mark Done',
    cluster: 'do_maintenance',
    side_effect_type: 'mutation_heavy',
    requires_confirmation: true,
    icon: 'CheckCircle',
    description: 'Close work order and log completion',
  },
  complete_work_order: {
    action_name: 'complete_work_order',
    label: 'Complete Work Order',
    cluster: 'do_maintenance',
    side_effect_type: 'mutation_heavy',
    requires_confirmation: true,
    icon: 'CheckCircle',
    description: 'Complete work order with outcome details',
  },
  link_parts_to_work_order: {
    action_name: 'link_parts_to_work_order',
    label: 'Link Parts',
    cluster: 'do_maintenance',
    side_effect_type: 'mutation_light',
    icon: 'Link',
    description: 'Link parts to a work order',
  },
  add_work_order_note: {
    action_name: 'add_work_order_note',
    label: 'Add Note',
    cluster: 'do_maintenance',
    side_effect_type: 'mutation_light',
    icon: 'StickyNote',
    description: 'Add progress note or findings to work order',
  },
  add_work_order_photo: {
    action_name: 'add_work_order_photo',
    label: 'Add Photo',
    cluster: 'do_maintenance',
    side_effect_type: 'mutation_light',
    icon: 'Camera',
    description: 'Attach photo to work order (before/after, evidence)',
  },
  add_parts_to_work_order: {
    action_name: 'add_parts_to_work_order',
    label: 'Add Parts',
    cluster: 'do_maintenance',
    side_effect_type: 'mutation_light',
    icon: 'Package',
    description: 'Link consumed parts to this work order',
  },
  view_work_order_checklist: {
    action_name: 'view_work_order_checklist',
    label: 'Show Checklist',
    cluster: 'do_maintenance',
    side_effect_type: 'read_only',
    icon: 'ListChecks',
    description: 'Display procedural checklist for this task',
  },
  assign_work_order: {
    action_name: 'assign_work_order',
    label: 'Assign Task',
    cluster: 'do_maintenance',
    side_effect_type: 'mutation_light',
    role_restricted: ['chief_engineer', 'captain', 'manager'],
    icon: 'UserPlus',
    description: 'Assign work order to crew member or contractor',
  },

  // EQUIPMENT
  view_equipment_details: {
    action_name: 'view_equipment_details',
    label: 'View Equipment',
    cluster: 'manage_equipment',
    side_effect_type: 'read_only',
    icon: 'Cog',
    description: 'Display full equipment profile (model, serial, location)',
  },
  view_equipment_history: {
    action_name: 'view_equipment_history',
    label: 'View History',
    cluster: 'manage_equipment',
    side_effect_type: 'read_only',
    icon: 'History',
    description: 'Show maintenance timeline for this equipment',
  },
  view_equipment_parts: {
    action_name: 'view_equipment_parts',
    label: 'View Parts',
    cluster: 'manage_equipment',
    side_effect_type: 'read_only',
    icon: 'Package',
    description: 'List compatible parts for this equipment',
  },
  view_linked_faults: {
    action_name: 'view_linked_faults',
    label: 'View Faults',
    cluster: 'manage_equipment',
    side_effect_type: 'read_only',
    icon: 'AlertTriangle',
    description: 'Show fault history for this equipment',
  },
  view_equipment_manual: {
    action_name: 'view_equipment_manual',
    label: 'Open Manual',
    cluster: 'manage_equipment',
    side_effect_type: 'read_only',
    icon: 'BookOpen',
    description: 'Access equipment-specific manual or documentation',
  },
  add_equipment_note: {
    action_name: 'add_equipment_note',
    label: 'Add Note',
    cluster: 'manage_equipment',
    side_effect_type: 'mutation_light',
    icon: 'StickyNote',
    description: 'Add observation about equipment condition',
  },

  // INVENTORY / PARTS
  view_part_stock: {
    action_name: 'view_part_stock',
    label: 'Check Stock',
    cluster: 'control_inventory',
    side_effect_type: 'read_only',
    icon: 'Package',
    description: 'Display current stock level and location',
  },
  add_part: {
    action_name: 'add_part',
    label: 'Add Part',
    cluster: 'control_inventory',
    side_effect_type: 'mutation_heavy',
    requires_confirmation: true,
    icon: 'Plus',
    description: 'Add a new part to inventory',
  },
  edit_part_quantity: {
    action_name: 'edit_part_quantity',
    label: 'Edit Quantity',
    cluster: 'control_inventory',
    side_effect_type: 'mutation_heavy',
    requires_confirmation: true,
    requires_reason: true,
    icon: 'Edit',
    description: 'Adjust part quantity with audit trail',
  },
  order_part: {
    action_name: 'order_part',
    label: 'Order Part',
    cluster: 'control_inventory',
    side_effect_type: 'mutation_heavy',
    requires_confirmation: true,
    icon: 'ShoppingCart',
    description: 'Create purchase request for this part',
  },
  view_part_location: {
    action_name: 'view_part_location',
    label: 'View Storage Location',
    cluster: 'control_inventory',
    side_effect_type: 'read_only',
    icon: 'MapPin',
    description: 'Show physical storage location (deck, locker, bin)',
  },
  view_part_usage: {
    action_name: 'view_part_usage',
    label: 'View Usage History',
    cluster: 'control_inventory',
    side_effect_type: 'read_only',
    icon: 'History',
    description: 'Show when/where this part was consumed',
  },
  log_part_usage: {
    action_name: 'log_part_usage',
    label: 'Log Usage',
    cluster: 'control_inventory',
    side_effect_type: 'mutation_light',
    icon: 'ClipboardList',
    description: 'Record part consumption against work order',
  },
  scan_part_barcode: {
    action_name: 'scan_part_barcode',
    label: 'Scan Barcode',
    cluster: 'control_inventory',
    side_effect_type: 'read_only',
    icon: 'QrCode',
    description: 'Identify part via barcode/QR code scan',
  },
  view_linked_equipment: {
    action_name: 'view_linked_equipment',
    label: 'View Equipment',
    cluster: 'control_inventory',
    side_effect_type: 'read_only',
    icon: 'Cog',
    description: 'Show which equipment uses this part',
  },

  // HANDOVER
  add_to_handover: {
    action_name: 'add_to_handover',
    label: 'Add to Handover',
    cluster: 'communicate_status',
    side_effect_type: 'mutation_light',
    icon: 'PlusCircle',
    description: 'Add item to active handover draft',
  },
  add_document_to_handover: {
    action_name: 'add_document_to_handover',
    label: 'Add Document',
    cluster: 'communicate_status',
    side_effect_type: 'mutation_light',
    icon: 'FileText',
    description: 'Attach document/manual to handover section',
  },
  add_predictive_insight_to_handover: {
    action_name: 'add_predictive_insight_to_handover',
    label: 'Add Insight',
    cluster: 'communicate_status',
    side_effect_type: 'mutation_light',
    icon: 'TrendingUp',
    description: 'Include predictive maintenance insight in handover',
  },
  edit_handover_section: {
    action_name: 'edit_handover_section',
    label: 'Edit Section',
    cluster: 'communicate_status',
    side_effect_type: 'mutation_light',
    icon: 'Edit',
    description: 'Modify handover section content',
  },
  export_handover: {
    action_name: 'export_handover',
    label: 'Export PDF',
    cluster: 'communicate_status',
    side_effect_type: 'read_only',
    icon: 'Download',
    description: 'Generate downloadable handover document',
  },
  regenerate_handover_summary: {
    action_name: 'regenerate_handover_summary',
    label: 'Regenerate Summary',
    cluster: 'communicate_status',
    side_effect_type: 'mutation_light',
    icon: 'RefreshCw',
    description: 'Auto-generate summary from recent activity',
  },

  // DOCUMENT
  view_document: {
    action_name: 'view_document',
    label: 'Open Document',
    cluster: 'fix_something',
    side_effect_type: 'read_only',
    icon: 'FileText',
    description: 'Display full document or manual',
  },
  view_related_documents: {
    action_name: 'view_related_documents',
    label: 'Related Docs',
    cluster: 'fix_something',
    side_effect_type: 'read_only',
    icon: 'Files',
    description: 'Find documents linked to current context',
  },
  view_document_section: {
    action_name: 'view_document_section',
    label: 'View Section',
    cluster: 'fix_something',
    side_effect_type: 'read_only',
    icon: 'FileSearch',
    description: 'Jump to specific section within document',
  },

  // HOURS OF REST / COMPLIANCE
  view_hours_of_rest: {
    action_name: 'view_hours_of_rest',
    label: 'View Hours',
    cluster: 'comply_audit',
    side_effect_type: 'read_only',
    icon: 'Clock',
    description: 'Display hours of rest summary for selected period',
  },
  update_hours_of_rest: {
    action_name: 'update_hours_of_rest',
    label: 'Update Hours',
    cluster: 'comply_audit',
    side_effect_type: 'mutation_heavy',
    requires_confirmation: true,
    icon: 'Edit',
    description: 'Edit or correct hours of rest entries',
  },
  export_hours_of_rest: {
    action_name: 'export_hours_of_rest',
    label: 'Export Logs',
    cluster: 'comply_audit',
    side_effect_type: 'read_only',
    icon: 'Download',
    description: 'Download hours of rest report (PDF/Excel)',
  },
  view_compliance_status: {
    action_name: 'view_compliance_status',
    label: 'Check Compliance',
    cluster: 'comply_audit',
    side_effect_type: 'read_only',
    icon: 'Shield',
    description: 'Show MLC compliance warnings/violations',
  },

  // PURCHASING / SUPPLIER
  create_purchase_request: {
    action_name: 'create_purchase_request',
    label: 'Create Purchase',
    cluster: 'procure_suppliers',
    side_effect_type: 'mutation_heavy',
    requires_confirmation: true,
    icon: 'ShoppingCart',
    description: 'Initiate purchase order for parts or services',
  },
  add_item_to_purchase: {
    action_name: 'add_item_to_purchase',
    label: 'Add Item',
    cluster: 'procure_suppliers',
    side_effect_type: 'mutation_light',
    icon: 'PlusCircle',
    description: 'Add part to existing purchase request',
  },
  approve_purchase: {
    action_name: 'approve_purchase',
    label: 'Approve',
    cluster: 'procure_suppliers',
    side_effect_type: 'mutation_heavy',
    requires_confirmation: true,
    role_restricted: ['chief_engineer', 'captain', 'manager'],
    icon: 'CheckCircle',
    description: 'Approve purchase request (role-based)',
  },
  upload_invoice: {
    action_name: 'upload_invoice',
    label: 'Upload Invoice',
    cluster: 'procure_suppliers',
    side_effect_type: 'mutation_light',
    icon: 'FileUp',
    description: 'Attach supplier invoice to purchase order',
  },
  track_delivery: {
    action_name: 'track_delivery',
    label: 'Track Delivery',
    cluster: 'procure_suppliers',
    side_effect_type: 'read_only',
    icon: 'Truck',
    description: 'View delivery status and ETA',
  },
  log_delivery_received: {
    action_name: 'log_delivery_received',
    label: 'Log Delivery',
    cluster: 'procure_suppliers',
    side_effect_type: 'mutation_heavy',
    requires_confirmation: true,
    icon: 'PackageCheck',
    description: 'Mark items as received and update inventory',
  },
  update_purchase_status: {
    action_name: 'update_purchase_status',
    label: 'Update Status',
    cluster: 'procure_suppliers',
    side_effect_type: 'mutation_light',
    icon: 'Edit',
    description: 'Change purchase order status',
  },

  // RECEIVING (10 actions)
  create_receiving: {
    action_name: 'create_receiving',
    label: 'Create Receiving',
    cluster: 'procure_suppliers',
    side_effect_type: 'mutation_heavy',
    requires_confirmation: true,
    role_restricted: ['chief_engineer', 'chief_officer', 'chief_steward', 'purser', 'captain', 'manager'],
    icon: 'Package',
    description: 'Create new receiving record for delivered goods',
  },
  view_receiving_history: {
    action_name: 'view_receiving_history',
    label: 'View Receiving History',
    cluster: 'procure_suppliers',
    side_effect_type: 'read_only',
    role_restricted: ['chief_engineer', 'chief_officer', 'chief_steward', 'purser', 'captain', 'manager'],
    icon: 'History',
    description: 'Display receiving audit log and history',
  },
  add_receiving_item: {
    action_name: 'add_receiving_item',
    label: 'Add Line Item',
    cluster: 'procure_suppliers',
    side_effect_type: 'mutation_light',
    role_restricted: ['chief_engineer', 'chief_officer', 'chief_steward', 'purser', 'captain', 'manager'],
    icon: 'PlusCircle',
    description: 'Add item to receiving record',
  },
  adjust_receiving_item: {
    action_name: 'adjust_receiving_item',
    label: 'Adjust Line Item',
    cluster: 'procure_suppliers',
    side_effect_type: 'mutation_light',
    role_restricted: ['chief_engineer', 'chief_officer', 'chief_steward', 'purser', 'captain', 'manager'],
    icon: 'Edit',
    description: 'Modify receiving line item quantity or details',
  },
  update_receiving: {
    action_name: 'update_receiving',
    label: 'Update Receiving Fields',
    cluster: 'procure_suppliers',
    side_effect_type: 'mutation_light',
    role_restricted: ['chief_engineer', 'chief_officer', 'chief_steward', 'purser', 'captain', 'manager'],
    icon: 'Edit',
    description: 'Update receiving header information',
  },
  attach_receiving_image_with_comment: {
    action_name: 'attach_receiving_image_with_comment',
    label: 'Attach Image',
    cluster: 'procure_suppliers',
    side_effect_type: 'mutation_light',
    role_restricted: ['chief_engineer', 'chief_officer', 'chief_steward', 'purser', 'captain', 'manager'],
    icon: 'Camera',
    description: 'Add photo documentation to receiving',
  },
  extract_receiving_candidates: {
    action_name: 'extract_receiving_candidates',
    label: 'Extract Line Items',
    cluster: 'procure_suppliers',
    side_effect_type: 'read_only',
    role_restricted: ['chief_engineer', 'chief_officer', 'chief_steward', 'purser', 'captain', 'manager'],
    icon: 'ScanText',
    description: 'Extract line items from attached invoice PDF',
  },
  accept_receiving: {
    action_name: 'accept_receiving',
    label: 'Accept',
    cluster: 'procure_suppliers',
    side_effect_type: 'mutation_heavy',
    requires_confirmation: true,
    role_restricted: ['chief_engineer', 'chief_officer', 'chief_steward', 'purser', 'captain', 'manager'],
    icon: 'CheckCircle',
    description: 'Accept receiving and finalize',
  },
  reject_receiving: {
    action_name: 'reject_receiving',
    label: 'Reject',
    cluster: 'procure_suppliers',
    side_effect_type: 'mutation_heavy',
    requires_confirmation: true,
    role_restricted: ['chief_engineer', 'chief_officer', 'chief_steward', 'purser', 'captain', 'manager'],
    icon: 'XCircle',
    description: 'Reject receiving and provide reason',
  },
  link_receiving_to_invoice: {
    action_name: 'link_receiving_to_invoice',
    label: 'Link Invoice PDF',
    cluster: 'procure_suppliers',
    side_effect_type: 'mutation_light',
    role_restricted: ['chief_engineer', 'chief_officer', 'chief_steward', 'purser', 'captain', 'manager'],
    icon: 'Link',
    description: 'Associate invoice PDF with receiving',
  },

  // OPERATIONAL CHECKLISTS
  view_checklist: {
    action_name: 'view_checklist',
    label: 'View Checklist',
    cluster: 'do_maintenance',
    side_effect_type: 'read_only',
    icon: 'ListChecks',
    description: 'Display operational checklist',
  },
  mark_checklist_item_complete: {
    action_name: 'mark_checklist_item_complete',
    label: 'Mark Complete',
    cluster: 'do_maintenance',
    side_effect_type: 'mutation_light',
    icon: 'CheckSquare',
    description: 'Tick off checklist item',
  },
  add_checklist_item: {
    action_name: 'add_checklist_item',
    label: 'Add Checklist Item',
    cluster: 'do_maintenance',
    side_effect_type: 'mutation_light',
    icon: 'ListPlus',
    description: 'Add new checklist item to work order',
  },
  add_checklist_note: {
    action_name: 'add_checklist_note',
    label: 'Add Note',
    cluster: 'do_maintenance',
    side_effect_type: 'mutation_light',
    icon: 'StickyNote',
    description: 'Add note to checklist item',
  },
  add_checklist_photo: {
    action_name: 'add_checklist_photo',
    label: 'Add Photo',
    cluster: 'do_maintenance',
    side_effect_type: 'mutation_light',
    icon: 'Camera',
    description: 'Attach photo to checklist item',
  },

  // SHIPYARD / REFIT
  view_worklist: {
    action_name: 'view_worklist',
    label: 'View Worklist',
    cluster: 'do_maintenance',
    side_effect_type: 'read_only',
    icon: 'ClipboardList',
    description: 'Display shipyard work items and snags',
  },
  add_worklist_task: {
    action_name: 'add_worklist_task',
    label: 'Add Task',
    cluster: 'do_maintenance',
    side_effect_type: 'mutation_heavy',
    icon: 'PlusCircle',
    description: 'Create new shipyard work item',
  },
  update_worklist_progress: {
    action_name: 'update_worklist_progress',
    label: 'Update Progress',
    cluster: 'do_maintenance',
    side_effect_type: 'mutation_light',
    icon: 'Edit',
    description: 'Update completion status of yard task',
  },
  export_worklist: {
    action_name: 'export_worklist',
    label: 'Export Worklist',
    cluster: 'do_maintenance',
    side_effect_type: 'read_only',
    icon: 'Download',
    description: 'Generate worklist document',
  },
  tag_for_survey: {
    action_name: 'tag_for_survey',
    label: 'Tag for Survey',
    cluster: 'comply_audit',
    side_effect_type: 'mutation_light',
    role_restricted: ['chief_engineer', 'captain'],
    icon: 'Flag',
    description: 'Flag item for class/flag survey prep',
  },

  // FLEET / MANAGEMENT
  view_fleet_summary: {
    action_name: 'view_fleet_summary',
    label: 'View Fleet',
    cluster: 'manage_equipment',
    side_effect_type: 'read_only',
    icon: 'Ship',
    description: 'Display multi-vessel overview',
  },
  open_vessel: {
    action_name: 'open_vessel',
    label: 'Open Vessel',
    cluster: 'manage_equipment',
    side_effect_type: 'read_only',
    icon: 'ExternalLink',
    description: 'Switch context to specific vessel',
  },
  export_fleet_summary: {
    action_name: 'export_fleet_summary',
    label: 'Export Summary',
    cluster: 'communicate_status',
    side_effect_type: 'read_only',
    icon: 'Download',
    description: 'Download fleet status report',
  },

  // PREDICTIVE / SMART SUMMARY
  request_predictive_insight: {
    action_name: 'request_predictive_insight',
    label: 'Predictive Insight',
    cluster: 'manage_equipment',
    side_effect_type: 'read_only',
    icon: 'TrendingUp',
    description: 'Request AI-driven maintenance predictions',
  },
  view_smart_summary: {
    action_name: 'view_smart_summary',
    label: 'View Summary',
    cluster: 'communicate_status',
    side_effect_type: 'read_only',
    icon: 'LayoutDashboard',
    description: 'Generate situational briefing (daily, pre-departure)',
  },

  // MOBILE-SPECIFIC
  upload_photo: {
    action_name: 'upload_photo',
    label: 'Upload Photo',
    cluster: 'communicate_status',
    side_effect_type: 'mutation_light',
    icon: 'Camera',
    description: 'Upload photo from mobile device',
  },
  record_voice_note: {
    action_name: 'record_voice_note',
    label: 'Voice Note',
    cluster: 'communicate_status',
    side_effect_type: 'mutation_light',
    icon: 'Mic',
    description: 'Record audio note and transcribe',
  },

  // EDIT ACTIONS - ADDENDUM
  edit_work_order_details: {
    action_name: 'edit_work_order_details',
    label: 'Edit Work Order',
    cluster: 'do_maintenance',
    side_effect_type: 'mutation_heavy',
    requires_confirmation: true,
    icon: 'Edit',
    description: 'Modify WO title, description, priority, due date',
  },
  edit_equipment_details: {
    action_name: 'edit_equipment_details',
    label: 'Edit Equipment',
    cluster: 'manage_equipment',
    side_effect_type: 'mutation_heavy',
    requires_confirmation: true,
    role_restricted: ['chief_engineer', 'manager'],
    icon: 'Edit',
    description: 'Update equipment info (serial, location, model)',
  },
  edit_part_details: {
    action_name: 'edit_part_details',
    label: 'Edit Part Info',
    cluster: 'control_inventory',
    side_effect_type: 'mutation_light',
    role_restricted: ['chief_engineer', 'manager'],
    icon: 'Edit',
    description: 'Update part details (location, min/max levels, supplier)',
  },
  edit_purchase_details: {
    action_name: 'edit_purchase_details',
    label: 'Edit Purchase',
    cluster: 'procure_suppliers',
    side_effect_type: 'mutation_heavy',
    requires_confirmation: true,
    icon: 'Edit',
    description: 'Modify PO items, quantities, supplier, delivery date',
  },
  edit_invoice_amount: {
    action_name: 'edit_invoice_amount',
    label: 'Edit Invoice Amount',
    cluster: 'procure_suppliers',
    side_effect_type: 'mutation_heavy',
    requires_confirmation: true,
    requires_reason: true,
    role_restricted: ['chief_engineer', 'captain', 'manager'],
    icon: 'DollarSign',
    description: 'Modify invoice total with required audit justification',
  },
  edit_fault_details: {
    action_name: 'edit_fault_details',
    label: 'Edit Fault',
    cluster: 'fix_something',
    side_effect_type: 'mutation_light',
    icon: 'Edit',
    description: 'Update fault description, resolution notes, severity',
  },
  edit_note: {
    action_name: 'edit_note',
    label: 'Edit Note',
    cluster: 'communicate_status',
    side_effect_type: 'mutation_light',
    icon: 'Edit',
    description: 'Modify existing note content (with edit history)',
  },
  delete_item: {
    action_name: 'delete_item',
    label: 'Delete Item',
    cluster: 'communicate_status',
    side_effect_type: 'mutation_heavy',
    requires_confirmation: true,
    icon: 'Trash2',
    description: 'Soft-delete item with audit trail',
  },
  approve_work_order: {
    action_name: 'approve_work_order',
    label: 'Approve Task',
    cluster: 'do_maintenance',
    side_effect_type: 'mutation_heavy',
    requires_confirmation: true,
    role_restricted: ['chief_engineer', 'captain'],
    icon: 'CheckCircle',
    description: 'HOD approval before WO execution (role-based)',
  },
  scan_equipment_barcode: {
    action_name: 'scan_equipment_barcode',
    label: 'Scan Equipment',
    cluster: 'manage_equipment',
    side_effect_type: 'read_only',
    icon: 'QrCode',
    description: 'QR/barcode lookup for equipment',
  },
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Get action metadata by action name
 */
export function getActionMetadata(action: MicroAction): ActionMetadata {
  return ACTION_REGISTRY[action];
}

/**
 * Get all actions for a specific card type
 */
export function getActionsForCard(cardType: CardType): MicroAction[] {
  // This would be populated from ACTION_OFFERING_MAP.md
  // For now, return placeholder
  return [];
}

/**
 * Check if action requires confirmation
 */
export function requiresConfirmation(action: MicroAction): boolean {
  return ACTION_REGISTRY[action].requires_confirmation || false;
}

/**
 * Check if action requires reason/justification
 */
export function requiresReason(action: MicroAction): boolean {
  return ACTION_REGISTRY[action].requires_reason || false;
}

/**
 * Check if user role can perform action
 */
export function canPerformAction(
  action: MicroAction,
  userRole: 'chief_engineer' | 'eto' | 'captain' | 'manager' | 'vendor' | 'crew' | 'deck' | 'interior'
): boolean {
  const metadata = ACTION_REGISTRY[action];
  if (!metadata.role_restricted) return true;
  return metadata.role_restricted.includes(userRole as any);
}
