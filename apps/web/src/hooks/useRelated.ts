'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/hooks/useAuth';

// ─── Types (mirrors backend RelatedItem + RelatedGroup shapes) ────────────────

export interface RelatedItem {
  entity_type: string;        // "work_order" | "equipment" | "fault" | "part" | "manual" | "attachment" | "handover"
  entity_id: string;          // UUID
  title: string;              // display name — backend field is "title", always present
  subtitle?: string | null;   // secondary info (e.g. WO number, equipment name)
  weight: number;             // 100 | 90 | 80 | 70 — already sorted by backend
  match_reasons: string[];    // ["FK:wo_part", "explicit_link:related", etc.]
}

export interface RelatedGroup {
  group_key: string;          // "equipment" | "faults" | "previous_work" | "parts" | "manuals" | "attachments" | "handovers"
  items: RelatedItem[];
}

export interface RelatedResponse {
  status: string;
  groups: RelatedGroup[];
  add_related_enabled: boolean;
  group_counts: Record<string, number>;
  missing_signals: string[];
  metadata: Record<string, unknown>;
}

// ─── Fetch function ───────────────────────────────────────────────────────────

async function fetchRelated(
  entityType: string,
  entityId: string,
  token: string
): Promise<RelatedResponse> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const url = new URL(`${baseUrl}/v1/related`);
  url.searchParams.set('entity_type', entityType);
  url.searchParams.set('entity_id', entityId);

  const response = await fetch(url.toString(), {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`GET /v1/related failed: ${response.status}`);
  }

  return response.json();
}

// ─── Add relation (HOD/manager only) ─────────────────────────────────────────

interface AddRelatedPayload {
  source_entity_type: string;
  source_entity_id: string;
  target_entity_type: string;
  target_entity_id: string;
  link_type: 'related' | 'reference' | 'evidence' | 'manual'; // NOT "explicit" — GAP-01 fixed in related_routes.py
  note?: string;
}

async function postAddRelated(
  payload: AddRelatedPayload,
  token: string
): Promise<void> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/related/add`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`POST /v1/related/add failed: ${response.status} — ${err}`);
  }
}

// ─── Hook: read related entities ─────────────────────────────────────────────

export function useRelated(entityType: string, entityId: string) {
  const { session } = useAuth();
  const token = session?.access_token;

  return useQuery<RelatedResponse>({
    queryKey: ['related', entityType, entityId],
    queryFn: () => fetchRelated(entityType, entityId, token!),
    enabled: !!token && !!entityId && SUPPORTED_ENTITY_TYPES.includes(entityType as typeof SUPPORTED_ENTITY_TYPES[number]),
    staleTime: 60_000,   // 60s — related data changes infrequently
    retry: 1,
  });
}

// ─── Hook: add explicit relation ──────────────────────────────────────────────

export function useAddRelated(entityType: string, entityId: string) {
  const { session } = useAuth();
  const token = session?.access_token;
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: AddRelatedPayload) => postAddRelated(payload, token!),
    onSuccess: () => {
      // Invalidate so the panel refreshes immediately
      queryClient.invalidateQueries({ queryKey: ['related', entityType, entityId] });
    },
  });
}

// ─── Constants ────────────────────────────────────────────────────────────────

// Entity types the backend supports. Pages for other entity types should not
// show the Show Related button until the backend adds FK traversal.
// See SHOW_RELATED_BACKEND.md §11 GAP-03 for details.
export const SUPPORTED_ENTITY_TYPES = ['work_order', 'fault', 'equipment', 'part'] as const;

// Fixed display order for groups — do not reorder dynamically
export const GROUP_DISPLAY_ORDER = [
  'equipment',
  'faults',
  'previous_work',
  'parts',
  'manuals',
  'attachments',
  'handovers',
] as const;

// Human-readable labels for each group key
export const GROUP_LABELS: Record<string, string> = {
  equipment:     'Equipment',
  faults:        'Faults',
  previous_work: 'Previous Work Orders',
  parts:         'Parts',
  manuals:       'Manuals',
  attachments:   'Attachments',
  handovers:     'Handovers',
};
