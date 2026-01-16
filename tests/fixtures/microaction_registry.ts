/**
 * MICROACTION REGISTRY - Machine-Readable Test Fixture
 *
 * Sources:
 * - /Users/celeste7/Desktop/Cloud_PMS_docs_v2/03_MICROACTIONS/MICRO_ACTION_REGISTRY.md
 * - /Users/celeste7/Desktop/Cloud_PMS_docs_v2/03_MICROACTIONS/ACTION_OFFERING_RULES.md
 * - /Users/celeste7/Desktop/Cloud_PMS_docs_v2/COMPLETE_ACTION_EXECUTION_CATALOG.md
 *
 * Purpose: Enable automated verification of all 57 microactions
 */

// ============================================================================
// TYPES
// ============================================================================

export type Cluster =
  | 'fix_something'
  | 'do_maintenance'
  | 'manage_equipment'
  | 'control_inventory'
  | 'communicate_status'
  | 'comply_audit'
  | 'procure_suppliers';

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

export type SideEffectType = 'read_only' | 'mutation_light' | 'mutation_heavy';

export type Role = 'member' | 'crew' | 'engineer' | '2nd_engineer' | 'eto' | 'chief_engineer' | 'chief_officer' | 'captain' | 'manager' | 'admin';

export type EntityStatus = string; // e.g., 'open', 'diagnosed', 'in_progress', etc.

export interface TriggerCondition {
  /** Entity statuses that enable this action */
  status?: EntityStatus[];
  /** Roles allowed to see/execute this action. 'any' means all roles */
  roles: Role[] | 'any';
  /** Additional boolean conditions */
  conditions?: {
    /** Condition name/description */
    name: string;
    /** How to evaluate: 'entity_field', 'related_query', 'user_context' */
    type: 'entity_field' | 'related_query' | 'user_context';
    /** Field or query to check */
    check: string;
    /** Expected value or comparison */
    expected: any;
  }[];
  /** Auto-execute when card appears (no button click needed) */
  autoRun?: boolean;
}

export interface RequiredField {
  name: string;
  type: 'string' | 'uuid' | 'number' | 'boolean' | 'array' | 'date' | 'file';
  /** Validation constraints */
  constraints?: {
    minLength?: number;
    maxLength?: number;
    min?: number;
    max?: number;
    pattern?: string;
    enum?: string[];
    required?: boolean;
  };
  /** Source for prefilling */
  prefillFrom?: string;
}

export interface ExpectedDatabaseChange {
  table: string;
  operation: 'INSERT' | 'UPDATE' | 'DELETE';
  columns?: string[];
  /** Field that changes and its expected value */
  expectedValue?: {
    field: string;
    value: any;
  };
}

export interface EdgeCase {
  name: string;
  description: string;
  payload: Record<string, any>;
  expectedStatus: number;
  expectedError?: string;
}

export interface Microaction {
  /** Unique action identifier */
  id: string;
  /** Human-readable label for UI */
  label: string;
  /** Purpose cluster */
  cluster: Cluster;
  /** Card types where this action appears */
  cardTypes: CardType[];
  /** Side effect classification */
  sideEffectType: SideEffectType;
  /** When to show this action */
  triggers: TriggerCondition;
  /** API endpoint */
  endpoint: string;
  /** Required input fields */
  requiredFields: RequiredField[];
  /** Optional input fields */
  optionalFields?: RequiredField[];
  /** Expected database changes */
  expectedChanges: ExpectedDatabaseChange[];
  /** Known edge cases for testing */
  edgeCases?: EdgeCase[];
  /** Short description */
  description: string;
}

// ============================================================================
// HOD ROLES (Head of Department)
// ============================================================================

export const HOD_ROLES: Role[] = ['chief_engineer', 'eto', 'captain', 'manager', 'admin'];
export const ENGINEER_ROLES: Role[] = ['engineer', '2nd_engineer', 'chief_engineer', 'eto'];
export const ALL_ROLES: Role[] = ['member', 'crew', 'engineer', '2nd_engineer', 'eto', 'chief_engineer', 'chief_officer', 'captain', 'manager', 'admin'];

// ============================================================================
// CLUSTER 1: FIX_SOMETHING (7 actions)
// ============================================================================

const FIX_SOMETHING_ACTIONS: Microaction[] = [
  {
    id: 'diagnose_fault',
    label: 'Diagnose Fault',
    cluster: 'fix_something',
    cardTypes: ['fault'],
    sideEffectType: 'read_only',
    triggers: {
      status: ['reported', 'acknowledged', 'open'],
      roles: 'any',
      autoRun: true, // Auto-runs when fault card appears
    },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'fault_id', type: 'uuid', constraints: { required: true } },
    ],
    optionalFields: [
      { name: 'diagnosis_text', type: 'string', constraints: { minLength: 20 } },
    ],
    expectedChanges: [
      { table: 'faults', operation: 'UPDATE', columns: ['status', 'diagnosis', 'diagnosed_at'], expectedValue: { field: 'status', value: 'diagnosed' } },
      { table: 'audit_log', operation: 'INSERT' },
    ],
    edgeCases: [
      { name: 'already_diagnosed', description: 'Fault already diagnosed', payload: { fault_id: 'already-diagnosed-id' }, expectedStatus: 400, expectedError: 'already diagnosed' },
      { name: 'invalid_fault_id', description: 'Non-existent fault', payload: { fault_id: 'non-existent-id' }, expectedStatus: 404, expectedError: 'not found' },
    ],
    description: 'Analyze fault code and provide diagnostic guidance',
  },
  {
    id: 'show_manual_section',
    label: 'View Manual',
    cluster: 'fix_something',
    cardTypes: ['fault', 'equipment', 'work_order'],
    sideEffectType: 'read_only',
    triggers: {
      roles: 'any',
      conditions: [{ name: 'equipment_identified', type: 'entity_field', check: 'equipment_id', expected: 'not_null' }],
    },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'equipment_id', type: 'uuid', constraints: { required: true } },
    ],
    optionalFields: [
      { name: 'section_query', type: 'string' },
      { name: 'fault_code', type: 'string' },
    ],
    expectedChanges: [], // Read-only, no DB changes
    description: 'Open relevant manual section for current context',
  },
  {
    id: 'view_fault_history',
    label: 'View History',
    cluster: 'fix_something',
    cardTypes: ['fault', 'equipment'],
    sideEffectType: 'read_only',
    triggers: {
      roles: 'any',
    },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'equipment_id', type: 'uuid', constraints: { required: true } },
    ],
    optionalFields: [
      { name: 'fault_type', type: 'string' },
      { name: 'date_range', type: 'string' },
    ],
    expectedChanges: [],
    description: 'Show historical occurrences of similar faults',
  },
  {
    id: 'suggest_parts',
    label: 'Suggest Parts',
    cluster: 'fix_something',
    cardTypes: ['fault'],
    sideEffectType: 'read_only',
    triggers: {
      status: ['diagnosed'],
      roles: 'any',
      conditions: [{ name: 'fault_is_known', type: 'entity_field', check: 'ai_diagnosis.is_known', expected: true }],
    },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'fault_id', type: 'uuid', constraints: { required: true } },
    ],
    expectedChanges: [],
    edgeCases: [
      { name: 'unknown_fault', description: 'Fault not in known database', payload: { fault_id: 'unknown-fault-id' }, expectedStatus: 200, expectedError: undefined }, // Returns empty suggestions
    ],
    description: 'Recommend likely parts needed for this fault',
  },
  {
    id: 'create_work_order_from_fault',
    label: 'Create Work Order',
    cluster: 'fix_something',
    cardTypes: ['fault'],
    sideEffectType: 'mutation_heavy',
    triggers: {
      status: ['diagnosed', 'acknowledged', 'open'],
      roles: HOD_ROLES,
    },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'fault_id', type: 'uuid', constraints: { required: true } },
      { name: 'title', type: 'string', constraints: { minLength: 5, required: true } },
      { name: 'description', type: 'string', constraints: { minLength: 10, required: true } },
    ],
    optionalFields: [
      { name: 'priority', type: 'string', constraints: { enum: ['low', 'normal', 'high', 'critical'] } },
      { name: 'estimated_hours', type: 'number', constraints: { min: 0 } },
      { name: 'parts', type: 'array' },
    ],
    expectedChanges: [
      { table: 'pms_work_orders', operation: 'INSERT' },
      { table: 'faults', operation: 'UPDATE', expectedValue: { field: 'status', value: 'work_created' } },
      { table: 'audit_log', operation: 'INSERT' },
    ],
    edgeCases: [
      { name: 'fault_not_diagnosed', description: 'Fault not diagnosed yet', payload: { fault_id: 'undiagnosed-fault' }, expectedStatus: 400, expectedError: 'must be diagnosed' },
      { name: 'wo_already_exists', description: 'WO already created for fault', payload: { fault_id: 'fault-with-wo' }, expectedStatus: 409, expectedError: 'already exists' },
    ],
    description: 'Generate work order pre-filled from fault context',
  },
  {
    id: 'add_fault_note',
    label: 'Add Note',
    cluster: 'fix_something',
    cardTypes: ['fault'],
    sideEffectType: 'mutation_light',
    triggers: {
      roles: 'any',
    },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'fault_id', type: 'uuid', constraints: { required: true } },
      { name: 'note_text', type: 'string', constraints: { minLength: 1, required: true } },
    ],
    expectedChanges: [
      { table: 'fault_notes', operation: 'INSERT' },
      { table: 'audit_log', operation: 'INSERT' },
    ],
    description: 'Attach observation or comment to fault record',
  },
  {
    id: 'add_fault_photo',
    label: 'Add Photo',
    cluster: 'fix_something',
    cardTypes: ['fault'],
    sideEffectType: 'mutation_light',
    triggers: {
      roles: 'any',
    },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'fault_id', type: 'uuid', constraints: { required: true } },
      { name: 'photo', type: 'file', constraints: { required: true } },
    ],
    optionalFields: [
      { name: 'caption', type: 'string' },
    ],
    expectedChanges: [
      { table: 'attachments', operation: 'INSERT' },
      { table: 'faults', operation: 'UPDATE', columns: ['photo_urls'] },
    ],
    description: 'Upload photo evidence of fault condition',
  },
];

// ============================================================================
// CLUSTER 2: DO_MAINTENANCE (16 actions)
// ============================================================================

const DO_MAINTENANCE_ACTIONS: Microaction[] = [
  {
    id: 'create_work_order',
    label: 'Create Work Order',
    cluster: 'do_maintenance',
    cardTypes: ['smart_summary', 'equipment'],
    sideEffectType: 'mutation_heavy',
    triggers: {
      roles: ENGINEER_ROLES,
    },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'equipment_id', type: 'uuid', constraints: { required: true } },
      { name: 'title', type: 'string', constraints: { minLength: 5, required: true } },
      { name: 'description', type: 'string', constraints: { minLength: 10, required: true } },
    ],
    optionalFields: [
      { name: 'priority', type: 'string', constraints: { enum: ['low', 'normal', 'high', 'critical'] } },
      { name: 'estimated_hours', type: 'number' },
      { name: 'due_date', type: 'date' },
    ],
    expectedChanges: [
      { table: 'pms_work_orders', operation: 'INSERT' },
      { table: 'audit_log', operation: 'INSERT' },
    ],
    description: 'Create new work order with manual equipment selection',
  },
  {
    id: 'view_work_order_history',
    label: 'View History',
    cluster: 'do_maintenance',
    cardTypes: ['work_order', 'equipment'],
    sideEffectType: 'read_only',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'equipment_id', type: 'uuid', constraints: { required: true } },
    ],
    expectedChanges: [],
    description: 'Show completion history for this work order type',
  },
  {
    id: 'mark_work_order_complete',
    label: 'Mark Done',
    cluster: 'do_maintenance',
    cardTypes: ['work_order'],
    sideEffectType: 'mutation_heavy',
    triggers: {
      status: ['open', 'in_progress'],
      roles: ENGINEER_ROLES,
    },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'work_order_id', type: 'uuid', constraints: { required: true } },
    ],
    optionalFields: [
      { name: 'completion_notes', type: 'string' },
      { name: 'actual_hours', type: 'number' },
    ],
    expectedChanges: [
      { table: 'pms_work_orders', operation: 'UPDATE', expectedValue: { field: 'status', value: 'completed' } },
      { table: 'audit_log', operation: 'INSERT' },
    ],
    edgeCases: [
      { name: 'already_completed', description: 'WO already completed', payload: { work_order_id: 'completed-wo' }, expectedStatus: 400, expectedError: 'already completed' },
      { name: 'cancelled_wo', description: 'WO is cancelled', payload: { work_order_id: 'cancelled-wo' }, expectedStatus: 400, expectedError: 'cannot complete cancelled' },
    ],
    description: 'Close work order and log completion',
  },
  {
    id: 'add_work_order_note',
    label: 'Add Note',
    cluster: 'do_maintenance',
    cardTypes: ['work_order'],
    sideEffectType: 'mutation_light',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'work_order_id', type: 'uuid', constraints: { required: true } },
      { name: 'note_text', type: 'string', constraints: { minLength: 1, required: true } },
    ],
    expectedChanges: [
      { table: 'work_order_notes', operation: 'INSERT' },
    ],
    description: 'Add progress note or findings to work order',
  },
  {
    id: 'add_work_order_photo',
    label: 'Add Photo',
    cluster: 'do_maintenance',
    cardTypes: ['work_order'],
    sideEffectType: 'mutation_light',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'work_order_id', type: 'uuid', constraints: { required: true } },
      { name: 'photo', type: 'file', constraints: { required: true } },
    ],
    expectedChanges: [
      { table: 'attachments', operation: 'INSERT' },
    ],
    description: 'Attach photo to work order (before/after, evidence)',
  },
  {
    id: 'add_parts_to_work_order',
    label: 'Add Parts',
    cluster: 'do_maintenance',
    cardTypes: ['work_order'],
    sideEffectType: 'mutation_light',
    triggers: {
      status: ['open', 'in_progress'],
      roles: ENGINEER_ROLES,
    },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'work_order_id', type: 'uuid', constraints: { required: true } },
      { name: 'parts', type: 'array', constraints: { required: true } }, // [{part_id, quantity}]
    ],
    expectedChanges: [
      { table: 'work_order_parts', operation: 'INSERT' },
      { table: 'pms_parts', operation: 'UPDATE', columns: ['current_quantity_onboard'] },
    ],
    description: 'Link consumed parts to this work order',
  },
  {
    id: 'view_work_order_checklist',
    label: 'Show Checklist',
    cluster: 'do_maintenance',
    cardTypes: ['work_order'],
    sideEffectType: 'read_only',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'work_order_id', type: 'uuid', constraints: { required: true } },
    ],
    expectedChanges: [],
    description: 'Display procedural checklist for this task',
  },
  {
    id: 'assign_work_order',
    label: 'Assign Task',
    cluster: 'do_maintenance',
    cardTypes: ['work_order'],
    sideEffectType: 'mutation_light',
    triggers: {
      status: ['open', 'in_progress'],
      roles: HOD_ROLES,
    },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'work_order_id', type: 'uuid', constraints: { required: true } },
      { name: 'assignee_id', type: 'uuid', constraints: { required: true } },
    ],
    expectedChanges: [
      { table: 'pms_work_orders', operation: 'UPDATE', columns: ['assigned_to', 'assigned_at'] },
      { table: 'audit_log', operation: 'INSERT' },
    ],
    description: 'Assign work order to crew member or contractor',
  },
  // Checklist actions
  {
    id: 'view_checklist',
    label: 'View Checklist',
    cluster: 'do_maintenance',
    cardTypes: ['checklist'],
    sideEffectType: 'read_only',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'checklist_type', type: 'string', constraints: { enum: ['arrival', 'departure', 'pre_guest', 'fuel_transfer'] } },
    ],
    expectedChanges: [],
    description: 'Display operational checklist',
  },
  {
    id: 'mark_checklist_item_complete',
    label: 'Mark Complete',
    cluster: 'do_maintenance',
    cardTypes: ['checklist'],
    sideEffectType: 'mutation_light',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'checklist_item_id', type: 'uuid', constraints: { required: true } },
    ],
    expectedChanges: [
      { table: 'checklist_items', operation: 'UPDATE', expectedValue: { field: 'completed', value: true } },
    ],
    description: 'Tick off checklist item',
  },
  {
    id: 'add_checklist_note',
    label: 'Add Note',
    cluster: 'do_maintenance',
    cardTypes: ['checklist'],
    sideEffectType: 'mutation_light',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'checklist_item_id', type: 'uuid', constraints: { required: true } },
      { name: 'note_text', type: 'string', constraints: { required: true } },
    ],
    expectedChanges: [
      { table: 'checklist_notes', operation: 'INSERT' },
    ],
    description: 'Add note or observation to checklist item',
  },
  {
    id: 'add_checklist_photo',
    label: 'Add Photo',
    cluster: 'do_maintenance',
    cardTypes: ['checklist'],
    sideEffectType: 'mutation_light',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'checklist_item_id', type: 'uuid', constraints: { required: true } },
      { name: 'photo', type: 'file', constraints: { required: true } },
    ],
    expectedChanges: [
      { table: 'attachments', operation: 'INSERT' },
    ],
    description: 'Attach photo to checklist item',
  },
  // Worklist/Shipyard actions
  {
    id: 'view_worklist',
    label: 'View Worklist',
    cluster: 'do_maintenance',
    cardTypes: ['worklist'],
    sideEffectType: 'read_only',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [],
    expectedChanges: [],
    description: 'Display shipyard work items and snags',
  },
  {
    id: 'add_worklist_task',
    label: 'Add Task',
    cluster: 'do_maintenance',
    cardTypes: ['worklist'],
    sideEffectType: 'mutation_heavy',
    triggers: { roles: ENGINEER_ROLES },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'title', type: 'string', constraints: { minLength: 5, required: true } },
      { name: 'description', type: 'string', constraints: { minLength: 10, required: true } },
    ],
    optionalFields: [
      { name: 'equipment_id', type: 'uuid' },
      { name: 'category', type: 'string' },
    ],
    expectedChanges: [
      { table: 'worklist_tasks', operation: 'INSERT' },
    ],
    description: 'Create new shipyard work item',
  },
  {
    id: 'update_worklist_progress',
    label: 'Update Progress',
    cluster: 'do_maintenance',
    cardTypes: ['worklist'],
    sideEffectType: 'mutation_light',
    triggers: { roles: ENGINEER_ROLES },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'worklist_task_id', type: 'uuid', constraints: { required: true } },
      { name: 'progress_percent', type: 'number', constraints: { min: 0, max: 100 } },
    ],
    expectedChanges: [
      { table: 'worklist_tasks', operation: 'UPDATE', columns: ['progress_percent'] },
    ],
    description: 'Update completion status of yard task',
  },
  {
    id: 'export_worklist',
    label: 'Export Worklist',
    cluster: 'do_maintenance',
    cardTypes: ['worklist'],
    sideEffectType: 'read_only',
    triggers: { roles: HOD_ROLES },
    endpoint: '/v1/actions/execute',
    requiredFields: [],
    optionalFields: [
      { name: 'format', type: 'string', constraints: { enum: ['pdf', 'excel'] } },
    ],
    expectedChanges: [],
    description: 'Generate worklist document for yard/contractors',
  },
];

// ============================================================================
// CLUSTER 3: MANAGE_EQUIPMENT (6 actions)
// ============================================================================

const MANAGE_EQUIPMENT_ACTIONS: Microaction[] = [
  {
    id: 'view_equipment_details',
    label: 'View Equipment',
    cluster: 'manage_equipment',
    cardTypes: ['equipment', 'fault', 'smart_summary'],
    sideEffectType: 'read_only',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'equipment_id', type: 'uuid', constraints: { required: true } },
    ],
    expectedChanges: [],
    description: 'Display full equipment profile (model, serial, location)',
  },
  {
    id: 'view_equipment_history',
    label: 'View History',
    cluster: 'manage_equipment',
    cardTypes: ['equipment'],
    sideEffectType: 'read_only',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'equipment_id', type: 'uuid', constraints: { required: true } },
    ],
    expectedChanges: [],
    description: 'Show maintenance timeline for this equipment',
  },
  {
    id: 'view_equipment_parts',
    label: 'View Parts',
    cluster: 'manage_equipment',
    cardTypes: ['equipment'],
    sideEffectType: 'read_only',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'equipment_id', type: 'uuid', constraints: { required: true } },
    ],
    expectedChanges: [],
    description: 'List compatible parts for this equipment',
  },
  {
    id: 'view_linked_faults',
    label: 'View Faults',
    cluster: 'manage_equipment',
    cardTypes: ['equipment'],
    sideEffectType: 'read_only',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'equipment_id', type: 'uuid', constraints: { required: true } },
    ],
    expectedChanges: [],
    description: 'Show fault history for this equipment',
  },
  {
    id: 'view_equipment_manual',
    label: 'Open Manual',
    cluster: 'manage_equipment',
    cardTypes: ['equipment'],
    sideEffectType: 'read_only',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'equipment_id', type: 'uuid', constraints: { required: true } },
    ],
    expectedChanges: [],
    description: 'Access equipment-specific manual or documentation',
  },
  {
    id: 'add_equipment_note',
    label: 'Add Note',
    cluster: 'manage_equipment',
    cardTypes: ['equipment'],
    sideEffectType: 'mutation_light',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'equipment_id', type: 'uuid', constraints: { required: true } },
      { name: 'note_text', type: 'string', constraints: { minLength: 1, required: true } },
    ],
    expectedChanges: [
      { table: 'equipment_notes', operation: 'INSERT' },
    ],
    description: 'Add observation about equipment condition',
  },
];

// ============================================================================
// CLUSTER 4: CONTROL_INVENTORY (7 actions)
// ============================================================================

const CONTROL_INVENTORY_ACTIONS: Microaction[] = [
  {
    id: 'view_part_stock',
    label: 'Check Stock',
    cluster: 'control_inventory',
    cardTypes: ['part', 'fault', 'work_order'],
    sideEffectType: 'read_only',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'part_id', type: 'uuid', constraints: { required: true } },
    ],
    expectedChanges: [],
    description: 'Display current stock level and location',
  },
  {
    id: 'order_part',
    label: 'Order Part',
    cluster: 'control_inventory',
    cardTypes: ['part', 'fault'],
    sideEffectType: 'mutation_heavy',
    triggers: {
      roles: HOD_ROLES,
      conditions: [
        { name: 'low_stock', type: 'entity_field', check: 'current_quantity_onboard', expected: '<=reorder_point' },
      ],
    },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'part_id', type: 'uuid', constraints: { required: true } },
      { name: 'quantity', type: 'number', constraints: { min: 1, required: true } },
    ],
    optionalFields: [
      { name: 'supplier_id', type: 'uuid' },
      { name: 'notes', type: 'string' },
    ],
    expectedChanges: [
      { table: 'purchase_requests', operation: 'INSERT' },
      { table: 'audit_log', operation: 'INSERT' },
    ],
    edgeCases: [
      { name: 'quantity_zero', description: 'Zero quantity', payload: { part_id: 'valid-id', quantity: 0 }, expectedStatus: 400 },
      { name: 'quantity_negative', description: 'Negative quantity', payload: { part_id: 'valid-id', quantity: -1 }, expectedStatus: 400 },
    ],
    description: 'Create purchase request for this part',
  },
  {
    id: 'view_part_location',
    label: 'View Storage Location',
    cluster: 'control_inventory',
    cardTypes: ['part'],
    sideEffectType: 'read_only',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'part_id', type: 'uuid', constraints: { required: true } },
    ],
    expectedChanges: [],
    description: 'Show physical storage location (deck, locker, bin)',
  },
  {
    id: 'view_part_usage',
    label: 'View Usage History',
    cluster: 'control_inventory',
    cardTypes: ['part'],
    sideEffectType: 'read_only',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'part_id', type: 'uuid', constraints: { required: true } },
    ],
    expectedChanges: [],
    description: 'Show when/where this part was consumed',
  },
  {
    id: 'log_part_usage',
    label: 'Log Usage',
    cluster: 'control_inventory',
    cardTypes: ['part', 'work_order'],
    sideEffectType: 'mutation_light',
    triggers: { roles: ENGINEER_ROLES },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'part_id', type: 'uuid', constraints: { required: true } },
      { name: 'quantity', type: 'number', constraints: { min: 1, required: true } },
    ],
    optionalFields: [
      { name: 'work_order_id', type: 'uuid' },
      { name: 'notes', type: 'string' },
    ],
    expectedChanges: [
      { table: 'part_usage', operation: 'INSERT' },
      { table: 'pms_parts', operation: 'UPDATE', columns: ['current_quantity_onboard'] },
    ],
    edgeCases: [
      { name: 'insufficient_stock', description: 'Not enough stock', payload: { part_id: 'valid-id', quantity: 999 }, expectedStatus: 400, expectedError: 'insufficient stock' },
    ],
    description: 'Record part consumption against work order',
  },
  {
    id: 'scan_part_barcode',
    label: 'Scan Barcode',
    cluster: 'control_inventory',
    cardTypes: ['part'],
    sideEffectType: 'read_only',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'barcode', type: 'string', constraints: { required: true } },
    ],
    expectedChanges: [],
    description: 'Identify part via barcode/QR code scan',
  },
  {
    id: 'view_linked_equipment',
    label: 'View Equipment',
    cluster: 'control_inventory',
    cardTypes: ['part'],
    sideEffectType: 'read_only',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'part_id', type: 'uuid', constraints: { required: true } },
    ],
    expectedChanges: [],
    description: 'Show which equipment uses this part',
  },
];

// ============================================================================
// CLUSTER 5: COMMUNICATE_STATUS (9 actions)
// ============================================================================

const COMMUNICATE_STATUS_ACTIONS: Microaction[] = [
  {
    id: 'add_to_handover',
    label: 'Add to Handover',
    cluster: 'communicate_status',
    cardTypes: ['fault', 'work_order', 'equipment', 'part', 'document'],
    sideEffectType: 'mutation_light',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'entity_type', type: 'string', constraints: { enum: ['fault', 'work_order', 'equipment', 'part', 'document'], required: true } },
      { name: 'entity_id', type: 'uuid', constraints: { required: true } },
    ],
    optionalFields: [
      { name: 'summary', type: 'string' },
      { name: 'priority', type: 'string', constraints: { enum: ['low', 'normal', 'high', 'critical'] } },
    ],
    expectedChanges: [
      { table: 'handover_entries', operation: 'INSERT' },
    ],
    description: 'Add this item to active handover draft',
  },
  {
    id: 'add_document_to_handover',
    label: 'Add Document',
    cluster: 'communicate_status',
    cardTypes: ['document', 'handover'],
    sideEffectType: 'mutation_light',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'document_id', type: 'uuid', constraints: { required: true } },
    ],
    expectedChanges: [
      { table: 'handover_documents', operation: 'INSERT' },
    ],
    description: 'Attach document/manual to handover section',
  },
  {
    id: 'add_predictive_insight_to_handover',
    label: 'Add Insight',
    cluster: 'communicate_status',
    cardTypes: ['equipment', 'smart_summary'],
    sideEffectType: 'mutation_light',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'insight_id', type: 'uuid', constraints: { required: true } },
    ],
    expectedChanges: [
      { table: 'handover_entries', operation: 'INSERT' },
    ],
    description: 'Include predictive maintenance insight in handover',
  },
  {
    id: 'edit_handover_section',
    label: 'Edit Section',
    cluster: 'communicate_status',
    cardTypes: ['handover'],
    sideEffectType: 'mutation_light',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'handover_section_id', type: 'uuid', constraints: { required: true } },
      { name: 'content', type: 'string', constraints: { required: true } },
    ],
    expectedChanges: [
      { table: 'handover_sections', operation: 'UPDATE' },
    ],
    description: 'Modify handover section content',
  },
  {
    id: 'export_handover',
    label: 'Export PDF',
    cluster: 'communicate_status',
    cardTypes: ['handover'],
    sideEffectType: 'read_only',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'handover_id', type: 'uuid', constraints: { required: true } },
    ],
    optionalFields: [
      { name: 'format', type: 'string', constraints: { enum: ['pdf', 'docx'] } },
    ],
    expectedChanges: [],
    description: 'Generate downloadable handover document',
  },
  {
    id: 'regenerate_handover_summary',
    label: 'Regenerate Summary',
    cluster: 'communicate_status',
    cardTypes: ['handover'],
    sideEffectType: 'mutation_light',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'handover_id', type: 'uuid', constraints: { required: true } },
    ],
    expectedChanges: [
      { table: 'handover', operation: 'UPDATE', columns: ['summary', 'regenerated_at'] },
    ],
    description: 'Auto-generate summary from recent activity',
  },
  {
    id: 'view_smart_summary',
    label: 'View Summary',
    cluster: 'communicate_status',
    cardTypes: ['smart_summary'],
    sideEffectType: 'read_only',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [],
    optionalFields: [
      { name: 'period', type: 'string', constraints: { enum: ['today', 'week', 'month'] } },
    ],
    expectedChanges: [],
    description: 'Generate situational briefing (daily, pre-departure)',
  },
  {
    id: 'upload_photo',
    label: 'Upload Photo',
    cluster: 'communicate_status',
    cardTypes: ['work_order', 'fault', 'checklist', 'equipment'],
    sideEffectType: 'mutation_light',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'entity_type', type: 'string', constraints: { required: true } },
      { name: 'entity_id', type: 'uuid', constraints: { required: true } },
      { name: 'photo', type: 'file', constraints: { required: true } },
    ],
    expectedChanges: [
      { table: 'attachments', operation: 'INSERT' },
    ],
    description: 'Upload photo from mobile device',
  },
  {
    id: 'record_voice_note',
    label: 'Voice Note',
    cluster: 'communicate_status',
    cardTypes: ['work_order', 'fault'],
    sideEffectType: 'mutation_light',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'entity_type', type: 'string', constraints: { required: true } },
      { name: 'entity_id', type: 'uuid', constraints: { required: true } },
      { name: 'audio', type: 'file', constraints: { required: true } },
    ],
    expectedChanges: [
      { table: 'voice_notes', operation: 'INSERT' },
    ],
    description: 'Record audio note and transcribe',
  },
];

// ============================================================================
// CLUSTER 6: COMPLY_AUDIT (5 actions)
// ============================================================================

const COMPLY_AUDIT_ACTIONS: Microaction[] = [
  {
    id: 'view_hours_of_rest',
    label: 'View Hours of Rest',
    cluster: 'comply_audit',
    cardTypes: ['hor_table'],
    sideEffectType: 'read_only',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [],
    optionalFields: [
      { name: 'crew_member_id', type: 'uuid' },
      { name: 'period', type: 'string', constraints: { enum: ['week', 'month', 'custom'] } },
    ],
    expectedChanges: [],
    description: 'Display hours of rest summary for selected period',
  },
  {
    id: 'update_hours_of_rest',
    label: 'Update Hours',
    cluster: 'comply_audit',
    cardTypes: ['hor_table'],
    sideEffectType: 'mutation_heavy',
    triggers: { roles: 'any' }, // Users update their own hours
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'date', type: 'date', constraints: { required: true } },
      { name: 'hours_data', type: 'array', constraints: { required: true } },
    ],
    expectedChanges: [
      { table: 'hours_of_rest', operation: 'UPDATE' },
      { table: 'audit_log', operation: 'INSERT' },
    ],
    edgeCases: [
      { name: 'future_date', description: 'Cannot update future date', payload: { date: '2099-01-01' }, expectedStatus: 400 },
      { name: 'exceeds_24h', description: 'Hours exceed 24', payload: { hours_data: [{ work: 25, rest: 0 }] }, expectedStatus: 400 },
    ],
    description: 'Edit or correct hours of rest entries',
  },
  {
    id: 'export_hours_of_rest',
    label: 'Export Logs',
    cluster: 'comply_audit',
    cardTypes: ['hor_table'],
    sideEffectType: 'read_only',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'period_start', type: 'date', constraints: { required: true } },
      { name: 'period_end', type: 'date', constraints: { required: true } },
    ],
    optionalFields: [
      { name: 'format', type: 'string', constraints: { enum: ['pdf', 'excel'] } },
    ],
    expectedChanges: [],
    description: 'Download hours of rest report (PDF/Excel)',
  },
  {
    id: 'view_compliance_status',
    label: 'Check Compliance',
    cluster: 'comply_audit',
    cardTypes: ['hor_table'],
    sideEffectType: 'read_only',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [],
    expectedChanges: [],
    description: 'Show MLC compliance warnings/violations',
  },
  {
    id: 'tag_for_survey',
    label: 'Tag for Survey',
    cluster: 'comply_audit',
    cardTypes: ['worklist'],
    sideEffectType: 'mutation_light',
    triggers: { roles: HOD_ROLES },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'worklist_task_id', type: 'uuid', constraints: { required: true } },
    ],
    expectedChanges: [
      { table: 'worklist_tasks', operation: 'UPDATE', columns: ['tagged_for_survey'] },
    ],
    description: 'Flag item for class/flag survey prep',
  },
];

// ============================================================================
// CLUSTER 7: PROCURE_SUPPLIERS (7 actions)
// ============================================================================

const PROCURE_SUPPLIERS_ACTIONS: Microaction[] = [
  {
    id: 'create_purchase_request',
    label: 'Create Purchase',
    cluster: 'procure_suppliers',
    cardTypes: ['part', 'smart_summary'],
    sideEffectType: 'mutation_heavy',
    triggers: { roles: HOD_ROLES },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'items', type: 'array', constraints: { required: true } }, // [{part_id, quantity}]
    ],
    optionalFields: [
      { name: 'supplier_id', type: 'uuid' },
      { name: 'notes', type: 'string' },
      { name: 'required_by', type: 'date' },
    ],
    expectedChanges: [
      { table: 'purchase_orders', operation: 'INSERT' },
      { table: 'purchase_order_items', operation: 'INSERT' },
      { table: 'audit_log', operation: 'INSERT' },
    ],
    description: 'Initiate purchase order for parts or services',
  },
  {
    id: 'add_item_to_purchase',
    label: 'Add Item',
    cluster: 'procure_suppliers',
    cardTypes: ['purchase'],
    sideEffectType: 'mutation_light',
    triggers: {
      status: ['draft', 'pending'],
      roles: HOD_ROLES,
    },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'purchase_order_id', type: 'uuid', constraints: { required: true } },
      { name: 'part_id', type: 'uuid', constraints: { required: true } },
      { name: 'quantity', type: 'number', constraints: { min: 1, required: true } },
    ],
    expectedChanges: [
      { table: 'purchase_order_items', operation: 'INSERT' },
    ],
    description: 'Add part to existing purchase request',
  },
  {
    id: 'approve_purchase',
    label: 'Approve',
    cluster: 'procure_suppliers',
    cardTypes: ['purchase'],
    sideEffectType: 'mutation_heavy',
    triggers: {
      status: ['pending_approval'],
      roles: HOD_ROLES,
    },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'purchase_order_id', type: 'uuid', constraints: { required: true } },
    ],
    optionalFields: [
      { name: 'approval_notes', type: 'string' },
    ],
    expectedChanges: [
      { table: 'purchase_orders', operation: 'UPDATE', expectedValue: { field: 'status', value: 'approved' } },
      { table: 'audit_log', operation: 'INSERT' },
    ],
    edgeCases: [
      { name: 'already_approved', description: 'PO already approved', payload: { purchase_order_id: 'approved-po' }, expectedStatus: 400 },
      { name: 'insufficient_permission', description: 'User cannot approve this amount', payload: { purchase_order_id: 'high-value-po' }, expectedStatus: 403 },
    ],
    description: 'Approve purchase request (role-based)',
  },
  {
    id: 'upload_invoice',
    label: 'Upload Invoice',
    cluster: 'procure_suppliers',
    cardTypes: ['purchase'],
    sideEffectType: 'mutation_light',
    triggers: {
      status: ['ordered', 'received'],
      roles: HOD_ROLES,
    },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'purchase_order_id', type: 'uuid', constraints: { required: true } },
      { name: 'invoice_file', type: 'file', constraints: { required: true } },
    ],
    optionalFields: [
      { name: 'invoice_number', type: 'string' },
      { name: 'invoice_amount', type: 'number' },
    ],
    expectedChanges: [
      { table: 'purchase_invoices', operation: 'INSERT' },
      { table: 'purchase_orders', operation: 'UPDATE', columns: ['invoice_uploaded_at'] },
    ],
    description: 'Attach supplier invoice to purchase order',
  },
  {
    id: 'track_delivery',
    label: 'Track Delivery',
    cluster: 'procure_suppliers',
    cardTypes: ['purchase'],
    sideEffectType: 'read_only',
    triggers: {
      status: ['ordered', 'shipped'],
      roles: 'any',
    },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'purchase_order_id', type: 'uuid', constraints: { required: true } },
    ],
    expectedChanges: [],
    description: 'View delivery status and ETA',
  },
  {
    id: 'log_delivery_received',
    label: 'Log Delivery',
    cluster: 'procure_suppliers',
    cardTypes: ['purchase'],
    sideEffectType: 'mutation_heavy',
    triggers: {
      status: ['ordered', 'shipped'],
      roles: ENGINEER_ROLES,
    },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'purchase_order_id', type: 'uuid', constraints: { required: true } },
      { name: 'received_items', type: 'array', constraints: { required: true } }, // [{item_id, quantity_received}]
    ],
    optionalFields: [
      { name: 'delivery_notes', type: 'string' },
      { name: 'discrepancies', type: 'string' },
    ],
    expectedChanges: [
      { table: 'purchase_orders', operation: 'UPDATE', expectedValue: { field: 'status', value: 'received' } },
      { table: 'pms_parts', operation: 'UPDATE', columns: ['current_quantity_onboard'] },
      { table: 'audit_log', operation: 'INSERT' },
    ],
    description: 'Mark items as received and update inventory',
  },
  {
    id: 'update_purchase_status',
    label: 'Update Status',
    cluster: 'procure_suppliers',
    cardTypes: ['purchase'],
    sideEffectType: 'mutation_light',
    triggers: { roles: HOD_ROLES },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'purchase_order_id', type: 'uuid', constraints: { required: true } },
      { name: 'new_status', type: 'string', constraints: { enum: ['draft', 'pending_approval', 'approved', 'ordered', 'shipped', 'received', 'cancelled'] } },
    ],
    expectedChanges: [
      { table: 'purchase_orders', operation: 'UPDATE', columns: ['status'] },
      { table: 'audit_log', operation: 'INSERT' },
    ],
    description: 'Change purchase order status',
  },
];

// ============================================================================
// ADDITIONAL ACTIONS (Documents, Fleet, Predictive)
// ============================================================================

const ADDITIONAL_ACTIONS: Microaction[] = [
  // Document actions
  {
    id: 'view_document',
    label: 'Open Document',
    cluster: 'fix_something',
    cardTypes: ['document'],
    sideEffectType: 'read_only',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'document_id', type: 'uuid', constraints: { required: true } },
    ],
    expectedChanges: [],
    description: 'Display full document or manual',
  },
  {
    id: 'view_related_documents',
    label: 'Related Docs',
    cluster: 'fix_something',
    cardTypes: ['fault', 'equipment'],
    sideEffectType: 'read_only',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'entity_type', type: 'string', constraints: { required: true } },
      { name: 'entity_id', type: 'uuid', constraints: { required: true } },
    ],
    expectedChanges: [],
    description: 'Find documents linked to current context',
  },
  {
    id: 'view_document_section',
    label: 'View Section',
    cluster: 'fix_something',
    cardTypes: ['fault', 'work_order'],
    sideEffectType: 'read_only',
    triggers: { roles: 'any' },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'document_id', type: 'uuid', constraints: { required: true } },
    ],
    optionalFields: [
      { name: 'section_query', type: 'string' },
      { name: 'page_number', type: 'number' },
    ],
    expectedChanges: [],
    description: 'Jump to specific section within document',
  },
  // Fleet actions
  {
    id: 'view_fleet_summary',
    label: 'View Fleet',
    cluster: 'manage_equipment',
    cardTypes: ['fleet_summary'],
    sideEffectType: 'read_only',
    triggers: { roles: ['captain', 'manager', 'admin'] },
    endpoint: '/v1/actions/execute',
    requiredFields: [],
    expectedChanges: [],
    description: 'Display multi-vessel overview',
  },
  {
    id: 'open_vessel',
    label: 'Open Vessel',
    cluster: 'manage_equipment',
    cardTypes: ['fleet_summary'],
    sideEffectType: 'read_only',
    triggers: { roles: ['captain', 'manager', 'admin'] },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'yacht_id', type: 'uuid', constraints: { required: true } },
    ],
    expectedChanges: [],
    description: 'Switch context to specific vessel',
  },
  {
    id: 'export_fleet_summary',
    label: 'Export Summary',
    cluster: 'communicate_status',
    cardTypes: ['fleet_summary'],
    sideEffectType: 'read_only',
    triggers: { roles: ['captain', 'manager', 'admin'] },
    endpoint: '/v1/actions/execute',
    requiredFields: [],
    optionalFields: [
      { name: 'format', type: 'string', constraints: { enum: ['pdf', 'excel'] } },
    ],
    expectedChanges: [],
    description: 'Download fleet status report',
  },
  // Predictive action
  {
    id: 'request_predictive_insight',
    label: 'Predictive Insight',
    cluster: 'manage_equipment',
    cardTypes: ['equipment', 'smart_summary'],
    sideEffectType: 'read_only',
    triggers: {
      roles: 'any',
      conditions: [{ name: 'predictive_enabled', type: 'user_context', check: 'yacht.predictive_maintenance_enabled', expected: true }],
    },
    endpoint: '/v1/actions/execute',
    requiredFields: [
      { name: 'equipment_id', type: 'uuid', constraints: { required: true } },
    ],
    expectedChanges: [],
    description: 'Request AI-driven maintenance predictions',
  },
];

// ============================================================================
// COMPLETE REGISTRY
// ============================================================================

export const MICROACTION_REGISTRY: Microaction[] = [
  ...FIX_SOMETHING_ACTIONS,
  ...DO_MAINTENANCE_ACTIONS,
  ...MANAGE_EQUIPMENT_ACTIONS,
  ...CONTROL_INVENTORY_ACTIONS,
  ...COMMUNICATE_STATUS_ACTIONS,
  ...COMPLY_AUDIT_ACTIONS,
  ...PROCURE_SUPPLIERS_ACTIONS,
  ...ADDITIONAL_ACTIONS,
];

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/** Get actions by cluster */
export function getActionsByCluster(cluster: Cluster): Microaction[] {
  return MICROACTION_REGISTRY.filter(a => a.cluster === cluster);
}

/** Get actions by card type */
export function getActionsByCardType(cardType: CardType): Microaction[] {
  return MICROACTION_REGISTRY.filter(a => a.cardTypes.includes(cardType));
}

/** Get actions allowed for a role */
export function getActionsForRole(role: Role): Microaction[] {
  return MICROACTION_REGISTRY.filter(a =>
    a.triggers.roles === 'any' ||
    (Array.isArray(a.triggers.roles) && a.triggers.roles.includes(role))
  );
}

/** Get mutation actions (for testing side effects) */
export function getMutationActions(): Microaction[] {
  return MICROACTION_REGISTRY.filter(a => a.sideEffectType !== 'read_only');
}

/** Get actions with edge cases defined */
export function getActionsWithEdgeCases(): Microaction[] {
  return MICROACTION_REGISTRY.filter(a => a.edgeCases && a.edgeCases.length > 0);
}

/** Get HOD-only actions */
export function getHodOnlyActions(): Microaction[] {
  return MICROACTION_REGISTRY.filter(a =>
    Array.isArray(a.triggers.roles) &&
    a.triggers.roles.every(r => HOD_ROLES.includes(r))
  );
}

/** Get auto-run actions */
export function getAutoRunActions(): Microaction[] {
  return MICROACTION_REGISTRY.filter(a => a.triggers.autoRun === true);
}

// ============================================================================
// STATISTICS
// ============================================================================

export const REGISTRY_STATS = {
  total: MICROACTION_REGISTRY.length,
  byCluster: {
    fix_something: FIX_SOMETHING_ACTIONS.length,
    do_maintenance: DO_MAINTENANCE_ACTIONS.length,
    manage_equipment: MANAGE_EQUIPMENT_ACTIONS.length,
    control_inventory: CONTROL_INVENTORY_ACTIONS.length,
    communicate_status: COMMUNICATE_STATUS_ACTIONS.length,
    comply_audit: COMPLY_AUDIT_ACTIONS.length,
    procure_suppliers: PROCURE_SUPPLIERS_ACTIONS.length,
    additional: ADDITIONAL_ACTIONS.length,
  },
  bySideEffect: {
    read_only: MICROACTION_REGISTRY.filter(a => a.sideEffectType === 'read_only').length,
    mutation_light: MICROACTION_REGISTRY.filter(a => a.sideEffectType === 'mutation_light').length,
    mutation_heavy: MICROACTION_REGISTRY.filter(a => a.sideEffectType === 'mutation_heavy').length,
  },
  withEdgeCases: getActionsWithEdgeCases().length,
  hodOnly: getHodOnlyActions().length,
  autoRun: getAutoRunActions().length,
};

// Log stats when loaded in test environment
if (typeof process !== 'undefined' && process.env.NODE_ENV === 'test') {
  console.log('MICROACTION_REGISTRY loaded:', REGISTRY_STATS);
}
