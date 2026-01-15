/**
 * Situation Engine Unit Tests
 *
 * Tests for the situation detection and recommendation system.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SituationEngine, getSituationEngine } from '@/lib/situations/situation-engine';
import type { ResolvedEntity, VesselContext, Situation } from '@/lib/situations/types';

// Mock Supabase client
vi.mock('@/lib/supabaseClient', () => ({
  createClient: () => ({
    rpc: vi.fn().mockImplementation((fnName, params) => {
      if (fnName === 'check_symptom_recurrence') {
        // Return recurrent symptom data
        return Promise.resolve({
          data: [{
            is_recurrent: true,
            occurrence_count: 4,
            span_days: 45,
            open_count: 1,
          }],
          error: null,
        });
      }
      return Promise.resolve({ data: null, error: null });
    }),
    from: vi.fn().mockReturnValue({
      select: vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          single: vi.fn().mockResolvedValue({
            data: { risk_score: 0.85, confidence: 0.9 },
            error: null,
          }),
          ilike: vi.fn().mockReturnValue({
            order: vi.fn().mockReturnValue({
              limit: vi.fn().mockReturnValue({
                single: vi.fn().mockResolvedValue({
                  data: { id: 'wo-123', title: 'Test WO', created_at: '2025-01-01' },
                  error: null,
                }),
              }),
            }),
          }),
        }),
      }),
      insert: vi.fn().mockReturnValue({
        select: vi.fn().mockReturnValue({
          single: vi.fn().mockResolvedValue({
            data: { id: 'new-id' },
            error: null,
          }),
        }),
      }),
    }),
  }),
}));

describe('SituationEngine', () => {
  let engine: SituationEngine;

  const validYachtId = '123e4567-e89b-12d3-a456-426614174000';

  beforeEach(() => {
    vi.clearAllMocks();
    engine = new SituationEngine();
  });

  // ============================================================================
  // Detection Tests
  // ============================================================================

  describe('Situation Detection', () => {
    it('should return null for empty resolved entities', async () => {
      const result = await engine.detectSituation(validYachtId, [], {});
      expect(result).toBeNull();
    });

    it('should detect RECURRENT_SYMPTOM pattern', async () => {
      const entities: ResolvedEntity[] = [
        { type: 'equipment', canonical: 'Generator 1', confidence: 0.9 },
        { type: 'symptom', canonical: 'OVERHEAT', confidence: 0.85 },
      ];

      const result = await engine.detectSituation(validYachtId, entities, {});

      expect(result).not.toBeNull();
      expect(result?.type).toBe('RECURRENT_SYMPTOM');
      expect(result?.severity).toBe('medium');
      expect(result?.evidence.length).toBeGreaterThan(0);
    });

    it('should detect RECURRENT_SYMPTOM_PRE_EVENT when critical event is near', async () => {
      const entities: ResolvedEntity[] = [
        { type: 'equipment', canonical: 'Generator 1', confidence: 0.9 },
        { type: 'symptom', canonical: 'OVERHEAT', confidence: 0.85 },
      ];

      const vesselContext: VesselContext = {
        hours_until_event: 48,
        next_event_type: 'charter',
      };

      const result = await engine.detectSituation(validYachtId, entities, vesselContext);

      expect(result).not.toBeNull();
      expect(result?.type).toBe('RECURRENT_SYMPTOM_PRE_EVENT');
      expect(result?.severity).toBe('high');
      expect(result?.context).toContain('Charter');
    });

    it('should detect HIGH_RISK_EQUIPMENT pattern', async () => {
      const entities: ResolvedEntity[] = [
        {
          type: 'equipment',
          entity_id: 'eq-123',
          canonical: 'Main Engine',
          confidence: 0.9,
        },
      ];

      const result = await engine.detectSituation(validYachtId, entities, {});

      expect(result).not.toBeNull();
      expect(result?.type).toBe('HIGH_RISK_EQUIPMENT');
    });

    it('should not detect situation without equipment entity', async () => {
      const entities: ResolvedEntity[] = [
        { type: 'symptom', canonical: 'OVERHEAT', confidence: 0.85 },
      ];

      const result = await engine.detectSituation(validYachtId, entities, {});
      expect(result).toBeNull();
    });
  });

  // ============================================================================
  // Recommendation Tests
  // ============================================================================

  describe('Recommendations', () => {
    const recurrentSituation: Situation = {
      type: 'RECURRENT_SYMPTOM',
      label: 'Generator 1 OVERHEAT (recurring)',
      severity: 'medium',
      context: null,
      evidence: ['4 OVERHEAT events in 45 days'],
    };

    const preEventSituation: Situation = {
      type: 'RECURRENT_SYMPTOM_PRE_EVENT',
      label: 'Generator 1 OVERHEAT (recurring)',
      severity: 'high',
      context: 'Charter in 48h',
      evidence: ['4 OVERHEAT events in 45 days'],
    };

    const highRiskSituation: Situation = {
      type: 'HIGH_RISK_EQUIPMENT',
      label: 'Main Engine at elevated risk',
      severity: 'high',
      context: null,
      evidence: ['Risk score: 85%'],
    };

    it('should return empty recommendations for null situation', () => {
      const recs = engine.getRecommendations(null, validYachtId, [], 'engineer');
      expect(recs).toHaveLength(0);
    });

    it('should return engineering recommendations for recurrent symptom', () => {
      const recs = engine.getRecommendations(
        recurrentSituation,
        validYachtId,
        [],
        'engineer'
      );

      expect(recs.length).toBeGreaterThan(0);
      expect(recs[0].action).toBe('create_work_order');
      expect(recs[0].template).toBe('inspection_root_cause');
    });

    it('should return captain recommendations for recurrent symptom', () => {
      const recs = engine.getRecommendations(
        recurrentSituation,
        validYachtId,
        [],
        'captain'
      );

      expect(recs.length).toBeGreaterThan(0);
      expect(recs[0].action).toBe('review_maintenance_status');
    });

    it('should add diagnostic recommendation for pre-event situation', () => {
      const recs = engine.getRecommendations(
        preEventSituation,
        validYachtId,
        [],
        'engineer'
      );

      expect(recs.length).toBeGreaterThan(1);
      const hasRunDiagnostic = recs.some((r) => r.action === 'run_diagnostic');
      expect(hasRunDiagnostic).toBe(true);
    });

    it('should add contingency recommendation for high severity captain', () => {
      const recs = engine.getRecommendations(
        preEventSituation,
        validYachtId,
        [],
        'captain'
      );

      const hasContingency = recs.some((r) => r.action === 'prepare_contingency');
      expect(hasContingency).toBe(true);
    });

    it('should return predictive analysis for high risk equipment', () => {
      const recs = engine.getRecommendations(
        highRiskSituation,
        validYachtId,
        [],
        'engineer'
      );

      expect(recs.length).toBeGreaterThan(0);
      expect(recs[0].action).toBe('view_predictive_analysis');
    });

    it('should set urgency based on severity', () => {
      const recs = engine.getRecommendations(
        preEventSituation,
        validYachtId,
        [],
        'engineer'
      );

      // High severity should have urgent recommendations
      expect(recs[0].urgency).toBe('urgent');
    });
  });

  // ============================================================================
  // Singleton Tests
  // ============================================================================

  describe('Singleton', () => {
    it('should return the same instance', () => {
      const engine1 = getSituationEngine();
      const engine2 = getSituationEngine();
      expect(engine1).toBe(engine2);
    });
  });

  // ============================================================================
  // Logging Tests
  // ============================================================================

  describe('Logging', () => {
    it('should log suggestion successfully', async () => {
      const situation: Situation = {
        type: 'RECURRENT_SYMPTOM',
        label: 'Test',
        severity: 'medium',
        context: null,
        evidence: [],
      };

      const result = await engine.logSuggestion(
        validYachtId,
        'user-123',
        'generator overheating',
        'information_query',
        situation,
        []
      );

      expect(result).toBe('new-id');
    });

    it('should log symptom report successfully', async () => {
      const result = await engine.logSymptomReport(
        validYachtId,
        'Generator 1',
        'OVERHEAT',
        'Overheating',
        'user-123'
      );

      expect(result).toBe('new-id');
    });
  });

  // ============================================================================
  // Edge Cases
  // ============================================================================

  describe('Edge Cases', () => {
    it('should handle equipment without entity_id for high risk check', async () => {
      const entities: ResolvedEntity[] = [
        { type: 'equipment', canonical: 'Unknown Equipment', confidence: 0.5 },
      ];

      const result = await engine.detectSituation(validYachtId, entities, {});
      // Should not throw, should return null (can't check risk without ID)
      expect(result).toBeNull();
    });

    it('should handle empty canonical labels', async () => {
      const entities: ResolvedEntity[] = [
        { type: 'equipment', canonical: '', confidence: 0.9 },
        { type: 'symptom', canonical: '', confidence: 0.85 },
      ];

      const result = await engine.detectSituation(validYachtId, entities, {});
      expect(result).toBeNull();
    });

    it('should handle management role same as captain', () => {
      const situation: Situation = {
        type: 'RECURRENT_SYMPTOM',
        label: 'Test',
        severity: 'medium',
        context: null,
        evidence: [],
      };

      const managementRecs = engine.getRecommendations(situation, validYachtId, [], 'management');
      const captainRecs = engine.getRecommendations(situation, validYachtId, [], 'captain');

      expect(managementRecs[0].action).toBe(captainRecs[0].action);
    });
  });
});
