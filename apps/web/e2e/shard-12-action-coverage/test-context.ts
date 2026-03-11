/**
 * Test Context - Real Entity IDs from Lens Exports
 *
 * These are REAL entity IDs extracted from lens CSV exports.
 * Using real IDs ensures actions have valid targets and proper
 * state for testing.
 *
 * Generated from: e2e/shard-12-action-coverage/real-lens-ids.json
 * Source: /Users/celeste7/Downloads/New Folder With Items/*.csv
 * Test Yacht: 85fe1119-b04c-41ac-80f1-829d23322598
 */

// =============================================================================
// REAL ENTITY IDs FROM LENS EXPORTS
// =============================================================================

/**
 * Equipment IDs - existing equipment in test yacht
 * Note: Equipment was in inventory.csv lens export
 */
export const EQUIPMENT_IDS = {
  // Equipment in maintenance status - good for status change tests
  MAINTENANCE: '8e91e289-a156-444c-b315-88c0a06c9492',
  // Equipment in operational status
  OPERATIONAL_1: '04c518e6-c61f-42fe-a7b2-4cd69a0505ce',
  OPERATIONAL_2: '23f5532b-03bb-49f9-abed-9121bb214c08',
};

/**
 * Work Order IDs - from work_order.csv lens export
 * Status: draft, planned, in_progress, completed, cancelled
 */
export const WORK_ORDER_IDS = {
  // Draft work orders - good for start tests
  DRAFT_1: '19de511d-727c-48da-bbad-ef2691595531',
  DRAFT_2: '1af54ee4-d90c-450e-9687-039ed7128068',
  // Planned work orders - good for update tests
  PLANNED: '30ec33c7-48f4-4047-b32d-eacd602e74d6',
  // Completed work orders
  COMPLETED_1: '2531d846-5753-4faa-a549-20a6dc2ade73',
  COMPLETED_2: 'b507e262-bdcf-4a59-971b-e5c8ff2707f6',
};

/**
 * Fault IDs - from fault.csv lens export
 * Status: open, closed
 */
export const FAULT_IDS = {
  // Faults in open status - good for acknowledge/diagnose/close tests
  OPEN_1: '29c6f2d0-69c2-4263-87ad-7ab56d5f9ab9',
  OPEN_2: '29c81ea1-f067-442b-b4a1-05c4ec2b84b9',
  // Additional open faults from audit
  OPEN_3: 'e9f058f8-4814-4228-aba4-7e66f9cb3430',
};

/**
 * Part IDs - from parts.csv lens export
 */
export const PART_IDS = {
  PART_1: '5dd34337-c4c4-41dd-9c6b-adf84af349a8',
  PART_2: '2f452e3b-bf3e-464e-82d5-7d0bc849e6c0',
  PART_3: '5543266b-2d8c-46a0-88e2-74a7ab403cdd',
  PART_4: 'f7913ad1-6832-4169-b816-4538c8b7a417',
  PART_5: '19770833-a0b7-42a1-a6a7-8d5316a1db3d',
  // Aliases for backwards compatibility
  FUEL_FILTER: 'f7913ad1-6832-4169-b816-4538c8b7a417',
  PUMP_SEAL_KIT: '2f452e3b-bf3e-464e-82d5-7d0bc849e6c0',
  ORING_KIT: '5543266b-2d8c-46a0-88e2-74a7ab403cdd',
};

/**
 * Certificate IDs - from certificate.csv lens export
 * Status: active (valid), superseded, expired
 */
export const CERTIFICATE_IDS = {
  // Active certificates
  ACTIVE_1: '486bc333-492d-4cc4-a1dc-31391785838a',
  ACTIVE_2: '4334eaad-50bb-451f-962a-e99220852545',
  ACTIVE_3: 'e95036e5-3fcc-4ceb-9ebe-67a9e2ce69d8',
  ACTIVE_4: 'ea02d9e6-4c0e-4ba3-9dcf-87a09e3c0f5b',
  ACTIVE_5: 'b0f191f6-d0ab-4433-8bc9-0a0b0bcbdbfc',
  // Aliases for backwards compatibility
  DNV_GL: '486bc333-492d-4cc4-a1dc-31391785838a',
  LLOYDS: '4334eaad-50bb-451f-962a-e99220852545',
  ABS: 'e95036e5-3fcc-4ceb-9ebe-67a9e2ce69d8',
};

/**
 * Document IDs - from document.csv lens export
 * NOW AVAILABLE from lens exports!
 */
export const DOCUMENT_IDS = {
  DOC_1: '9c16cf55-e5f8-449b-b86f-08658e2914b5',
  DOC_2: '5633f722-c425-4abd-85c9-0bb9af7fa541',
  DOC_3: '25287ff9-7839-441f-bfa3-30808a6e7509',
  DOC_4: 'a39b99e4-eb07-49af-b0fb-e72e1b6a8918',
  DOC_5: 'e7aba7f7-93b1-4223-bf14-c2b870542db4',
};

/**
 * Receiving IDs - from receiving.csv lens export
 * Status: draft, in_progress, completed, accepted
 */
export const RECEIVING_IDS = {
  // Receiving in draft status - good for start/update tests
  DRAFT_1: '0fa6556b-b9ef-49d2-979d-30e0f0d15c0f',
  // Additional receiving records
  DRAFT_2: 'db7f455b-192e-4c7d-b502-c329308dac79',
  ACCEPTED: '5374631e-3e7c-4388-b666-8de8883e8460',
};

/**
 * Shopping List Item IDs - from shopping_list.csv lens export
 * Status: pending, approved, ordered, received
 */
export const SHOPPING_LIST_IDS = {
  // Pending items - good for approve/reject tests
  PENDING_1: '386121a0-1956-44af-b662-0274680024c2',
  // Approved items
  APPROVED_1: '693eae41-0873-4de5-85e9-f5c659d47863',
  APPROVED_2: '94d00427-4642-487e-b824-34d775494493',
  APPROVED_3: '317f4092-3e37-4402-975e-090703f1273d',
};

/**
 * Configuration - test yacht and API
 */
export const TEST_CONFIG = {
  yachtId: '85fe1119-b04c-41ac-80f1-829d23322598',
  apiBaseUrl: 'http://localhost:8001',
};

// =============================================================================
// CONTEXT BUILDER - Maps contextKey to real IDs
// =============================================================================

/**
 * Get context object for an action based on its contextKey
 *
 * @param contextKey - The key indicating what entity ID is needed
 * @returns Record with the entity ID mapped to the correct key
 *
 * @example
 * ```ts
 * const context = getContext('equipment_id');
 * // Returns: { equipment_id: '8e91e289-...', yacht_id: '85fe1119-...' }
 * ```
 */
export function getContext(contextKey?: string): Record<string, string> {
  const base = { yacht_id: TEST_CONFIG.yachtId };

  if (!contextKey) return base;

  switch (contextKey) {
    case 'equipment_id':
      return { ...base, equipment_id: EQUIPMENT_IDS.OPERATIONAL_1 };

    case 'work_order_id':
      return { ...base, work_order_id: WORK_ORDER_IDS.PLANNED };

    case 'fault_id':
      return { ...base, fault_id: FAULT_IDS.OPEN_1 };

    case 'part_id':
      return { ...base, part_id: PART_IDS.FUEL_FILTER };

    case 'certificate_id':
      return { ...base, certificate_id: CERTIFICATE_IDS.DNV_GL };

    case 'receiving_id':
      return { ...base, receiving_id: RECEIVING_IDS.DRAFT_1 };

    case 'item_id':
      // Shopping list items exist with approved status
      return { ...base, item_id: SHOPPING_LIST_IDS.APPROVED_1 };

    case 'document_id':
      // Documents NOW AVAILABLE from lens exports!
      return { ...base, document_id: DOCUMENT_IDS.DOC_1 };

    case 'handover_id':
      // Handover records need to be created - skip for now
      return { ...base, handover_id: 'skip-no-handover' };

    case 'record_id':
      // Hours of Rest records - skip
      return { ...base, record_id: 'skip-no-hor-record' };

    case 'warning_id':
      // HoR warnings - skip
      return { ...base, warning_id: 'skip-no-warning' };

    case 'signoff_id':
      // HoR signoffs - skip
      return { ...base, signoff_id: 'skip-no-signoff' };

    case 'template_id':
      // HoR templates - skip
      return { ...base, template_id: 'skip-no-template' };

    case 'warranty_id':
      // Warranty claims - skip
      return { ...base, warranty_id: 'skip-no-warranty' };

    case 'worklist_id':
      // Worklist records - skip
      return { ...base, worklist_id: 'skip-no-worklist' };

    default:
      console.warn(`Unknown contextKey: ${contextKey}`);
      return base;
  }
}

/**
 * Check if a context key has real data available
 * Updated with REAL lens exports - document_id NOW AVAILABLE!
 */
export function hasRealData(contextKey?: string): boolean {
  if (!contextKey) return true;

  const realDataKeys = [
    'equipment_id',
    'work_order_id',
    'fault_id',
    'part_id',
    'certificate_id',
    'receiving_id',
    'item_id',        // Shopping list items exist
    'document_id',    // Documents NOW AVAILABLE from lens!
  ];

  return realDataKeys.includes(contextKey);
}

/**
 * Get the skip reason for a context key without real data
 * NOTE: document_id REMOVED - we now have real documents from lens!
 */
export function getSkipReason(contextKey?: string): string | undefined {
  if (!contextKey || hasRealData(contextKey)) return undefined;

  const reasons: Record<string, string> = {
    // document_id: REMOVED - we now have real documents!
    handover_id: 'No handover records in test yacht',
    record_id: 'No HoR records in test yacht',
    warning_id: 'No HoR warnings in test yacht',
    signoff_id: 'No HoR signoffs in test yacht',
    template_id: 'No HoR templates in test yacht',
    warranty_id: 'No warranty claims in test yacht',
    worklist_id: 'No worklist records in test yacht',
  };

  return reasons[contextKey] || `Unknown context: ${contextKey}`;
}

// =============================================================================
// SPECIAL CASES - Actions that need more than just an entity ID
// =============================================================================

/**
 * Actions that require a parent entity ID in addition to contextKey
 */
export const PARENT_REQUIREMENTS: Record<string, { key: string; value: string }> = {
  // link_part_to_equipment needs both equipment_id AND part_id
  link_part_to_equipment: { key: 'part_id', value: PART_IDS.FUEL_FILTER },

  // add_part_to_work_order needs both work_order_id AND part_id
  add_part_to_work_order: { key: 'part_id', value: PART_IDS.FUEL_FILTER },

  // assign_work_order needs assignee_id (use a real user)
  assign_work_order: { key: 'assignee_id', value: '4fa92437-3d17-4471-a5e7-eee33ffa0563' },

  // assign_parent_equipment needs parent_equipment_id
  assign_parent_equipment: { key: 'parent_equipment_id', value: EQUIPMENT_IDS.OPERATIONAL_2 },

  // add_entity_link needs entity_id
  add_entity_link: { key: 'entity_id', value: FAULT_IDS.OPEN_1 },

  // link_document_to_certificate needs document_id - NOW AVAILABLE!
  link_document_to_certificate: { key: 'document_id', value: DOCUMENT_IDS.DOC_1 },

  // link_invoice_document needs document_id - NOW AVAILABLE!
  link_invoice_document: { key: 'document_id', value: DOCUMENT_IDS.DOC_2 },

  // report_fault needs equipment_id
  report_fault: { key: 'equipment_id', value: EQUIPMENT_IDS.OPERATIONAL_1 },

  // create_work_order_for_equipment already has equipment_id from context
  // but also needs valid work order data
};

/**
 * Get enriched context for actions with parent requirements
 */
export function getEnrichedContext(
  action: string,
  contextKey?: string
): Record<string, string> {
  const base = getContext(contextKey);

  if (PARENT_REQUIREMENTS[action]) {
    const req = PARENT_REQUIREMENTS[action];
    base[req.key] = req.value;
  }

  return base;
}

// =============================================================================
// STATE MACHINE HELPERS - For actions that require specific states
// =============================================================================

/**
 * Actions that require entities in specific states
 */
export const STATE_REQUIREMENTS: Record<string, string> = {
  // Work order state transitions
  start_work_order: 'Needs draft work order',
  mark_work_order_complete: 'Needs in-progress work order',
  cancel_work_order: 'Needs non-cancelled work order',
  archive_work_order: 'Needs completed work order',

  // Fault state transitions
  acknowledge_fault: 'Needs unacknowledged fault',
  close_fault: 'Needs open fault',
  reopen_fault: 'Needs closed fault',
  mark_fault_false_alarm: 'Needs open fault',

  // Equipment state transitions
  decommission_equipment: 'Needs non-decommissioned equipment',
  archive_equipment: 'Needs non-archived equipment',
  restore_archived_equipment: 'Needs archived equipment',

  // Receiving state transitions
  start_receiving_event: 'Needs draft receiving',
  complete_receiving_event: 'Needs in-progress receiving',
  accept_receiving: 'Needs completed receiving',

  // Certificate state transitions
  supersede_certificate: 'Needs certificate and replacement certificate',
};

/**
 * Check if action requires specific entity state
 */
export function requiresSpecificState(action: string): boolean {
  return action in STATE_REQUIREMENTS;
}
