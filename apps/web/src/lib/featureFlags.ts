/**
 * Feature Flags for Celeste7
 *
 * Build-time feature flag resolution for controlled rollout of new features.
 * No external dependencies - simple env var checks.
 *
 * @see REQUIREMENTS_TABLE.md - FF-01, FF-02
 */

/**
 * Check if fragmented routes are enabled
 *
 * When enabled:
 * - /work-orders, /faults, /equipment, /inventory routes are available
 * - Legacy /app route remains accessible
 *
 * When disabled:
 * - Only legacy /app route is available
 * - New routes return 404
 *
 * Set via environment variable:
 * NEXT_PUBLIC_FRAGMENTED_ROUTES_ENABLED=true
 */
export function isFragmentedRoutesEnabled(): boolean {
  return process.env.NEXT_PUBLIC_FRAGMENTED_ROUTES_ENABLED === 'true';
}

/**
 * Feature flag configuration object
 * Useful for passing to components or context
 */
export const featureFlags = {
  get fragmentedRoutes() {
    return isFragmentedRoutesEnabled();
  },
} as const;

/**
 * Route paths for Tier 1 fragmented routes
 * Only exposed when feature flag is enabled
 */
export const fragmentedRoutePaths = {
  workOrders: '/work-orders',
  workOrderDetail: (id: string) => `/work-orders/${id}`,
  faults: '/faults',
  faultDetail: (id: string) => `/faults/${id}`,
  equipment: '/equipment',
  equipmentDetail: (id: string) => `/equipment/${id}`,
  inventory: '/inventory',
  inventoryDetail: (id: string) => `/inventory/${id}`,
  email: '/email',
} as const;

/**
 * Get the appropriate route for an entity type
 * Falls back to legacy /app route if fragmented routes disabled
 */
export function getEntityRoute(
  entityType: 'work_order' | 'fault' | 'equipment' | 'part' | 'email',
  entityId?: string
): string {
  if (!isFragmentedRoutesEnabled()) {
    // Legacy single-URL route with query params
    return entityId
      ? `/app?entity=${entityType}&id=${entityId}`
      : '/app';
  }

  switch (entityType) {
    case 'work_order':
      return entityId
        ? fragmentedRoutePaths.workOrderDetail(entityId)
        : fragmentedRoutePaths.workOrders;
    case 'fault':
      return entityId
        ? fragmentedRoutePaths.faultDetail(entityId)
        : fragmentedRoutePaths.faults;
    case 'equipment':
      return entityId
        ? fragmentedRoutePaths.equipmentDetail(entityId)
        : fragmentedRoutePaths.equipment;
    case 'part':
      return entityId
        ? fragmentedRoutePaths.inventoryDetail(entityId)
        : fragmentedRoutePaths.inventory;
    case 'email':
      return fragmentedRoutePaths.email;
    default:
      return '/app';
  }
}

export default featureFlags;
