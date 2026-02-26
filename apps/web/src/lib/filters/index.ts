/**
 * Quick Filters Module
 *
 * Single source of truth for filter definitions, inference, and execution.
 *
 * @module filters
 */

// Re-export catalog types and functions
export {
  type QuickFilter,
  ALL_FILTERS,
  WORK_ORDER_FILTERS,
  FAULT_FILTERS,
  EQUIPMENT_FILTERS,
  INVENTORY_FILTERS,
  CERTIFICATE_FILTERS,
  EMAIL_FILTERS,
  SHOPPING_LIST_FILTERS,
  RECEIVING_FILTERS,
  getFiltersByDomain,
  getFilterById,
  getActiveFilters,
  FILTER_ROUTES,
} from './catalog';

// Re-export inference types and functions
export {
  type InferredFilter,
  inferFilters,
  hasExplicitFilterMatch,
  getSuggestionsForDomain,
} from './infer';

// Re-export execution functions
export {
  applyFilter,
  applyWorkOrderFilter,
  applyFaultFilter,
  applyEquipmentFilter,
  applyInventoryFilter,
  applyCertificateFilter,
  getFilterLabel,
} from './execute';
