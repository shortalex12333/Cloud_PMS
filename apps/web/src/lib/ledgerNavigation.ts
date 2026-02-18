/**
 * ledgerNavigation.ts
 * ====================
 *
 * Maps ledger entity types to their lens routes and provides
 * click handler helpers for LedgerEventCard navigation.
 *
 * Supported entity types:
 * - work_order       → /work-orders/{id}
 * - fault            → /faults/{id}
 * - equipment        → /equipment/{id}
 * - part             → /parts/{id}
 * - certificate      → /certificates/{id}
 * - handover         → /handover/{id}
 * - hours_of_rest    → /hours-of-rest/{id}
 * - warranty         → /warranty/{id}
 * - shopping_list    → /shopping-list/{id}
 * - handover_export  → /handover-export/{id}
 */

import { AppRouterInstance } from 'next/dist/shared/lib/app-router-context.shared-runtime';

// ============================================================================
// ENTITY ROUTES
// ============================================================================

export const ENTITY_ROUTES: Record<string, (id: string) => string> = {
  work_order: (id) => `/work-orders/${id}`,
  fault: (id) => `/faults/${id}`,
  equipment: (id) => `/equipment/${id}`,
  part: (id) => `/parts/${id}`,
  certificate: (id) => `/certificates/${id}`,
  handover: (id) => `/handover/${id}`,
  hours_of_rest: (id) => `/hours-of-rest/${id}`,
  warranty: (id) => `/warranty/${id}`,
  shopping_list: (id) => `/shopping-list/${id}`,
  handover_export: (id) => `/handover-export/${id}`,
};

// ============================================================================
// ROUTE BUILDER
// ============================================================================

/**
 * Get the route for a given entity type and ID.
 * Returns null if the entity type has no registered route.
 */
export function getEntityRoute(entityType: string, entityId: string): string | null {
  const routeBuilder = ENTITY_ROUTES[entityType];
  if (!routeBuilder) return null;
  return routeBuilder(entityId);
}

// ============================================================================
// CLICK HANDLER
// ============================================================================

/**
 * Navigate to the lens for a ledger event's entity.
 *
 * For handover_export entities, appends a mode query param:
 * - action === 'requires_countersignature' → ?mode=review
 * - otherwise → ?mode=edit
 *
 * @param entityType - The entity_type field from the ledger event
 * @param entityId   - The entity_id field from the ledger event
 * @param action     - The action field from the ledger event (optional)
 * @param router     - Next.js router instance from useRouter()
 */
export function handleLedgerClick(
  entityType: string,
  entityId: string,
  action?: string,
  router?: AppRouterInstance
): void {
  const route = getEntityRoute(entityType, entityId);
  if (!route) return;

  // Add mode param for handover exports based on action
  if (entityType === 'handover_export') {
    if (action === 'requires_countersignature') {
      router?.push(`${route}?mode=review`);
    } else {
      router?.push(`${route}?mode=edit`);
    }
    return;
  }

  router?.push(route);
}
