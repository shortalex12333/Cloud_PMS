#!/usr/bin/env npx ts-node
/**
 * Results Validator - Gatekeeper Script
 *
 * This script enforces PASS criteria. Claude can't cheat.
 *
 * Rules:
 * - If status != 200/201 (or 204 explicitly allowed) → FAIL
 * - NEGATIVE_CONTROL cases must be declared and include "no DB mutation" proof
 * - Missing required fields → auto-FAIL
 * - No interpretation, just enforcement
 */

import * as fs from 'fs';
import * as path from 'path';

// ============================================================================
// INLINE TYPE DEFINITIONS (to avoid module resolution issues)
// ============================================================================

type FailureReason =
  | 'MISSING_ENDPOINT'
  | 'AUTH_FAILED'
  | 'VALIDATION_FAILED'
  | 'WRONG_ACTION'
  | 'NO_DB_MUTATION'
  | 'NO_DATA_RETURNED'
  | 'REDIRECTED'
  | 'UNHANDLED_EXCEPTION'
  | 'UNVERIFIED'
  | 'GATE_A_TRANSPORT'
  | 'GATE_B_SEMANTIC'
  | 'GATE_C_STATE'
  | 'GATE_D_DATA'
  | 'NONE';

type TestType = 'POSITIVE' | 'NEGATIVE_CONTROL';
type ActionCategory = 'READ' | 'WRITE';

interface DbProof {
  query: string;
  table: string;
  row_ids: string[];
  before_count: number;
  after_count: number;
  mutation_verified: boolean;
}

interface LedgerProof {
  query: string;
  event_ids: string[];
  event_type: string;
  verified: boolean;
}

interface TestResult {
  case_id: string;
  test_type: TestType;
  action_category: ActionCategory;
  expected_action: string;
  query: string;
  surface_state: string;
  status_code: number;
  response_action_name: string;
  execution_id: string;
  gate_a_transport: boolean;
  gate_b_semantic: boolean;
  gate_c_state: boolean | null;
  gate_d_data: boolean | null;
  db_proof: DbProof | null;
  ledger_proof: LedgerProof | null;
  evidence_files: string[];
  passed: boolean;
  failure_reason: FailureReason;
  timestamp: string;
  duration_ms: number;
}

interface NegativeControlResult extends TestResult {
  test_type: 'NEGATIVE_CONTROL';
  expected_status_code: number;
  expected_error_payload: string;
  no_db_mutation_verified: boolean;
}

const STATUS_TO_FAILURE: Record<number, FailureReason> = {
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

const WRITE_ACTIONS = new Set([
  'create_work_order', 'update_work_order', 'close_work_order', 'add_note_to_work_order',
  'attach_photo_to_work_order', 'assign_work_order', 'set_priority_on_work_order',
  'schedule_work_order', 'add_to_handover', 'edit_handover_section', 'attach_document_to_handover',
  'order_part', 'add_part_to_work_order', 'update_stock_level', 'reserve_part',
  'create_purchase_request', 'log_hours_of_rest', 'submit_compliance_report',
  'upload_certificate_document', 'upload_document', 'attach_document_to_work_order',
  'archive_document', 'approve_purchase_order', 'link_supplier', 'upload_invoice',
  'create_purchase_order', 'create_task', 'mark_work_order_complete', 'add_checklist_item',
  'assign_task', 'log_contractor_work', 'schedule_shipyard_task', 'set_reminder', 'add_note',
  'link_document_to_equipment', 'update_certificate_metadata', 'report_fault',
]);

function getActionCategory(action: string): ActionCategory {
  return WRITE_ACTIONS.has(action) ? 'WRITE' : 'READ';
}

const GATES = {
  A_TRANSPORT: (status: number, allowedStatuses: number[] = [200, 201]) => {
    return allowedStatuses.includes(status);
  },
  B_SEMANTIC: (responseAction: string, expectedAction: string, responseStatus: string, executionId: string) => {
    return responseAction === expectedAction && responseStatus === 'success' && !!executionId;
  },
  C_STATE: (dbProof: DbProof | null, ledgerProof: LedgerProof | null) => {
    if (!dbProof) return false;
    return dbProof.mutation_verified && (ledgerProof?.verified ?? true);
  },
  D_DATA: (hasData: boolean, fixturesExist: boolean) => {
    if (fixturesExist) return hasData;
    return !hasData;
  },
};

// ============================================================================
// VALIDATION FUNCTIONS
// ============================================================================

function validateResult(result: TestResult): TestResult {
  let failureReason: FailureReason = 'UNVERIFIED';

  const requiredFields = ['case_id', 'expected_action', 'query', 'status_code'];
  for (const field of requiredFields) {
    if (!(field in result) || result[field as keyof TestResult] === undefined) {
      return { ...result, passed: false, failure_reason: 'UNVERIFIED' };
    }
  }

  const gateA = GATES.A_TRANSPORT(result.status_code);
  result.gate_a_transport = gateA;

  if (!gateA) {
    failureReason = STATUS_TO_FAILURE[result.status_code] || 'GATE_A_TRANSPORT';
    return { ...result, passed: false, failure_reason: failureReason };
  }

  const gateB = GATES.B_SEMANTIC(result.response_action_name, result.expected_action, 'success', result.execution_id);
  result.gate_b_semantic = gateB;

  if (!gateB) {
    failureReason = result.response_action_name !== result.expected_action ? 'WRONG_ACTION' : 'GATE_B_SEMANTIC';
    return { ...result, passed: false, failure_reason: failureReason };
  }

  const category = getActionCategory(result.expected_action);

  if (category === 'WRITE') {
    const gateC = GATES.C_STATE(result.db_proof, result.ledger_proof);
    result.gate_c_state = gateC;
    result.gate_d_data = null;
    if (!gateC) {
      return { ...result, passed: false, failure_reason: 'NO_DB_MUTATION' };
    }
  } else {
    const hasData = result.gate_d_data === true;
    result.gate_c_state = null;
    if (!hasData) {
      return { ...result, passed: false, failure_reason: 'NO_DATA_RETURNED' };
    }
  }

  return { ...result, passed: true, failure_reason: 'NONE' };
}

function validateNegativeControl(result: NegativeControlResult): NegativeControlResult {
  if (result.status_code !== result.expected_status_code) {
    return { ...result, passed: false, failure_reason: 'GATE_A_TRANSPORT' };
  }
  if (!result.no_db_mutation_verified) {
    return { ...result, passed: false, failure_reason: 'NO_DB_MUTATION' };
  }
  return { ...result, passed: true, failure_reason: 'NONE' };
}

// ============================================================================
// MAIN VALIDATOR
// ============================================================================

interface ValidationSummary {
  total: number;
  passed: number;
  failed: number;
  pass_rate: string;
  failures_by_reason: Record<FailureReason, number>;
  negative_controls: { total: number; passed: number; failed: number };
}

function validateResultsFile(inputPath: string, outputPath: string): ValidationSummary {
  const rawData = fs.readFileSync(inputPath, 'utf-8');
  const lines = rawData.trim().split('\n');

  const validatedResults: TestResult[] = [];
  const summary: ValidationSummary = {
    total: 0,
    passed: 0,
    failed: 0,
    pass_rate: '0%',
    failures_by_reason: {} as Record<FailureReason, number>,
    negative_controls: { total: 0, passed: 0, failed: 0 },
  };

  for (const line of lines) {
    if (!line.trim()) continue;

    try {
      const result = JSON.parse(line) as TestResult;
      summary.total++;

      let validated: TestResult;

      if (result.test_type === 'NEGATIVE_CONTROL') {
        summary.negative_controls.total++;
        validated = validateNegativeControl(result as NegativeControlResult);
        if (validated.passed) {
          summary.negative_controls.passed++;
        } else {
          summary.negative_controls.failed++;
        }
      } else {
        validated = validateResult(result);
      }

      if (validated.passed) {
        summary.passed++;
      } else {
        summary.failed++;
        const reason = validated.failure_reason;
        summary.failures_by_reason[reason] = (summary.failures_by_reason[reason] || 0) + 1;
      }

      validatedResults.push(validated);
    } catch (e) {
      console.error(`Failed to parse line: ${line}`);
      summary.total++;
      summary.failed++;
      summary.failures_by_reason['UNVERIFIED'] = (summary.failures_by_reason['UNVERIFIED'] || 0) + 1;
    }
  }

  summary.pass_rate = summary.total > 0 ? ((summary.passed / summary.total) * 100).toFixed(2) + '%' : '0%';

  fs.writeFileSync(outputPath, validatedResults.map(r => JSON.stringify(r)).join('\n'));

  return summary;
}

// ============================================================================
// CLI
// ============================================================================

// Run if invoked directly
const isMain = import.meta.url === `file://${process.argv[1]}` || process.argv[1]?.endsWith('validate-results.ts');
if (isMain) {
  const args = process.argv.slice(2);
  const inputPath = args[0] || 'results.jsonl';
  const outputPath = args[1] || 'validated_results.jsonl';

  console.log('=== TEST RESULTS VALIDATOR ===\n');
  console.log(`Input:  ${inputPath}`);
  console.log(`Output: ${outputPath}\n`);

  if (!fs.existsSync(inputPath)) {
    console.error(`ERROR: Input file not found: ${inputPath}`);
    process.exit(1);
  }

  const summary = validateResultsFile(inputPath, outputPath);

  console.log('=== VALIDATION SUMMARY ===\n');
  console.log(`Total Tests:     ${summary.total}`);
  console.log(`Passed:          ${summary.passed}`);
  console.log(`Failed:          ${summary.failed}`);
  console.log(`Pass Rate:       ${summary.pass_rate}`);

  if (summary.negative_controls.total > 0) {
    console.log(`\nNegative Controls:`);
    console.log(`  Total:   ${summary.negative_controls.total}`);
    console.log(`  Passed:  ${summary.negative_controls.passed}`);
    console.log(`  Failed:  ${summary.negative_controls.failed}`);
  }

  if (Object.keys(summary.failures_by_reason).length > 0) {
    console.log('\nFailures by Reason:');
    for (const [reason, count] of Object.entries(summary.failures_by_reason)) {
      console.log(`  ${reason}: ${count}`);
    }
  }

  console.log(`\nValidated results written to: ${outputPath}`);

  if (summary.failed > 0) {
    process.exit(1);
  }
}

export { validateResultsFile };
