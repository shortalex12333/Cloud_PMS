'use client';

/**
 * useFilteredEntityList — React Query hook that fetches entity data
 * from the Render API (pipeline-core).
 *
 * Architecture: Frontend → Render API → Tenant Supabase
 * Frontend does NOT query tenant DB directly.
 * See: docs/Explanations/DB_architecture.md
 */

import { useInfiniteQuery } from '@tanstack/react-query';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/hooks/useAuth';
import { useActiveVessel } from '@/contexts/VesselContext';
import type { ActiveFilters, DateRange } from '../types/filter-config';
import { isDateRange } from '../types/filter-config';
import type { EntityListResult, EntityAdapter } from '../types';

const PAGE_SIZE = 50;
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';

/** Map frontend domain slugs to API domain params */
const DOMAIN_MAP: Record<string, string> = {
  'work-orders': 'work_orders',
  faults: 'faults',
  equipment: 'equipment',
  inventory: 'parts',
  certificates: 'certificates',
  documents: 'documents',
  'handover-export': 'handover',
  'hours-of-rest': 'hours_of_rest',
  'shopping-list': 'shopping_list',
  purchasing: 'purchase_orders',
  receiving: 'receiving',
  warranties: 'warranty',
};

interface UseFilteredEntityListOptions<T> {
  queryKey: string[];
  /** Supabase table name — kept for backwards compat but no longer used for queries */
  table: string;
  /** Columns — kept for backwards compat but no longer used */
  columns: string;
  /** Adapter to convert raw API record to EntityListResult */
  adapter: EntityAdapter<T>;
  /** Active filters */
  filters?: ActiveFilters;
  /** Sort column */
  sortBy?: string;
  /** Sort direction */
  sortDir?: 'asc' | 'desc';
  /** Text fields — no longer needed (API handles search) */
  textFields?: Set<string>;
}

/** Convert API record to the shape adapters expect */
function apiRecordToAdapterInput(record: Record<string, unknown>, domain: string): Record<string, unknown> {
  // Map API response fields to what the adapters expect
  return {
    id: record.id,
    title: record.title,
    description: record.meta,
    status: record.status,
    severity: record.severity,
    priority: record.priority || record.severity,

    // Work orders
    wo_number: record.ref?.toString().replace('WO-', ''),
    equipment_id: record.linked_equipment_id,
    equipment_name: record.linked_equipment_name,
    assigned_to: record.assigned_to,
    assigned_to_name: record.assigned_to,
    due_date: record.due_date,

    // Faults
    fault_code: record.ref?.toString().replace('F-', ''),
    fault_number: record.ref?.toString().replace('F-', ''),
    reported_by_name: record.assigned_to,

    // Parts
    name: record.title,
    part_number: record.ref,
    quantity_on_hand: record.stock_level ?? record.quantity_on_hand,
    minimum_quantity: record.min_stock ?? record.minimum_quantity,
    location: record.location,
    category: record.category,

    // Certificates
    certificate_name: record.title,
    certificate_number: record.ref,
    certificate_type: record.certificate_type,
    issuing_authority: record.issuing_authority,
    expiry_date: record.expiry_date,

    // Generic
    created_at: record.updated_at || record.created_at || new Date().toISOString(),
    updated_at: record.updated_at,

    // Pass through everything else
    ...record,
  };
}

export function useFilteredEntityList<T extends { id: string }>({
  queryKey,
  table,
  columns,
  adapter,
  filters = {},
  sortBy = 'created_at',
  sortDir = 'desc',
  textFields,
}: UseFilteredEntityListOptions<T>) {
  const { user } = useAuth();
  const { vesselId: activeVesselId, isAllVessels } = useActiveVessel();
  // "all" for fleet overview mode, otherwise specific vessel ID
  const effectiveVesselId = isAllVessels ? 'all' : (activeVesselId || user?.yachtId);

  // Derive API domain from queryKey or table name
  const domain = queryKey[0] || '';
  const apiDomain = DOMAIN_MAP[domain] || domain.replace(/-/g, '_');

  const filterKeys = Object.entries(filters)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
    .join('&');

  const query = useInfiniteQuery({
    queryKey: [...queryKey, effectiveVesselId, filterKeys, sortBy, sortDir],
    queryFn: async ({ pageParam = 0 }) => {
      if (!effectiveVesselId) throw new Error('No vessel selected');

      // Get auth token
      const { data: sessionData } = await supabase.auth.getSession();
      const token = sessionData.session?.access_token;
      if (!token) throw new Error('Not authenticated');

      // Build query params
      const params = new URLSearchParams();
      params.set('limit', String(PAGE_SIZE));
      params.set('offset', String(pageParam));
      if (sortBy) params.set('sort', sortBy);

      // Map filters to API params
      for (const [key, value] of Object.entries(filters)) {
        if (value == null) continue;
        if (isDateRange(value)) {
          if (value.from) params.set('date_from', value.from);
          if (value.to) params.set('date_to', value.to);
          continue;
        }
        if (key === 'status' && typeof value === 'string') {
          params.set('status', value);
        } else if (key === 'title' && typeof value === 'string') {
          params.set('q', value);
        } else if (typeof value === 'string') {
          params.set(key, value);
        }
      }

      const url = `${API_BASE}/api/vessel/${effectiveVesselId}/domain/${apiDomain}/records?${params.toString()}`;

      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`API ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      const records = data.records || data.items || [];
      const totalCount = data.total_count ?? data.filtered_count ?? records.length;

      // Convert API records through adapter
      const items: EntityListResult[] = records.map((record: Record<string, unknown>) => {
        const mapped = apiRecordToAdapterInput(record, apiDomain) as T;
        const result = adapter(mapped);
        // Attach vessel attribution from API response (present in overview mode)
        if (record.yacht_name && typeof record.yacht_name === 'string') {
          result.vesselName = record.yacht_name;
        }
        if (record.yacht_id && typeof record.yacht_id === 'string') {
          result.yachtId = record.yacht_id;
        }
        return result;
      });

      return {
        items,
        total: totalCount,
        nextOffset: pageParam + PAGE_SIZE < totalCount ? pageParam + PAGE_SIZE : undefined,
      };
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage) => lastPage.nextOffset,
    enabled: !!effectiveVesselId,
    staleTime: 15_000,
    refetchOnWindowFocus: true,
  });

  // Flatten pages
  const items = query.data?.pages.flatMap((p) => p.items) ?? [];
  const total = query.data?.pages[0]?.total ?? 0;

  return {
    items,
    total,
    isLoading: query.isLoading,
    isFetchingNextPage: query.isFetchingNextPage,
    hasNextPage: query.hasNextPage ?? false,
    fetchNextPage: query.fetchNextPage,
    error: query.error,
  };
}
