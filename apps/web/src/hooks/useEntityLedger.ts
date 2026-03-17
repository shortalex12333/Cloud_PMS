'use client';

import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/hooks/useAuth';
import type { AuditLogEntry } from '@/components/lens/sections/HistorySection';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

// Clickthrough navigation: entity_type → frontend route prefix
const ENTITY_ROUTES: Record<string, string> = {
  work_order:         '/work-orders',
  fault:              '/faults',
  equipment:          '/equipment',
  part:               '/inventory',
  shopping_list_item: '/shopping-list',
  receiving:          '/receiving',
  purchase_order:     '/purchasing',
  document:           '/documents',
  certificate:        '/certificates',
};

function buildNavigationUrl(
  entityType: string,
  entityId: string,
  metadata: Record<string, unknown>
): string {
  const base = ENTITY_ROUTES[entityType];
  if (!base || !entityId) return '';
  let url = `${base}/${entityId}`;
  if (metadata?.page) url += `?page=${metadata.page}`;
  return url;
}

async function fetchEntityLedger(
  entityType: string,
  entityId: string,
  token: string
): Promise<AuditLogEntry[]> {
  const res = await fetch(
    `${API_BASE}/v1/ledger/events/by-entity/${entityType}/${entityId}?limit=50`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  if (!res.ok) return [];
  const json = await res.json();
  return (json.events || []).map((ev: Record<string, unknown>) => {
    const metadata = (ev.metadata as Record<string, unknown>) || {};
    return {
      id: (ev.id as string) || String(Math.random()),
      action: (ev.action as string) || 'unknown',
      actor: (ev.actor_name as string) || (ev.user_id as string)?.slice(0, 8) || 'system',
      actor_id: ev.user_id as string,
      timestamp: (ev.created_at as string) || new Date().toISOString(),
      description: ev.change_summary as string | undefined,
      details: metadata,
      navigation_url: buildNavigationUrl(
        ev.entity_type as string,
        ev.entity_id as string,
        metadata
      ),
    };
  });
}

export function useEntityLedger(entityType: string, entityId: string | undefined) {
  const { session } = useAuth();
  const token = session?.access_token;

  return useQuery({
    queryKey: ['entity-ledger', entityType, entityId],
    queryFn: () => fetchEntityLedger(entityType, entityId!, token!),
    enabled: !!entityId && !!token,
    staleTime: 30_000,
    retry: 1,
  });
}
