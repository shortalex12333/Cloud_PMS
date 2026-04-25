/**
 * Microaction Handlers Index
 *
 * Exports all domain handlers and provides a registration function
 * to wire them into the executor.
 */

import { registerHandler } from '../executor';
import type { ActionContext, ActionResult } from '../types';

// Handler function type (matches executor's HandlerFunction)
type HandlerFunction = (
  context: ActionContext,
  params?: Record<string, unknown>
) => Promise<ActionResult>;

// Import all handler modules
// NOTE: faults.ts was deleted — it queried TENANT tables from a MASTER-scoped
// Supabase client (broken in production). All fault actions now route through
// executeAction() → Render backend which holds TENANT credentials.
import { workOrderHandlers } from './workOrders';
import { equipmentHandlers } from './equipment';
import { inventoryHandlers } from './inventory';
import { handoverHandlers } from './handover';
import { complianceHandlers } from './compliance';
import { procurementHandlers } from './procurement';

/**
 * All handlers grouped by domain
 */
const allHandlers = {
  ...workOrderHandlers,
  ...equipmentHandlers,
  ...inventoryHandlers,
  ...handoverHandlers,
  ...complianceHandlers,
  ...procurementHandlers,
};

/**
 * Register all handlers with the executor
 *
 * Call this function once during app initialization to wire up
 * all microaction handlers.
 */
export function registerAllHandlers(): void {
  // Fault handlers: REMOVED — queried TENANT from MASTER client (broken in prod).
  // All fault actions route via executeAction() → Render backend (TENANT creds).

  // Work order handlers
  for (const [name, handler] of Object.entries(workOrderHandlers)) {
    registerHandler(name, handler as HandlerFunction);
  }

  // Equipment handlers
  for (const [name, handler] of Object.entries(equipmentHandlers)) {
    registerHandler(name, handler as HandlerFunction);
  }

  // Inventory handlers
  for (const [name, handler] of Object.entries(inventoryHandlers)) {
    registerHandler(name, handler as HandlerFunction);
  }

  // Handover handlers
  for (const [name, handler] of Object.entries(handoverHandlers)) {
    registerHandler(name, handler as HandlerFunction);
  }

  // Compliance handlers
  for (const [name, handler] of Object.entries(complianceHandlers)) {
    registerHandler(name, handler as HandlerFunction);
  }

  // Procurement handlers
  for (const [name, handler] of Object.entries(procurementHandlers)) {
    registerHandler(name, handler as HandlerFunction);
  }
}

/**
 * Get count of registered handlers by domain
 */
function getHandlerStats(): Record<string, number> {
  return {
    workOrders: Object.keys(workOrderHandlers).length,
    equipment: Object.keys(equipmentHandlers).length,
    inventory: Object.keys(inventoryHandlers).length,
    handover: Object.keys(handoverHandlers).length,
    compliance: Object.keys(complianceHandlers).length,
    procurement: Object.keys(procurementHandlers).length,
    total: Object.keys(allHandlers).length,
  };
}
