/**
 * Entity Route Utilities
 *
 * Fragmented routes are the ONLY architecture (single-surface retired 2026-03-18).
 * Each entity type maps to its own URL route.
 *
 * Latent-bug correction 2026-04-24 (HANDOVER08 + WORKORDER05):
 *   `'handover_item'` was previously mapped to `/handover-export/{id}` —
 *   which 404'd because `handover_items.id` is not a `handover_exports.id`,
 *   yet the route expected the latter. Callers need either:
 *     (a) the PARENT export URL  → `/handover-export/{export_id}`
 *         (needs a join, not expressible as a static routeMap entry), or
 *     (b) the SOURCE entity URL  → `/<entity_type>/<entity_id>` via the
 *         stored `handover_items.entity_url` column (canonical — already
 *         populated at export time using this same helper).
 *   Removed from the map so accidental future use falls through to '/',
 *   which surfaces loudly in dev instead of silently 404ing.
 *   If you have a `handover_item` row and want its URL, read
 *   `handover_items.entity_url` directly; don't call this helper for it.
 */

export type EntityRouteType =
  | 'work_order'
  | 'fault'
  | 'equipment'
  | 'part'
  | 'email'
  | 'shopping_list'
  | 'receiving'
  | 'document'
  | 'certificate'
  | 'warranty'
  | 'purchase_order'
  | 'hours_of_rest'
  | 'hours_of_rest_signoff'
  | 'manual'
  | 'shopping_item'
  | 'inventory'
  | 'handover_item'   // intentionally has NO routeMap entry — see header
  | 'handover_export';

/**
 * Get the route for an entity type.
 *
 * Unknown types (or the explicitly-unsupported `'handover_item'`) return '/'
 * so the caller's UI surfaces a visible bug rather than silently 404ing.
 */
export function getEntityRoute(
  entityType: EntityRouteType,
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
    // handover_item intentionally absent — see file header comment.
    handover_export: '/handover-export',
  };

  const base = routeMap[entityType];
  if (!base) return '/';
  return entityId ? `${base}/${entityId}` : base;
}

