/**
 * Handler + Database Integration Tests
 *
 * Tests handlers against real Supabase database.
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from 'vitest';
import {
  getTestClient,
  cleanupTestData,
  generateTestId,
  TEST_CONFIG,
  TEST_USER_CONTEXT,
} from './setup';

describe('Handler + Database Integration', () => {
  const createdIds: Record<string, string[]> = {
    action_executions: [],
    symptom_reports: [],
    pms_equipment_notes: [],
  };

  // Skip if no service key (CI environment without secrets)
  const skipIfNoCredentials =
    !TEST_CONFIG.SUPABASE_SERVICE_KEY ||
    TEST_CONFIG.SUPABASE_SERVICE_KEY.includes('undefined');

  beforeAll(() => {
    if (skipIfNoCredentials) {
      console.warn('Skipping integration tests: No Supabase credentials');
    }
  });

  afterEach(async () => {
    // Clean up created records
    for (const [table, ids] of Object.entries(createdIds)) {
      if (ids.length > 0) {
        await cleanupTestData(table, ids);
        createdIds[table] = [];
      }
    }
  });

  // ============================================================================
  // Action Execution Logging Tests
  // ============================================================================

  describe('Action Execution Logging', () => {
    it.skipIf(skipIfNoCredentials)('should log action execution to database', async () => {
      const client = getTestClient();
      const testId = generateTestId();

      const { data, error } = await client
        .from('action_executions')
        .insert({
          id: testId,
          yacht_id: TEST_CONFIG.TEST_YACHT_ID,
          user_id: TEST_USER_CONTEXT.user_id,
          action_name: 'test_action',
          entity_type: 'equipment',
          params: { test: true },
          result: { success: true },
          success: true,
          duration_ms: 100,
        })
        .select()
        .single();

      expect(error).toBeNull();
      expect(data).toBeDefined();
      expect(data.action_name).toBe('test_action');
      expect(data.success).toBe(true);

      createdIds.action_executions.push(testId);
    });

    it.skipIf(skipIfNoCredentials)('should log failed action with error message', async () => {
      const client = getTestClient();
      const testId = generateTestId();

      const { data, error } = await client
        .from('action_executions')
        .insert({
          id: testId,
          yacht_id: TEST_CONFIG.TEST_YACHT_ID,
          user_id: TEST_USER_CONTEXT.user_id,
          action_name: 'failed_action',
          entity_type: 'work_order',
          params: { work_order_id: 'invalid' },
          success: false,
          error_code: 'NOT_FOUND',
          error_message: 'Work order not found',
          duration_ms: 50,
        })
        .select()
        .single();

      expect(error).toBeNull();
      expect(data.success).toBe(false);
      expect(data.error_code).toBe('NOT_FOUND');

      createdIds.action_executions.push(testId);
    });

    it.skipIf(skipIfNoCredentials)('should query action history', async () => {
      const client = getTestClient();
      const testId1 = generateTestId();
      const testId2 = generateTestId();

      // Insert multiple actions
      await client.from('action_executions').insert([
        {
          id: testId1,
          yacht_id: TEST_CONFIG.TEST_YACHT_ID,
          user_id: TEST_USER_CONTEXT.user_id,
          action_name: 'action_1',
          entity_type: 'equipment',
          success: true,
        },
        {
          id: testId2,
          yacht_id: TEST_CONFIG.TEST_YACHT_ID,
          user_id: TEST_USER_CONTEXT.user_id,
          action_name: 'action_2',
          entity_type: 'equipment',
          success: true,
        },
      ]);

      createdIds.action_executions.push(testId1, testId2);

      // Query history
      const { data, error } = await client
        .from('action_executions')
        .select('*')
        .eq('yacht_id', TEST_CONFIG.TEST_YACHT_ID)
        .in('id', [testId1, testId2])
        .order('created_at', { ascending: false });

      expect(error).toBeNull();
      expect(data?.length).toBe(2);
    });
  });

  // ============================================================================
  // Symptom Report Tests
  // ============================================================================

  describe('Symptom Reports', () => {
    it.skipIf(skipIfNoCredentials)('should create symptom report', async () => {
      const client = getTestClient();
      const testId = generateTestId();

      const { data, error } = await client
        .from('symptom_reports')
        .insert({
          id: testId,
          yacht_id: TEST_CONFIG.TEST_YACHT_ID,
          equipment_label: 'Generator 1',
          symptom_code: 'OVERHEAT',
          symptom_label: 'Overheating',
          source: 'search',
          reported_by: TEST_USER_CONTEXT.user_id,
        })
        .select()
        .single();

      expect(error).toBeNull();
      expect(data.equipment_label).toBe('Generator 1');
      expect(data.symptom_code).toBe('OVERHEAT');
      expect(data.resolved).toBe(false);

      createdIds.symptom_reports.push(testId);
    });

    it.skipIf(skipIfNoCredentials)('should mark symptom as resolved', async () => {
      const client = getTestClient();
      const testId = generateTestId();

      // Create symptom
      await client.from('symptom_reports').insert({
        id: testId,
        yacht_id: TEST_CONFIG.TEST_YACHT_ID,
        equipment_label: 'Pump 2',
        symptom_code: 'LEAK',
        symptom_label: 'Leaking',
        source: 'manual',
      });

      createdIds.symptom_reports.push(testId);

      // Mark as resolved
      const { data, error } = await client
        .from('symptom_reports')
        .update({
          resolved: true,
          resolved_at: new Date().toISOString(),
          resolved_by: TEST_USER_CONTEXT.user_id,
        })
        .eq('id', testId)
        .select()
        .single();

      expect(error).toBeNull();
      expect(data.resolved).toBe(true);
      expect(data.resolved_at).toBeDefined();
    });

    it.skipIf(skipIfNoCredentials)('should query symptoms by equipment', async () => {
      const client = getTestClient();
      const testId = generateTestId();

      await client.from('symptom_reports').insert({
        id: testId,
        yacht_id: TEST_CONFIG.TEST_YACHT_ID,
        equipment_label: 'Main Engine',
        symptom_code: 'VIBRATION',
        symptom_label: 'Excessive vibration',
        source: 'search',
      });

      createdIds.symptom_reports.push(testId);

      const { data, error } = await client
        .from('symptom_reports')
        .select('*')
        .eq('yacht_id', TEST_CONFIG.TEST_YACHT_ID)
        .ilike('equipment_label', '%Main Engine%');

      expect(error).toBeNull();
      expect(data?.length).toBeGreaterThan(0);
      expect(data?.[0].symptom_code).toBe('VIBRATION');
    });
  });

  // ============================================================================
  // Database Function Tests
  // ============================================================================

  describe('Database Functions', () => {
    it.skipIf(skipIfNoCredentials)('should call check_symptom_recurrence function', async () => {
      const client = getTestClient();

      // Create some symptom reports for testing
      const testIds = [generateTestId(), generateTestId(), generateTestId()];

      await client.from('symptom_reports').insert(
        testIds.map((id, index) => ({
          id,
          yacht_id: TEST_CONFIG.TEST_YACHT_ID,
          equipment_label: 'Test Equipment',
          symptom_code: 'TEST_SYMPTOM',
          symptom_label: 'Test symptom',
          source: 'test',
          created_at: new Date(Date.now() - index * 24 * 60 * 60 * 1000).toISOString(), // Spread over days
        }))
      );

      createdIds.symptom_reports.push(...testIds);

      // Call the function
      const { data, error } = await client.rpc('check_symptom_recurrence', {
        p_yacht_id: TEST_CONFIG.TEST_YACHT_ID,
        p_equipment_label: 'Test Equipment',
        p_symptom_code: 'TEST_SYMPTOM',
        p_threshold_count: 3,
        p_threshold_days: 60,
      });

      expect(error).toBeNull();
      expect(data).toBeDefined();
      expect(data[0].occurrence_count).toBeGreaterThanOrEqual(3);
      expect(data[0].is_recurrent).toBe(true);
    });

    it.skipIf(skipIfNoCredentials)('should call log_symptom_from_search function', async () => {
      const client = getTestClient();

      const { data, error } = await client.rpc('log_symptom_from_search', {
        p_yacht_id: TEST_CONFIG.TEST_YACHT_ID,
        p_equipment_label: 'Watermaker',
        p_symptom_code: 'LOW_PRESSURE',
        p_symptom_label: 'Low pressure',
        p_user_id: TEST_USER_CONTEXT.user_id,
      });

      expect(error).toBeNull();
      expect(data).toBeDefined();

      // Clean up
      if (data) {
        createdIds.symptom_reports.push(data);
      }
    });
  });

  // ============================================================================
  // Situation Detection Tests
  // ============================================================================

  describe('Situation Detections', () => {
    it.skipIf(skipIfNoCredentials)('should create situation detection', async () => {
      const client = getTestClient();
      const testId = generateTestId();

      const { data, error } = await client
        .from('situation_detections')
        .insert({
          id: testId,
          yacht_id: TEST_CONFIG.TEST_YACHT_ID,
          user_id: TEST_USER_CONTEXT.user_id,
          situation_type: 'RECURRENT_SYMPTOM',
          severity: 'medium',
          label: 'Generator 1 OVERHEAT (recurring)',
          evidence: ['3 occurrences in 30 days'],
          recommendations: [{ action: 'create_work_order', reason: 'Root cause investigation' }],
        })
        .select()
        .single();

      expect(error).toBeNull();
      expect(data.situation_type).toBe('RECURRENT_SYMPTOM');
      expect(data.acknowledged).toBe(false);

      // Clean up
      await client.from('situation_detections').delete().eq('id', testId);
    });

    it.skipIf(skipIfNoCredentials)('should acknowledge situation', async () => {
      const client = getTestClient();
      const testId = generateTestId();

      // Create situation
      await client.from('situation_detections').insert({
        id: testId,
        yacht_id: TEST_CONFIG.TEST_YACHT_ID,
        situation_type: 'HIGH_RISK_EQUIPMENT',
        severity: 'high',
        label: 'Main Engine at elevated risk',
        evidence: ['Risk score: 85%'],
      });

      // Acknowledge it
      const { data, error } = await client
        .from('situation_detections')
        .update({
          acknowledged: true,
          acknowledged_at: new Date().toISOString(),
          acknowledged_by: TEST_USER_CONTEXT.user_id,
        })
        .eq('id', testId)
        .select()
        .single();

      expect(error).toBeNull();
      expect(data.acknowledged).toBe(true);

      // Clean up
      await client.from('situation_detections').delete().eq('id', testId);
    });
  });

  // ============================================================================
  // Suggestion Log Tests
  // ============================================================================

  describe('Suggestion Log', () => {
    it.skipIf(skipIfNoCredentials)('should log search suggestion', async () => {
      const client = getTestClient();
      const testId = generateTestId();

      const { data, error } = await client
        .from('suggestion_log')
        .insert({
          id: testId,
          yacht_id: TEST_CONFIG.TEST_YACHT_ID,
          user_id: TEST_USER_CONTEXT.user_id,
          query_text: 'generator overheating',
          intent: 'information_query',
          situation_detected: true,
          situation_type: 'RECURRENT_SYMPTOM',
          suggested_actions: ['create_work_order', 'view_fault_history'],
        })
        .select()
        .single();

      expect(error).toBeNull();
      expect(data.query_text).toBe('generator overheating');
      expect(data.situation_detected).toBe(true);

      // Clean up
      await client.from('suggestion_log').delete().eq('id', testId);
    });

    it.skipIf(skipIfNoCredentials)('should record action taken from suggestion', async () => {
      const client = getTestClient();
      const testId = generateTestId();

      // Create suggestion log
      await client.from('suggestion_log').insert({
        id: testId,
        yacht_id: TEST_CONFIG.TEST_YACHT_ID,
        query_text: 'pump fault',
        intent: 'action_query',
        suggested_actions: ['diagnose_fault', 'create_work_order'],
      });

      // Record action taken
      const { data, error } = await client
        .from('suggestion_log')
        .update({
          action_taken: 'create_work_order',
          action_taken_at: new Date().toISOString(),
        })
        .eq('id', testId)
        .select()
        .single();

      expect(error).toBeNull();
      expect(data.action_taken).toBe('create_work_order');

      // Clean up
      await client.from('suggestion_log').delete().eq('id', testId);
    });
  });

  // ============================================================================
  // Predictive State Tests
  // ============================================================================

  describe('Predictive State', () => {
    it.skipIf(skipIfNoCredentials)('should create predictive state entry', async () => {
      const client = getTestClient();
      const equipmentId = generateTestId();

      const { data, error } = await client
        .from('predictive_state')
        .insert({
          yacht_id: TEST_CONFIG.TEST_YACHT_ID,
          equipment_id: equipmentId,
          risk_score: 0.85,
          confidence: 0.9,
          failure_probability: 0.3,
          trend: 'increasing',
          anomalies: [{ type: 'vibration', severity: 'medium' }],
        })
        .select()
        .single();

      expect(error).toBeNull();
      // DECIMAL returns as number in Supabase JS
      expect(parseFloat(data.risk_score)).toBe(0.85);
      expect(data.trend).toBe('increasing');

      // Clean up
      await client.from('predictive_state').delete().eq('equipment_id', equipmentId);
    });

    it.skipIf(skipIfNoCredentials)('should update predictive state', async () => {
      const client = getTestClient();
      const equipmentId = generateTestId();

      // Create initial state
      await client.from('predictive_state').insert({
        yacht_id: TEST_CONFIG.TEST_YACHT_ID,
        equipment_id: equipmentId,
        risk_score: 0.5,
        confidence: 0.8,
        trend: 'stable',
      });

      // Update with new risk score
      const { data, error } = await client
        .from('predictive_state')
        .update({
          risk_score: 0.75,
          trend: 'increasing',
          last_updated: new Date().toISOString(),
        })
        .eq('equipment_id', equipmentId)
        .select()
        .single();

      expect(error).toBeNull();
      // DECIMAL returns as number in Supabase JS
      expect(parseFloat(data.risk_score)).toBe(0.75);
      expect(data.trend).toBe('increasing');

      // Clean up
      await client.from('predictive_state').delete().eq('equipment_id', equipmentId);
    });
  });
});
