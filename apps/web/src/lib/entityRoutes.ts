/**
 * Entity Route Utilities
 *
 * Fragmented routes are the ONLY architecture (single-surface retired 2026-03-18).
 * Each entity type maps to its own URL route.
 */

/**
 * Get the route for an entity type
 */
export function getEntityRoute(
  entityType: 'work_order' | 'fault' | 'equipment' | 'part' | 'email' | 'shopping_list' | 'receiving' | 'document' | 'certificate' | 'warranty' | 'purchase_order' | 'hours_of_rest' | 'hours_of_rest_signoff' | 'manual' | 'shopping_item' | 'inventory' | 'handover_item' | 'handover_export',
  entityId?: string
): string {
  const routeMap: Record<string, string> = {
    work_order: '/work-orders',
    fault: '/faults',
    equipment: '/equipment',
    part: '/inventory',
    email: '/email',
    shopping_list: '/shopping-list',
    receiving: '/receiving',
    document: '/documents',
    certificate: '/certificates',
    warranty: '/warranties',
    purchase_order: '/purchasing',
    hours_of_rest: '/hours-of-rest',
    hours_of_rest_signoff: '/hours-of-rest/signoffs',
    manual: '/documents',
    shopping_item: '/shopping-list',
    inventory: '/inventory',
    handover_item: '/handover-export',
    handover_export: '/handover-export',
  };

  const base = routeMap[entityType];
  if (!base) return '/';
  return entityId ? `${base}/${entityId}` : base;
}

