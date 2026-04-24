'use client';

/**
 * useMonthWorkOrders — fetch all work orders with due_date in a given month.
 *
 * Dedicated hook (not reusing useFilteredEntityList) because:
 *   * Calendar needs every WO in the window, not paginated infinite-scroll.
 *   * Backend supports this via the work_orders-specific `due_from` / `due_to`
 *     query params added in PR-WO-5 (vessel_surface_routes.py). No client-side
 *     filter, no N+1.
 *   * Single `useQuery` with generous `limit=500` — enough for any yacht's
 *     monthly WO volume (real-world ~20-60 / month).
 *
 * Returns raw backend records unchanged so the consumer can map exactly the
 * columns they need (UX sheet specifies a distinct calendar column set).
 */

import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/hooks/useAuth';
import { useActiveVessel } from '@/contexts/VesselContext';

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

/** Raw backend record — whatever vessel_surface_routes._format_record emits. */
export interface WorkOrderCalendarRecord {
  id: string;
  ref?: string;              // wo_number (formatter output)
  title: string;
  status?: string;
  priority?: string;
  severity?: string | null;
  wo_type?: string | null;
  frequency?: string | null;
  due_date?: string | null;
  completed_at?: string | null;
  assigned_to?: string | null;
  assigned_to_name?: string | null;
  linked_equipment_id?: string | null;
  linked_equipment_name?: string | null;
  updated_at?: string;
  yacht_id?: string;
  yacht_name?: string;
  // Free-form pass-through for anything the formatter adds.
  [k: string]: unknown;
}

export interface UseMonthWorkOrdersArgs {
  /** First day of the month to fetch, in YYYY-MM-DD. Inclusive. */
  fromISO: string;
  /** Last day of the month to fetch, in YYYY-MM-DD. Inclusive. */
  toISO: string;
  /** Opt-out for pages that know they don't want the fetch. */
  enabled?: boolean;
}

export interface UseMonthWorkOrdersResult {
  records: WorkOrderCalendarRecord[];
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

export function useMonthWorkOrders({
  fromISO,
  toISO,
  enabled = true,
}: UseMonthWorkOrdersArgs): UseMonthWorkOrdersResult {
  const { user } = useAuth();
  const { vesselId: activeVesselId, isAllVessels } = useActiveVessel();
  const effectiveVesselId = isAllVessels
    ? 'all'
    : activeVesselId || user?.yachtId;

  const query = useQuery({
    queryKey: ['work-orders-calendar', effectiveVesselId, fromISO, toISO],
    enabled: enabled && Boolean(effectiveVesselId),
    queryFn: async (): Promise<WorkOrderCalendarRecord[]> => {
      if (!effectiveVesselId) throw new Error('No vessel selected');

      const { data: sessionData } = await supabase.auth.getSession();
      const token = sessionData.session?.access_token;
      if (!token) throw new Error('Not authenticated');

      const params = new URLSearchParams();
      params.set('limit', '500');
      params.set('offset', '0');
      params.set('sort', 'due_date');
      params.set('due_from', fromISO);
      params.set('due_to', toISO);

      const url = `${API_BASE}/api/vessel/${effectiveVesselId}/domain/work_orders/records?${params.toString()}`;

      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (!response.ok) {
        throw new Error(`API ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      return (data.records || data.items || []) as WorkOrderCalendarRecord[];
    },
    staleTime: 60 * 1000, // 1 min
    refetchOnWindowFocus: false,
  });

  return {
    records: query.data ?? [],
    isLoading: query.isLoading,
    error: (query.error as Error) ?? null,
    refetch: () => void query.refetch(),
  };
}

// ── Date helpers ───────────────────────────────────────────────────────────
//
// Calendar uses local-time date keys (YYYY-MM-DD) to avoid timezone drift when
// a yacht spans UTC boundaries. Server returns ISO timestamps; we downcast to
// date-string for bucketing.

export function toISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function firstOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}

export function lastOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth() + 1, 0);
}

/** Return the due-date ISO for a record, trimmed to YYYY-MM-DD or null. */
export function recordDueDateKey(
  record: WorkOrderCalendarRecord,
): string | null {
  const raw = record.due_date;
  if (!raw) return null;
  // Accept both "YYYY-MM-DD" and "YYYY-MM-DDTHH:MM:SS…Z" shapes.
  return String(raw).slice(0, 10);
}
