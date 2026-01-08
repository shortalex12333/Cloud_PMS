/**
 * CelesteOS Situation State Management Hook
 *
 * Manages the situation state machine lifecycle:
 * IDLE → CANDIDATE → ACTIVE → COOLDOWN → RESOLVED
 *
 * Tracks evidence flags to determine state transitions and action availability
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { getYachtId } from '@/lib/authHelpers';
import type {
  SituationContext,
  SituationState,
  SituationPhase,
  SituationEvidence,
  EntityType,
  SituationDomain,
  SituationTransition,
  SituationUpdate,
  CreateSituationPayload,
} from '@/types/situation';

// ============================================================================
// TYPES
// ============================================================================

interface UseSituationStateReturn {
  // Current state
  situation: SituationContext | null;
  isActive: boolean;
  isCandidate: boolean;
  isIdle: boolean;

  // Actions
  createSituation: (payload: CreateSituationPayload) => Promise<void>;
  updateSituation: (update: SituationUpdate) => Promise<void>;
  transitionTo: (newState: SituationState, reason: string) => Promise<void>;
  resolveSituation: () => Promise<void>;
  resetToIdle: () => void;

  // Evidence tracking
  markEvidenceFlag: (flag: keyof SituationEvidence, value: boolean | number) => void;
  incrementConfidence: (points: number) => void;

  // History
  transitions: SituationTransition[];
}

// ============================================================================
// CONSTANTS
// ============================================================================

const CONFIDENCE_THRESHOLDS = {
  CANDIDATE: 10,  // Selecting a result
  ACTIVE: 25,     // Opening an entity view
  COOLDOWN: 50,   // Completing an action
  RESOLVED: 100,  // Fully resolved
};

const IDLE_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes of inactivity → IDLE

// ============================================================================
// INITIAL STATE
// ============================================================================

function createInitialEvidence(): SituationEvidence {
  return {
    opened_manual: false,
    viewed_history: false,
    mutation_prepared: false,
    mutation_committed: false,
    handover_added: false,
    repeated_queries_count: 0,
  };
}

// ============================================================================
// HOOK
// ============================================================================

export function useSituationState(): UseSituationStateReturn {
  const [situation, setSituation] = useState<SituationContext | null>(null);
  const [transitions, setTransitions] = useState<SituationTransition[]>([]);
  const idleTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Get session ID from sessionStorage or create new
   */
  const getSessionId = useCallback((): string => {
    if (typeof sessionStorage === 'undefined') return crypto.randomUUID();

    let sessionId = sessionStorage.getItem('celeste_session_id');
    if (!sessionId) {
      sessionId = crypto.randomUUID();
      sessionStorage.setItem('celeste_session_id', sessionId);
    }
    return sessionId;
  }, []);

  /**
   * Infer situation phase from evidence flags
   */
  const inferPhase = useCallback((evidence: SituationEvidence): SituationPhase => {
    if (evidence.mutation_committed) return 'wrapping_up';
    if (evidence.mutation_prepared) return 'acting';
    return 'investigating';
  }, []);

  /**
   * Reset idle timeout
   */
  const resetIdleTimeout = useCallback(() => {
    if (idleTimeoutRef.current) {
      clearTimeout(idleTimeoutRef.current);
    }

    idleTimeoutRef.current = setTimeout(() => {
      console.log('[useSituationState] Idle timeout reached, resetting to IDLE');
      setSituation(null);
      setTransitions([]);
    }, IDLE_TIMEOUT_MS);
  }, []);

  /**
   * Create a new situation
   */
  const createSituation = useCallback(async (payload: CreateSituationPayload) => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const yachtId = await getYachtId();

      if (!session?.user || !yachtId) {
        console.warn('[useSituationState] Cannot create situation: no auth');
        return;
      }

      const now = Date.now();
      const newSituation: SituationContext = {
        // Identity
        yacht_id: yachtId,
        user_id: session.user.id,
        role: session.user.user_metadata?.role || 'Engineer',
        device_type: typeof window !== 'undefined' && window.innerWidth < 768 ? 'mobile' : 'desktop',

        // Situation key
        primary_entity_type: payload.entity_type,
        primary_entity_id: payload.entity_id,
        domain: payload.domain,

        // State
        state: payload.initial_state || 'CANDIDATE',
        confidence_points: payload.initial_state === 'ACTIVE' ? CONFIDENCE_THRESHOLDS.ACTIVE : CONFIDENCE_THRESHOLDS.CANDIDATE,
        phase: 'investigating',

        // Evidence
        evidence: createInitialEvidence(),

        // Nudge control
        nudge_dismissed: {},
        nudge_budget_remaining: 1,

        // Session
        session_id: getSessionId(),
        created_at: now,
        last_activity_at: now,
      };

      setSituation(newSituation);
      resetIdleTimeout();

      console.log('[useSituationState] Created situation:', {
        entity_type: payload.entity_type,
        entity_id: payload.entity_id,
        state: newSituation.state,
      });
    } catch (error) {
      console.error('[useSituationState] Failed to create situation:', error);
    }
  }, [getSessionId, resetIdleTimeout]);

  /**
   * Update current situation
   */
  const updateSituation = useCallback(async (update: SituationUpdate) => {
    if (!situation) {
      console.warn('[useSituationState] Cannot update: no active situation');
      return;
    }

    setSituation(prev => {
      if (!prev) return null;

      const updated = {
        ...prev,
        ...update,
        evidence: update.evidence ? { ...prev.evidence, ...update.evidence } : prev.evidence,
        last_activity_at: update.last_activity_at || Date.now(),
      };

      // Infer phase from evidence
      if (update.evidence) {
        updated.phase = inferPhase(updated.evidence);
      }

      return updated;
    });

    resetIdleTimeout();
  }, [situation, inferPhase, resetIdleTimeout]);

  /**
   * Transition to a new state
   */
  const transitionTo = useCallback(async (newState: SituationState, reason: string) => {
    if (!situation) {
      console.warn('[useSituationState] Cannot transition: no active situation');
      return;
    }

    const transition: SituationTransition = {
      from_state: situation.state,
      to_state: newState,
      reason,
      confidence_change: 0,
      timestamp: Date.now(),
    };

    setTransitions(prev => [...prev, transition]);

    await updateSituation({
      state: newState,
      last_activity_at: Date.now(),
    });

    console.log('[useSituationState] State transition:', {
      from: situation.state,
      to: newState,
      reason,
    });
  }, [situation, updateSituation]);

  /**
   * Mark situation as resolved
   */
  const resolveSituation = useCallback(async () => {
    if (!situation) return;

    await transitionTo('RESOLVED', 'User explicitly resolved situation');

    // Clear after 1 second
    setTimeout(() => {
      setSituation(null);
      setTransitions([]);
    }, 1000);
  }, [situation, transitionTo]);

  /**
   * Reset to IDLE (e.g., back to search)
   */
  const resetToIdle = useCallback(() => {
    if (situation) {
      console.log('[useSituationState] Resetting to IDLE');
    }
    setSituation(null);
    setTransitions([]);

    if (idleTimeoutRef.current) {
      clearTimeout(idleTimeoutRef.current);
      idleTimeoutRef.current = null;
    }
  }, [situation]);

  /**
   * Mark an evidence flag
   */
  const markEvidenceFlag = useCallback((flag: keyof SituationEvidence, value: boolean | number) => {
    if (!situation) return;

    const update: Partial<SituationEvidence> = {
      [flag]: value,
    };

    updateSituation({ evidence: update });

    console.log('[useSituationState] Evidence updated:', flag, value);
  }, [situation, updateSituation]);

  /**
   * Increment confidence points
   */
  const incrementConfidence = useCallback((points: number) => {
    if (!situation) return;

    const newConfidence = situation.confidence_points + points;

    updateSituation({
      confidence_points: newConfidence,
    });

    console.log('[useSituationState] Confidence updated:', {
      old: situation.confidence_points,
      new: newConfidence,
      change: points,
    });
  }, [situation, updateSituation]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (idleTimeoutRef.current) {
        clearTimeout(idleTimeoutRef.current);
      }
    };
  }, []);

  return {
    // State
    situation,
    isActive: situation?.state === 'ACTIVE',
    isCandidate: situation?.state === 'CANDIDATE',
    isIdle: situation === null || situation.state === 'IDLE',

    // Actions
    createSituation,
    updateSituation,
    transitionTo,
    resolveSituation,
    resetToIdle,

    // Evidence
    markEvidenceFlag,
    incrementConfidence,

    // History
    transitions,
  };
}
