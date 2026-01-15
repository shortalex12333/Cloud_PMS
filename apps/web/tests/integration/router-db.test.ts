/**
 * Router + Database Integration Tests
 *
 * Tests action router execution against real Supabase database.
 */

import { describe, it, expect, afterEach } from 'vitest';
import {
  getTestClient,
  generateTestId,
  TEST_CONFIG,
  TEST_USER_CONTEXT,
  TEST_MANAGER_CONTEXT,
} from './setup';

describe('Router + Database Integration', () => {
  const createdIds: Record<string, string[]> = {
    action_executions: [],
    situation_detections: [],
    suggestion_log: [],
  };

  // Skip if no service key
  const skipIfNoCredentials =
    !TEST_CONFIG.SUPABASE_SERVICE_KEY ||
    TEST_CONFIG.SUPABASE_SERVICE_KEY.includes('undefined');

  afterEach(async () => {
    const client = getTestClient();
    for (const [table, ids] of Object.entries(createdIds)) {
      if (ids.length > 0) {
        await client.from(table).delete().in('id', ids);
        createdIds[table] = [];
      }
    }
  });

  // ============================================================================
  // Action Execution Flow Tests
  // ============================================================================

  describe('Action Execution Flow', () => {
    it.skipIf(skipIfNoCredentials)('should log successful action execution', async () => {
      const client = getTestClient();
      const testId = generateTestId();

      // Simulate action execution logging
      const { data, error } = await client
        .from('action_executions')
        .insert({
          id: testId,
          yacht_id: TEST_CONFIG.TEST_YACHT_ID,
          user_id: TEST_USER_CONTEXT.user_id,
          action_name: 'add_note',
          entity_type: 'equipment',
          entity_id: generateTestId(),
          params: {
            note_text: 'Test note from integration test',
            equipment_id: generateTestId(),
          },
          result: {
            note_id: generateTestId(),
            created_at: new Date().toISOString(),
          },
          success: true,
          duration_ms: 150,
        })
        .select()
        .single();

      expect(error).toBeNull();
      expect(data.action_name).toBe('add_note');
      expect(data.success).toBe(true);
      expect(data.duration_ms).toBe(150);

      createdIds.action_executions.push(testId);
    });

    it.skipIf(skipIfNoCredentials)('should log failed action with error details', async () => {
      const client = getTestClient();
      const testId = generateTestId();

      const { data, error } = await client
        .from('action_executions')
        .insert({
          id: testId,
          yacht_id: TEST_CONFIG.TEST_YACHT_ID,
          user_id: TEST_USER_CONTEXT.user_id,
          action_name: 'close_work_order',
          entity_type: 'work_order',
          params: {
            work_order_id: 'invalid-uuid',
          },
          success: false,
          error_code: 'NOT_FOUND',
          error_message: 'Work order not found',
          duration_ms: 45,
        })
        .select()
        .single();

      expect(error).toBeNull();
      expect(data.success).toBe(false);
      expect(data.error_code).toBe('NOT_FOUND');
      expect(data.error_message).toBe('Work order not found');

      createdIds.action_executions.push(testId);
    });

    it.skipIf(skipIfNoCredentials)('should track action with entity reference', async () => {
      const client = getTestClient();
      const testId = generateTestId();
      const entityId = generateTestId();

      await client.from('action_executions').insert({
        id: testId,
        yacht_id: TEST_CONFIG.TEST_YACHT_ID,
        user_id: TEST_USER_CONTEXT.user_id,
        action_name: 'create_work_order',
        entity_type: 'work_order',
        entity_id: entityId,
        params: {
          equipment_id: generateTestId(),
          title: 'Test Work Order',
          priority: 'high',
        },
        result: {
          work_order_id: entityId,
          work_order_number: 'WO-2026-TEST-001',
        },
        success: true,
        duration_ms: 250,
      });

      createdIds.action_executions.push(testId);

      // Query by entity
      const { data, error } = await client
        .from('action_executions')
        .select('*')
        .eq('entity_id', entityId)
        .single();

      expect(error).toBeNull();
      expect(data.action_name).toBe('create_work_order');
      expect(data.result.work_order_number).toBe('WO-2026-TEST-001');
    });
  });

  // ============================================================================
  // Action Statistics Tests
  // ============================================================================

  describe('Action Statistics', () => {
    it.skipIf(skipIfNoCredentials)('should calculate action success rate', async () => {
      const client = getTestClient();
      const testIds: string[] = [];

      // Create mix of successful and failed actions
      for (let i = 0; i < 5; i++) {
        const id = generateTestId();
        testIds.push(id);
        await client.from('action_executions').insert({
          id,
          yacht_id: TEST_CONFIG.TEST_YACHT_ID,
          user_id: TEST_USER_CONTEXT.user_id,
          action_name: `test_action_${i}`,
          entity_type: 'equipment',
          success: i < 4, // 4 success, 1 failure
          duration_ms: 100 + i * 50,
        });
      }

      createdIds.action_executions.push(...testIds);

      // Query and calculate stats
      const { data, error } = await client
        .from('action_executions')
        .select('success, duration_ms')
        .eq('yacht_id', TEST_CONFIG.TEST_YACHT_ID)
        .in('id', testIds);

      expect(error).toBeNull();
      expect(data?.length).toBe(5);

      const successCount = data?.filter((d) => d.success).length || 0;
      const failureCount = data?.filter((d) => !d.success).length || 0;
      expect(successCount).toBe(4);
      expect(failureCount).toBe(1);
    });

    it.skipIf(skipIfNoCredentials)('should calculate average duration', async () => {
      const client = getTestClient();
      const testIds: string[] = [];
      const durations = [100, 200, 300];

      for (let i = 0; i < durations.length; i++) {
        const id = generateTestId();
        testIds.push(id);
        await client.from('action_executions').insert({
          id,
          yacht_id: TEST_CONFIG.TEST_YACHT_ID,
          user_id: TEST_USER_CONTEXT.user_id,
          action_name: 'duration_test',
          entity_type: 'equipment',
          success: true,
          duration_ms: durations[i],
        });
      }

      createdIds.action_executions.push(...testIds);

      const { data, error } = await client
        .from('action_executions')
        .select('duration_ms')
        .in('id', testIds);

      expect(error).toBeNull();

      const avgDuration =
        (data?.reduce((sum, d) => sum + (d.duration_ms || 0), 0) || 0) /
        (data?.length || 1);

      expect(avgDuration).toBe(200);
    });
  });

  // ============================================================================
  // Audit Trail Tests
  // ============================================================================

  describe('Audit Trail', () => {
    it.skipIf(skipIfNoCredentials)('should maintain chronological order', async () => {
      const client = getTestClient();
      const testIds: string[] = [];

      // Create actions with slight delays
      for (let i = 0; i < 3; i++) {
        const id = generateTestId();
        testIds.push(id);
        await client.from('action_executions').insert({
          id,
          yacht_id: TEST_CONFIG.TEST_YACHT_ID,
          user_id: TEST_USER_CONTEXT.user_id,
          action_name: `chronological_${i}`,
          entity_type: 'equipment',
          success: true,
        });
        // Small delay to ensure different timestamps
        await new Promise((r) => setTimeout(r, 10));
      }

      createdIds.action_executions.push(...testIds);

      const { data, error } = await client
        .from('action_executions')
        .select('action_name, created_at')
        .in('id', testIds)
        .order('created_at', { ascending: true });

      expect(error).toBeNull();
      expect(data?.length).toBe(3);
      expect(data?.[0].action_name).toBe('chronological_0');
      expect(data?.[2].action_name).toBe('chronological_2');
    });

    it.skipIf(skipIfNoCredentials)('should filter actions by time range', async () => {
      const client = getTestClient();
      const testId = generateTestId();

      // Create recent action
      await client.from('action_executions').insert({
        id: testId,
        yacht_id: TEST_CONFIG.TEST_YACHT_ID,
        user_id: TEST_USER_CONTEXT.user_id,
        action_name: 'recent_action',
        entity_type: 'equipment',
        success: true,
      });

      createdIds.action_executions.push(testId);

      // Query for last hour
      const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000).toISOString();

      const { data, error } = await client
        .from('action_executions')
        .select('*')
        .eq('yacht_id', TEST_CONFIG.TEST_YACHT_ID)
        .eq('id', testId)
        .gte('created_at', oneHourAgo);

      expect(error).toBeNull();
      expect(data?.length).toBe(1);
    });
  });

  // ============================================================================
  // Suggestion Tracking Tests
  // ============================================================================

  describe('Suggestion Tracking', () => {
    it.skipIf(skipIfNoCredentials)('should track suggestion to action conversion', async () => {
      const client = getTestClient();
      const suggestionId = generateTestId();

      // Create suggestion
      await client.from('suggestion_log').insert({
        id: suggestionId,
        yacht_id: TEST_CONFIG.TEST_YACHT_ID,
        user_id: TEST_USER_CONTEXT.user_id,
        query_text: 'create work order for pump',
        intent: 'action_query',
        suggested_actions: ['create_work_order', 'view_equipment_details'],
      });

      createdIds.suggestion_log.push(suggestionId);

      // User takes action
      const { data, error } = await client
        .from('suggestion_log')
        .update({
          action_taken: 'create_work_order',
          action_taken_at: new Date().toISOString(),
        })
        .eq('id', suggestionId)
        .select()
        .single();

      expect(error).toBeNull();
      expect(data.action_taken).toBe('create_work_order');
      expect(data.action_taken_at).toBeDefined();
    });

    it.skipIf(skipIfNoCredentials)('should track user feedback on suggestions', async () => {
      const client = getTestClient();
      const suggestionId = generateTestId();

      // Create suggestion with action
      await client.from('suggestion_log').insert({
        id: suggestionId,
        yacht_id: TEST_CONFIG.TEST_YACHT_ID,
        user_id: TEST_USER_CONTEXT.user_id,
        query_text: 'generator fault',
        intent: 'information_query',
        situation_detected: true,
        situation_type: 'RECURRENT_SYMPTOM',
        suggested_actions: ['diagnose_fault'],
        action_taken: 'diagnose_fault',
        action_taken_at: new Date().toISOString(),
      });

      createdIds.suggestion_log.push(suggestionId);

      // Add feedback
      const { data, error } = await client
        .from('suggestion_log')
        .update({
          feedback: 'helpful',
        })
        .eq('id', suggestionId)
        .select()
        .single();

      expect(error).toBeNull();
      expect(data.feedback).toBe('helpful');
    });
  });

  // ============================================================================
  // Situation Acknowledgment Tests
  // ============================================================================

  describe('Situation Acknowledgment', () => {
    it.skipIf(skipIfNoCredentials)('should track situation acknowledgment by user', async () => {
      const client = getTestClient();
      const situationId = generateTestId();

      // Create situation
      await client.from('situation_detections').insert({
        id: situationId,
        yacht_id: TEST_CONFIG.TEST_YACHT_ID,
        user_id: TEST_USER_CONTEXT.user_id,
        situation_type: 'RECURRENT_SYMPTOM',
        severity: 'high',
        label: 'Generator OVERHEAT recurring',
        evidence: ['4 occurrences in 30 days'],
        recommendations: [{ action: 'create_work_order' }],
      });

      createdIds.situation_detections.push(situationId);

      // Acknowledge
      const { data, error } = await client
        .from('situation_detections')
        .update({
          acknowledged: true,
          acknowledged_at: new Date().toISOString(),
          acknowledged_by: TEST_MANAGER_CONTEXT.user_id,
        })
        .eq('id', situationId)
        .select()
        .single();

      expect(error).toBeNull();
      expect(data.acknowledged).toBe(true);
      expect(data.acknowledged_by).toBe(TEST_MANAGER_CONTEXT.user_id);
    });

    it.skipIf(skipIfNoCredentials)('should query unacknowledged situations', async () => {
      const client = getTestClient();
      const unackId = generateTestId();
      const ackId = generateTestId();

      // Create one acknowledged and one not
      await client.from('situation_detections').insert([
        {
          id: unackId,
          yacht_id: TEST_CONFIG.TEST_YACHT_ID,
          situation_type: 'HIGH_RISK_EQUIPMENT',
          severity: 'high',
          label: 'Engine at risk',
          acknowledged: false,
        },
        {
          id: ackId,
          yacht_id: TEST_CONFIG.TEST_YACHT_ID,
          situation_type: 'RECURRENT_SYMPTOM',
          severity: 'medium',
          label: 'Pump issue',
          acknowledged: true,
          acknowledged_at: new Date().toISOString(),
        },
      ]);

      createdIds.situation_detections.push(unackId, ackId);

      // Query unacknowledged
      const { data, error } = await client
        .from('situation_detections')
        .select('*')
        .eq('yacht_id', TEST_CONFIG.TEST_YACHT_ID)
        .eq('acknowledged', false)
        .in('id', [unackId, ackId]);

      expect(error).toBeNull();
      expect(data?.length).toBe(1);
      expect(data?.[0].id).toBe(unackId);
    });
  });
});
