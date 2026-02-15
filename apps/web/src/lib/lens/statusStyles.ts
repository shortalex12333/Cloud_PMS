/**
 * =============================================================================
 * SHARED STATUS STYLES - CelesteOS Lens System
 * =============================================================================
 *
 * Consolidated status-to-style mappings for all CelesteOS lens pages.
 * ALL returned classes use celeste-* or restricted-* tokens exclusively.
 *
 * USAGE:
 *   import { getEquipmentStatusStyle, formatLensDate } from '@/lib/lens/statusStyles';
 *
 * INVARIANTS:
 *   - No hardcoded Tailwind colors (no gray-*, blue-*, etc.)
 *   - All status/severity/priority functions return StatusStyle
 *   - formatLensDate handles optional time display
 *
 * =============================================================================
 */

// --- Shared Types ---

export interface StatusStyle {
  bg: string;
  text: string;
  label: string;
  border?: string;
}

// =============================================================================
// EQUIPMENT
// =============================================================================

/**
 * Map equipment status to visual style
 * Statuses: operational, faulty, maintenance, offline
 */
export function getEquipmentStatusStyle(status: string): StatusStyle {
  switch (status?.toLowerCase()) {
    case 'operational':
      return { bg: 'bg-restricted-green/10', text: 'text-restricted-green', label: 'Operational' };
    case 'faulty':
      return { bg: 'bg-restricted-red/10', text: 'text-restricted-red', label: 'Faulty' };
    case 'maintenance':
      return { bg: 'bg-restricted-yellow/10', text: 'text-restricted-yellow', label: 'Under Maintenance' };
    case 'offline':
      return { bg: 'bg-celeste-text-disabled/10', text: 'text-celeste-text-muted', label: 'Offline' };
    default:
      return { bg: 'bg-celeste-accent-subtle', text: 'text-celeste-accent', label: status || 'Unknown' };
  }
}

/**
 * Map risk score (0-100) to visual style
 * Used for predictive maintenance risk indicators
 */
export function getRiskStyle(score: number): StatusStyle {
  if (score >= 75) return { bg: 'bg-restricted-red/10', text: 'text-restricted-red', label: 'High Risk' };
  if (score >= 50) return { bg: 'bg-restricted-yellow/10', text: 'text-restricted-yellow', label: 'Medium Risk' };
  if (score >= 25) return { bg: 'bg-restricted-yellow/10', text: 'text-restricted-yellow', label: 'Low Risk' };
  return { bg: 'bg-restricted-green/10', text: 'text-restricted-green', label: 'Minimal Risk' };
}

// =============================================================================
// FAULTS
// =============================================================================

/**
 * Map fault severity to visual style
 * Severities: critical, high, medium, low
 */
export function getSeverityStyle(severity: string): StatusStyle {
  switch (severity?.toLowerCase()) {
    case 'critical':
      return { bg: 'bg-restricted-red/10', text: 'text-restricted-red', label: 'Critical' };
    case 'high':
      return { bg: 'bg-restricted-orange/10', text: 'text-restricted-orange', label: 'High' };
    case 'medium':
      return { bg: 'bg-restricted-yellow/10', text: 'text-restricted-yellow', label: 'Medium' };
    default:
      return { bg: 'bg-celeste-text-disabled/10', text: 'text-celeste-text-muted', label: 'Low' };
  }
}

// =============================================================================
// WORK ORDERS
// =============================================================================

/**
 * Map work order status to visual style
 * Statuses: completed, in_progress, cancelled, pending_parts, open/pending
 */
export function getWorkOrderStatusStyle(status: string): StatusStyle {
  switch (status?.toLowerCase()) {
    case 'completed':
      return { bg: 'bg-restricted-green/10', text: 'text-restricted-green', label: 'Completed' };
    case 'in_progress':
      return { bg: 'bg-celeste-accent-subtle', text: 'text-celeste-accent', label: 'In Progress' };
    case 'cancelled':
      return { bg: 'bg-celeste-text-disabled/10', text: 'text-celeste-text-muted', label: 'Cancelled' };
    case 'pending_parts':
      return { bg: 'bg-celeste-accent/10', text: 'text-celeste-accent', label: 'Pending Parts' };
    default:
      return { bg: 'bg-restricted-yellow/10', text: 'text-restricted-yellow', label: 'Pending' };
  }
}

/**
 * Map priority to visual style
 * Priorities: critical, urgent, high, medium, low
 * Used by work orders and faults
 */
export function getPriorityStyle(priority: string): StatusStyle {
  switch (priority?.toLowerCase()) {
    case 'critical':
    case 'urgent':
      return { bg: 'bg-restricted-red/10', text: 'text-restricted-red', label: priority.charAt(0).toUpperCase() + priority.slice(1) };
    case 'high':
      return { bg: 'bg-restricted-orange/10', text: 'text-restricted-orange', label: 'High' };
    case 'medium':
      return { bg: 'bg-restricted-yellow/10', text: 'text-restricted-yellow', label: 'Medium' };
    default:
      return { bg: 'bg-celeste-text-disabled/10', text: 'text-celeste-text-muted', label: 'Low' };
  }
}

// =============================================================================
// PARTS / INVENTORY
// =============================================================================

/**
 * Map stock status to visual style
 * Statuses: OUT_OF_STOCK, LOW_STOCK, IN_STOCK
 */
export function getStockStyle(status: string, isLowStock?: boolean): StatusStyle {
  if (status === 'OUT_OF_STOCK' || isLowStock) {
    return {
      bg: 'bg-restricted-red/10',
      text: 'text-restricted-red',
      label: status === 'OUT_OF_STOCK' ? 'Out of Stock' : 'Low Stock'
    };
  }
  if (status === 'LOW_STOCK') {
    return { bg: 'bg-restricted-yellow/10', text: 'text-restricted-yellow', label: 'Low Stock' };
  }
  return { bg: 'bg-restricted-green/10', text: 'text-restricted-green', label: 'In Stock' };
}

// =============================================================================
// SHARED FORMATTERS
// =============================================================================

/**
 * Format date for lens display
 * @param dateStr - ISO date string
 * @param includeTime - Whether to include hour:minute (default: false)
 * @returns Formatted date string (e.g., "13 Feb 2026" or "13 Feb 2026, 14:30")
 */
export function formatLensDate(dateStr: string, includeTime?: boolean): string {
  try {
    const options: Intl.DateTimeFormatOptions = {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    };

    if (includeTime) {
      options.hour = '2-digit';
      options.minute = '2-digit';
    }

    return new Date(dateStr).toLocaleDateString('en-GB', options);
  } catch {
    return dateStr;
  }
}

/**
 * Format currency for display
 * @param amount - Numeric amount
 * @param currency - Currency code (default: 'USD')
 * @returns Formatted currency string (e.g., "$1,234.56")
 */
export function formatCurrency(amount: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
  }).format(amount);
}
