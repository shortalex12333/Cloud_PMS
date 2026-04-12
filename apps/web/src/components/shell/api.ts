/**
 * Shell API — fetchers for Vessel Surface + Domain Records
 *
 * Uses the same API base URL and auth pattern as the rest of the app.
 * Endpoints built by ENGINEER01 on the FastAPI backend.
 */

import { supabase } from '@/lib/supabaseClient';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

/** Get current access token from Supabase session */
async function getToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

/** Authenticated fetch wrapper */
async function apiFetch<T>(path: string): Promise<T> {
  const token = await getToken();
  if (!token) throw new Error('Not authenticated');

  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText}`);
  }

  return res.json();
}

/* ─────────────────────────────────────────────
   TYPES — match ENGINEER01's response schemas
   ───────────────────────────────────────────── */

export interface VesselSurfaceResponse {
  work_orders: {
    open_count: number;
    overdue_count: number;
    items: SurfaceItem[];
    limit: number;
  };
  faults: {
    open_count: number;
    critical_count: number;
    items: SurfaceItem[];
  };
  last_handover: {
    id: string;
    from_crew: string;
    to_crew: string;
    signed_at: string;
    status: string;
    is_draft?: boolean;
  } | null;
  parts_below_min: {
    count: number;
    items: SurfacePartItem[];
  };
  recent_activity: SurfaceActivityItem[];
  certificates_expiring: {
    count: number;
    items: SurfaceCertItem[];
  };
  domain_counts: Record<string, number>;
}

export interface SurfaceItem {
  id: string;
  title: string;
  ref?: string;
  wo_number?: string;
  fault_code?: string;
  equipment_id?: string;
  equipment_name?: string;
  assigned_to?: string;
  status: string;
  priority?: string;
  age_days?: number;
  due_date?: string;
  severity?: string;
  yacht_id?: string;
  yacht_name?: string;
}

export interface SurfacePartItem {
  id: string;
  name: string;
  stock_level: number;
  min_stock: number;
  location?: string;
  linked_equipment_id?: string;
}

export interface SurfaceActivityItem {
  entity_type: string;
  entity_id: string;
  entity_ref: string;
  action: string;
  actor: string;
  timestamp: string;
  time_display?: string;
  summary: string;
}

export interface SurfaceCertItem {
  id: string;
  name: string;
  expiry_date: string;
  days_remaining: number;
  status: string;
}

export interface DomainRecordsResponse {
  domain: string;
  total_count: number;
  filtered_count: number;
  records: DomainRecord[];
  /** True when vessel_id=all (fleet overview mode) */
  is_overview?: boolean;
}

export interface DomainRecord {
  id: string;
  ref: string;
  title: string;
  status: string;
  priority?: string;
  assigned_to?: string;
  linked_equipment_id?: string;
  linked_equipment_name?: string;
  age_display?: string;
  updated_at?: string;
  meta: string;
  /** Present in overview mode — identifies which vessel this record belongs to */
  yacht_id?: string;
  /** Vessel name — present in overview mode for display */
  yacht_name?: string;
}

/* ─────────────────────────────────────────────
   FETCHERS
   ───────────────────────────────────────────── */

/** Fetch Vessel Surface data for the home screen */
export function fetchVesselSurface(vesselId: string): Promise<VesselSurfaceResponse> {
  return apiFetch(`/api/vessel/${vesselId}/surface`);
}

/** Fetch domain record list (powers list views + Tier 2 search) */
export function fetchDomainRecords(
  vesselId: string,
  domain: string,
  params?: { q?: string; status?: string; limit?: number; offset?: number }
): Promise<DomainRecordsResponse> {
  const searchParams = new URLSearchParams();
  if (params?.q) searchParams.set('q', params.q);
  if (params?.status) searchParams.set('status', params.status);
  if (params?.limit) searchParams.set('limit', String(params.limit));
  if (params?.offset) searchParams.set('offset', String(params.offset));

  const qs = searchParams.toString();
  return apiFetch(`/api/vessel/${vesselId}/domain/${domain}/records${qs ? `?${qs}` : ''}`);
}

/** Fetch unread email count */
export async function fetchEmailUnreadCount(): Promise<number> {
  try {
    const data = await apiFetch<{ unread_count: number }>('/email/unread-count');
    return data.unread_count ?? 0;
  } catch {
    return 0; // Email not connected or token expired — no badge
  }
}

/* ─────────────────────────────────────────────
   HANDOVER QUEUE
   ───────────────────────────────────────────── */

/** Single item in a queue section. Fields vary by section type. */
export interface HandoverQueueItem {
  id: string;
  title?: string;           // faults, work_orders, pending_orders
  name?: string;            // low_stock_parts
  severity?: string;        // faults
  equipment_name?: string;  // faults
  created_at?: string;      // faults, pending_orders
  priority?: string;        // work_orders
  due_at?: string;          // work_orders
  assigned_to?: string;     // work_orders
  current_qty?: number;     // low_stock_parts
  reorder_threshold?: number; // low_stock_parts
  status?: string;          // pending_orders
}

/** An entity already added to the active handover draft */
export interface HandoverQueuedItem {
  id: string;
  entity_type: string;
  entity_id: string;
  summary: string;
  priority?: string;
}

export interface HandoverQueueResponse {
  open_faults: HandoverQueueItem[];
  overdue_work_orders: HandoverQueueItem[];
  low_stock_parts: HandoverQueueItem[];
  pending_orders: HandoverQueueItem[];
  already_queued: HandoverQueuedItem[];
  counts: {
    faults: number;
    work_orders: number;
    parts: number;
    orders: number;
    already_queued: number;
  };
}

/** Fetch items auto-detected as relevant for next handover */
export function fetchHandoverQueue(vesselId: string): Promise<HandoverQueueResponse> {
  return apiFetch(`/v1/actions/handover/queue?vessel_id=${encodeURIComponent(vesselId)}`);
}

/* ─────────────────────────────────────────────
   DOMAIN ID MAPPING
   Frontend routes use hyphens, API uses underscores.
   ───────────────────────────────────────────── */

/** Map frontend route domain IDs to API domain params */
export const DOMAIN_TO_API: Record<string, string> = {
  'work-orders': 'work_orders',
  'faults': 'faults',
  'equipment': 'equipment',
  'handover-export': 'handover',
  'hours-of-rest': 'hours_of_rest',
  'inventory': 'parts',
  'shopping-list': 'shopping_list',
  'purchasing': 'purchase_orders',
  'receiving': 'receiving',
  'certificates': 'certificates',
  'documents': 'documents',
  'warranties': 'warranty',
};
