/**
 * DATABASE PROOF: get_work_order_details (read-only)
 */

import { test, expect } from '@playwright/test';
import { createClient } from '@supabase/supabase-js';
import { ApiClient } from '../helpers/api-client';

const supabase = createClient(
  process.env.TENANT_SUPABASE_URL!,
  process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY!
);

const TEST_YACHT_ID = process.env.TEST_YACHT_ID!;
const TEST_USER_ID = process.env.TEST_USER_ID || 'a35cad0b-02ff-4287-b6e4-17c96fa6a424';

test.describe('get_work_order_details - Database Proof', () => {
  let apiClient: ApiClient;
  let testWorkOrderId: string;

  test.beforeAll(async () => {
    apiClient = new ApiClient(process.env.RENDER_API_URL);
    await apiClient.authenticate(
      process.env.TEST_USER_EMAIL!,
      process.env.TEST_USER_PASSWORD!
    );

    // Create a test work order
    const createResponse = await apiClient.request('POST', '/v1/actions/execute', {
      action: 'create_work_order',
      context: {
        yacht_id: TEST_YACHT_ID,
        user_id: TEST_USER_ID,
        role: 'engineer'
      },
      payload: {
        title: `Test WO for get - ${Date.now()}`,
        description: 'Created for get test'
      }
    });

    testWorkOrderId = createResponse.data.work_order_id;
    console.log(`\nCreated test work order: ${testWorkOrderId}\n`);
  });

  test('should retrieve work order details from database', async () => {
    console.log('\n🚀 Executing get_work_order action...\n');

    const response = await apiClient.request('POST', '/v1/actions/execute', {
      action: 'get_work_order',
      context: {
        yacht_id: TEST_YACHT_ID,
        user_id: TEST_USER_ID,
        role: 'engineer'
      },
      payload: {
        work_order_id: testWorkOrderId
      }
    });

    console.log(`Response status: ${response.status}`);
    console.log('Response body:', JSON.stringify(response.data, null, 2));

    expect(response.status).toBe(200);
    expect(response.data.status).toBe('success');
    expect(response.data.work_order).toBeTruthy();

    const workOrder = response.data.work_order;
    expect(workOrder.id).toBe(testWorkOrderId);
    expect(workOrder.title).toContain('Test WO for get');
    expect(workOrder.yacht_id).toBe(TEST_YACHT_ID);

    console.log('\n✅ Work order details retrieved successfully\n');

    console.log('📊 Verifying audit_log entry (should be N/A for read-only)...\n');

    const { data: auditLogs } = await supabase
      .from('pms_audit_log')
      .select('*')
      .eq('entity_id', testWorkOrderId)
      .eq('action', 'get_work_order');

    console.log(`Found ${auditLogs?.length || 0} audit log entries`);
    if (auditLogs && auditLogs.length > 0) {
      console.warn('⚠️  Unexpected: Read-only action created audit log');
    } else {
      console.log('✅ No audit log (expected for read-only action)');
    }

    console.log('═══════════════════════════════════════════════════════════');
    console.log('✅ READ PROOF COMPLETE');
    console.log('═══════════════════════════════════════════════════════════');
    console.log(`Action:         get_work_order`);
    console.log(`HTTP Status:    ${response.status}`);
    console.log(`Work Order ID:  ${testWorkOrderId}`);
    console.log(`Data Returned:  ✅ YES`);
    console.log(`Audit Log:      N/A (read-only)`);
    console.log('═══════════════════════════════════════════════════════════\n');
  });

  test.afterAll(async () => {
    // Clean up
    if (testWorkOrderId) {
      console.log(`\n🧹 Cleaning up test work order: ${testWorkOrderId}`);
      await supabase
        .from('pms_work_orders')
        .update({
          deleted_at: new Date().toISOString(),
          deleted_by: TEST_USER_ID,
          deletion_reason: 'Test cleanup'
        })
        .eq('id', testWorkOrderId);
      console.log('✅ Test work order soft deleted\n');
    }
  });
});
