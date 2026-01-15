/**
 * Microaction Validator
 *
 * Validates action parameters and context before execution.
 * Uses Zod schemas for type-safe validation.
 */

import { z } from 'zod';
import { getAction } from './registry';
import type { ActionContext, ValidationResult, ValidationError } from './types';

// ============================================================================
// Common Schemas
// ============================================================================

const uuidSchema = z.string().uuid('Invalid UUID format');

const contextSchema = z.object({
  yacht_id: uuidSchema,
  user_id: uuidSchema,
  user_role: z.string().min(1, 'User role is required'),
  entity_id: uuidSchema.optional(),
  entity_type: z
    .enum([
      'fault',
      'work_order',
      'equipment',
      'part',
      'handover',
      'document',
      'hor_table',
      'purchase',
      'checklist',
      'worklist',
      'fleet_summary',
      'smart_summary',
    ])
    .optional(),
  source_card: z
    .enum([
      'fault',
      'work_order',
      'equipment',
      'part',
      'handover',
      'document',
      'hor_table',
      'purchase',
      'checklist',
      'worklist',
      'fleet_summary',
      'smart_summary',
    ])
    .optional(),
});

// ============================================================================
// Action-Specific Parameter Schemas
// ============================================================================

const actionParamSchemas: Record<string, z.ZodSchema> = {
  // Fault actions
  diagnose_fault: z.object({
    fault_id: uuidSchema,
  }),
  add_fault_note: z.object({
    fault_id: uuidSchema,
    note_text: z.string().min(1).max(10000),
  }),
  add_fault_photo: z.object({
    fault_id: uuidSchema,
    photo_url: z.string().url(),
    caption: z.string().max(500).optional(),
  }),
  create_work_order_from_fault: z.object({
    fault_id: uuidSchema,
    title: z.string().min(1).max(200).optional(),
    priority: z.enum(['low', 'medium', 'high', 'critical']).optional(),
    assignee_id: uuidSchema.optional(),
  }),

  // Work order actions
  create_work_order: z.object({
    title: z.string().min(1).max(200),
    description: z.string().max(10000).optional(),
    equipment_id: uuidSchema.optional(),
    priority: z.enum(['low', 'medium', 'high', 'critical']).default('medium'),
    due_date: z.string().datetime().optional(),
    assignee_id: uuidSchema.optional(),
  }),
  mark_work_order_complete: z.object({
    work_order_id: uuidSchema,
    completion_notes: z.string().max(10000).optional(),
    parts_used: z
      .array(
        z.object({
          part_id: uuidSchema,
          quantity: z.number().int().positive(),
        })
      )
      .optional(),
  }),
  add_work_order_note: z.object({
    work_order_id: uuidSchema,
    note_text: z.string().min(1).max(10000),
  }),
  assign_work_order: z.object({
    work_order_id: uuidSchema,
    assignee_id: uuidSchema,
  }),

  // Equipment actions
  view_equipment_details: z.object({
    equipment_id: uuidSchema,
  }),
  add_equipment_note: z.object({
    equipment_id: uuidSchema,
    note_text: z.string().min(1).max(10000),
  }),

  // Inventory actions
  order_part: z.object({
    part_id: uuidSchema,
    quantity: z.number().int().positive(),
    urgency: z.enum(['normal', 'urgent', 'critical']).default('normal'),
    notes: z.string().max(1000).optional(),
  }),
  log_part_usage: z.object({
    part_id: uuidSchema,
    work_order_id: uuidSchema,
    quantity: z.number().int().positive(),
  }),

  // Handover actions
  add_to_handover: z.object({
    entity_id: uuidSchema,
    entity_type: z.enum(['fault', 'work_order', 'equipment', 'part', 'document']),
    section: z.string().min(1).max(100).optional(),
    summary: z.string().max(1000).optional(),
  }),
  edit_handover_section: z.object({
    handover_id: uuidSchema,
    section_id: uuidSchema,
    content: z.string().min(1).max(50000),
  }),

  // Purchasing actions
  create_purchase_request: z.object({
    items: z.array(
      z.object({
        part_id: uuidSchema.optional(),
        description: z.string().min(1).max(500),
        quantity: z.number().int().positive(),
        estimated_cost: z.number().positive().optional(),
      })
    ).min(1),
    supplier_id: uuidSchema.optional(),
    notes: z.string().max(2000).optional(),
    urgency: z.enum(['normal', 'urgent', 'critical']).default('normal'),
  }),
  approve_purchase: z.object({
    purchase_id: uuidSchema,
    approval_notes: z.string().max(1000).optional(),
  }),
  log_delivery_received: z.object({
    purchase_id: uuidSchema,
    items_received: z.array(
      z.object({
        item_id: uuidSchema,
        quantity_received: z.number().int().nonnegative(),
        condition_notes: z.string().max(500).optional(),
      })
    ).min(1),
  }),

  // Compliance actions
  update_hours_of_rest: z.object({
    user_id: uuidSchema,
    date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    hours: z.array(
      z.object({
        start_hour: z.number().int().min(0).max(23),
        end_hour: z.number().int().min(0).max(23),
        type: z.enum(['work', 'rest']),
      })
    ),
  }),
};

// ============================================================================
// Validation Functions
// ============================================================================

/**
 * Validate action context
 */
export function validateContext(context: unknown): ValidationResult {
  const result = contextSchema.safeParse(context);

  if (result.success) {
    return { valid: true, errors: [] };
  }

  const errors: ValidationError[] = result.error.issues.map((issue) => ({
    field: issue.path.join('.'),
    message: issue.message,
    code: issue.code,
  }));

  return { valid: false, errors };
}

/**
 * Validate action parameters
 */
export function validateParams(
  actionName: string,
  params: unknown
): ValidationResult {
  const schema = actionParamSchemas[actionName];

  // If no schema defined, allow any params (for read-only actions)
  if (!schema) {
    const action = getAction(actionName);
    if (action?.side_effect === 'read_only') {
      return { valid: true, errors: [] };
    }
    // For mutation actions without schema, require empty or undefined params
    if (params === undefined || params === null || Object.keys(params as object).length === 0) {
      return { valid: true, errors: [] };
    }
    return {
      valid: false,
      errors: [
        {
          field: 'params',
          message: `No validation schema defined for action: ${actionName}`,
          code: 'custom',
        },
      ],
    };
  }

  const result = schema.safeParse(params);

  if (result.success) {
    return { valid: true, errors: [] };
  }

  const errors: ValidationError[] = result.error.issues.map((issue) => ({
    field: issue.path.join('.'),
    message: issue.message,
    code: issue.code,
  }));

  return { valid: false, errors };
}

/**
 * Validate action name exists
 */
export function validateActionName(actionName: string): ValidationResult {
  if (!actionName || typeof actionName !== 'string') {
    return {
      valid: false,
      errors: [
        {
          field: 'action_name',
          message: 'Action name is required',
          code: 'required',
        },
      ],
    };
  }

  const action = getAction(actionName);
  if (!action) {
    return {
      valid: false,
      errors: [
        {
          field: 'action_name',
          message: `Unknown action: ${actionName}`,
          code: 'invalid_enum_value',
        },
      ],
    };
  }

  return { valid: true, errors: [] };
}

/**
 * Full validation of action execution request
 */
export function validateActionRequest(
  actionName: string,
  context: unknown,
  params?: unknown
): ValidationResult {
  const errors: ValidationError[] = [];

  // Validate action name
  const nameResult = validateActionName(actionName);
  if (!nameResult.valid) {
    errors.push(...nameResult.errors);
    return { valid: false, errors };
  }

  // Validate context
  const contextResult = validateContext(context);
  if (!contextResult.valid) {
    errors.push(...contextResult.errors);
  }

  // Validate params
  const paramsResult = validateParams(actionName, params);
  if (!paramsResult.valid) {
    errors.push(...paramsResult.errors);
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * Get the validation schema for an action's parameters
 */
export function getParamSchema(actionName: string): z.ZodSchema | null {
  return actionParamSchemas[actionName] || null;
}

/**
 * Check if action requires entity_id in context
 */
export function requiresEntityId(actionName: string): boolean {
  const actionsRequiringEntity = [
    'diagnose_fault',
    'add_fault_note',
    'add_fault_photo',
    'view_fault_history',
    'suggest_parts',
    'create_work_order_from_fault',
    'view_equipment_details',
    'view_equipment_history',
    'view_equipment_parts',
    'view_linked_faults',
    'view_equipment_manual',
    'add_equipment_note',
    'view_part_stock',
    'view_part_location',
    'view_part_usage',
    'view_linked_equipment',
    'order_part',
  ];

  return actionsRequiringEntity.includes(actionName);
}

// Export schemas for external use
export { contextSchema, actionParamSchemas };
