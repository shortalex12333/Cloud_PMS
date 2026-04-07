'use client';

/**
 * Shell Hooks — React Query hooks for Vessel Surface + Domain Records
 */

import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/hooks/useAuth';
import { useActiveVessel } from '@/contexts/VesselContext';
import {
  fetchVesselSurface,
  fetchDomainRecords,
  DOMAIN_TO_API,
  type VesselSurfaceResponse,
  type DomainRecordsResponse,
} from './api';
import type { DomainId } from './Sidebar';

/**
 * Fetch Vessel Surface data for the home screen.
 * Returns all 6 sections + domain_counts for sidebar badges.
 */
export function useVesselSurface() {
  const { user } = useAuth();
  const vessel = useActiveVessel();
  // "all" for fleet overview mode, otherwise specific vessel ID
  const vesselId = vessel.isAllVessels ? 'all' : (vessel.vesselId || user?.yachtId);

  return useQuery<VesselSurfaceResponse>({
    queryKey: ['vessel-surface', vesselId],
    queryFn: () => fetchVesselSurface(vesselId!),
    enabled: !!vesselId,
    staleTime: 30_000, // 30s — surface data refreshes on navigation
    refetchOnWindowFocus: true,
  });
}

/**
 * Fetch domain record list for list views + Tier 2 search.
 * Debounce the query string on the caller side.
 */
export function useDomainRecords(
  domain: DomainId,
  params?: { q?: string; status?: string; limit?: number; offset?: number }
) {
  const { user } = useAuth();
  const vessel = useActiveVessel();
  // "all" for fleet overview mode, otherwise specific vessel ID
  const vesselId = vessel.isAllVessels ? 'all' : (vessel.vesselId || user?.yachtId);
  const apiDomain = DOMAIN_TO_API[domain];

  return useQuery<DomainRecordsResponse>({
    queryKey: ['domain-records', vesselId, apiDomain, params?.q, params?.status, params?.limit, params?.offset],
    queryFn: () => fetchDomainRecords(vesselId!, apiDomain, params),
    enabled: !!vesselId && !!apiDomain && domain !== 'surface',
    staleTime: 15_000,
    refetchOnWindowFocus: true,
  });
}

/**
 * Extract sidebar count badges from Vessel Surface domain_counts.
 * Maps API underscore keys to frontend hyphenated DomainIds.
 */
export function useSidebarCounts() {
  const { data } = useVesselSurface();

  if (!data?.domain_counts) return undefined;

  const counts = data.domain_counts;

  const result: Partial<Record<DomainId, { count: number; severity?: 'critical' | 'warning' | 'ok' | null }>> = {};

  // Work Orders
  if (counts.work_orders !== undefined) {
    result['work-orders'] = {
      count: counts.work_orders,
      severity: (counts.work_orders_overdue ?? 0) > 0 ? 'warning' : null,
    };
  }

  // Faults
  if (counts.faults !== undefined) {
    result['faults'] = {
      count: counts.faults,
      severity: (counts.faults_critical ?? 0) > 0 ? 'critical' : null,
    };
  }

  // Parts below min
  if (counts.parts_below_min !== undefined) {
    result['inventory'] = {
      count: counts.parts_below_min,
      severity: counts.parts_below_min > 0 ? 'warning' : null,
    };
  }

  // Certificates expiring
  if (counts.certificates_expiring !== undefined) {
    result['certificates'] = {
      count: counts.certificates_expiring,
      severity: counts.certificates_expiring > 0 ? 'warning' : null,
    };
  }

  return result;
}
