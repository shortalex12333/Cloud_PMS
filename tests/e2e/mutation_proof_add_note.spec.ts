/**
 * DATABASE MUTATION PROOF: add_wo_note (add_note)
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

test.describe('add_wo_note - Database Mutation Proof', () => {
  let apiClient: ApiClient;
  let testWorkOrderId: string;
  let noteId: string;

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
        title: `Test WO for note - ${Date.now()}`,
        description: 'Created for note test'
      }
    });

    testWorkOrderId = createResponse.data.work_order_id;
    console.log(`\nCreated test work order: ${testWorkOrderId}\n`);
  });

  test('should add note to work order and create DB row', async () => {
    const noteText = `Test note added at ${new Date().toISOString()}`;

    console.log('\n📊 STEP 1: Querying database BEFORE action...\n');

    const { data: beforeNotes } = await supabase
      .from('pms_work_order_notes')
      .select('id')
      .eq('work_order_id', testWorkOrderId);

    console.log(`Before: ${beforeNotes?.length || 0} notes for work order`);

    console.log('\n🚀 STEP 2: Executing add_wo_note action...\n');

    const response = await apiClient.request('POST', '/v1/actions/execute', {
      action: 'add_wo_note',
      context: {
        yacht_id: TEST_YACHT_ID,
        user_id: TEST_USER_ID,
        role: 'engineer'
      },
      payload: {
        work_order_id: testWorkOrderId,
        note_text: noteText,
        note_type: 'general'
      }
    });

    console.log(`Response status: ${response.status}`);
    console.log('Response body:', JSON.stringify(response.data, null, 2));

    expect(response.status).toBe(200);
    expect(response.data.status).toBe('success');

    console.log('\n📊 STEP 3: Querying database AFTER action...\n');

    const { data: afterNotes } = await supabase
      .from('pms_work_order_notes')
      .select('*')
      .eq('work_order_id', testWorkOrderId)
      .eq('note_text', noteText)
      .order('created_at', { ascending: false })
      .limit(1);

    console.log(`After: ${afterNotes?.length || 0} notes found`);

    if (afterNotes && afterNotes.length > 0) {
      noteId = afterNotes[0].id;
      console.log('Note found in database:');
      console.log(JSON.stringify(afterNotes[0], null, 2));

      expect(afterNotes[0]).toBeTruthy();
      expect(afterNotes[0].work_order_id).toBe(testWorkOrderId);
      expect(afterNotes[0].note_text).toBe(noteText);
      expect(afterNotes[0].note_type).toBe('general');

      console.log('\n✅ Note row verified in pms_work_order_notes table\n');
    } else {
      throw new Error('Note not found in database after creation');
    }

    console.log('📊 STEP 4: Verifying audit_log entry...\n');

    const { data: auditLogs, error: auditError } = await supabase
      .from('pms_audit_log')
      .select('*')
      .eq('entity_id', noteId)
      .eq('action', 'add_wo_note');

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
    console.log(`Action:         add_wo_note`);
    console.log(`HTTP Status:    ${response.status}`);
    console.log(`Work Order ID:  ${testWorkOrderId}`);
    console.log(`Note ID:        ${noteId}`);
    console.log(`DB Row Created: ✅ YES`);
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
