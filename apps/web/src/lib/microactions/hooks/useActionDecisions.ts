'use client';

/**
 * useActionDecisions Hook
 *
 * Phase 11.2: Replaces client-side shouldShowAction() with server decisions.
 *
 * Calls /v1/decisions endpoint to get ActionDecision[] for all 30 actions.
 * UI renders decisions - UI does NOT make decisions.
 *
 * Per E020: "The UI must render decisions, not make them."
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';

// Decision types from E020/E021
export interface ConfidenceBreakdown {
  intent: number;
  entity: number;
  situation: number;
}

export interface BlockedBy {
  type: 'state_guard' | 'missing_trigger' | 'threshold' | 'permission' | 'forbidden';
  detail: string;
}

export interface ActionDecision {
  action: string;
  allowed: boolean;
  tier: 'primary' | 'conditional' | 'rare';
  confidence: number;
  reasons: string[];
  breakdown: ConfidenceBreakdown;
  blocked_by?: BlockedBy;
  explanation: string;
}

export interface DecisionResponse {
  execution_id: string;
  yacht_id: string;
  user_id: string;
  user_role: string;
  decisions: ActionDecision[];
  allowed_count: number;
  blocked_count: number;
  timing_ms: number;
}

// Entity input for decision request
export interface EntityInput {
  type: 'work_order' | 'fault' | 'equipment' | 'part' | 'purchase' | 'handover';
  id?: string;
  name?: string;
  status?: string;
  has_work_order?: boolean;
  has_checklist?: boolean;
  has_manual?: boolean;
  acknowledged?: boolean;
}

export interface UseActionDecisionsOptions {
  /** Detected user intents (e.g., 'diagnose', 'repair', 'view') */
  detected_intents?: string[];
  /** Entity context for evaluation */
  entities?: EntityInput[];
  /** Additional situation flags */
  situation?: Record<string, unknown>;
  /** Environment: at_sea, shipyard, port */
  environment?: string;
  /** Whether to include blocked actions in response */
  include_blocked?: boolean;
  /** Polling interval in ms (0 = no polling) */
  poll_interval?: number;
  /** Skip fetching if true */
  skip?: boolean;
}

interface UseActionDecisionsReturn {
  /** All decisions from server */
  decisions: ActionDecision[];
  /** Decisions grouped by tier */
  byTier: {
    primary: ActionDecision[];
    conditional: ActionDecision[];
    rare: ActionDecision[];
  };
  /** Only allowed (visible) decisions */
  allowedDecisions: ActionDecision[];
  /** Only blocked (hidden) decisions */
  blockedDecisions: ActionDecision[];
  /** Check if specific action is allowed */
  isAllowed: (actionName: string) => boolean;
  /** Get decision for specific action */
  getDecision: (actionName: string) => ActionDecision | undefined;
  /** Get disabled reason for action */
  getDisabledReason: (actionName: string) => string | undefined;
  /** Execution ID for audit/debugging */
  executionId: string | null;
  /** Loading state */
  isLoading: boolean;
  /** Error state */
  error: string | null;
  /** Timing from server */
  timingMs: number | null;
  /** Refetch decisions */
  refetch: () => Promise<void>;
}

const PIPELINE_URL = process.env.NEXT_PUBLIC_PIPELINE_URL || 'https://pipeline-core.int.celeste7.ai';

/**
 * Hook for fetching action decisions from the Decision Engine.
 *
 * Usage:
 * ```tsx
 * const { decisions, isAllowed, getDisabledReason } = useActionDecisions({
 *   detected_intents: ['diagnose'],
 *   entities: [{ type: 'fault', id: faultId, status: 'reported' }],
 * });
 *
 * // Render button based on decision
 * <button disabled={!isAllowed('diagnose_fault')}>
 *   Diagnose
 * </button>
 * ```
 */
export function useActionDecisions(
  options: UseActionDecisionsOptions = {}
): UseActionDecisionsReturn {
  const {
    detected_intents = [],
    entities = [],
    situation = {},
    environment = 'at_sea',
    include_blocked = true,
    poll_interval = 0,
    skip = false,
  } = options;

  const { session, isLoading: authLoading } = useAuth();

  const [decisions, setDecisions] = useState<ActionDecision[]>([]);
  const [executionId, setExecutionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timingMs, setTimingMs] = useState<number | null>(null);

  const fetchDecisions = useCallback(async () => {
    if (skip || authLoading || !session?.access_token) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${PIPELINE_URL}/v1/decisions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          detected_intents,
          entities,
          situation,
          environment,
          include_blocked,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Decision fetch failed: ${response.status} - ${errorText}`);
      }

      const data: DecisionResponse = await response.json();

      setDecisions(data.decisions);
      setExecutionId(data.execution_id);
      setTimingMs(data.timing_ms);
    } catch (err) {
      console.error('[useActionDecisions] Error:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
      // Keep previous decisions on error for resilience
    } finally {
      setIsLoading(false);
    }
  }, [
    skip,
    authLoading,
    session?.access_token,
    JSON.stringify(detected_intents),
    JSON.stringify(entities),
    JSON.stringify(situation),
    environment,
    include_blocked,
  ]);

  // Initial fetch
  useEffect(() => {
    fetchDecisions();
  }, [fetchDecisions]);

  // Polling (if enabled)
  useEffect(() => {
    if (poll_interval <= 0) return;

    const interval = setInterval(fetchDecisions, poll_interval);
    return () => clearInterval(interval);
  }, [fetchDecisions, poll_interval]);

  // Memoized computations
  const allowedDecisions = useMemo(
    () => decisions.filter((d) => d.allowed),
    [decisions]
  );

  const blockedDecisions = useMemo(
    () => decisions.filter((d) => !d.allowed),
    [decisions]
  );

  const byTier = useMemo(
    () => ({
      primary: decisions.filter((d) => d.tier === 'primary' && d.allowed),
      conditional: decisions.filter((d) => d.tier === 'conditional' && d.allowed),
      rare: decisions.filter((d) => d.tier === 'rare' && d.allowed),
    }),
    [decisions]
  );

  const isAllowed = useCallback(
    (actionName: string): boolean => {
      const decision = decisions.find((d) => d.action === actionName);
      return decision?.allowed ?? false;
    },
    [decisions]
  );

  const getDecision = useCallback(
    (actionName: string): ActionDecision | undefined => {
      return decisions.find((d) => d.action === actionName);
    },
    [decisions]
  );

  const getDisabledReason = useCallback(
    (actionName: string): string | undefined => {
      const decision = decisions.find((d) => d.action === actionName);
      if (!decision) return 'Action not found';
      if (decision.allowed) return undefined;
      return decision.blocked_by?.detail || 'Action not available';
    },
    [decisions]
  );

  return {
    decisions,
    byTier,
    allowedDecisions,
    blockedDecisions,
    isAllowed,
    getDecision,
    getDisabledReason,
    executionId,
    isLoading,
    error,
    timingMs,
    refetch: fetchDecisions,
  };
}

export default useActionDecisions;
