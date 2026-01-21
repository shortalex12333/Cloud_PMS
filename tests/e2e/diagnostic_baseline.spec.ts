/**
 * DIAGNOSTIC BASELINE TEST
 * =========================
 *
 * Purpose: Capture holistic system state in ONE run to identify ALL bottlenecks
 *
 * This test:
 * 1. Runs every registered action exactly once
 * 2. Captures response status, timing, errors
 * 3. Saves a baseline JSON for regression detection
 * 4. Categorizes bottlenecks by type
 * 5. Generates a comprehensive health report
 *
 * Run with: npx playwright test diagnostic_baseline.spec.ts
 */

import { test, expect } from '@playwright/test';
import { MICROACTION_REGISTRY, Microaction } from '../fixtures/microaction_registry';
import { ApiClient } from '../helpers/api-client';
import { ensureMinimalTestData, printDiscoverySummary, DiscoveredTestData } from '../helpers/test-data-discovery';
import * as fs from 'fs';
import * as path from 'path';

// ============================================================================
// TYPES
// ============================================================================

interface ActionResult {
  action_id: string;
  label: string;
  cluster: string;
  side_effect: string;

  // Execution results
  http_status: number;
  response_body: any;
  execution_time_ms: number;
  timestamp: string;

  // Classification
  bottleneck_type: BottleneckType;
  error_message?: string;

  // Metadata
  has_handler: boolean;
  is_stub: boolean;
  is_functional: boolean;
}

type BottleneckType =
  | 'WORKING'           // 200 with expected response
  | 'NOT_IMPLEMENTED'   // 404 - handler doesn't exist
  | 'STUB'              // 501 - handler exists but not implemented
  | 'VALIDATION_ERROR'  // 400 - payload rejected
  | 'AUTH_ERROR'        // 401/403 - permission issue
  | 'RUNTIME_ERROR'     // 500 - server crash
  | 'SLOW'              // 200 but > 2s
  | 'UNEXPECTED'        // Anything else
  | 'DB_ERROR'          // Database-related failure
  | 'RLS_ERROR';        // Row-level security violation

interface DiagnosticReport {
  meta: {
    timestamp: string;
    total_actions: number;
    test_duration_ms: number;
    environment: string;
  };

  summary: {
    working: number;
    not_implemented: number;
    stub: number;
    validation_error: number;
    auth_error: number;
    runtime_error: number;
    slow: number;
    db_error: number;
    rls_error: number;
    unexpected: number;
  };

  by_cluster: Record<string, {
    total: number;
    working: number;
    broken: number;
    coverage_percent: number;
  }>;

  results: ActionResult[];

  // Priority queue for fixes
  fix_priority: {
    critical: string[];    // Runtime errors, DB errors
    high: string[];        // Auth errors, RLS errors
    medium: string[];      // Not implemented (core features)
    low: string[];         // Stubs, slow responses
  };

  // Regression detection
  baseline_hash: string;
}

// ============================================================================
// TEST PAYLOADS - Using Discovered Real Data
// ============================================================================

/**
 * Generate test payloads using REAL IDs discovered from the database
 * This prevents PGRST116 errors from queries on non-existent records
 */
function getTestPayload(action: Microaction, data: DiscoveredTestData): Record<string, any> {
  const { yacht_id, user_id } = data;

  // Use discovered IDs or fallback placeholders (will fail gracefully)
  const faultId = data.fault_id || data.fault_open_id || 'no-fault-found';
  const faultOpenId = data.fault_open_id || faultId;
  const faultClosedId = data.fault_closed_id || faultId;
  const woId = data.work_order_id || data.work_order_open_id || 'no-wo-found';
  const woOpenId = data.work_order_open_id || woId;
  const equipmentId = data.equipment_id || 'no-equipment-found';
  const partId = data.part_id || 'no-part-found';
  const documentId = data.document_id || 'no-document-found';
  const handoverId = data.handover_id || 'no-handover-found';

  // Map action IDs to their payloads with real data
  const payloads: Record<string, Record<string, any>> = {
    // Fault actions - use real fault IDs
    'diagnose_fault': { fault_id: faultOpenId },
    'show_manual_section': { equipment_id: equipmentId },
    'view_fault_history': { equipment_id: equipmentId },
    'suggest_parts': { fault_id: faultId },
    'create_work_order_from_fault': {
      fault_id: faultId,
      title: 'Diagnostic Test WO',
      description: 'Created by diagnostic baseline test'
    },
    'add_fault_note': { fault_id: faultId, note_text: 'Diagnostic test note' },
    'add_fault_photo': { fault_id: faultId, photo_url: 'https://example.com/test.jpg' },
    'acknowledge_fault': { fault_id: faultOpenId },
    'report_fault': { equipment_id: equipmentId, description: 'Test fault from diagnostic' },
    'close_fault': { fault_id: faultOpenId },
    'update_fault': { fault_id: faultId, description: 'Updated by diagnostic test' },
    'reopen_fault': { fault_id: faultClosedId },
    'mark_fault_false_alarm': { fault_id: faultOpenId },
    'resolve_fault': { fault_id: faultOpenId, resolution: 'Fixed during diagnostic test' },
    'view_fault_detail': { fault_id: faultId },
    'list_faults': {},

    // Work order actions - use real work order IDs
    'create_work_order': {
      equipment_id: equipmentId,
      title: 'Diagnostic WO',
      description: 'Test work order from diagnostic'
    },
    'view_work_order_history': { equipment_id: equipmentId },
    'mark_work_order_complete': { work_order_id: woOpenId, completion_notes: 'Completed by diagnostic test run', signature: { user_id: data.user_id, timestamp: new Date().toISOString() } },
    'add_work_order_note': { work_order_id: woId, note_text: 'Diagnostic test note' },
    'add_work_order_photo': { work_order_id: woId, photo_url: 'https://example.com/test.jpg' },
    'add_parts_to_work_order': { work_order_id: woId, part_id: partId, parts: [{ part_id: partId, quantity: 1 }] },
    'view_work_order_checklist': { work_order_id: woId },
    'assign_work_order': { work_order_id: woOpenId, assigned_to: user_id },
    'start_work_order': { work_order_id: woOpenId },
    'update_work_order': { work_order_id: woId, title: 'Updated by diagnostic' },
    'close_work_order': { work_order_id: woOpenId },
    'cancel_work_order': { work_order_id: woOpenId },
    'view_work_order_detail': { work_order_id: woId },
    'add_note_to_work_order': { work_order_id: woId, note_text: 'Diagnostic test note' },
    'add_part_to_work_order': { work_order_id: woId, part_id: partId, quantity: 1 },
    'add_wo_hours': { work_order_id: woId, hours: 1 },
    'add_wo_part': { work_order_id: woId, part_id: partId, quantity: 1 },
    'add_wo_note': { work_order_id: woId, note_text: 'Diagnostic test note' },

    // Checklist actions - use placeholder checklist_id
    'view_checklist': { checklist_id: 'no-checklist-found' },
    'mark_checklist_item_complete': { checklist_item_id: 'no-checklist-item' },
    'add_checklist_note': { checklist_item_id: 'no-checklist-item', note_text: 'test' },
    'add_checklist_photo': { checklist_item_id: 'no-checklist-item', photo_url: 'test.jpg' },

    // Worklist actions
    'view_worklist': {},
    'add_worklist_task': { task_description: 'Test task from diagnostic', title: 'Test task', description: 'Test description' },
    'update_worklist_progress': { worklist_item_id: 'no-worklist-item', progress: 50 },
    'export_worklist': {},

    // Equipment actions - use real equipment ID
    'view_equipment_details': { equipment_id: equipmentId },
    'view_equipment_history': { equipment_id: equipmentId },
    'view_equipment_parts': { equipment_id: equipmentId },
    'view_linked_faults': { equipment_id: equipmentId },
    'view_equipment_manual': { equipment_id: equipmentId },
    'add_equipment_note': { equipment_id: equipmentId, note_text: 'Diagnostic test note' },
    'view_equipment': { equipment_id: equipmentId },
    'view_equipment_detail': { equipment_id: equipmentId },
    'update_equipment_status': { equipment_id: equipmentId, new_status: 'operational' },

    // Inventory actions - use real part ID
    'view_part_stock': { part_id: partId },
    'order_part': { part_id: partId, quantity: 1 },
    'view_part_location': { part_id: partId },
    'view_part_usage': { part_id: partId },
    'log_part_usage': { part_id: partId, quantity: 1, usage_reason: 'diagnostic_test' },
    'scan_part_barcode': { barcode: 'TEST123' },
    'view_linked_equipment': { part_id: partId },
    'check_stock_level': { part_id: partId },

    // Handover actions - use discovered handover_id
    'add_to_handover': { entity_type: 'fault', entity_id: faultId, title: 'Diagnostic handover item' },
    'add_document_to_handover': { handover_id: handoverId, document_id: documentId },
    'add_predictive_insight_to_handover': { handover_id: handoverId, insight_text: 'Diagnostic test insight' },
    'edit_handover_section': { handover_id: handoverId, section_name: 'notes' },
    'export_handover': { handover_id: handoverId },
    'regenerate_handover_summary': { handover_id: handoverId },
    'view_smart_summary': { entity_type: 'fault', entity_id: faultId },
    'upload_photo': { entity_type: 'fault', entity_id: faultId, photo_url: 'test.jpg' },
    'record_voice_note': { entity_type: 'fault', entity_id: faultId, audio_url: 'test.mp3' },

    // Compliance actions - use user_id as crew_id (same person)
    'view_hours_of_rest': { crew_id: user_id },
    'update_hours_of_rest': { crew_id: user_id, date: '2025-01-21', hours: 8 },
    'export_hours_of_rest': { crew_id: user_id },
    'view_compliance_status': {},
    'tag_for_survey': { equipment_id: equipmentId },

    // Purchase actions - use correct field names (purchase_request_id not purchase_order_id)
    'create_purchase_request': { title: 'Diagnostic Test Purchase Request' },
    'add_item_to_purchase': { purchase_request_id: 'no-pr-found', item_description: 'Test item' },
    'approve_purchase': { purchase_request_id: 'no-pr-found' },
    'upload_invoice': { purchase_request_id: 'no-pr-found', invoice_url: 'test.pdf' },
    'track_delivery': { purchase_request_id: 'no-pr-found' },
    'log_delivery_received': { purchase_request_id: 'no-pr-found' },
    'update_purchase_status': { purchase_request_id: 'no-pr-found', status: 'approved' },

    // Document actions - use real document ID
    'view_document': { document_id: documentId },
    'view_related_documents': { entity_type: 'equipment', entity_id: equipmentId },
    'view_document_section': { document_id: documentId, section_id: 'intro' },
    'upload_document': { filename: 'test.pdf', folder: 'documents' },
    'delete_document': { document_id: documentId },

    // Fleet actions
    'view_fleet_summary': {},
    'open_vessel': { vessel_id: yacht_id },
    'export_fleet_summary': {},

    // Predictive - use correct field names
    'request_predictive_insight': { entity_type: 'equipment', entity_id: equipmentId },
  };

  return payloads[action.id] || {};
}

// ============================================================================
// CLASSIFICATION LOGIC
// ============================================================================

function classifyResult(status: number, body: any, timing: number): BottleneckType {
  // Check for specific error patterns
  const detail = body?.detail?.toLowerCase() || '';
  const message = body?.message?.toLowerCase() || '';
  const errorText = detail + ' ' + message;

  // 404 - Not implemented
  if (status === 404) {
    if (errorText.includes('not found') || errorText.includes('not implemented')) {
      return 'NOT_IMPLEMENTED';
    }
  }

  // 501 - Stub
  if (status === 501) {
    return 'STUB';
  }

  // 400 - Validation
  if (status === 400) {
    if (errorText.includes('rls') || errorText.includes('policy')) {
      return 'RLS_ERROR';
    }
    return 'VALIDATION_ERROR';
  }

  // 401/403 - Auth
  if (status === 401 || status === 403) {
    if (errorText.includes('yacht') || errorText.includes('isolation')) {
      return 'RLS_ERROR';
    }
    return 'AUTH_ERROR';
  }

  // 500 - Runtime
  if (status === 500) {
    if (errorText.includes('database') || errorText.includes('supabase') || errorText.includes('postgres')) {
      return 'DB_ERROR';
    }
    return 'RUNTIME_ERROR';
  }

  // 200 but slow
  if (status === 200 && timing > 2000) {
    return 'SLOW';
  }

  // 200 - Working
  if (status === 200) {
    return 'WORKING';
  }

  return 'UNEXPECTED';
}

// ============================================================================
// MAIN TEST
// ============================================================================

test.describe('DIAGNOSTIC BASELINE', () => {
  let apiClient: ApiClient;
  let testData: DiscoveredTestData;
  const results: ActionResult[] = [];
  const startTime = Date.now();

  test.beforeAll(async () => {
    // Initialize API client with cached auth
    apiClient = new ApiClient();
    await apiClient.authenticate();

    // Discover or create test data
    console.log('\n📊 Discovering test data from tenant database...');
    testData = await ensureMinimalTestData();
    printDiscoverySummary(testData);
  });

  test('Run comprehensive system diagnostic', async () => {
    const yacht_id = testData.yacht_id;

    console.log('\n' + '='.repeat(60));
    console.log('DIAGNOSTIC BASELINE: Testing all', MICROACTION_REGISTRY.length, 'actions');
    console.log('Using discovered data:', {
      fault: testData.fault_id ? 'found' : 'none',
      work_order: testData.work_order_id ? 'found' : 'none',
      equipment: testData.equipment_id ? 'found' : 'none',
      part: testData.part_id ? 'found' : 'none',
    });
    console.log('='.repeat(60) + '\n');

    // Test each action
    for (const action of MICROACTION_REGISTRY) {
      const payload = getTestPayload(action, testData);
      const actionStart = Date.now();

      let response: { status: number; data: any };
      let error: string | undefined;

      try {
        // Merge yacht_id into payload - ApiClient extracts it and sends in context
        response = await apiClient.executeAction(action.id, { ...payload, yacht_id });
      } catch (e: any) {
        // Capture network/timeout errors
        response = { status: 0, data: { error: e.message } };
        error = e.message;
      }

      const timing = Date.now() - actionStart;
      const bottleneck = classifyResult(response.status, response.data, timing);

      const result: ActionResult = {
        action_id: action.id,
        label: action.label,
        cluster: action.cluster,
        side_effect: action.sideEffectType,
        http_status: response.status,
        response_body: response.data,
        execution_time_ms: timing,
        timestamp: new Date().toISOString(),
        bottleneck_type: bottleneck,
        error_message: error || response.data?.detail || response.data?.message,
        has_handler: response.status !== 404,
        is_stub: response.status === 501,
        is_functional: bottleneck === 'WORKING' || bottleneck === 'SLOW',
      };

      results.push(result);

      // Live progress output
      const icon = bottleneck === 'WORKING' ? '✓' :
                   bottleneck === 'SLOW' ? '⏱' :
                   bottleneck === 'NOT_IMPLEMENTED' ? '○' :
                   bottleneck === 'STUB' ? '◐' : '✗';
      console.log(`${icon} ${action.id.padEnd(35)} ${response.status} ${bottleneck.padEnd(18)} ${timing}ms`);
    }

    // Generate report
    const report = generateReport(results, startTime);

    // Save report
    const artifactDir = path.join(process.cwd(), 'test-results', 'diagnostic');
    if (!fs.existsSync(artifactDir)) {
      fs.mkdirSync(artifactDir, { recursive: true });
    }

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const reportPath = path.join(artifactDir, `baseline_${timestamp}.json`);
    const latestPath = path.join(artifactDir, 'baseline_latest.json');

    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    fs.writeFileSync(latestPath, JSON.stringify(report, null, 2));

    // Print summary
    printSummary(report);

    // Check for regressions against previous baseline
    const previousPath = path.join(artifactDir, 'baseline_previous.json');
    if (fs.existsSync(previousPath)) {
      const previous = JSON.parse(fs.readFileSync(previousPath, 'utf-8'));
      checkRegressions(previous, report);
    }

    // This test always passes - it's for diagnostics, not assertions
    // The value is in the report, not the pass/fail
    expect(true).toBe(true);
  });
});

// ============================================================================
// REPORT GENERATION
// ============================================================================

function generateReport(results: ActionResult[], startTime: number): DiagnosticReport {
  const summary = {
    working: results.filter(r => r.bottleneck_type === 'WORKING').length,
    not_implemented: results.filter(r => r.bottleneck_type === 'NOT_IMPLEMENTED').length,
    stub: results.filter(r => r.bottleneck_type === 'STUB').length,
    validation_error: results.filter(r => r.bottleneck_type === 'VALIDATION_ERROR').length,
    auth_error: results.filter(r => r.bottleneck_type === 'AUTH_ERROR').length,
    runtime_error: results.filter(r => r.bottleneck_type === 'RUNTIME_ERROR').length,
    slow: results.filter(r => r.bottleneck_type === 'SLOW').length,
    db_error: results.filter(r => r.bottleneck_type === 'DB_ERROR').length,
    rls_error: results.filter(r => r.bottleneck_type === 'RLS_ERROR').length,
    unexpected: results.filter(r => r.bottleneck_type === 'UNEXPECTED').length,
  };

  // By cluster analysis
  const clusters = [...new Set(results.map(r => r.cluster))];
  const by_cluster: Record<string, any> = {};

  for (const cluster of clusters) {
    const clusterResults = results.filter(r => r.cluster === cluster);
    const working = clusterResults.filter(r => r.is_functional).length;
    by_cluster[cluster] = {
      total: clusterResults.length,
      working,
      broken: clusterResults.length - working,
      coverage_percent: Math.round((working / clusterResults.length) * 100),
    };
  }

  // Priority queue
  const fix_priority = {
    critical: results
      .filter(r => ['RUNTIME_ERROR', 'DB_ERROR'].includes(r.bottleneck_type))
      .map(r => r.action_id),
    high: results
      .filter(r => ['AUTH_ERROR', 'RLS_ERROR'].includes(r.bottleneck_type))
      .map(r => r.action_id),
    medium: results
      .filter(r => r.bottleneck_type === 'NOT_IMPLEMENTED')
      .map(r => r.action_id),
    low: results
      .filter(r => ['STUB', 'SLOW', 'VALIDATION_ERROR'].includes(r.bottleneck_type))
      .map(r => r.action_id),
  };

  // Create hash for regression detection
  const hashInput = results.map(r => `${r.action_id}:${r.bottleneck_type}`).join('|');
  const baseline_hash = Buffer.from(hashInput).toString('base64').substring(0, 32);

  return {
    meta: {
      timestamp: new Date().toISOString(),
      total_actions: results.length,
      test_duration_ms: Date.now() - startTime,
      environment: process.env.NODE_ENV || 'test',
    },
    summary,
    by_cluster,
    results,
    fix_priority,
    baseline_hash,
  };
}

function printSummary(report: DiagnosticReport): void {
  console.log('\n' + '='.repeat(60));
  console.log('DIAGNOSTIC SUMMARY');
  console.log('='.repeat(60));

  console.log('\n📊 OVERALL STATUS:');
  console.log(`   ✓ Working:         ${report.summary.working}/${report.meta.total_actions}`);
  console.log(`   ○ Not Implemented: ${report.summary.not_implemented}`);
  console.log(`   ◐ Stub:            ${report.summary.stub}`);
  console.log(`   ✗ Validation:      ${report.summary.validation_error}`);
  console.log(`   🔐 Auth/RLS:        ${report.summary.auth_error + report.summary.rls_error}`);
  console.log(`   💥 Runtime:         ${report.summary.runtime_error}`);
  console.log(`   🗄 Database:        ${report.summary.db_error}`);
  console.log(`   ⏱ Slow:            ${report.summary.slow}`);

  console.log('\n📦 BY CLUSTER:');
  for (const [cluster, data] of Object.entries(report.by_cluster)) {
    const bar = '█'.repeat(Math.floor(data.coverage_percent / 5)) + '░'.repeat(20 - Math.floor(data.coverage_percent / 5));
    console.log(`   ${cluster.padEnd(20)} ${bar} ${data.coverage_percent}% (${data.working}/${data.total})`);
  }

  console.log('\n🔧 FIX PRIORITY:');
  if (report.fix_priority.critical.length > 0) {
    console.log(`   🚨 CRITICAL (${report.fix_priority.critical.length}): ${report.fix_priority.critical.slice(0, 5).join(', ')}${report.fix_priority.critical.length > 5 ? '...' : ''}`);
  }
  if (report.fix_priority.high.length > 0) {
    console.log(`   ⚠️  HIGH (${report.fix_priority.high.length}): ${report.fix_priority.high.slice(0, 5).join(', ')}${report.fix_priority.high.length > 5 ? '...' : ''}`);
  }
  if (report.fix_priority.medium.length > 0) {
    console.log(`   📋 MEDIUM (${report.fix_priority.medium.length}): ${report.fix_priority.medium.slice(0, 5).join(', ')}${report.fix_priority.medium.length > 5 ? '...' : ''}`);
  }
  if (report.fix_priority.low.length > 0) {
    console.log(`   📝 LOW (${report.fix_priority.low.length}): ${report.fix_priority.low.slice(0, 5).join(', ')}${report.fix_priority.low.length > 5 ? '...' : ''}`);
  }

  const healthScore = Math.round((report.summary.working / report.meta.total_actions) * 100);
  console.log('\n' + '='.repeat(60));
  console.log(`SYSTEM HEALTH SCORE: ${healthScore}%`);
  console.log(`Baseline hash: ${report.baseline_hash}`);
  console.log('='.repeat(60) + '\n');
}

function checkRegressions(previous: DiagnosticReport, current: DiagnosticReport): void {
  console.log('\n🔄 REGRESSION CHECK:');

  const regressions: string[] = [];
  const improvements: string[] = [];

  for (const currentResult of current.results) {
    const previousResult = previous.results.find(r => r.action_id === currentResult.action_id);
    if (!previousResult) continue;

    // Regression: was working, now broken
    if (previousResult.is_functional && !currentResult.is_functional) {
      regressions.push(`${currentResult.action_id}: ${previousResult.bottleneck_type} → ${currentResult.bottleneck_type}`);
    }

    // Improvement: was broken, now working
    if (!previousResult.is_functional && currentResult.is_functional) {
      improvements.push(`${currentResult.action_id}: ${previousResult.bottleneck_type} → ${currentResult.bottleneck_type}`);
    }
  }

  if (regressions.length === 0 && improvements.length === 0) {
    console.log('   No changes detected from previous baseline.');
  } else {
    if (regressions.length > 0) {
      console.log(`   ❌ REGRESSIONS (${regressions.length}):`);
      regressions.forEach(r => console.log(`      - ${r}`));
    }
    if (improvements.length > 0) {
      console.log(`   ✅ IMPROVEMENTS (${improvements.length}):`);
      improvements.forEach(i => console.log(`      + ${i}`));
    }
  }
}
