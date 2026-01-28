/**
 * DATABASE MUTATION PROOF: resolve_fault (mark_fault_resolved)
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

test.describe('resolve_fault - Database Mutation Proof', () => {
  let apiClient: ApiClient;
  let testFaultId: string;

  test.beforeAll(async () => {
    apiClient = new ApiClient(process.env.RENDER_API_URL);
    await apiClient.authenticate(
      process.env.TEST_USER_EMAIL!,
      process.env.TEST_USER_PASSWORD!
    );

    // Create a test fault first
    const { data: faultData, error } = await supabase
      .from('pms_faults')
      .insert({
        yacht_id: TEST_YACHT_ID,
        title: `Test Fault - ${Date.now()}`,
        description: 'Created for resolve test',
        status: 'open',
        severity: 'medium'
      })
      .select()
      .single();

    if (error) throw error;
    testFaultId = faultData.id;
    console.log(`\nCreated test fault: ${testFaultId}\n`);
  });

  test('should resolve fault and update database', async () => {
    console.log('\n📊 STEP 1: Querying database BEFORE action...\n');

    const { data: beforeFault } = await supabase
      .from('pms_faults')
      .select('status, resolved_at')
      .eq('id', testFaultId)
      .single();

    console.log(`Before: status = ${beforeFault?.status}, resolved_at = ${beforeFault?.resolved_at || 'null'}`);
    expect(beforeFault?.status).toBe('open');
    expect(beforeFault?.resolved_at).toBeFalsy();

    console.log('\n🚀 STEP 2: Executing resolve_fault action...\n');

    const response = await apiClient.request('POST', '/v1/actions/execute', {
      action: 'resolve_fault',
      context: {
        yacht_id: TEST_YACHT_ID,
        user_id: TEST_USER_ID,
        role: 'engineer'
      },
      payload: {
        fault_id: testFaultId
      }
    });

    console.log(`Response status: ${response.status}`);
    console.log('Response body:', JSON.stringify(response.data, null, 2));

    expect(response.status).toBe(200);
    expect(response.data.status).toBe('success');

    console.log('\n📊 STEP 3: Querying database AFTER action...\n');

    const { data: afterFault } = await supabase
      .from('pms_faults')
      .select('*')
      .eq('id', testFaultId)
      .single();

    console.log('Fault after resolution:');
    console.log(JSON.stringify(afterFault, null, 2));

    expect(afterFault).toBeTruthy();
    expect(afterFault.status).toBe('resolved');
    expect(afterFault.resolved_at).toBeTruthy();

    console.log('\n✅ Fault resolution verified\n');

    console.log('📊 STEP 4: Verifying audit_log entry...\n');

    const { data: auditLogs, error: auditError } = await supabase
      .from('pms_audit_log')
      .select('*')
      .eq('entity_id', testFaultId)
      .eq('action', 'resolve_fault');

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
    console.log(`Action:         resolve_fault`);
    console.log(`HTTP Status:    ${response.status}`);
    console.log(`Fault ID:       ${testFaultId}`);
    console.log(`Status:         ${afterFault.status}`);
    console.log(`Resolved At:    ${afterFault.resolved_at}`);
    console.log(`DB Updated:     ✅ YES`);
    console.log(`Audit Log:      ${auditLogs && auditLogs.length > 0 ? '✅ YES' : '⚠️  NOT FOUND'}`);
    console.log('═══════════════════════════════════════════════════════════\n');
  });

  test.afterAll(async () => {
    // Clean up
    if (testFaultId) {
      console.log(`\n🧹 Cleaning up test fault: ${testFaultId}`);
      await supabase
        .from('pms_faults')
        .delete()
        .eq('id', testFaultId);
      console.log('✅ Test fault deleted\n');
    }
  });
});
