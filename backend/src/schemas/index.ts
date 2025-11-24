// CelesteOS Backend Validation Schemas
// Uses Zod for runtime validation

import { z } from 'zod';

// ============================================================================
// COMMON SCHEMAS
// ============================================================================

export const uuidSchema = z.string().uuid();

export const prioritySchema = z.enum(['low', 'medium', 'high', 'critical']);

export const paginationSchema = z.object({
  limit: z.coerce.number().min(1).max(100).default(50),
  offset: z.coerce.number().min(0).default(0),
});

// ============================================================================
// ACTION SCHEMAS
// ============================================================================

// Base action context
export const actionContextSchema = z.object({
  yacht_id: uuidSchema,
  equipment_id: uuidSchema.optional(),
  work_order_id: uuidSchema.optional(),
  document_id: uuidSchema.optional(),
  handover_id: uuidSchema.optional(),
});

// Add Note Action
export const addNotePayloadSchema = z.object({
  note_text: z.string().min(1).max(10000),
});

export const addNoteRequestSchema = z.object({
  action: z.literal('add_note'),
  context: actionContextSchema.extend({
    equipment_id: uuidSchema,
  }),
  payload: addNotePayloadSchema,
});

// Create Work Order Action
export const createWorkOrderPayloadSchema = z.object({
  title: z.string().min(1).max(500),
  description: z.string().max(10000).optional(),
  priority: prioritySchema.default('medium'),
});

export const createWorkOrderRequestSchema = z.object({
  action: z.literal('create_work_order'),
  context: actionContextSchema.extend({
    equipment_id: uuidSchema,
  }),
  payload: createWorkOrderPayloadSchema,
});

// Add Note to Work Order
export const addNoteToWorkOrderPayloadSchema = z.object({
  note_text: z.string().min(1).max(10000),
});

export const addNoteToWorkOrderRequestSchema = z.object({
  action: z.literal('add_note_to_work_order'),
  context: actionContextSchema.extend({
    work_order_id: uuidSchema,
  }),
  payload: addNoteToWorkOrderPayloadSchema,
});

// Close Work Order
export const closeWorkOrderRequestSchema = z.object({
  action: z.literal('close_work_order'),
  context: actionContextSchema.extend({
    work_order_id: uuidSchema,
  }),
  payload: z.object({}).optional(),
});

// Add to Handover
export const addToHandoverPayloadSchema = z.object({
  summary_text: z.string().min(1).max(5000),
});

export const addToHandoverRequestSchema = z.object({
  action: z.literal('add_to_handover'),
  context: actionContextSchema.extend({
    equipment_id: uuidSchema,
  }),
  payload: addToHandoverPayloadSchema,
});

// Add Document to Handover
export const addDocumentToHandoverPayloadSchema = z.object({
  context: z.string().max(5000).optional(),
});

export const addDocumentToHandoverRequestSchema = z.object({
  action: z.literal('add_document_to_handover'),
  context: actionContextSchema.extend({
    document_id: uuidSchema,
  }),
  payload: addDocumentToHandoverPayloadSchema,
});

// Add Predictive to Handover
export const addPredictiveToHandoverPayloadSchema = z.object({
  insight_id: uuidSchema,
  summary: z.string().min(1).max(5000),
});

export const addPredictiveToHandoverRequestSchema = z.object({
  action: z.literal('add_predictive_to_handover'),
  context: actionContextSchema.extend({
    equipment_id: uuidSchema,
  }),
  payload: addPredictiveToHandoverPayloadSchema,
});

// Edit Handover Section
export const editHandoverSectionPayloadSchema = z.object({
  section_name: z.string().min(1).max(200),
  new_text: z.string().min(1).max(50000),
});

export const editHandoverSectionRequestSchema = z.object({
  action: z.literal('edit_handover_section'),
  context: actionContextSchema.extend({
    handover_id: uuidSchema,
  }),
  payload: editHandoverSectionPayloadSchema,
});

// Export Handover
export const exportHandoverPayloadSchema = z.object({
  format: z.enum(['pdf', 'html']).default('pdf'),
});

export const exportHandoverRequestSchema = z.object({
  action: z.literal('export_handover'),
  context: actionContextSchema,
  payload: exportHandoverPayloadSchema.optional(),
});

// Open Document
export const openDocumentPayloadSchema = z.object({
  storage_path: z.string().min(1),
});

export const openDocumentRequestSchema = z.object({
  action: z.literal('open_document'),
  context: actionContextSchema,
  payload: openDocumentPayloadSchema,
});

// Order Part
export const orderPartPayloadSchema = z.object({
  part_id: uuidSchema,
  qty: z.number().int().min(1).max(10000),
});

export const orderPartRequestSchema = z.object({
  action: z.literal('order_part'),
  context: actionContextSchema,
  payload: orderPartPayloadSchema,
});

// ============================================================================
// UNIFIED ACTION REQUEST SCHEMA
// ============================================================================

export const actionExecuteRequestSchema = z.discriminatedUnion('action', [
  addNoteRequestSchema,
  createWorkOrderRequestSchema,
  addNoteToWorkOrderRequestSchema,
  closeWorkOrderRequestSchema,
  addToHandoverRequestSchema,
  addDocumentToHandoverRequestSchema,
  addPredictiveToHandoverRequestSchema,
  editHandoverSectionRequestSchema,
  exportHandoverRequestSchema,
  openDocumentRequestSchema,
  orderPartRequestSchema,
]);

// Generic action request for validation
export const genericActionRequestSchema = z.object({
  action: z.string().min(1),
  context: actionContextSchema,
  payload: z.record(z.unknown()).optional(),
});

// ============================================================================
// SEARCH SCHEMA
// ============================================================================

export const searchRequestSchema = z.object({
  query: z.string().min(1).max(1000),
  mode: z.enum(['auto', 'semantic', 'keyword', 'graph']).default('auto'),
  filters: z.object({
    equipment_id: uuidSchema.optional(),
    document_type: z.string().optional(),
    date_from: z.string().datetime().optional(),
    date_to: z.string().datetime().optional(),
  }).optional(),
  limit: z.number().int().min(1).max(50).default(20),
});

// ============================================================================
// PREDICTIVE SCHEMAS
// ============================================================================

export const predictiveEventSchema = z.object({
  event: z.enum([
    'fault_created',
    'fault_resolved',
    'wo_created',
    'wo_updated',
    'wo_overdue',
    'wo_completed',
    'note_added',
    'part_used',
  ]),
  equipment_id: uuidSchema,
  yacht_id: uuidSchema,
  metadata: z.record(z.unknown()).optional(),
});

export const predictiveRecomputeSchema = z.object({
  equipment_id: uuidSchema,
  yacht_id: uuidSchema,
  event: z.string().optional(),
  event_category: z.string().optional(),
  signal_weight: z.string().optional(),
  weight_delta: z.number().optional(),
});

// ============================================================================
// QUERY PARAM SCHEMAS
// ============================================================================

export const equipmentIdParamSchema = z.object({
  equipment_id: uuidSchema,
});

export const insightIdParamSchema = z.object({
  id: uuidSchema,
});

export const workOrderIdParamSchema = z.object({
  work_order_id: uuidSchema,
});

export const documentIdParamSchema = z.object({
  document_id: uuidSchema,
});

export const partIdParamSchema = z.object({
  part_id: uuidSchema,
});

// ============================================================================
// INTERNAL WORKFLOW SCHEMAS
// ============================================================================

export const microActionDispatchSchema = z.object({
  insight_id: uuidSchema,
  equipment_id: uuidSchema,
  yacht_id: uuidSchema,
  severity: z.enum(['low', 'elevated', 'high', 'critical']),
  equipment_name: z.string().optional(),
  title: z.string().optional(),
});

// ============================================================================
// EXPORT TYPES
// ============================================================================

export type AddNoteRequest = z.infer<typeof addNoteRequestSchema>;
export type CreateWorkOrderRequest = z.infer<typeof createWorkOrderRequestSchema>;
export type AddToHandoverRequest = z.infer<typeof addToHandoverRequestSchema>;
export type ActionExecuteRequest = z.infer<typeof actionExecuteRequestSchema>;
export type GenericActionRequest = z.infer<typeof genericActionRequestSchema>;
export type SearchRequest = z.infer<typeof searchRequestSchema>;
export type PredictiveEventRequest = z.infer<typeof predictiveEventSchema>;
export type PredictiveRecomputeRequest = z.infer<typeof predictiveRecomputeSchema>;
