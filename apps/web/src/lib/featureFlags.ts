/**
 * Feature Flags for Fragmented Routes Migration
 *
 * Controls the gradual rollout of the new route-based architecture.
 * When enabled, routes like /work-orders, /faults, /equipment, /inventory
 * become active. When disabled, users are redirected to legacy /app.
 *
 * @see REQUIREMENTS_TABLE.md - FF-01, FF-02
 */

/**
 * Check if fragmented routes are enabled
 *
 * Uses build-time environment variable for deterministic behavior.
 * Set NEXT_PUBLIC_FRAGMENTED_ROUTES_ENABLED=true in deployment to enable.
 */
export function isFragmentedRoutesEnabled(): boolean {
  return process.env.NEXT_PUBLIC_FRAGMENTED_ROUTES_ENABLED === 'true';
}

/**
 * Get the appropriate route for an entity type
 *
 * Returns the fragmented route if enabled, otherwise returns legacy /app route.
 */
export function getEntityRoute(
  entityType: 'work_order' | 'fault' | 'equipment' | 'part' | 'email' | 'shopping_list' | 'receiving' | 'document' | 'certificate' | 'warranty' | 'purchase_order' | 'hours_of_rest',
  entityId?: string
): string {
  if (isFragmentedRoutesEnabled()) {
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
    };

    const base = routeMap[entityType] || '/app';
    return entityId ? `${base}/${entityId}` : base;
  }

  // Legacy route
  return entityId
    ? `/app?entity=${entityType}&id=${entityId}`
    : '/app';
}

/**
 * Feature flag names for reference
 */
export const FEATURE_FLAGS = {
  FRAGMENTED_ROUTES: 'NEXT_PUBLIC_FRAGMENTED_ROUTES_ENABLED',
} as const;
