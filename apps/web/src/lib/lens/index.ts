/**
 * CelesteOS Lens System - Barrel Export
 *
 * Usage:
 *   import { getEquipmentStatusStyle, formatLensDate } from '@/lib/lens';
 */

export {
  // Types
  type StatusStyle,

  // Equipment
  getEquipmentStatusStyle,
  getRiskStyle,

  // Faults
  getSeverityStyle,

  // Work Orders
  getWorkOrderStatusStyle,
  getPriorityStyle,

  // Parts/Inventory
  getStockStyle,

  // Formatters
  formatLensDate,
  formatCurrency,
} from './statusStyles';
