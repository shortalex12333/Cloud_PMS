import { useCallback, useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/hooks/useAuth';
import { ATTENTION_QUERY_KEY } from '@/hooks/useNeedsAttention';
import type { EntityType, AvailableAction, ActionResult } from '@/types/entity';
import { normalizeWarrantyEntity } from '@/lib/normalizeWarranty';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// entity_type → queryKey[0] used by each FilteredEntityList page. Keeping this
// map here (rather than per-page) lets executeAction invalidate the parent
// list for any action (delete/cancel/status/etc.) without each page having to
// wire a refetch callback through the overlay.
const LIST_QUERY_KEY_FOR_ENTITY: Partial<Record<EntityType, string>> = {
  purchase_order: 'purchasing',
  shopping_list: 'shopping-list',
  certificate: 'certificates',
  document: 'documents',
  receiving: 'receiving',
  warranty: 'warranties',
  work_order: 'work-orders',
  fault: 'faults',
  equipment: 'equipment',
  part: 'inventory',
  handover_export: 'handover-export',
  hours_of_rest: 'hours-of-rest',
};

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
  entityId: string,
  /** Optional yacht_id for cross-vessel access in overview mode */
  yachtId?: string | null
): UseEntityLensResult {
  const { session } = useAuth();
  const queryClient = useQueryClient();
  const token = session?.access_token ?? null;

  const [entity, setEntity] = useState<Record<string, unknown> | null>(null);
  const [availableActions, setAvailableActions] = useState<AvailableAction[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchEntity = useCallback(async () => {
    if (!entityId || !token) return;
    setIsLoading(true);
    setError(null);
    try {
      const yachtParam = yachtId ? `?yacht_id=${yachtId}` : '';
      const res = await fetch(`${API_BASE}/v1/entity/${entityType}/${entityId}${yachtParam}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`${res.status}`);
      const data = await res.json() as Record<string, unknown> & { available_actions?: AvailableAction[] };
      const { available_actions = [], ...rest } = data;
      // Normalize entity shape for warranty (and other entities with field contract deviations)
      const normalized = entityType === 'warranty' ? normalizeWarrantyEntity(rest) : rest;
      setEntity(normalized);
      setAvailableActions(available_actions);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    } finally {
      setIsLoading(false);
    }
  }, [entityType, entityId, yachtId, token]);

  // AbortController prevents stale responses when entityId changes rapidly
  useEffect(() => {
    const controller = new AbortController();

    const run = async () => {
      if (!entityId || !token) return;
      setIsLoading(true);
      setError(null);
      try {
        const yachtParam = yachtId ? `?yacht_id=${yachtId}` : '';
      const res = await fetch(`${API_BASE}/v1/entity/${entityType}/${entityId}${yachtParam}`, {
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
        });
        if (!res.ok) throw new Error(`${res.status}`);
        const data = await res.json() as Record<string, unknown> & { available_actions?: AvailableAction[] };
        const { available_actions = [], ...rest } = data;
        // Normalize entity shape for warranty (and other entities with field contract deviations)
        const normalized = entityType === 'warranty' ? normalizeWarrantyEntity(rest) : rest;
        setEntity(normalized);
        setAvailableActions(available_actions);
      } catch (e) {
        if (e instanceof Error && e.name === 'AbortError') return; // ignore cancellation
        setError(e instanceof Error ? e.message : 'Failed to load');
      } finally {
        setIsLoading(false);
      }
    };

    run();

    return () => controller.abort();
  }, [entityType, entityId, yachtId, token]);

  const executeAction = useCallback(
    async (actionId: string, payload: Record<string, unknown> = {}): Promise<ActionResult> => {
      if (!token) throw new Error('Not authenticated');
      // Merge prefill from the matching available_actions entry
      const actionMeta = availableActions.find((a) => a.action_id === actionId);
      const mergedPayload = { ...actionMeta?.prefill, ...payload };
      // Next.js proxy — mutations route through /api/v1/actions/execute
      const res = await fetch('/api/v1/actions/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          action: actionId,
          context: { entity_id: entityId, ...(yachtId ? { yacht_id: yachtId } : {}) },
          payload: mergedPayload,
        }),
      });
      const result: ActionResult = await res.json();
      if (res.ok) {
        await fetchEntity();
        queryClient.invalidateQueries({ queryKey: [...ATTENTION_QUERY_KEY] });
        // Invalidate the parent domain list so delete/cancel/status actions
        // visually take effect without a manual reload.
        const listKey = LIST_QUERY_KEY_FOR_ENTITY[entityType];
        if (listKey) {
          queryClient.invalidateQueries({ queryKey: [listKey] });
        }
      }
      return result;
    },
    [token, entityId, yachtId, availableActions, fetchEntity, queryClient]
  );

  const getAction = useCallback(
    (actionId: string): AvailableAction | null =>
      availableActions.find((a) => a.action_id === actionId) ?? null,
    [availableActions]
  );

  return { entity, availableActions, isLoading, error, executeAction, refetch: fetchEntity, getAction };
}
