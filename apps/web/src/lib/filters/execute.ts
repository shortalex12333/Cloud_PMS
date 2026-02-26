/**
 * Quick Filters Execution Layer
 *
 * Applies filter logic to entity lists.
 * Filters are applied client-side until backend facet columns are added to search_index.
 *
 * NOTE: This is Phase 1 implementation. Phase 2 will move filter execution to backend.
 */

import { getFilterById, type QuickFilter } from './catalog';

// =============================================================================
// WORK ORDER FILTERS
// =============================================================================

interface WorkOrderItem {
  id: string;
  status: string;
  priority?: string;
  due_date?: string;
  assigned_to?: string;
  [key: string]: unknown;
}

/**
 * Apply work order filter to list
 */
export function applyWorkOrderFilter(
  items: WorkOrderItem[],
  filterId: string
): WorkOrderItem[] {
  const now = new Date();
  const nowDate = now.toISOString().split('T')[0]; // YYYY-MM-DD
  const weekFromNow = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000)
    .toISOString()
    .split('T')[0];

  switch (filterId) {
    case 'wo_overdue':
      return items.filter((item) => {
        if (!item.due_date) return false;
        const dueDate = item.due_date.split('T')[0];
        return (
          dueDate < nowDate &&
          !['completed', 'cancelled', 'closed'].includes(item.status)
        );
      });

    case 'wo_due_7d':
      return items.filter((item) => {
        if (!item.due_date) return false;
        const dueDate = item.due_date.split('T')[0];
        return (
          dueDate >= nowDate &&
          dueDate <= weekFromNow &&
          !['completed', 'cancelled', 'closed'].includes(item.status)
        );
      });

    case 'wo_open':
      // DB schema: status uses 'planned', 'in_progress' (not 'open')
      return items.filter((item) =>
        ['planned', 'in_progress'].includes(item.status)
      );

    case 'wo_priority_emergency':
      return items.filter(
        (item) =>
          item.priority === 'emergency' &&
          !['completed', 'cancelled', 'closed'].includes(item.status)
      );

    case 'wo_priority_critical':
      return items.filter(
        (item) =>
          item.priority === 'critical' &&
          !['completed', 'cancelled', 'closed'].includes(item.status)
      );

    default:
      return items;
  }
}

// =============================================================================
// FAULT FILTERS
// =============================================================================

interface FaultItem {
  id: string;
  status: string;
  severity?: string;
  [key: string]: unknown;
}

/**
 * Apply fault filter to list
 */
export function applyFaultFilter(items: FaultItem[], filterId: string): FaultItem[] {
  switch (filterId) {
    case 'fault_open':
      return items.filter((item) => item.status === 'open');

    case 'fault_unresolved':
      // DB schema: 'work_ordered' status doesn't exist, only 'open', 'investigating', 'closed'
      return items.filter((item) =>
        ['open', 'investigating'].includes(item.status)
      );

    case 'fault_critical':
      // DB schema: severity uses 'high', 'medium' (not 'critical', 'safety')
      return items.filter((item) => item.severity === 'high');

    case 'fault_investigating':
      return items.filter((item) => item.status === 'investigating');

    default:
      return items;
  }
}

// =============================================================================
// EQUIPMENT FILTERS
// =============================================================================

interface EquipmentItem {
  id: string;
  status?: string;
  criticality?: string;
  attention_flag?: boolean;
  [key: string]: unknown;
}

/**
 * Apply equipment filter to list
 */
export function applyEquipmentFilter(
  items: EquipmentItem[],
  filterId: string
): EquipmentItem[] {
  switch (filterId) {
    case 'eq_attention':
      return items.filter((item) => item.attention_flag === true);

    case 'eq_failed':
      return items.filter((item) => item.status === 'failed');

    case 'eq_maintenance':
      return items.filter((item) => item.status === 'maintenance');

    case 'eq_critical':
      return items.filter((item) => item.criticality === 'critical');

    default:
      return items;
  }
}

// =============================================================================
// INVENTORY FILTERS
// =============================================================================

interface InventoryItem {
  id: string;
  quantity_on_hand?: number;
  minimum_quantity?: number;
  [key: string]: unknown;
}

/**
 * Apply inventory filter to list
 */
export function applyInventoryFilter(
  items: InventoryItem[],
  filterId: string
): InventoryItem[] {
  switch (filterId) {
    case 'inv_low_stock':
      return items.filter((item) => {
        const onHand = item.quantity_on_hand ?? 0;
        const minQty = item.minimum_quantity ?? 0;
        return minQty > 0 && onHand <= minQty;
      });

    case 'inv_out_of_stock':
      return items.filter((item) => (item.quantity_on_hand ?? 0) === 0);

    default:
      return items;
  }
}

// =============================================================================
// CERTIFICATE FILTERS
// =============================================================================

interface CertificateItem {
  id: string;
  status?: string;
  expiry_date?: string;
  [key: string]: unknown;
}

/**
 * Apply certificate filter to list
 */
export function applyCertificateFilter(
  items: CertificateItem[],
  filterId: string
): CertificateItem[] {
  const now = new Date();
  const nowDate = now.toISOString().split('T')[0];
  const thirtyDaysFromNow = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000)
    .toISOString()
    .split('T')[0];

  switch (filterId) {
    case 'cert_expiring_30d':
      return items.filter((item) => {
        if (!item.expiry_date || item.status === 'superseded') return false;
        const expiryDate = item.expiry_date.split('T')[0];
        return expiryDate >= nowDate && expiryDate <= thirtyDaysFromNow;
      });

    case 'cert_expired':
      return items.filter((item) => {
        if (!item.expiry_date || item.status === 'superseded') return false;
        const expiryDate = item.expiry_date.split('T')[0];
        return expiryDate < nowDate;
      });

    default:
      return items;
  }
}

// =============================================================================
// GENERIC FILTER APPLICATION
// =============================================================================

/**
 * Apply filter by domain
 * Returns filtered items or original items if filter not found/applicable
 */
export function applyFilter<T extends Record<string, unknown>>(
  items: T[],
  filterId: string | null,
  domain: string
): T[] {
  if (!filterId) return items;

  const filter = getFilterById(filterId);
  if (!filter || filter.blocked) return items;

  switch (domain) {
    case 'work-orders':
      return applyWorkOrderFilter(items as unknown as WorkOrderItem[], filterId) as unknown as T[];
    case 'faults':
      return applyFaultFilter(items as unknown as FaultItem[], filterId) as unknown as T[];
    case 'equipment':
      return applyEquipmentFilter(items as unknown as EquipmentItem[], filterId) as unknown as T[];
    case 'inventory':
      return applyInventoryFilter(items as unknown as InventoryItem[], filterId) as unknown as T[];
    case 'certificates':
      return applyCertificateFilter(items as unknown as CertificateItem[], filterId) as unknown as T[];
    default:
      return items;
  }
}

/**
 * Get human-readable filter label for display
 */
export function getFilterLabel(filterId: string): string | null {
  const filter = getFilterById(filterId);
  return filter?.label || null;
}
