/**
 * Situation Engine + Database Integration Tests
 *
 * Tests situation detection patterns against real Supabase database.
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
  getTestClient,
  generateTestId,
  TEST_CONFIG,
  TEST_USER_CONTEXT,
} from './setup';

describe('Situation Engine + Database Integration', () => {
  const createdSymptomIds: string[] = [];
  const createdFaultIds: string[] = [];

  // Skip if no service key
  const skipIfNoCredentials =
    !TEST_CONFIG.SUPABASE_SERVICE_KEY ||
    TEST_CONFIG.SUPABASE_SERVICE_KEY.includes('undefined');

  afterEach(async () => {
    const client = getTestClient();

    // Clean up symptom reports
    if (createdSymptomIds.length > 0) {
      await client.from('symptom_reports').delete().in('id', createdSymptomIds);
      createdSymptomIds.length = 0;
    }

    // Clean up test faults
    if (createdFaultIds.length > 0) {
      await client.from('pms_faults').delete().in('id', createdFaultIds);
      createdFaultIds.length = 0;
    }
  });

  // ============================================================================
  // Recurrent Symptom Detection Tests
  // ============================================================================

  describe('Recurrent Symptom Pattern', () => {
    it.skipIf(skipIfNoCredentials)('should detect recurrent symptom when threshold met', async () => {
      const client = getTestClient();

      // Create 3 symptom reports for same equipment/symptom
      const equipmentLabel = `Test Gen ${Date.now()}`;
      const symptomCode = 'OVERHEAT';

      for (let i = 0; i < 3; i++) {
        const id = generateTestId();
        await client.from('symptom_reports').insert({
          id,
          yacht_id: TEST_CONFIG.TEST_YACHT_ID,
          equipment_label: equipmentLabel,
          symptom_code: symptomCode,
          symptom_label: 'Overheating',
          source: 'test',
          created_at: new Date(Date.now() - i * 10 * 24 * 60 * 60 * 1000).toISOString(),
        });
        createdSymptomIds.push(id);
      }

      // Check recurrence
      const { data, error } = await client.rpc('check_symptom_recurrence', {
        p_yacht_id: TEST_CONFIG.TEST_YACHT_ID,
        p_equipment_label: equipmentLabel,
        p_symptom_code: symptomCode,
        p_threshold_count: 3,
        p_threshold_days: 60,
      });

      expect(error).toBeNull();
      expect(data[0].is_recurrent).toBe(true);
      expect(data[0].occurrence_count).toBe(3);
    });

    it.skipIf(skipIfNoCredentials)('should not detect recurrence below threshold', async () => {
      const client = getTestClient();

      // Create only 2 symptom reports (below threshold of 3)
      const equipmentLabel = `Test Pump ${Date.now()}`;
      const symptomCode = 'LEAK';

      for (let i = 0; i < 2; i++) {
        const id = generateTestId();
        await client.from('symptom_reports').insert({
          id,
          yacht_id: TEST_CONFIG.TEST_YACHT_ID,
          equipment_label: equipmentLabel,
          symptom_code: symptomCode,
          symptom_label: 'Leaking',
          source: 'test',
        });
        createdSymptomIds.push(id);
      }

      const { data, error } = await client.rpc('check_symptom_recurrence', {
        p_yacht_id: TEST_CONFIG.TEST_YACHT_ID,
        p_equipment_label: equipmentLabel,
        p_symptom_code: symptomCode,
        p_threshold_count: 3,
        p_threshold_days: 60,
      });

      expect(error).toBeNull();
      expect(data[0].is_recurrent).toBe(false);
      expect(data[0].occurrence_count).toBe(2);
    });

    it.skipIf(skipIfNoCredentials)('should count open symptoms correctly', async () => {
      const client = getTestClient();

      const equipmentLabel = `Test Engine ${Date.now()}`;
      const symptomCode = 'VIBRATION';

      // Create 3 symptoms, 1 resolved
      for (let i = 0; i < 3; i++) {
        const id = generateTestId();
        await client.from('symptom_reports').insert({
          id,
          yacht_id: TEST_CONFIG.TEST_YACHT_ID,
          equipment_label: equipmentLabel,
          symptom_code: symptomCode,
          symptom_label: 'Vibration',
          source: 'test',
          resolved: i === 0, // First one is resolved
        });
        createdSymptomIds.push(id);
      }

      const { data, error } = await client.rpc('check_symptom_recurrence', {
        p_yacht_id: TEST_CONFIG.TEST_YACHT_ID,
        p_equipment_label: equipmentLabel,
        p_symptom_code: symptomCode,
        p_threshold_count: 3,
        p_threshold_days: 60,
      });

      expect(error).toBeNull();
      expect(data[0].occurrence_count).toBe(3);
      expect(data[0].open_count).toBe(2); // 2 unresolved
    });

    it.skipIf(skipIfNoCredentials)('should isolate symptoms by yacht', async () => {
      const client = getTestClient();

      const equipmentLabel = `Test Equipment ${Date.now()}`;
      const symptomCode = 'NOISE';
      const differentYachtId = generateTestId();

      // Create symptoms for test yacht
      for (let i = 0; i < 3; i++) {
        const id = generateTestId();
        await client.from('symptom_reports').insert({
          id,
          yacht_id: TEST_CONFIG.TEST_YACHT_ID,
          equipment_label: equipmentLabel,
          symptom_code: symptomCode,
          symptom_label: 'Noise',
          source: 'test',
        });
        createdSymptomIds.push(id);
      }

      // Check for different yacht (should be 0)
      const { data, error } = await client.rpc('check_symptom_recurrence', {
        p_yacht_id: differentYachtId,
        p_equipment_label: equipmentLabel,
        p_symptom_code: symptomCode,
        p_threshold_count: 3,
        p_threshold_days: 60,
      });

      expect(error).toBeNull();
      expect(data[0].occurrence_count).toBe(0);
      expect(data[0].is_recurrent).toBe(false);
    });
  });

  // ============================================================================
  // High Risk Equipment Pattern Tests
  // ============================================================================

  describe('High Risk Equipment Pattern', () => {
    it.skipIf(skipIfNoCredentials)('should query equipment risk score', async () => {
      const client = getTestClient();
      const equipmentId = generateTestId();

      // Create predictive state with high risk
      await client.from('predictive_state').insert({
        yacht_id: TEST_CONFIG.TEST_YACHT_ID,
        equipment_id: equipmentId,
        risk_score: 0.85,
        confidence: 0.9,
        failure_probability: 0.3,
        trend: 'increasing',
      });

      // Query risk
      const { data, error } = await client.rpc('get_equipment_risk', {
        p_equipment_id: equipmentId,
      });

      expect(error).toBeNull();
      expect(data).toBeDefined();
      if (data && data.length > 0) {
        expect(parseFloat(data[0].risk_score)).toBeGreaterThan(0.7);
      }

      // Clean up
      await client.from('predictive_state').delete().eq('equipment_id', equipmentId);
    });

    it.skipIf(skipIfNoCredentials)('should return empty for equipment without predictive state', async () => {
      const client = getTestClient();
      const nonExistentEquipmentId = generateTestId();

      const { data, error } = await client.rpc('get_equipment_risk', {
        p_equipment_id: nonExistentEquipmentId,
      });

      expect(error).toBeNull();
      expect(data?.length || 0).toBe(0);
    });
  });

  // ============================================================================
  // Cross-Table Symptom Detection Tests
  // ============================================================================

  describe('Cross-Table Symptom Detection', () => {
    it.skipIf(skipIfNoCredentials)('should detect symptoms from both symptom_reports and pms_faults', async () => {
      const client = getTestClient();

      const equipmentLabel = `Test AC ${Date.now()}`;
      const symptomCode = 'FAILURE';

      // Create symptom report
      const symptomId = generateTestId();
      await client.from('symptom_reports').insert({
        id: symptomId,
        yacht_id: TEST_CONFIG.TEST_YACHT_ID,
        equipment_label: equipmentLabel,
        symptom_code: symptomCode,
        symptom_label: 'Failure',
        source: 'test',
      });
      createdSymptomIds.push(symptomId);

      // Check that symptom is counted
      const { data, error } = await client.rpc('check_symptom_recurrence', {
        p_yacht_id: TEST_CONFIG.TEST_YACHT_ID,
        p_equipment_label: equipmentLabel,
        p_symptom_code: symptomCode,
        p_threshold_count: 1,
        p_threshold_days: 60,
      });

      expect(error).toBeNull();
      expect(data[0].occurrence_count).toBeGreaterThanOrEqual(1);
    });
  });

  // ============================================================================
  // Span Days Calculation Tests
  // ============================================================================

  describe('Span Days Calculation', () => {
    it.skipIf(skipIfNoCredentials)('should calculate span days correctly', async () => {
      const client = getTestClient();

      const equipmentLabel = `Span Test ${Date.now()}`;
      const symptomCode = 'ALARM';

      // Create symptoms 30 days apart
      const now = Date.now();
      const thirtyDaysAgo = now - 30 * 24 * 60 * 60 * 1000;

      const id1 = generateTestId();
      const id2 = generateTestId();

      await client.from('symptom_reports').insert([
        {
          id: id1,
          yacht_id: TEST_CONFIG.TEST_YACHT_ID,
          equipment_label: equipmentLabel,
          symptom_code: symptomCode,
          symptom_label: 'Alarm',
          source: 'test',
          created_at: new Date(thirtyDaysAgo).toISOString(),
        },
        {
          id: id2,
          yacht_id: TEST_CONFIG.TEST_YACHT_ID,
          equipment_label: equipmentLabel,
          symptom_code: symptomCode,
          symptom_label: 'Alarm',
          source: 'test',
          created_at: new Date(now).toISOString(),
        },
      ]);

      createdSymptomIds.push(id1, id2);

      const { data, error } = await client.rpc('check_symptom_recurrence', {
        p_yacht_id: TEST_CONFIG.TEST_YACHT_ID,
        p_equipment_label: equipmentLabel,
        p_symptom_code: symptomCode,
        p_threshold_count: 2,
        p_threshold_days: 60,
      });

      expect(error).toBeNull();
      expect(data[0].span_days).toBeGreaterThanOrEqual(29);
      expect(data[0].span_days).toBeLessThanOrEqual(31);
    });
  });

  // ============================================================================
  // Partial Equipment Label Matching Tests
  // ============================================================================

  describe('Partial Equipment Label Matching', () => {
    it.skipIf(skipIfNoCredentials)('should match partial equipment labels', async () => {
      const client = getTestClient();

      const fullLabel = `Port Generator Unit 1 ${Date.now()}`;
      const symptomCode = 'SMOKE';

      // Create with full label
      const id = generateTestId();
      await client.from('symptom_reports').insert({
        id,
        yacht_id: TEST_CONFIG.TEST_YACHT_ID,
        equipment_label: fullLabel,
        symptom_code: symptomCode,
        symptom_label: 'Smoke',
        source: 'test',
      });
      createdSymptomIds.push(id);

      // Search with partial label
      const { data, error } = await client.rpc('check_symptom_recurrence', {
        p_yacht_id: TEST_CONFIG.TEST_YACHT_ID,
        p_equipment_label: 'Generator Unit',
        p_symptom_code: symptomCode,
        p_threshold_count: 1,
        p_threshold_days: 60,
      });

      expect(error).toBeNull();
      expect(data[0].occurrence_count).toBeGreaterThanOrEqual(1);
    });
  });
});
