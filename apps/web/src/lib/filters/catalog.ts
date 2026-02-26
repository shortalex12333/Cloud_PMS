/**
 * Quick Filters Catalog - Single Source of Truth
 *
 * Each filter is a predefined, deterministic query that maps to a list route.
 * Filters do NOT invent data - they use existing schema columns only.
 *
 * @see docs/CELESTE_GSD_WORKER_CONTRACT.md for execution rules
 */

export interface QuickFilter {
  /** Stable identifier (e.g., "wo_overdue") */
  filter_id: string;

  /** Button text shown to user */
  label: string;

  /** Route group (e.g., "work-orders") */
  domain: string;

  /** Canonical entity type (e.g., "work_order") */
  entity_type: string;

  /** Target route path */
  route: string;

  /** Query params to append */
  query_params: Record<string, string>;

  /** Keywords that trigger this filter suggestion */
  keywords: string[];

  /** Exact semantic definition (for testing/debugging) */
  definition: string;

  /** Required permissions (optional) */
  guardrails?: string[];

  /** If blocked, reason why */
  blocked?: string;
}

// =============================================================================
// WORK ORDER FILTERS
// =============================================================================

export const WORK_ORDER_FILTERS: QuickFilter[] = [
  {
    filter_id: 'wo_overdue',
    label: 'Overdue work orders',
    domain: 'work-orders',
    entity_type: 'work_order',
    route: '/work-orders',
    query_params: { filter: 'wo_overdue' },
    keywords: ['overdue', 'past due', 'late', 'missed deadline', 'behind schedule'],
    definition: "due_date < CURRENT_DATE AND status NOT IN ('completed', 'cancelled')",
  },
  {
    filter_id: 'wo_due_7d',
    label: 'Due this week',
    domain: 'work-orders',
    entity_type: 'work_order',
    route: '/work-orders',
    query_params: { filter: 'wo_due_7d' },
    keywords: ['due soon', 'due this week', 'upcoming', 'next 7 days', 'coming up'],
    definition: "due_date BETWEEN CURRENT_DATE AND CURRENT_DATE + 7 AND status NOT IN ('completed', 'cancelled')",
  },
  {
    filter_id: 'wo_open',
    label: 'Open work orders',
    domain: 'work-orders',
    entity_type: 'work_order',
    route: '/work-orders',
    query_params: { filter: 'wo_open' },
    keywords: ['open', 'active', 'in progress', 'pending', 'not done'],
    definition: "status IN ('planned', 'in_progress')",
  },
  {
    filter_id: 'wo_priority_emergency',
    label: 'Emergency priority',
    domain: 'work-orders',
    entity_type: 'work_order',
    route: '/work-orders',
    query_params: { filter: 'wo_priority_emergency' },
    keywords: ['emergency', 'urgent', 'critical priority'],
    definition: "priority = 'emergency' AND status NOT IN ('completed', 'cancelled')",
  },
  {
    filter_id: 'wo_priority_critical',
    label: 'Critical priority',
    domain: 'work-orders',
    entity_type: 'work_order',
    route: '/work-orders',
    query_params: { filter: 'wo_priority_critical' },
    keywords: ['critical', 'high priority'],
    definition: "priority = 'critical' AND status NOT IN ('completed', 'cancelled')",
  },
];

// =============================================================================
// FAULT FILTERS
// =============================================================================

export const FAULT_FILTERS: QuickFilter[] = [
  {
    filter_id: 'fault_open',
    label: 'Open faults',
    domain: 'faults',
    entity_type: 'fault',
    route: '/faults',
    query_params: { filter: 'fault_open' },
    keywords: ['open faults', 'active faults', 'unresolved faults'],
    definition: "status = 'open'",
  },
  {
    filter_id: 'fault_unresolved',
    label: 'Unresolved faults',
    domain: 'faults',
    entity_type: 'fault',
    route: '/faults',
    query_params: { filter: 'fault_unresolved' },
    keywords: ['unresolved', 'not fixed', 'pending faults'],
    definition: "status IN ('open', 'investigating')", // DB schema: 'work_ordered' doesn't exist
  },
  {
    filter_id: 'fault_critical',
    label: 'Critical faults',
    domain: 'faults',
    entity_type: 'fault',
    route: '/faults',
    query_params: { filter: 'fault_critical' },
    keywords: ['critical', 'safety', 'severe', 'major fault'],
    definition: "severity = 'high'", // DB schema: 'high' is the highest severity level
  },
  {
    filter_id: 'fault_investigating',
    label: 'Under investigation',
    domain: 'faults',
    entity_type: 'fault',
    route: '/faults',
    query_params: { filter: 'fault_investigating' },
    keywords: ['investigating', 'being looked at'],
    definition: "status = 'investigating'",
  },
];

// =============================================================================
// EQUIPMENT FILTERS
// =============================================================================

export const EQUIPMENT_FILTERS: QuickFilter[] = [
  {
    filter_id: 'eq_attention',
    label: 'Needs attention',
    domain: 'equipment',
    entity_type: 'equipment',
    route: '/equipment',
    query_params: { filter: 'eq_attention' },
    keywords: ['attention', 'flagged', 'needs attention', 'check equipment'],
    definition: 'attention_flag = true',
  },
  {
    filter_id: 'eq_failed',
    label: 'Failed equipment',
    domain: 'equipment',
    entity_type: 'equipment',
    route: '/equipment',
    query_params: { filter: 'eq_failed' },
    keywords: ['failed', 'broken', 'not working', 'down'],
    definition: "status = 'failed'",
  },
  {
    filter_id: 'eq_maintenance',
    label: 'In maintenance',
    domain: 'equipment',
    entity_type: 'equipment',
    route: '/equipment',
    query_params: { filter: 'eq_maintenance' },
    keywords: ['maintenance', 'being serviced', 'under repair'],
    definition: "status = 'maintenance'",
  },
  {
    filter_id: 'eq_critical',
    label: 'Critical equipment',
    domain: 'equipment',
    entity_type: 'equipment',
    route: '/equipment',
    query_params: { filter: 'eq_critical' },
    keywords: ['critical equipment', 'essential', 'vital'],
    definition: "criticality = 'critical'",
  },
  {
    filter_id: 'eq_due_service_30d',
    label: 'Service due (30d)',
    domain: 'equipment',
    entity_type: 'equipment',
    route: '/equipment',
    query_params: { filter: 'eq_due_service_30d' },
    keywords: ['service due', 'needs service', 'maintenance due'],
    definition: 'next_service_date <= CURRENT_DATE + 30',
    blocked: 'SCHEMA_MISSING: next_service_date column does not exist in pms_equipment',
  },
];

// =============================================================================
// INVENTORY FILTERS
// =============================================================================

export const INVENTORY_FILTERS: QuickFilter[] = [
  {
    filter_id: 'inv_low_stock',
    label: 'Low stock',
    domain: 'inventory',
    entity_type: 'part',
    route: '/inventory',
    query_params: { filter: 'inv_low_stock' },
    keywords: ['low stock', 'running low', 'reorder', 'below minimum'],
    definition: 'quantity_on_hand <= minimum_quantity AND minimum_quantity > 0',
  },
  {
    filter_id: 'inv_out_of_stock',
    label: 'Out of stock',
    domain: 'inventory',
    entity_type: 'part',
    route: '/inventory',
    query_params: { filter: 'inv_out_of_stock' },
    keywords: ['out of stock', 'zero stock', 'no stock', 'empty'],
    definition: 'quantity_on_hand = 0',
  },
];

// =============================================================================
// CERTIFICATE FILTERS
// =============================================================================

export const CERTIFICATE_FILTERS: QuickFilter[] = [
  {
    filter_id: 'cert_expiring_30d',
    label: 'Expiring soon',
    domain: 'certificates',
    entity_type: 'certificate',
    route: '/certificates',
    query_params: { filter: 'cert_expiring_30d' },
    keywords: ['expiring', 'expiring soon', 'due for renewal', 'expires'],
    definition: "expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE + 30 AND status != 'superseded'",
  },
  {
    filter_id: 'cert_expired',
    label: 'Expired certificates',
    domain: 'certificates',
    entity_type: 'certificate',
    route: '/certificates',
    query_params: { filter: 'cert_expired' },
    keywords: ['expired', 'past expiry', 'lapsed'],
    definition: "expiry_date < CURRENT_DATE AND status != 'superseded'",
  },
];

// =============================================================================
// EMAIL FILTERS
// =============================================================================

export const EMAIL_FILTERS: QuickFilter[] = [
  {
    filter_id: 'email_unlinked',
    label: 'Unlinked emails',
    domain: 'email',
    entity_type: 'email_thread',
    route: '/email',
    query_params: { filter: 'email_unlinked', linked: 'false' },
    keywords: ['unlinked', 'not linked', 'orphan emails', 'unassigned'],
    definition: 'NOT EXISTS (SELECT 1 FROM email_links WHERE thread_id = id AND is_active = true)',
  },
  {
    filter_id: 'email_linked',
    label: 'Linked emails',
    domain: 'email',
    entity_type: 'email_thread',
    route: '/email',
    query_params: { filter: 'email_linked', linked: 'true' },
    keywords: ['linked', 'connected', 'assigned emails'],
    definition: 'EXISTS (SELECT 1 FROM email_links WHERE thread_id = id AND is_active = true)',
  },
  {
    filter_id: 'email_with_attachments',
    label: 'With attachments',
    domain: 'email',
    entity_type: 'email_thread',
    route: '/email',
    query_params: { filter: 'email_with_attachments' },
    keywords: ['attachments', 'has files', 'with documents'],
    definition: 'has_attachments = true',
  },
];

// =============================================================================
// SHOPPING LIST FILTERS
// =============================================================================

export const SHOPPING_LIST_FILTERS: QuickFilter[] = [
  {
    filter_id: 'shop_pending',
    label: 'Pending approval',
    domain: 'shopping-list',
    entity_type: 'shopping_list_item',
    route: '/shopping-list',
    query_params: { filter: 'shop_pending' },
    keywords: ['pending', 'awaiting approval', 'needs approval'],
    definition: "status IN ('candidate', 'under_review')",
  },
  {
    filter_id: 'shop_urgent',
    label: 'Urgent items',
    domain: 'shopping-list',
    entity_type: 'shopping_list_item',
    route: '/shopping-list',
    query_params: { filter: 'shop_urgent' },
    keywords: ['urgent', 'critical', 'rush order'],
    definition: "urgency IN ('high', 'critical') AND status NOT IN ('fulfilled', 'installed')",
  },
];

// =============================================================================
// RECEIVING FILTERS
// =============================================================================

export const RECEIVING_FILTERS: QuickFilter[] = [
  {
    filter_id: 'recv_pending',
    label: 'Pending receiving',
    domain: 'receiving',
    entity_type: 'receiving_event',
    route: '/receiving',
    query_params: { filter: 'recv_pending' },
    keywords: ['pending', 'in progress', 'not complete'],
    definition: "status IN ('in_progress', 'partial')",
  },
  {
    filter_id: 'recv_discrepancy',
    label: 'With discrepancies',
    domain: 'receiving',
    entity_type: 'receiving_event',
    route: '/receiving',
    query_params: { filter: 'recv_discrepancy' },
    keywords: ['discrepancy', 'issue', 'problem', 'mismatch'],
    definition: "status = 'discrepancy'",
  },
];

// =============================================================================
// ALL FILTERS (COMBINED CATALOG)
// =============================================================================

export const ALL_FILTERS: QuickFilter[] = [
  ...WORK_ORDER_FILTERS,
  ...FAULT_FILTERS,
  ...EQUIPMENT_FILTERS,
  ...INVENTORY_FILTERS,
  ...CERTIFICATE_FILTERS,
  ...EMAIL_FILTERS,
  ...SHOPPING_LIST_FILTERS,
  ...RECEIVING_FILTERS,
];

/**
 * Get filters by domain
 */
export function getFiltersByDomain(domain: string): QuickFilter[] {
  return ALL_FILTERS.filter((f) => f.domain === domain && !f.blocked);
}

/**
 * Get a specific filter by ID
 */
export function getFilterById(filterId: string): QuickFilter | undefined {
  return ALL_FILTERS.find((f) => f.filter_id === filterId);
}

/**
 * Get all active (non-blocked) filters
 */
export function getActiveFilters(): QuickFilter[] {
  return ALL_FILTERS.filter((f) => !f.blocked);
}

/**
 * Filter ID to route mapping (for quick lookups)
 */
export const FILTER_ROUTES: Record<string, string> = Object.fromEntries(
  ALL_FILTERS.map((f) => [f.filter_id, f.route])
);
