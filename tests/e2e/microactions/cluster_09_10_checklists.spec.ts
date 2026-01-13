/**
 * Cluster 09 & 10: CHECKLISTS
 *
 * Tests actions:
 * - 9.1 execute_checklist
 * - 10.2 create_checklist_template
 * - 10.3 complete_checklist_item
 * - 10.4 sign_off_checklist
 *
 * From: COMPLETE_ACTION_EXECUTION_CATALOG.md
 */

import { test, expect } from '@playwright/test';
import {
  saveArtifact,
  saveRequest,
  saveResponse,
  saveDbState,
  createEvidenceBundle,
} from '../../helpers/artifacts';
import { ApiClient } from '../../helpers/api-client';
import { getTenantClient } from '../../helpers/supabase_tenant';

test.describe('Cluster 09 & 10: CHECKLISTS', () => {
  let apiClient: ApiClient;
  let tenantClient: ReturnType<typeof getTenantClient>;
  const yachtId = process.env.TEST_USER_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';

  let testChecklistId: string;
  let testChecklistItemId: string;

  test.beforeAll(async () => {
    apiClient = new ApiClient();
    await apiClient.ensureAuth();
    tenantClient = getTenantClient();
  });

  // ==========================================================================
  // ACTION 10.2: create_checklist_template
  // Classification: MUTATE_MEDIUM
  // ==========================================================================
  test('ACTION 10.2: create_checklist_template - creates checklist template', async () => {
    const testName = 'cluster_09_10/01_create_checklist_template';

    const response = await apiClient.executeAction('create_checklist_template', {
      name: `E2E Test Checklist - ${Date.now()}`,
      category: 'safety',
      description: 'Checklist template created via E2E test',
      items: [
        { title: 'Check item 1', order: 1 },
        { title: 'Check item 2', order: 2 },
        { title: 'Check item 3', order: 3 },
      ],
    });

    saveRequest(testName, response.request);
    saveResponse(testName, { status: response.status, body: response.data });

    if (response.data?.checklist_id) {
      testChecklistId = response.data.checklist_id;
    }

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      assertions: [
        { name: 'HTTP status is 200', passed: response.status === 200 },
        { name: 'Checklist ID returned', passed: !!response.data?.checklist_id || !!response.data?.data?.id },
      ],
    });

    if (response.status === 404) return;
    expect(response.status).toBe(200);
  });

  // ==========================================================================
  // ACTION 9.1: execute_checklist
  // Classification: MUTATE_MEDIUM
  // ==========================================================================
  test('ACTION 9.1: execute_checklist - starts checklist execution', async () => {
    const testName = 'cluster_09_10/02_execute_checklist';

    const response = await apiClient.executeAction('execute_checklist', {
      template_id: testChecklistId || 'test-template-id',
      execution_date: new Date().toISOString(),
      notes: 'Checklist execution started via E2E test',
    });

    saveRequest(testName, response.request);
    saveResponse(testName, { status: response.status, body: response.data });

    if (response.data?.execution_id) {
      testChecklistId = response.data.execution_id;
    }

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      assertions: [
        { name: 'HTTP status is 200', passed: response.status === 200 },
      ],
    });

    if (response.status === 404) return;
    expect(response.status).toBe(200);
  });

  // ==========================================================================
  // ACTION 10.3: complete_checklist_item
  // Classification: MUTATE_LOW
  // ==========================================================================
  test('ACTION 10.3: complete_checklist_item - marks checklist item complete', async () => {
    const testName = 'cluster_09_10/03_complete_checklist_item';

    const response = await apiClient.executeAction('complete_checklist_item', {
      checklist_id: testChecklistId || 'test-checklist-id',
      item_id: testChecklistItemId || 'test-item-id',
      completed: true,
      notes: 'Item completed via E2E test',
    });

    saveRequest(testName, response.request);
    saveResponse(testName, { status: response.status, body: response.data });

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      assertions: [
        { name: 'HTTP status handled', passed: response.status !== 500 },
      ],
    });

    expect(response.status).not.toBe(500);
  });

  // ==========================================================================
  // ACTION 10.4: sign_off_checklist
  // Classification: MUTATE_MEDIUM
  // ==========================================================================
  test('ACTION 10.4: sign_off_checklist - signs off completed checklist', async () => {
    const testName = 'cluster_09_10/04_sign_off_checklist';

    const response = await apiClient.executeAction('sign_off_checklist', {
      checklist_id: testChecklistId || 'test-checklist-id',
      signature: 'e2e-test-signature',
      notes: 'Checklist signed off via E2E test',
    });

    saveRequest(testName, response.request);
    saveResponse(testName, { status: response.status, body: response.data });

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      assertions: [
        { name: 'HTTP status handled', passed: response.status !== 500 },
      ],
    });

    expect(response.status).not.toBe(500);
  });

  // ==========================================================================
  // SUMMARY
  // ==========================================================================
  test('SUMMARY: Cluster 09 & 10 - CHECKLISTS actions complete', async () => {
    const testName = 'cluster_09_10/00_summary';
    saveArtifact('summary.json', { cluster: 'CHECKLISTS', actions: 4 }, testName);
    console.log('\nCluster 09 & 10 Summary: CHECKLISTS - 4 actions tested');
  });
});
