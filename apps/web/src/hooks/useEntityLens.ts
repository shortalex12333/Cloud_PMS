'use client';

import { useCallback, useState, useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import type { EntityType, AvailableAction, ActionResult } from '@/types/entity';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

export interface UseEntityLensResult {
  entity: Record<string, unknown> | null;
  availableActions: AvailableAction[];
  isLoading: boolean;
  error: string | null;
  executeAction: (actionId: string, payload?: Record<string, unknown>) => Promise<ActionResult>;
  refetch: () => void;
  getAction: (actionId: string) => AvailableAction | null;
}

export function useEntityLens(
  entityType: EntityType,
  entityId: string
): UseEntityLensResult {
  const { session } = useAuth();
  const token = session?.access_token ?? null;

  const [entity, setEntity] = useState<Record<string, unknown> | null>(null);
  const [availableActions, setAvailableActions] = useState<AvailableAction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchEntity = useCallback(async () => {
    if (!entityId || !token) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/v1/entity/${entityType}/${entityId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`${res.status}`);
      const data = await res.json() as Record<string, unknown> & { available_actions?: AvailableAction[] };
      const { available_actions = [], ...rest } = data;
      setEntity(rest);
      setAvailableActions(available_actions);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    } finally {
      setIsLoading(false);
    }
  }, [entityType, entityId, token]);

  useEffect(() => {
    fetchEntity();
  }, [fetchEntity]);

  const executeAction = useCallback(
    async (actionId: string, payload: Record<string, unknown> = {}): Promise<ActionResult> => {
      if (!token) throw new Error('Not authenticated');
      // Merge prefill from the matching available_actions entry
      const actionMeta = availableActions.find((a) => a.action_id === actionId);
      const mergedPayload = { ...actionMeta?.prefill, ...payload };
      const res = await fetch('/api/v1/actions/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          action: actionId,
          context: { entity_id: entityId },
          payload: mergedPayload,
        }),
      });
      const result: ActionResult = await res.json();
      if (res.ok) {
        await fetchEntity();
      }
      return result;
    },
    [token, entityId, availableActions, fetchEntity]
  );

  const getAction = useCallback(
    (actionId: string): AvailableAction | null =>
      availableActions.find((a) => a.action_id === actionId) ?? null,
    [availableActions]
  );

  return { entity, availableActions, isLoading, error, executeAction, refetch: fetchEntity, getAction };
}
