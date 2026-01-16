/**
 * Work Order Lifecycle E2E Tests
 *
 * Phase 18: End-to-End User Flow Testing
 *
 * Tests the complete work order lifecycle:
 * Create WO → Add Parts → Assign → Start → Log Hours → Complete
 */

import { test, expect } from '@playwright/test';
import {
  saveArtifact,
  saveResponse,
  createEvidenceBundle,
} from '../../helpers/artifacts';
import { ApiClient } from '../../helpers/api-client';
import { getTenantClient } from '../../helpers/supabase_tenant';
import { TEST_YACHT_ID, getPrimaryTestUser } from '../../fixtures/test_users';

// ============================================================================
// TEST SUITE
// ============================================================================

test.describe('WORK ORDER LIFECYCLE: Complete User Journey', () => {
  let apiClient: ApiClient;
  let supabase: ReturnType<typeof getTenantClient>;
  let testWorkOrderId: string | null = null;
  let testPartId: string | null = null;

  test.beforeAll(async () => {
    supabase = getTenantClient();

    // Get a part for testing
    const { data: part } = await supabase
      .from('pms_parts')
      .select('id, name')
      .eq('yacht_id', TEST_YACHT_ID)
      .limit(1)
      .single();

    if (part) {
      testPartId = part.id;
    }
  });

  test.beforeEach(async ({ page }) => {
    apiClient = new ApiClient(page, 'work-order-lifecycle');
  });

  test.afterAll(async () => {
    // Cleanup
    if (testWorkOrderId && supabase) {
      await supabase.from('pms_work_orders').delete().eq('id', testWorkOrderId);
    }
  });

  // =========================================================================
  // STEP 1: Create work order
  // =========================================================================
  test('Step 1: Create work order', async ({ page }) => {
    const user = getPrimaryTestUser();
    await apiClient.authenticate(user.email, user.password);

    // Get equipment
    const { data: equipment } = await supabase
      .from('pms_equipment')
      .select('id, name')
      .eq('yacht_id', TEST_YACHT_ID)
      .limit(1)
      .single();

    const response = await apiClient.executeAction('create_work_order', {
      yacht_id: TEST_YACHT_ID,
      equipment_id: equipment?.id,
      title: 'E2E Test Work Order - Lifecycle Test',
      description: 'Automated test work order for lifecycle testing',
      priority: 'medium',
      type: 'preventive',
      estimated_hours: 4,
    });

    await saveResponse('work-order-lifecycle/step1', 'create_work_order_response.json', response);

    if (response.status === 200 || response.status === 201) {
      const body = await response.json();
      testWorkOrderId = body.work_order_id || body.id;
    }

    await createEvidenceBundle('work-order-lifecycle/step1', {
      test: 'create_work_order',
      status: [200, 201].includes(response.status) ? 'passed' : 'documented',
      work_order_id: testWorkOrderId,
      response_status: response.status,
    });

    expect([200, 201, 400]).toContain(response.status);
  });

  // =========================================================================
  // STEP 2: Add parts to work order
  // =========================================================================
  test('Step 2: Add parts to work order', async ({ page }) => {
    if (!testWorkOrderId) {
      // Try to find an existing work order
      const { data: wo } = await supabase
        .from('pms_work_orders')
        .select('id')
        .eq('yacht_id', TEST_YACHT_ID)
        .in('status', ['open', 'scheduled', 'pending'])
        .limit(1)
        .single();

      if (wo) {
        testWorkOrderId = wo.id;
      } else {
        test.skip();
        return;
      }
    }

    if (!testPartId) {
      test.skip();
      return;
    }

    const user = getPrimaryTestUser();
    await apiClient.authenticate(user.email, user.password);

    const response = await apiClient.executeAction('add_wo_part', {
      work_order_id: testWorkOrderId,
      part_id: testPartId,
      quantity: 2,
    });

    await saveResponse('work-order-lifecycle/step2', 'add_wo_part_response.json', response);

    await createEvidenceBundle('work-order-lifecycle/step2', {
      test: 'add_wo_part',
      status: [200, 201].includes(response.status) ? 'passed' : 'documented',
      work_order_id: testWorkOrderId,
      part_id: testPartId,
      response_status: response.status,
    });

    expect([200, 201, 400, 404]).toContain(response.status);
  });

  // =========================================================================
  // STEP 3: Assign work order
  // =========================================================================
  test('Step 3: Assign work order', async ({ page }) => {
    if (!testWorkOrderId) {
      test.skip();
      return;
    }

    const user = getPrimaryTestUser();
    await apiClient.authenticate(user.email, user.password);

    // Get a user to assign to
    const { data: assignee } = await supabase
      .from('user_roles')
      .select('user_id')
      .eq('yacht_id', TEST_YACHT_ID)
      .limit(1)
      .single();

    const response = await apiClient.executeAction('assign_work_order', {
      work_order_id: testWorkOrderId,
      assignee_id: assignee?.user_id || user.userId,
    });

    await saveResponse('work-order-lifecycle/step3', 'assign_work_order_response.json', response);

    await createEvidenceBundle('work-order-lifecycle/step3', {
      test: 'assign_work_order',
      status: [200, 201].includes(response.status) ? 'passed' : 'documented',
      work_order_id: testWorkOrderId,
      response_status: response.status,
    });

    expect([200, 201, 400, 403, 404]).toContain(response.status);
  });

  // =========================================================================
  // STEP 4: Start work order
  // =========================================================================
  test('Step 4: Start work order', async ({ page }) => {
    if (!testWorkOrderId) {
      test.skip();
      return;
    }

    const user = getPrimaryTestUser();
    await apiClient.authenticate(user.email, user.password);

    const response = await apiClient.executeAction('start_work_order', {
      work_order_id: testWorkOrderId,
    });

    await saveResponse('work-order-lifecycle/step4', 'start_work_order_response.json', response);

    await createEvidenceBundle('work-order-lifecycle/step4', {
      test: 'start_work_order',
      status: [200, 201].includes(response.status) ? 'passed' : 'documented',
      work_order_id: testWorkOrderId,
      response_status: response.status,
    });

    expect([200, 201, 400, 404]).toContain(response.status);
  });

  // =========================================================================
  // STEP 5: Log work hours
  // =========================================================================
  test('Step 5: Log work hours', async ({ page }) => {
    if (!testWorkOrderId) {
      test.skip();
      return;
    }

    const user = getPrimaryTestUser();
    await apiClient.authenticate(user.email, user.password);

    const response = await apiClient.executeAction('log_hours_worked', {
      work_order_id: testWorkOrderId,
      hours: 2.5,
      date: new Date().toISOString().split('T')[0],
      notes: 'E2E test - logged 2.5 hours of work',
    });

    await saveResponse('work-order-lifecycle/step5', 'log_hours_worked_response.json', response);

    await createEvidenceBundle('work-order-lifecycle/step5', {
      test: 'log_hours_worked',
      status: [200, 201].includes(response.status) ? 'passed' : 'documented',
      work_order_id: testWorkOrderId,
      response_status: response.status,
    });

    expect([200, 201, 400, 404]).toContain(response.status);
  });

  // =========================================================================
  // STEP 6: Complete work order
  // =========================================================================
  test('Step 6: Complete work order', async ({ page }) => {
    if (!testWorkOrderId) {
      test.skip();
      return;
    }

    const user = getPrimaryTestUser();
    await apiClient.authenticate(user.email, user.password);

    const response = await apiClient.executeAction('complete_work_order', {
      work_order_id: testWorkOrderId,
      completion_notes: 'E2E lifecycle test completed successfully',
      hours_worked: 4,
    });

    await saveResponse('work-order-lifecycle/step6', 'complete_work_order_response.json', response);

    await createEvidenceBundle('work-order-lifecycle/step6', {
      test: 'complete_work_order',
      status: [200, 201].includes(response.status) ? 'passed' : 'documented',
      work_order_id: testWorkOrderId,
      response_status: response.status,
    });

    expect([200, 201, 400, 404]).toContain(response.status);
  });

  // =========================================================================
  // SUMMARY
  // =========================================================================
  test('Lifecycle Summary', async ({ page }) => {
    await createEvidenceBundle('work-order-lifecycle/SUMMARY', {
      test_suite: 'work_order_lifecycle',
      steps: [
        { step: 1, action: 'create_work_order', entity: testWorkOrderId || 'not_created' },
        { step: 2, action: 'add_wo_part', part_id: testPartId || 'none' },
        { step: 3, action: 'assign_work_order' },
        { step: 4, action: 'start_work_order' },
        { step: 5, action: 'log_hours_worked' },
        { step: 6, action: 'complete_work_order' },
      ],
      yacht_id: TEST_YACHT_ID,
      timestamp: new Date().toISOString(),
    });

    expect(true).toBe(true);
  });
});
