/**
 * Maps legacy QuickFilter IDs to ActiveFilters objects.
 * Extracted from FilteredEntityList so both FilterPanel and
 * FilteredEntityList can use it for preset/URL initialization.
 */

import type { ActiveFilters, DateRange } from '@/features/entity-list/types/filter-config';

function _isoDate(d: Date): string {
  return d.toISOString().split('T')[0];
}

function _certExpiring30d(): DateRange {
  const today = new Date();
  const future = new Date();
  future.setDate(today.getDate() + 30);
  return { from: _isoDate(today), to: _isoDate(future) };
}

function _certExpired(): DateRange {
  const today = new Date();
  return { from: '2000-01-01', to: _isoDate(today) };
}

const LEGACY_FILTER_MAP: Record<string, ActiveFilters> = {
  wo_overdue: { status: 'planned' },
  wo_open: { status: 'planned' },
  wo_due_7d: { status: 'planned' },
  wo_priority_emergency: { priority: 'emergency' },
  wo_priority_critical: { priority: 'critical' },
  fault_open: { status: 'open' },
  fault_unresolved: { status: 'open' },
  fault_critical: { severity: 'high' },
  fault_investigating: { status: 'investigating' },
  eq_attention: {},
  eq_failed: { status: 'failed' },
  eq_maintenance: { status: 'maintenance' },
  eq_critical: { criticality: 'critical' },
  inv_low_stock: { _stock_status: 'low' },
  inv_out_of_stock: { _stock_status: 'out' },
  cert_expiring_30d: { expiry_date: _certExpiring30d() },
  cert_expired: { expiry_date: _certExpired() },
  shop_pending: { status: 'candidate' },
  shop_urgent: { urgency: 'critical' },
  recv_pending: { status: 'draft' },
};

export function mapLegacyFilter(filterId: string): ActiveFilters | null {
  return LEGACY_FILTER_MAP[filterId] ?? null;
}
