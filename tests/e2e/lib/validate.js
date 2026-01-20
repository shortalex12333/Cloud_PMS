#!/usr/bin/env node
/**
 * Results Validator - Gatekeeper Script (CommonJS version)
 *
 * Rules:
 * - If status != 200/201 (or 204 explicitly allowed) → FAIL
 * - NEGATIVE_CONTROL cases must be declared and include "no DB mutation" proof
 */

const fs = require('fs');

const STATUS_TO_FAILURE = {
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
  'add_worklist_task', 'update_equipment_status',
]);

function getActionCategory(action) {
  return WRITE_ACTIONS.has(action) ? 'WRITE' : 'READ';
}

function gateA(status) {
  return status === 200 || status === 201;
}

function gateB(responseAction, expectedAction, executionId) {
  return responseAction === expectedAction && !!executionId;
}

function gateC(result) {
  // STRICT: Require actual db_proof with mutation_verified=true
  // No shortcuts - must have real DB verification
  return result.db_proof && result.db_proof.mutation_verified === true;
}

function validateResult(result) {
  // Gate A: Transport
  if (!gateA(result.status_code)) {
    return { ...result, passed: false, failure_reason: STATUS_TO_FAILURE[result.status_code] || 'GATE_A_TRANSPORT' };
  }

  // Gate B: Semantic
  if (!gateB(result.response_action_name, result.expected_action, result.execution_id)) {
    const reason = result.response_action_name !== result.expected_action ? 'WRONG_ACTION' : 'GATE_B_SEMANTIC';
    return { ...result, passed: false, failure_reason: reason };
  }

  // Gate C or D based on action type
  const category = getActionCategory(result.expected_action);

  if (category === 'WRITE') {
    if (!gateC(result)) {
      return { ...result, passed: false, failure_reason: 'NO_DB_MUTATION' };
    }
  } else {
    if (result.gate_d_data !== true) {
      return { ...result, passed: false, failure_reason: 'NO_DATA_RETURNED' };
    }
  }

  return { ...result, passed: true, failure_reason: 'NONE' };
}

function validateNegativeControl(result) {
  // Check expected status
  if (result.status_code !== result.expected_status_code) {
    return { ...result, passed: false, failure_reason: 'GATE_A_TRANSPORT' };
  }
  // For write actions, verify no mutation
  if (getActionCategory(result.expected_action) === 'WRITE') {
    if (result.db_proof && result.db_proof.mutation_verified) {
      return { ...result, passed: false, failure_reason: 'NO_DB_MUTATION' };
    }
  }
  return { ...result, passed: true, failure_reason: 'NONE' };
}

function main() {
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

  const rawData = fs.readFileSync(inputPath, 'utf-8');
  const lines = rawData.trim().split('\n').filter(l => l.trim());

  const validatedResults = [];
  const summary = {
    total: 0,
    passed: 0,
    failed: 0,
    failures_by_reason: {},
    negative_controls: { total: 0, passed: 0, failed: 0 },
  };

  for (const line of lines) {
    try {
      const result = JSON.parse(line);
      summary.total++;

      let validated;
      if (result.test_type === 'NEGATIVE_CONTROL') {
        summary.negative_controls.total++;
        validated = validateNegativeControl(result);
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
        summary.failures_by_reason[validated.failure_reason] =
          (summary.failures_by_reason[validated.failure_reason] || 0) + 1;
      }

      validatedResults.push(validated);
    } catch (e) {
      console.error(`Parse error: ${e.message}`);
      summary.total++;
      summary.failed++;
      summary.failures_by_reason['UNVERIFIED'] = (summary.failures_by_reason['UNVERIFIED'] || 0) + 1;
    }
  }

  const passRate = summary.total > 0 ? ((summary.passed / summary.total) * 100).toFixed(2) : 0;

  fs.writeFileSync(outputPath, validatedResults.map(r => JSON.stringify(r)).join('\n'));

  console.log('=== VALIDATION SUMMARY ===\n');
  console.log(`Total Tests:     ${summary.total}`);
  console.log(`Passed:          ${summary.passed}`);
  console.log(`Failed:          ${summary.failed}`);
  console.log(`Pass Rate:       ${passRate}%`);

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

  process.exit(summary.failed > 0 ? 1 : 0);
}

main();
