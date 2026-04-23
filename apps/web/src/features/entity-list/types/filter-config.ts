/**
 * Filter Configuration for Entity List Views
 *
 * Defines what filters are available per entity type.
 * Filter values are applied at the Supabase query level (server-side).
 */

export type FilterFieldType = 'select' | 'multi-select' | 'date-range' | 'text';

export interface FilterOption {
  value: string;
  label: string;
}

export interface FilterFieldConfig {
  /** Column name in the Supabase table */
  key: string;
  /** Display label */
  label: string;
  /** Input type */
  type: FilterFieldType;
  /** Static options for select/multi-select */
  options?: FilterOption[];
  /** Placeholder text for text/date inputs */
  placeholder?: string;
  /** Category grouping for FilterPanel sidebar */
  category?: 'status-priority' | 'dates' | 'equipment-systems' | 'properties';
}

export const FILTER_CATEGORY_LABELS: Record<string, string> = {
  'status-priority': 'Status & Priority',
  'dates': 'Dates & Deadlines',
  'equipment-systems': 'Equipment & Systems',
  'properties': 'Properties',
};

/** Active filter values keyed by column name */
export type ActiveFilters = Record<string, string | string[] | DateRange>;

export interface DateRange {
  from: string;
  to: string;
}

export function isDateRange(v: unknown): v is DateRange {
  return typeof v === 'object' && v !== null && 'from' in v && 'to' in v;
}

// =============================================================================
// PER-ENTITY FILTER CONFIGS
// =============================================================================

export const FAULT_FILTERS: FilterFieldConfig[] = [
  {
    key: 'status',
    label: 'Status',
    type: 'select',
    options: [
      { value: 'open', label: 'Open' },
      { value: 'investigating', label: 'Investigating' },
      { value: 'resolved', label: 'Resolved' },
      { value: 'closed', label: 'Closed' },
    ],
    category: 'status-priority',
  },
  {
    key: 'severity',
    label: 'Severity',
    type: 'select',
    options: [
      { value: 'high', label: 'High' },
      { value: 'medium', label: 'Medium' },
      { value: 'low', label: 'Low' },
    ],
    category: 'status-priority',
  },
  {
    key: 'detected_at',
    label: 'Detected',
    type: 'date-range',
    category: 'dates',
  },
];

export const WORK_ORDER_FILTERS: FilterFieldConfig[] = [
  {
    key: 'status',
    label: 'Status',
    type: 'select',
    options: [
      { value: 'planned', label: 'Planned' },
      { value: 'in_progress', label: 'In Progress' },
      { value: 'completed', label: 'Completed' },
      { value: 'cancelled', label: 'Cancelled' },
    ],
    category: 'status-priority',
  },
  {
    key: 'priority',
    label: 'Priority',
    type: 'select',
    options: [
      { value: 'emergency', label: 'Emergency' },
      { value: 'critical', label: 'Critical' },
      { value: 'important', label: 'Important' },
      { value: 'routine', label: 'Routine' },
    ],
    category: 'status-priority',
  },
  {
    key: 'due_date',
    label: 'Due Date',
    type: 'date-range',
    category: 'dates',
  },
];

export const CERTIFICATE_FILTERS: FilterFieldConfig[] = [
  {
    key: 'status',
    label: 'Status',
    type: 'select',
    options: [
      { value: 'valid', label: 'Valid' },
      { value: 'expiring_soon', label: 'Expiring Soon' },
      { value: 'expired', label: 'Expired' },
      { value: 'superseded', label: 'Superseded' },
    ],
    category: 'status-priority',
  },
  {
    key: 'expiry_date',
    label: 'Expiry Date',
    type: 'date-range',
    category: 'dates',
  },
];

export const EQUIPMENT_FILTERS: FilterFieldConfig[] = [
  {
    key: 'status',
    label: 'Status',
    type: 'select',
    options: [
      { value: 'operational', label: 'Operational' },
      { value: 'degraded', label: 'Degraded' },
      { value: 'maintenance', label: 'Maintenance' },
      { value: 'failed', label: 'Failed' },
      { value: 'decommissioned', label: 'Decommissioned' },
    ],
    category: 'status-priority',
  },
  {
    key: 'criticality',
    label: 'Criticality',
    type: 'select',
    options: [
      { value: 'critical', label: 'Critical' },
      { value: 'high', label: 'High' },
      { value: 'medium', label: 'Medium' },
      { value: 'low', label: 'Low' },
    ],
    category: 'status-priority',
  },
  {
    key: 'category',
    label: 'Category',
    type: 'text',
    placeholder: 'Filter by category...',
    category: 'equipment-systems',
  },
];

export const INVENTORY_FILTERS: FilterFieldConfig[] = [
  {
    key: '_stock_status',
    label: 'Stock',
    type: 'select',
    options: [
      { value: 'in_stock', label: 'In Stock' },
      { value: 'low', label: 'Low Stock' },
      { value: 'out', label: 'Out of Stock' },
    ],
    category: 'status-priority',
  },
  {
    key: 'category',
    label: 'Category',
    type: 'text',
    placeholder: 'Filter by category...',
    category: 'equipment-systems',
  },
  {
    key: 'manufacturer',
    label: 'Manufacturer',
    type: 'text',
    placeholder: 'Filter by manufacturer...',
    category: 'equipment-systems',
  },
];

export const RECEIVING_FILTERS: FilterFieldConfig[] = [
  {
    key: 'status',
    label: 'Status',
    type: 'select',
    options: [
      { value: 'draft', label: 'Draft' },
      { value: 'in_review', label: 'In Review' },
      { value: 'accepted', label: 'Accepted' },
      { value: 'rejected', label: 'Rejected' },
    ],
    category: 'status-priority',
  },
  {
    key: 'received_date',
    label: 'Received Date',
    type: 'date-range',
    category: 'dates',
  },
  {
    key: 'vendor_name',
    label: 'Vendor',
    type: 'text',
    placeholder: 'Filter by vendor...',
    category: 'properties',
  },
  {
    key: 'po_number',
    label: 'PO Number',
    type: 'text',
    placeholder: 'Filter by PO number...',
    category: 'properties',
  },
];

export const SHOPPING_LIST_FILTERS: FilterFieldConfig[] = [
  {
    key: 'status',
    label: 'Status',
    type: 'select',
    options: [
      { value: 'candidate', label: 'Candidate' },
      { value: 'under_review', label: 'Under Review' },
      { value: 'approved', label: 'Approved' },
      { value: 'rejected', label: 'Rejected' },
      { value: 'ordered', label: 'Ordered' },
      { value: 'partially_fulfilled', label: 'Partially Fulfilled' },
      { value: 'fulfilled', label: 'Fulfilled' },
      { value: 'installed', label: 'Installed' },
    ],
    category: 'status-priority',
  },
  {
    key: 'urgency',
    label: 'Urgency',
    type: 'select',
    options: [
      { value: 'critical', label: 'Critical' },
      { value: 'high', label: 'High' },
      { value: 'normal', label: 'Normal' },
      { value: 'low', label: 'Low' },
    ],
    category: 'status-priority',
  },
  {
    key: 'source_type',
    label: 'Source',
    type: 'select',
    options: [
      { value: 'manual_add', label: 'Manual Add' },
      { value: 'inventory_low', label: 'Inventory Low' },
      { value: 'inventory_oos', label: 'Out of Stock' },
      { value: 'work_order_usage', label: 'Work Order' },
      { value: 'receiving_damaged', label: 'Damaged on Receipt' },
      { value: 'receiving_missing', label: 'Missing on Receipt' },
    ],
    category: 'properties',
  },
  {
    key: 'is_candidate_part',
    label: 'Candidate Part',
    type: 'select',
    options: [
      { value: 'true', label: 'Candidates only' },
      { value: 'false', label: 'Catalogued only' },
    ],
    category: 'properties',
  },
  {
    key: 'required_by_date',
    label: 'Required By',
    type: 'date-range',
    category: 'dates',
  },
];

export const HANDOVER_FILTERS: FilterFieldConfig[] = [
  {
    key: 'status',
    label: 'Status',
    type: 'select',
    options: [
      { value: 'pending', label: 'Pending' },
      { value: 'acknowledged', label: 'Acknowledged' },
      { value: 'completed', label: 'Completed' },
    ],
    category: 'status-priority',
  },
  {
    key: 'category',
    label: 'Category',
    type: 'text',
    placeholder: 'Filter by category...',
    category: 'properties',
  },
];

// =============================================================================
// DOMAIN → FILTER CONFIG MAPPING
// =============================================================================

export const FILTER_CONFIGS: Record<string, FilterFieldConfig[]> = {
  faults: FAULT_FILTERS,
  'work-orders': WORK_ORDER_FILTERS,
  certificates: CERTIFICATE_FILTERS,
  equipment: EQUIPMENT_FILTERS,
  inventory: INVENTORY_FILTERS,
  receiving: RECEIVING_FILTERS,
  'shopping-list': SHOPPING_LIST_FILTERS,
  handover: HANDOVER_FILTERS,
};
