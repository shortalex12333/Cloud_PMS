'use client';

/**
 * useSignalRelated
 *
 * Fetches semantically-related entities from the signal endpoint
 * GET /v1/show-related-signal.
 *
 * The signal endpoint serializes the source entity's attributes into text,
 * generates an embedding, and runs f1_search_cards — the same RPC used by
 * the spotlight search bar. Results are cross-domain (WOs, manuals, faults,
 * parts, handovers) ranked by semantic proximity.
 *
 * This runs ALONGSIDE the FK-based useRelated hook — not as a replacement.
 * Items that already appear via FK links get "signal" added to match_reasons.
 * Items that are new appear in the "Also Related" section of RelatedDrawer.
 */

import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/hooks/useAuth';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface SignalRelatedItem {
  entity_type: string;
  entity_id: string;
  title: string;
  subtitle?: string | null;
  match_reasons: string[];
  fused_score?: number;
  weight: number;
}

export interface SignalRelatedResponse {
  status: string;
  entity_type: string;
  entity_id: string;
  entity_text: string;
  items: SignalRelatedItem[];
  count: number;
  signal_source: string;
  metadata: {
    limit: number;
    embedding_generated: boolean;
  };
}

// ─── Supported entity types ───────────────────────────────────────────────────
// Must stay in sync with VALID_ENTITY_TYPES in routes/show_related_signal_routes.py.
// Attachment is intentionally excluded (no standalone lens page).

const SIGNAL_SUPPORTED_TYPES = [
  'work_order',
  'equipment',
  'fault',
  'part',
  'manual',
  'handover_item',
  'handover_export',
] as const;

// ─── Fetch ────────────────────────────────────────────────────────────────────

async function fetchSignalRelated(
  entityType: string,
  entityId: string,
  token: string,
  limit: number
): Promise<SignalRelatedResponse> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const url = new URL(`${baseUrl}/v1/show-related-signal/`);
  url.searchParams.set('entity_type', entityType);
  url.searchParams.set('entity_id', entityId);
  url.searchParams.set('limit', String(limit));

  const response = await fetch(url.toString(), {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`GET /v1/show-related-signal failed: ${response.status}`);
  }

  return response.json();
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useSignalRelated(
  entityType: string,
  entityId: string,
  limit = 10
) {
  const { session } = useAuth();
  const token = session?.access_token;

  return useQuery<SignalRelatedResponse>({
    queryKey: ['signal-related', entityType, entityId, limit],
    queryFn: () => fetchSignalRelated(entityType, entityId, token!, limit),
    enabled:
      !!token &&
      !!entityId &&
      SIGNAL_SUPPORTED_TYPES.includes(
        entityType as (typeof SIGNAL_SUPPORTED_TYPES)[number]
      ),
    staleTime: 300_000, // 5 min — backend uses cached embeddings, no need to refetch often
    refetchOnWindowFocus: false,
    retry: 1,
  });
}
