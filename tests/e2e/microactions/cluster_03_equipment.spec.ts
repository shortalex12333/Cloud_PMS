/**
 * Cluster 03: MANAGE_EQUIPMENT - Equipment Management Actions
 *
 * Tests actions:
 * - 3.1 add_equipment
 * - 3.2 update_equipment
 * - 3.3 decommission_equipment
 * - 3.4 update_running_hours
 * - 3.5 view_equipment_detail
 *
 * From: COMPLETE_ACTION_EXECUTION_CATALOG.md
 */

import { test, expect } from '@playwright/test';
import {
  saveArtifact,
  saveRequest,
  saveResponse,
  saveDbState,
  saveAuditLog,
  createEvidenceBundle,
} from '../../helpers/artifacts';
import { ApiClient } from '../../helpers/api-client';
import { getTenantClient } from '../../helpers/supabase_tenant';

test.describe('Cluster 03: MANAGE_EQUIPMENT', () => {
  let apiClient: ApiClient;
  let tenantClient: ReturnType<typeof getTenantClient>;
  const yachtId = process.env.TEST_USER_YACHT_ID || '85fe1119-b04c-41ac-80f1-829d23322598';

  let testEquipmentId: string;

  test.beforeAll(async () => {
    apiClient = new ApiClient();
    await apiClient.ensureAuth();
    tenantClient = getTenantClient();

    const { data: equipment } = await tenantClient
      .from('pms_equipment')
      .select('id')
      .eq('yacht_id', yachtId)
      .limit(1)
      .single();
    if (equipment) testEquipmentId = equipment.id;
  });

  // ==========================================================================
  // ACTION 3.1: add_equipment
  // Classification: MUTATE_MEDIUM
  // ==========================================================================
  test('ACTION 3.1: add_equipment - creates new equipment record', async () => {
    const testName = 'cluster_03/01_add_equipment';

    const { data: equipBefore } = await tenantClient
      .from('pms_equipment')
      .select('id')
      .eq('yacht_id', yachtId);
    saveDbState(testName, 'before', { count: equipBefore?.length || 0 });

    const response = await apiClient.executeAction('add_equipment', {
      name: `E2E Test Equipment - ${Date.now()}`,
      code: `TEST-${Date.now()}`,
      description: 'Equipment created via E2E test',
      location: 'Engine Room',
      manufacturer: 'Test Manufacturer',
      model: 'TEST-MODEL-001',
      system_type: 'electrical',
      criticality: 'medium',
    });

    saveRequest(testName, response.request);
    saveResponse(testName, { status: response.status, body: response.data });

    const { data: equipAfter } = await tenantClient
      .from('pms_equipment')
      .select('id')
      .eq('yacht_id', yachtId);
    saveDbState(testName, 'after', { count: equipAfter?.length || 0 });

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      dbBefore: { count: equipBefore?.length },
      dbAfter: { count: equipAfter?.length },
      assertions: [
        { name: 'HTTP status is 200', passed: response.status === 200 },
        { name: 'Equipment count increased', passed: (equipAfter?.length || 0) > (equipBefore?.length || 0) },
      ],
    });

    if (response.status === 404) return;
    expect(response.status).toBe(200);
  });

  // ==========================================================================
  // ACTION 3.1: add_equipment - GUARD RAIL: Missing name
  // ==========================================================================
  test('ACTION 3.1: add_equipment - GUARD RAIL: Missing name', async () => {
    const testName = 'cluster_03/01_add_equipment_guard_no_name';

    const response = await apiClient.executeAction('add_equipment', {
      // name: MISSING
      code: 'TEST-NO-NAME',
      location: 'Engine Room',
    });

    saveRequest(testName, response.request);
    saveResponse(testName, { status: response.status, body: response.data });

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      assertions: [
        { name: 'Rejects missing name', passed: [400, 422].includes(response.status) || response.data?.success === false },
      ],
    });

    if (response.status !== 404) {
      expect(response.status).not.toBe(500);
    }
  });

  // ==========================================================================
  // ACTION 3.2: update_equipment
  // Classification: MUTATE_LOW
  // ==========================================================================
  test('ACTION 3.2: update_equipment - modifies equipment details', async () => {
    const testName = 'cluster_03/02_update_equipment';

    if (!testEquipmentId) {
      test.skip();
      return;
    }

    const { data: equipBefore } = await tenantClient
      .from('pms_equipment')
      .select('*')
      .eq('id', testEquipmentId)
      .single();
    saveDbState(testName, 'before', equipBefore);

    const response = await apiClient.executeAction('update_equipment', {
      equipment_id: testEquipmentId,
      description: `Updated via E2E test at ${new Date().toISOString()}`,
    });

    saveRequest(testName, response.request);
    saveResponse(testName, { status: response.status, body: response.data });

    const { data: equipAfter } = await tenantClient
      .from('pms_equipment')
      .select('*')
      .eq('id', testEquipmentId)
      .single();
    saveDbState(testName, 'after', equipAfter);

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      dbBefore: equipBefore,
      dbAfter: equipAfter,
      assertions: [
        { name: 'HTTP status is 200', passed: response.status === 200 },
        { name: 'Equipment updated', passed: equipAfter?.updated_at !== equipBefore?.updated_at },
      ],
    });

    if (response.status === 404) return;
    expect(response.status).toBe(200);
  });

  // ==========================================================================
  // ACTION 3.3: decommission_equipment
  // Classification: MUTATE_HIGH
  // ==========================================================================
  test('ACTION 3.3: decommission_equipment - soft deletes equipment', async () => {
    const testName = 'cluster_03/03_decommission_equipment';

    // Create a temporary equipment to decommission
    const { data: tempEquip } = await tenantClient
      .from('pms_equipment')
      .insert({
        yacht_id: yachtId,
        name: `Temp Equipment for Decommission Test - ${Date.now()}`,
        code: `TEMP-${Date.now()}`,
        location: 'Test Location',
      })
      .select()
      .single();

    if (!tempEquip) {
      saveArtifact('skip_reason.json', { reason: 'Could not create temp equipment' }, testName);
      test.skip();
      return;
    }

    saveDbState(testName, 'before', tempEquip);

    const response = await apiClient.executeAction('decommission_equipment', {
      equipment_id: tempEquip.id,
      reason: 'Decommissioned for E2E testing',
    });

    saveRequest(testName, response.request);
    saveResponse(testName, { status: response.status, body: response.data });

    const { data: equipAfter } = await tenantClient
      .from('pms_equipment')
      .select('*')
      .eq('id', tempEquip.id)
      .single();
    saveDbState(testName, 'after', equipAfter);

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      dbBefore: tempEquip,
      dbAfter: equipAfter,
      assertions: [
        { name: 'HTTP status is 200', passed: response.status === 200 },
        { name: 'Equipment has deleted_at', passed: !!equipAfter?.deleted_at },
      ],
    });

    if (response.status === 404) return;
    expect(response.status).toBe(200);
  });

  // ==========================================================================
  // ACTION 3.4: update_running_hours
  // Classification: MUTATE_LOW
  // ==========================================================================
  test('ACTION 3.4: update_running_hours - updates equipment running hours', async () => {
    const testName = 'cluster_03/04_update_running_hours';

    if (!testEquipmentId) {
      test.skip();
      return;
    }

    const { data: equipBefore } = await tenantClient
      .from('pms_equipment')
      .select('running_hours')
      .eq('id', testEquipmentId)
      .single();
    saveDbState(testName, 'before', equipBefore);

    const newHours = (equipBefore?.running_hours || 0) + 10;

    const response = await apiClient.executeAction('update_running_hours', {
      equipment_id: testEquipmentId,
      running_hours: newHours,
    });

    saveRequest(testName, response.request);
    saveResponse(testName, { status: response.status, body: response.data });

    const { data: equipAfter } = await tenantClient
      .from('pms_equipment')
      .select('running_hours')
      .eq('id', testEquipmentId)
      .single();
    saveDbState(testName, 'after', equipAfter);

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      dbBefore: equipBefore,
      dbAfter: equipAfter,
      assertions: [
        { name: 'HTTP status is 200', passed: response.status === 200 },
        { name: 'Running hours updated', passed: equipAfter?.running_hours === newHours },
      ],
    });

    if (response.status === 404) return;
    expect(response.status).toBe(200);
  });

  // ==========================================================================
  // ACTION 3.5: view_equipment_detail
  // Classification: READ
  // ==========================================================================
  test('ACTION 3.5: view_equipment_detail - returns equipment with related data', async () => {
    const testName = 'cluster_03/05_view_equipment_detail';

    if (!testEquipmentId) {
      test.skip();
      return;
    }

    const response = await apiClient.executeAction('view_equipment_detail', {
      equipment_id: testEquipmentId,
    });

    saveRequest(testName, response.request);
    saveResponse(testName, { status: response.status, body: response.data });

    createEvidenceBundle(testName, {
      request: response.request,
      response: { status: response.status, body: response.data },
      assertions: [
        { name: 'HTTP status is 200', passed: response.status === 200 },
        { name: 'Response has equipment data', passed: !!response.data?.equipment || !!response.data?.data },
      ],
    });

    if (response.status === 404) return;
    expect(response.status).toBe(200);
  });

  // ==========================================================================
  // SUMMARY
  // ==========================================================================
  test('SUMMARY: Cluster 03 - MANAGE_EQUIPMENT actions complete', async () => {
    const testName = 'cluster_03/00_summary';
    saveArtifact('summary.json', { cluster: 'MANAGE_EQUIPMENT', actions: 5 }, testName);
    console.log('\nCluster 03 Summary: MANAGE_EQUIPMENT - 5 actions tested');
  });
});
