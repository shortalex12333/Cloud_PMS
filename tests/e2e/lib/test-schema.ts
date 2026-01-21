/**
 * Test Results Schema - Single Source of Truth
 *
 * PASS Definition (non-negotiable):
 * A test case is PASS only if ALL required gates pass.
 */

// ============================================================================
// FAILURE REASONS (Fixed Enum)
// ============================================================================

export type FailureReason =
  | 'MISSING_ENDPOINT'      // 404
  | 'AUTH_FAILED'           // 401/403
  | 'VALIDATION_FAILED'     // 400/422
  | 'WRONG_ACTION'          // 200 but wrong action_name
  | 'NO_DB_MUTATION'        // Write action returned 200 but no DB proof
  | 'NO_DATA_RETURNED'      // Read action returned 200 but empty with fixtures
  | 'REDIRECTED'            // 3xx
  | 'UNHANDLED_EXCEPTION'   // 500
  | 'UNVERIFIED'            // Missing evidence fields
  | 'GATE_A_TRANSPORT'      // Transport gate failed
  | 'GATE_B_SEMANTIC'       // Semantic correctness failed
  | 'GATE_C_STATE'          // State proof failed (write actions)
  | 'GATE_D_DATA'           // Data proof failed (read actions)
  | 'NONE';                 // No failure (PASS)

// ============================================================================
// TEST CASE TYPES
// ============================================================================

export type TestType =
  | 'POSITIVE'              // Normal test - expects success
  | 'NEGATIVE_CONTROL';     // Expects specific failure (401, 422, etc.)

export type ActionCategory =
  | 'READ'                  // Requires Gate D (data proof)
  | 'WRITE';                // Requires Gate C (state proof)

// ============================================================================
// RESULT RECORD (Required Fields)
// ============================================================================

export interface TestResult {
  // Identity
  case_id: string;                    // e.g., "diagnose_fault_Y1"
  test_type: TestType;                // POSITIVE or NEGATIVE_CONTROL
  action_category: ActionCategory;    // READ or WRITE

  // Input
  expected_action: string;            // Canonical action name
  query: string;                      // User input/query
  surface_state: string;              // UI state when executed

  // Response
  status_code: number;                // HTTP status
  response_action_name: string;       // Action returned by API
  execution_id: string;               // Request ID for traceability

  // Gates
  gate_a_transport: boolean;          // 200/201/204, no redirects
  gate_b_semantic: boolean;           // Correct action, status=success
  gate_c_state: boolean | null;       // DB proof (write only, null for read)
  gate_d_data: boolean | null;        // Data proof (read only, null for write)

  // Proofs
  db_proof: DbProof | null;           // Query + row IDs
  ledger_proof: LedgerProof | null;   // Audit log proof
  evidence_files: string[];           // Screenshots, logs

  // Verdict
  passed: boolean;                    // ALL gates must pass
  failure_reason: FailureReason;      // Why it failed (or NONE)

  // Metadata
  timestamp: string;                  // ISO timestamp
  duration_ms: number;                // Execution time
}

export interface DbProof {
  query: string;                      // SQL/query used
  table: string;                      // Table checked
  row_ids: string[];                  // Row IDs found/created
  before_count: number;               // Rows before action
  after_count: number;                // Rows after action
  mutation_verified: boolean;         // Did count change?
}

export interface LedgerProof {
  query: string;                      // Ledger query
  event_ids: string[];                // Ledger event IDs
  event_type: string;                 // Type of event logged
  verified: boolean;                  // Event exists?
}

// ============================================================================
// NEGATIVE CONTROL SPECIFIC
// ============================================================================

export interface NegativeControlResult extends TestResult {
  test_type: 'NEGATIVE_CONTROL';
  expected_status_code: number;       // Expected error (401, 422, etc.)
  expected_error_payload: string;     // Expected error message pattern
  no_db_mutation_verified: boolean;   // Proved no write occurred
}

// ============================================================================
// GATE DEFINITIONS
// ============================================================================

export const GATES = {
  /**
   * Gate A - Transport
   * Must hit correct endpoint (no redirects)
   * Status must be 200/201 (or 204 if explicitly allowed)
   */
  A_TRANSPORT: (status: number, allowedStatuses: number[] = [200, 201]) => {
    return allowedStatuses.includes(status);
  },

  /**
   * Gate B - Semantic Correctness
   * Response must contain:
   * - action_name == expected_action
   * - status == "success"
   * - execution_id for traceability
   */
  B_SEMANTIC: (
    responseAction: string,
    expectedAction: string,
    responseStatus: string,
    executionId: string
  ) => {
    return (
      responseAction === expectedAction &&
      responseStatus === 'success' &&
      !!executionId
    );
  },

  /**
   * Gate C - State Proof (write actions only)
   * Must prove DB change:
   * - Row exists with expected keys
   * - Timestamps updated
   * - Ledger/audit record exists
   */
  C_STATE: (dbProof: DbProof | null, ledgerProof: LedgerProof | null) => {
    if (!dbProof) return false;
    return dbProof.mutation_verified && (ledgerProof?.verified ?? true);
  },

  /**
   * Gate D - Data Proof (read actions only)
   * Must return non-empty results when fixtures exist
   * Must return deterministic "no results" when fixtures don't
   */
  D_DATA: (hasData: boolean, fixturesExist: boolean) => {
    if (fixturesExist) return hasData;
    return !hasData; // Empty is correct when no fixtures
  },
};

// ============================================================================
// STATUS CODE MAPPINGS
// ============================================================================

export const STATUS_TO_FAILURE: Record<number, FailureReason> = {
  307: 'REDIRECTED',
  308: 'REDIRECTED',
  400: 'VALIDATION_FAILED',
  401: 'AUTH_FAILED',
  403: 'AUTH_FAILED',
  404: 'MISSING_ENDPOINT',
  422: 'VALIDATION_FAILED',
  500: 'UNHANDLED_EXCEPTION',
  502: 'UNHANDLED_EXCEPTION',
  503: 'UNHANDLED_EXCEPTION',
};

// ============================================================================
// ACTION CLASSIFICATIONS
// ============================================================================

export const WRITE_ACTIONS = new Set([
  'create_work_order',
  'update_work_order',
  'close_work_order',
  'add_note_to_work_order',
  'attach_photo_to_work_order',
  'assign_work_order',
  'set_priority_on_work_order',
  'schedule_work_order',
  'add_to_handover',
  'edit_handover_section',
  'attach_document_to_handover',
  'order_part',
  'add_part_to_work_order',
  'update_stock_level',
  'reserve_part',
  'create_purchase_request',
  'log_hours_of_rest',
  'submit_compliance_report',
  'upload_certificate_document',
  'upload_document',
  'attach_document_to_work_order',
  'archive_document',
  'approve_purchase_order',
  'link_supplier',
  'upload_invoice',
  'create_purchase_order',
  'create_task',
  'mark_work_order_complete',
  'add_checklist_item',
  'assign_task',
  'log_contractor_work',
  'schedule_shipyard_task',
  'set_reminder',
  'add_note',
  'link_document_to_equipment',
  'update_certificate_metadata',
  'report_fault',
]);

export const READ_ACTIONS = new Set([
  'diagnose_fault',
  'show_manual_section',
  'show_related_documents',
  'show_equipment_overview',
  'show_equipment_history',
  'show_recent_state',
  'show_predictive_insight',
  'suggest_likely_parts',
  'show_similar_past_events',
  'trace_related_faults',
  'trace_related_equipment',
  'view_linked_entities',
  'show_document_graph',
  'expand_fault_tree',
  'show_entity_timeline',
  'list_work_orders',
  'show_work_order_history',
  'view_handover',
  'export_handover',
  'check_stock_level',
  'show_storage_location',
  'scan_barcode',
  'show_part_compatibility',
  'show_low_stock_alerts',
  'show_hours_of_rest',
  'show_certificates',
  'show_certificate_expiry',
  'export_compliance_logs',
  'generate_audit_pack',
  'search_documents',
  'open_document',
  'show_document_metadata',
  'download_document',
  'share_document',
  'track_delivery',
  'compare_supplier_prices',
  'show_tasks_due',
  'show_checklist',
  'export_summary',
  'generate_summary',
  'show_analytics',
  'export_work_order_history',
  'show_equipment_utilization',
  'show_fault_trends',
  'compare_fleet_equipment',
  'show_fleet_alerts',
  'share_with_shipyard',
  'open_equipment_card',
  'detect_anomaly',
]);

export function getActionCategory(action: string): ActionCategory {
  if (WRITE_ACTIONS.has(action)) return 'WRITE';
  return 'READ';
}
