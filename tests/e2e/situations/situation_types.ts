/**
 * CelesteOS Situation Type Definitions
 *
 * Canonical list of all 9 situation types with their allowed actions,
 * states, and UX contracts based on situation policy specs.
 */

export type SituationState = 'IDLE' | 'CANDIDATE' | 'ACTIVE' | 'COOLDOWN' | 'RESOLVED';

export type ActionBracket = 'READ' | 'WRITE-NOTE' | 'WRITE-STATE' | 'WRITE-COMMS' | 'WRITE-FINANCIAL';

export interface SituationType {
  id: string;
  name: string;
  entityType: string;
  states: SituationState[];
  allowedBrackets: ActionBracket[];
  entryTriggers: string[];
  activationTriggers: string[];
  resolutionTriggers: string[];
  uxContract: {
    bannerRequired: boolean;
    actionsLocation: 'top' | 'bottom' | 'both';
    signatureRequired: boolean;
    previewRequired: boolean;
  };
  associatedActions: string[];
}

/**
 * All 9 Situation Types
 */
export const SITUATION_TYPES: SituationType[] = [
  // 1. WORK ORDER SITUATION
  {
    id: 'work_order',
    name: 'Work Order Situation',
    entityType: 'work_order',
    states: ['IDLE', 'CANDIDATE', 'ACTIVE', 'COOLDOWN', 'RESOLVED'],
    allowedBrackets: ['READ', 'WRITE-NOTE', 'WRITE-STATE', 'WRITE-COMMS'],
    entryTriggers: ['open_work_order', 'navigate_from_search'],
    activationTriggers: ['add_note', 'attach_photo', 'change_status', 'log_time', 'link_inventory'],
    resolutionTriggers: ['mark_as_done_signed'],
    uxContract: {
      bannerRequired: true,
      actionsLocation: 'both', // capture at top, completion at bottom
      signatureRequired: true,
      previewRequired: true,
    },
    associatedActions: [
      'create_work_order',
      'update_work_order',
      'close_work_order',
      'add_wo_note',
      'add_wo_part',
      'add_wo_photo',
      'assign_work_order',
      'log_work_order_time',
    ],
  },

  // 2. INVENTORY SITUATION
  {
    id: 'inventory',
    name: 'Inventory Situation',
    entityType: 'part',
    states: ['IDLE', 'CANDIDATE', 'ACTIVE', 'COOLDOWN', 'RESOLVED'],
    allowedBrackets: ['READ', 'WRITE-NOTE', 'WRITE-STATE', 'WRITE-COMMS'],
    entryTriggers: ['view_part', 'open_container', 'expand_inventory_table'],
    activationTriggers: ['part_opened_twice', 'deduct_used', 'log_usage'],
    resolutionTriggers: ['usage_event_signed'],
    uxContract: {
      bannerRequired: false,
      actionsLocation: 'bottom',
      signatureRequired: true,
      previewRequired: true,
    },
    associatedActions: [
      'adjust_inventory',
      'add_inventory_item',
      'update_inventory_item',
      'log_inventory_usage',
      'view_stock_levels',
      'reorder_part',
    ],
  },

  // 3. DOCUMENT SITUATION
  {
    id: 'document',
    name: 'Document Situation',
    entityType: 'document',
    states: ['IDLE', 'CANDIDATE'],
    allowedBrackets: ['READ', 'WRITE-NOTE'],
    entryTriggers: ['open_document'],
    activationTriggers: [], // Document view is strictly read-only
    resolutionTriggers: ['exit_document'],
    uxContract: {
      bannerRequired: false,
      actionsLocation: 'top',
      signatureRequired: false,
      previewRequired: false,
    },
    associatedActions: [
      'upload_document',
      'process_document_chunks',
      'delete_document',
      'search_document_content',
    ],
  },

  // 4. HOURS OF REST SITUATION
  {
    id: 'hours_of_rest',
    name: 'Hours of Rest Situation',
    entityType: 'hor_record',
    states: ['IDLE', 'CANDIDATE', 'ACTIVE', 'RESOLVED'], // No COOLDOWN for HOR
    allowedBrackets: ['READ', 'WRITE-STATE'],
    entryTriggers: ['open_hor_ledger'],
    activationTriggers: ['edit_daily_entry'],
    resolutionTriggers: ['weekly_endorsement_signed', 'monthly_countersign'],
    uxContract: {
      bannerRequired: true,
      actionsLocation: 'bottom',
      signatureRequired: true,
      previewRequired: true,
    },
    associatedActions: [
      'submit_hor_entry',
      'edit_hor_entry',
      'endorse_hor_week',
      'countersign_hor_month',
    ],
  },

  // 5. SEARCH BAR SITUATION (Passive - No Actions)
  {
    id: 'search',
    name: 'Search Bar Situation',
    entityType: 'search_query',
    states: ['IDLE'], // Search never goes beyond IDLE
    allowedBrackets: ['READ'],
    entryTriggers: ['type_in_search'],
    activationTriggers: [], // Search NEVER activates
    resolutionTriggers: ['click_result'], // Click exits search, creates new situation
    uxContract: {
      bannerRequired: false,
      actionsLocation: 'top',
      signatureRequired: false,
      previewRequired: false,
    },
    associatedActions: [
      'search_documents',
      'search_equipment',
      'search_parts',
    ],
  },

  // 6. EQUIPMENT/MAINTENANCE SITUATION
  {
    id: 'equipment',
    name: 'Equipment Situation',
    entityType: 'equipment',
    states: ['IDLE', 'CANDIDATE', 'ACTIVE', 'COOLDOWN', 'RESOLVED'],
    allowedBrackets: ['READ', 'WRITE-NOTE', 'WRITE-STATE', 'WRITE-COMMS'],
    entryTriggers: ['open_equipment', 'report_symptom'],
    activationTriggers: ['create_wo_draft', 'report_fault', 'view_manual'],
    resolutionTriggers: ['fault_resolved', 'wo_completed'],
    uxContract: {
      bannerRequired: true,
      actionsLocation: 'both',
      signatureRequired: true, // WRITE-STATE requires signature
      previewRequired: true,
    },
    associatedActions: [
      'add_equipment',
      'update_equipment',
      'view_equipment_history',
      'report_fault',
      'acknowledge_fault',
      'diagnose_fault',
      'resolve_fault',
      'create_work_order_from_fault',
    ],
  },

  // 7. HANDOVER SITUATION
  {
    id: 'handover',
    name: 'Handover Situation',
    entityType: 'handover_item',
    states: ['IDLE', 'CANDIDATE', 'ACTIVE', 'RESOLVED'],
    allowedBrackets: ['READ', 'WRITE-NOTE', 'WRITE-STATE'],
    entryTriggers: ['open_handover_list', 'create_handover'],
    activationTriggers: ['add_handover_item', 'edit_handover'],
    resolutionTriggers: ['acknowledge_handover'],
    uxContract: {
      bannerRequired: true,
      actionsLocation: 'bottom',
      signatureRequired: true,
      previewRequired: true,
    },
    associatedActions: [
      'create_handover',
      'acknowledge_handover',
      'update_handover',
      'delete_handover',
      'filter_handover',
    ],
  },

  // 8. COMPLIANCE SITUATION
  {
    id: 'compliance',
    name: 'Compliance Situation',
    entityType: 'certificate',
    states: ['IDLE', 'CANDIDATE', 'ACTIVE', 'RESOLVED'],
    allowedBrackets: ['READ', 'WRITE-STATE'],
    entryTriggers: ['open_certificate', 'view_compliance_dashboard'],
    activationTriggers: ['renew_certificate', 'add_certificate'],
    resolutionTriggers: ['certificate_verified'],
    uxContract: {
      bannerRequired: true,
      actionsLocation: 'bottom',
      signatureRequired: true,
      previewRequired: true,
    },
    associatedActions: [
      'add_certificate',
      'renew_certificate',
      'update_certificate',
      'add_service_contract',
      'record_contract_claim',
    ],
  },

  // 9. PURCHASING SITUATION
  {
    id: 'purchasing',
    name: 'Purchasing Situation',
    entityType: 'purchase_order',
    states: ['IDLE', 'CANDIDATE', 'ACTIVE', 'COOLDOWN', 'RESOLVED'],
    allowedBrackets: ['READ', 'WRITE-NOTE', 'WRITE-STATE', 'WRITE-FINANCIAL'],
    entryTriggers: ['open_shopping_list', 'create_po'],
    activationTriggers: ['add_to_cart', 'approve_item', 'create_po'],
    resolutionTriggers: ['po_received', 'receiving_committed'],
    uxContract: {
      bannerRequired: true,
      actionsLocation: 'both',
      signatureRequired: true,
      previewRequired: true,
    },
    associatedActions: [
      'add_to_shopping_list',
      'approve_shopping_item',
      'reject_shopping_item',
      'delete_shopping_item',
      'update_shopping_list',
      'create_purchase_order',
      'update_purchase_order',
      'close_purchase_order',
      'start_receiving_session',
      'check_in_item',
      'commit_receiving_session',
      'upload_discrepancy_photo',
      'add_receiving_notes',
    ],
  },
];

/**
 * Get situation by ID
 */
export function getSituation(id: string): SituationType | undefined {
  return SITUATION_TYPES.find(s => s.id === id);
}

/**
 * Get all actions for a situation
 */
export function getActionsForSituation(situationId: string): string[] {
  const situation = getSituation(situationId);
  return situation?.associatedActions || [];
}

/**
 * Get all situation IDs
 */
export function getAllSituationIds(): string[] {
  return SITUATION_TYPES.map(s => s.id);
}
