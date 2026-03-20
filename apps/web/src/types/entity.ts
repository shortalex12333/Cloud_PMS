// apps/web/src/types/entity.ts

export type EntityType =
  | 'work_order'
  | 'fault'
  | 'equipment'
  | 'part'
  | 'receiving'
  | 'certificate'
  | 'document'
  | 'shopping_list'
  | 'warranty'
  | 'hours_of_rest'
  | 'hours_of_rest_signoff'
  | 'purchase_order'
  | 'handover_export';

/**
 * One action entry from the backend GET /v1/entity/{type}/{id} response.
 * Backend populates: action_id, label, variant, disabled, disabled_reason,
 * requires_signature, prefill, required_fields, optional_fields.
 * Frontend role filtering has been moved to the backend (Phase 2).
 * If an action is absent from this array, the current user has no permission.
 */
export interface AvailableAction {
  action_id: string;
  label: string;
  variant: 'READ' | 'MUTATE' | 'SIGNED';
  disabled: boolean;
  disabled_reason: string | null;
  requires_signature: boolean;
  prefill: Record<string, unknown>;
  required_fields: string[];
  optional_fields: string[];
}

/**
 * Response shape from POST /api/v1/actions/execute (Next.js proxy → backend).
 */
export interface ActionResult {
  success: boolean;
  data?: Record<string, unknown>;
  message?: string;
  error?: string;
  code?: string;
  execution_id?: string;
}
