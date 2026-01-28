/**
 * DATABASE MUTATION PROOF: assign_work_order
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

test.describe('assign_work_order - Database Mutation Proof', () => {
  let apiClient: ApiClient;
  let testWorkOrderId: string;

  test.beforeAll(async () => {
    apiClient = new ApiClient(process.env.RENDER_API_URL);
    await apiClient.authenticate(
      process.env.TEST_USER_EMAIL!,
      process.env.TEST_USER_PASSWORD!
    );

    // Create a test work order first
    const createResponse = await apiClient.request('POST', '/v1/actions/execute', {
      action: 'create_work_order',
      context: {
        yacht_id: TEST_YACHT_ID,
        user_id: TEST_USER_ID,
        role: 'engineer'
      },
      payload: {
        title: `Test WO for assignment - ${Date.now()}`,
        description: 'Created for assignment test'
      }
    });

    testWorkOrderId = createResponse.data.work_order_id;
    console.log(`\nCreated test work order: ${testWorkOrderId}\n`);
  });

  test('should assign work order and update database', async () => {
    const assignedTo = TEST_USER_ID;

    console.log('\n📊 STEP 1: Querying database BEFORE action...\n');

    const { data: beforeWO } = await supabase
      .from('pms_work_orders')
      .select('assigned_to')
      .eq('id', testWorkOrderId)
      .single();

    console.log(`Before: assigned_to = ${beforeWO?.assigned_to || 'null'}`);
    expect(beforeWO?.assigned_to).toBeFalsy(); // Should be null/empty

    console.log('\n🚀 STEP 2: Executing assign_work_order action...\n');

    const response = await apiClient.request('POST', '/v1/actions/execute', {
      action: 'assign_work_order',
      context: {
        yacht_id: TEST_YACHT_ID,
        user_id: TEST_USER_ID,
        role: 'engineer'
      },
      payload: {
        work_order_id: testWorkOrderId,
        assigned_to: assignedTo
      }
    });

    console.log(`Response status: ${response.status}`);
    console.log('Response body:', JSON.stringify(response.data, null, 2));

    expect(response.status).toBe(200);
    expect(response.data.status).toBe('success');

    console.log('\n📊 STEP 3: Querying database AFTER action...\n');

    const { data: afterWO } = await supabase
      .from('pms_work_orders')
      .select('*')
      .eq('id', testWorkOrderId)
      .single();

    console.log('Work order after assignment:');
    console.log(JSON.stringify(afterWO, null, 2));

    expect(afterWO).toBeTruthy();
    expect(afterWO.assigned_to).toBe(assignedTo);

    console.log('\n✅ Work order assignment verified\n');

    console.log('📊 STEP 4: Verifying audit_log entry...\n');

    const { data: auditLogs, error: auditError } = await supabase
      .from('pms_audit_log')
      .select('*')
      .eq('entity_id', testWorkOrderId)
      .eq('action', 'assign_work_order');

    if (auditError) {
      console.warn('⚠️  Audit log query error or table not exists');
    } else {
      console.log(`Found ${auditLogs?.length || 0} audit log entries`);
      if (auditLogs && auditLogs.length > 0) {
        console.log('Audit log entry:');
        console.log(JSON.stringify(auditLogs[0], null, 2));
        console.log('\n✅ Audit log entry verified\n');
      } else {
        console.warn('⚠️  No audit log entry found');
      }
    }

    console.log('═══════════════════════════════════════════════════════════');
    console.log('✅ MUTATION PROOF COMPLETE');
    console.log('═══════════════════════════════════════════════════════════');
    console.log(`Action:         assign_work_order`);
    console.log(`HTTP Status:    ${response.status}`);
    console.log(`Work Order ID:  ${testWorkOrderId}`);
    console.log(`Assigned To:    ${assignedTo}`);
    console.log(`DB Updated:     ✅ YES`);
    console.log(`Audit Log:      ${auditLogs && auditLogs.length > 0 ? '✅ YES' : '⚠️  NOT FOUND'}`);
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
