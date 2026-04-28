/**
 * field-schema.ts — Canonical field rendering classification config.
 *
 * Mirrors FieldClassification in apps/api/action_router/registry.py.
 * Single source of truth for which prefill keys to suppress or style in the UI.
 */

/** Prefill keys that are backend-only plumbing and must never surface to the user. */
export const PREFILL_NEVER_RENDER: ReadonlySet<string> = new Set([
  // Generic routing / session context (FieldClassification.CONTEXT equivalent)
  'entity_id',
  'entity_type',
  'yacht_id',
  'fleet_id',
  'user_id',
  'tenant_id',
  'id',
  'url',
  'entity_url',
  'metadata',
  // Foreign-key UUIDs — each expected alongside a human-readable *_name field.
  // Per FAULT05 cohort review of PR #704 (2026-04-24): UUID surfacing skipped.
  'equipment_id',
  'part_id',
  'work_order_id',
  'fault_id',
  'certificate_id',
  'document_id',
  'purchase_order_id',
  'receiving_id',
  'warranty_id',
  'shopping_list_id',
  'shopping_item_id',
  'hours_of_rest_id',
  'handover_id',
  'handover_item_id',
  'handover_export_id',
  'previous_export_id',
  'draft_id',
  // Audit-trail UUID columns — who performed an action, by DB row reference.
  'added_by',
  'updated_by',
  'deleted_by',
  'resolved_by',
  'completed_by',
  'reported_by',
  'exported_by_user_id',
  'outgoing_user_id',
  'incoming_user_id',
]);

/** Prefill keys whose values are machine identifiers — render in monospace. */
export const PREFILL_MONO_KEYS: ReadonlySet<string> = new Set([
  'code',
  'part_number',
  'wonumber',
  'fault_code',
  'po_number',
  'serial_number',
]);

/**
 * Label overrides for prefill keys whose auto-humanised form reads poorly.
 * Keep narrow — only add when the default is genuinely worse.
 * Per PURCHASE05 cohort review of PR #704 (2026-04-24).
 */
export const PREFILL_LABEL_OVERRIDES: Readonly<Record<string, string>> = {
  po_number: 'PO number',
  wonumber: 'WO number',
  wo_number: 'WO number',
  sku: 'SKU',
};

/** Form fields the backend handles automatically — excluded from the user-facing form. */
export const FORM_BACKEND_AUTO: ReadonlySet<string> = new Set([
  'yacht_id',
  'signature',
  'idempotency_key',
]);
