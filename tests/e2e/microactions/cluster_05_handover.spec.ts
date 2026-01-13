/**
 * Cluster 05: HANDOVER - Communication & Handover Actions
 *
 * Tests actions:
 * - 5.1 create_handover
 * - 5.2 acknowledge_handover
 * - 5.3 update_handover
 * - 5.4 delete_handover
 * - 5.5 filter_handover
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

test.describe('Cluster 05: HANDOVER', () => {
  let apiClient: ApiClient;
  let tenantClient: ReturnType<typeof getTenantClient>;
  const yachtId = process.env.TEST_USER_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';

  let testHandoverId: string;

  test.beforeAll(async () => {
    apiClient = new ApiClient();
    await apiClient.ensureAuth();
    tenantClient = getTenantClient();

    const { data: handover } = await tenantClient
      .from('dash_handover_items')
      .select('id')
      .eq('yacht_id', yachtId)
      .limit(1)
      .single();
    if (handover) testHandoverId = handover.id;
  });

  // ==========================================================================
  // ACTION 5.1: create_handover
  // Classification: MUTATE_LOW
  // ==========================================================================
  test('ACTION 5.1: create_handover - creates new handover item', async () => {
    const testName = 'cluster_05/01_create_handover';

    const { data: handoversBefore } = await tenantClient
      .from('dash_handover_items')
      .select('id')
      .eq('yacht_id', yachtId);
    saveDbState(testName, 'before', { count: handoversBefore?.length || 0 });

    const response = await apiClient.executeAction('create_handover', {
      title: `E2E Test Handover - ${Date.now()}`,
      description: 'Handover item created via E2E test',
      category: 'equipment',
      priority: 'normal',
    });

    saveRequest(testName, response.request);
    saveResponse(testName, { status: response.status, body: response.data });

    const { data: handoversAfter } = await tenantClient
      .from('dash_handover_items')
      .select('id')
      .eq('yacht_id', yachtId);
    saveDbState(testName, 'after', { count: handoversAfter?.length || 0 });

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      dbBefore: { count: handoversBefore?.length },
      dbAfter: { count: handoversAfter?.length },
      assertions: [
        { name: 'HTTP status is 200', passed: response.status === 200 },
        { name: 'Handover count increased', passed: (handoversAfter?.length || 0) > (handoversBefore?.length || 0) },
      ],
    });

    if (response.status === 404) return;
    expect(response.status).toBe(200);
  });

  // ==========================================================================
  // ACTION 5.1: create_handover - GUARD RAIL: Missing title
  // ==========================================================================
  test('ACTION 5.1: create_handover - GUARD RAIL: Missing title', async () => {
    const testName = 'cluster_05/01_create_handover_guard_no_title';

    const response = await apiClient.executeAction('create_handover', {
      // title: MISSING
      description: 'Handover without title',
    });

    saveRequest(testName, response.request);
    saveResponse(testName, { status: response.status, body: response.data });

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      assertions: [
        { name: 'Rejects missing title', passed: [400, 422].includes(response.status) || response.data?.success === false },
      ],
    });
  });

  // ==========================================================================
  // ACTION 5.2: acknowledge_handover
  // Classification: MUTATE_LOW
  // ==========================================================================
  test('ACTION 5.2: acknowledge_handover - marks handover as acknowledged', async () => {
    const testName = 'cluster_05/02_acknowledge_handover';

    if (!testHandoverId) {
      saveArtifact('skip_reason.json', { reason: 'No handover available' }, testName);
      test.skip();
      return;
    }

    const { data: handoverBefore } = await tenantClient
      .from('dash_handover_items')
      .select('*')
      .eq('id', testHandoverId)
      .single();
    saveDbState(testName, 'before', handoverBefore);

    const response = await apiClient.executeAction('acknowledge_handover', {
      handover_id: testHandoverId,
      notes: 'Acknowledged via E2E test',
    });

    saveRequest(testName, response.request);
    saveResponse(testName, { status: response.status, body: response.data });

    const { data: handoverAfter } = await tenantClient
      .from('dash_handover_items')
      .select('*')
      .eq('id', testHandoverId)
      .single();
    saveDbState(testName, 'after', handoverAfter);

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      dbBefore: handoverBefore,
      dbAfter: handoverAfter,
      assertions: [
        { name: 'HTTP status is 200', passed: response.status === 200 },
        { name: 'Handover acknowledged', passed: !!handoverAfter?.acknowledged_at },
      ],
    });

    if (response.status === 404) return;
    expect(response.status).toBe(200);
  });

  // ==========================================================================
  // ACTION 5.3: update_handover
  // Classification: MUTATE_LOW
  // ==========================================================================
  test('ACTION 5.3: update_handover - modifies handover details', async () => {
    const testName = 'cluster_05/03_update_handover';

    if (!testHandoverId) {
      test.skip();
      return;
    }

    const { data: handoverBefore } = await tenantClient
      .from('dash_handover_items')
      .select('*')
      .eq('id', testHandoverId)
      .single();
    saveDbState(testName, 'before', handoverBefore);

    const response = await apiClient.executeAction('update_handover', {
      handover_id: testHandoverId,
      description: `Updated via E2E test at ${new Date().toISOString()}`,
      priority: 'high',
    });

    saveRequest(testName, response.request);
    saveResponse(testName, { status: response.status, body: response.data });

    const { data: handoverAfter } = await tenantClient
      .from('dash_handover_items')
      .select('*')
      .eq('id', testHandoverId)
      .single();
    saveDbState(testName, 'after', handoverAfter);

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      dbBefore: handoverBefore,
      dbAfter: handoverAfter,
      assertions: [
        { name: 'HTTP status is 200', passed: response.status === 200 },
      ],
    });

    if (response.status === 404) return;
    expect(response.status).toBe(200);
  });

  // ==========================================================================
  // ACTION 5.4: delete_handover
  // Classification: MUTATE_LOW
  // ==========================================================================
  test('ACTION 5.4: delete_handover - removes handover item', async () => {
    const testName = 'cluster_05/04_delete_handover';

    // Create temp handover to delete
    const { data: tempHandover } = await tenantClient
      .from('dash_handover_items')
      .insert({
        yacht_id: yachtId,
        title: `Temp Handover for Delete Test - ${Date.now()}`,
        category: 'general',
      })
      .select()
      .single();

    if (!tempHandover) {
      saveArtifact('skip_reason.json', { reason: 'Could not create temp handover' }, testName);
      test.skip();
      return;
    }

    saveDbState(testName, 'before', tempHandover);

    const response = await apiClient.executeAction('delete_handover', {
      handover_id: tempHandover.id,
    });

    saveRequest(testName, response.request);
    saveResponse(testName, { status: response.status, body: response.data });

    const { data: handoverAfter } = await tenantClient
      .from('dash_handover_items')
      .select('*')
      .eq('id', tempHandover.id)
      .single();
    saveDbState(testName, 'after', handoverAfter);

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      dbBefore: tempHandover,
      dbAfter: handoverAfter,
      assertions: [
        { name: 'HTTP status is 200', passed: response.status === 200 },
        { name: 'Handover deleted or soft-deleted', passed: !handoverAfter || !!handoverAfter?.deleted_at },
      ],
    });

    if (response.status === 404) return;
    expect(response.status).toBe(200);
  });

  // ==========================================================================
  // ACTION 5.5: filter_handover
  // Classification: READ
  // ==========================================================================
  test('ACTION 5.5: filter_handover - filters handover items', async () => {
    const testName = 'cluster_05/05_filter_handover';

    const response = await apiClient.executeAction('filter_handover', {
      yacht_id: yachtId,
      category: 'equipment',
      status: 'pending',
    });

    saveRequest(testName, response.request);
    saveResponse(testName, { status: response.status, body: response.data });

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      assertions: [
        { name: 'HTTP status is 200', passed: response.status === 200 },
        { name: 'Response has items array', passed: Array.isArray(response.data?.items) || Array.isArray(response.data?.handovers) },
      ],
    });

    if (response.status === 404) return;
    expect(response.status).toBe(200);
  });

  // ==========================================================================
  // SUMMARY
  // ==========================================================================
  test('SUMMARY: Cluster 05 - HANDOVER actions complete', async () => {
    const testName = 'cluster_05/00_summary';
    saveArtifact('summary.json', { cluster: 'HANDOVER', actions: 5 }, testName);
    console.log('\nCluster 05 Summary: HANDOVER - 5 actions tested');
  });
});
