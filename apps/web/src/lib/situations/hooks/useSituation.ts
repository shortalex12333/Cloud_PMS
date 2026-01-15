'use client';

/**
 * useSituation Hook
 *
 * React hook for detecting situations from search queries and entity context.
 */

import { useState, useCallback, useMemo } from 'react';
import { getSituationEngine } from '../situation-engine';
import { classifyIntent, extractEntityReferences, detectSymptomCodes } from '../intent-parser';
import type {
  Situation,
  Recommendation,
  ResolvedEntity,
  VesselContext,
  QueryIntent,
  UserRole,
  DetectionResult,
} from '../types';

interface UseSituationOptions {
  /** Yacht ID */
  yachtId: string;
  /** User role for tailored recommendations */
  userRole?: UserRole;
  /** Vessel context for pre-event detection */
  vesselContext?: VesselContext;
  /** Callback when situation is detected */
  onSituationDetected?: (situation: Situation) => void;
}

interface UseSituationReturn {
  /** Current detected situation */
  situation: Situation | null;
  /** Recommendations for the current situation */
  recommendations: Recommendation[];
  /** Resolved entities from the query */
  resolvedEntities: ResolvedEntity[];
  /** Query intent classification */
  intent: QueryIntent | null;
  /** Whether detection is in progress */
  isDetecting: boolean;
  /** Error if detection failed */
  error: string | null;
  /** Analyze a search query for situations */
  analyzeQuery: (query: string) => Promise<DetectionResult>;
  /** Analyze entities directly */
  analyzeEntities: (entities: ResolvedEntity[]) => Promise<DetectionResult>;
  /** Clear current situation */
  clearSituation: () => void;
  /** Log the current suggestion */
  logSuggestion: (queryText: string) => Promise<string | null>;
}

export function useSituation(options: UseSituationOptions): UseSituationReturn {
  const { yachtId, userRole = 'crew', vesselContext = {}, onSituationDetected } = options;

  const [situation, setSituation] = useState<Situation | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [resolvedEntities, setResolvedEntities] = useState<ResolvedEntity[]>([]);
  const [intent, setIntent] = useState<QueryIntent | null>(null);
  const [isDetecting, setIsDetecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const engine = useMemo(() => getSituationEngine(), []);

  /**
   * Resolve entities from a search query
   */
  const resolveEntitiesFromQuery = useCallback(
    async (query: string): Promise<ResolvedEntity[]> => {
      const entities: ResolvedEntity[] = [];

      // Extract entity references
      const references = extractEntityReferences(query);
      for (const ref of references) {
        // For now, create a basic resolved entity
        // In production, this would query the database
        entities.push({
          type: 'equipment',
          canonical: ref,
          confidence: 0.8,
          value: ref,
        });
      }

      // Detect symptom codes
      const symptoms = detectSymptomCodes(query);
      for (const symptom of symptoms) {
        entities.push({
          type: 'symptom',
          canonical: symptom,
          confidence: 0.9,
          value: symptom,
        });
      }

      return entities;
    },
    []
  );

  /**
   * Analyze a search query for situations
   */
  const analyzeQuery = useCallback(
    async (query: string): Promise<DetectionResult> => {
      setIsDetecting(true);
      setError(null);

      try {
        // Classify intent
        const queryIntent = classifyIntent(query);
        setIntent(queryIntent);

        // Resolve entities from query
        const entities = await resolveEntitiesFromQuery(query);
        setResolvedEntities(entities);

        // Detect situation
        const detectedSituation = await engine.detectSituation(
          yachtId,
          entities,
          vesselContext
        );
        setSituation(detectedSituation);

        // Get recommendations if situation detected
        let recs: Recommendation[] = [];
        if (detectedSituation) {
          recs = engine.getRecommendations(
            detectedSituation,
            yachtId,
            entities,
            userRole
          );
          onSituationDetected?.(detectedSituation);
        }
        setRecommendations(recs);

        return {
          situation: detectedSituation,
          recommendations: recs,
          resolved_entities: entities,
        };
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error';
        setError(message);
        return {
          situation: null,
          recommendations: [],
          resolved_entities: [],
        };
      } finally {
        setIsDetecting(false);
      }
    },
    [engine, yachtId, userRole, vesselContext, onSituationDetected, resolveEntitiesFromQuery]
  );

  /**
   * Analyze entities directly (when entities are already resolved)
   */
  const analyzeEntities = useCallback(
    async (entities: ResolvedEntity[]): Promise<DetectionResult> => {
      setIsDetecting(true);
      setError(null);
      setResolvedEntities(entities);

      try {
        // Detect situation
        const detectedSituation = await engine.detectSituation(
          yachtId,
          entities,
          vesselContext
        );
        setSituation(detectedSituation);

        // Get recommendations if situation detected
        let recs: Recommendation[] = [];
        if (detectedSituation) {
          recs = engine.getRecommendations(
            detectedSituation,
            yachtId,
            entities,
            userRole
          );
          onSituationDetected?.(detectedSituation);
        }
        setRecommendations(recs);

        return {
          situation: detectedSituation,
          recommendations: recs,
          resolved_entities: entities,
        };
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error';
        setError(message);
        return {
          situation: null,
          recommendations: [],
          resolved_entities: [],
        };
      } finally {
        setIsDetecting(false);
      }
    },
    [engine, yachtId, userRole, vesselContext, onSituationDetected]
  );

  /**
   * Clear the current situation
   */
  const clearSituation = useCallback(() => {
    setSituation(null);
    setRecommendations([]);
    setResolvedEntities([]);
    setIntent(null);
    setError(null);
  }, []);

  /**
   * Log the current suggestion
   */
  const logSuggestion = useCallback(
    async (queryText: string): Promise<string | null> => {
      return engine.logSuggestion(
        yachtId,
        null, // userId would come from auth context
        queryText,
        intent,
        situation,
        recommendations
      );
    },
    [engine, yachtId, intent, situation, recommendations]
  );

  return {
    situation,
    recommendations,
    resolvedEntities,
    intent,
    isDetecting,
    error,
    analyzeQuery,
    analyzeEntities,
    clearSituation,
    logSuggestion,
  };
}

export default useSituation;
