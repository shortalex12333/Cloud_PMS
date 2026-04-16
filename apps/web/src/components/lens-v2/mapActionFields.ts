/**
 * mapActionFields — Shared utility for building ActionPopup fields
 *
 * Reads field_metadata from the action definition to produce correctly
 * typed form fields (select, date-pick, text-area, etc.) instead of
 * defaulting everything to plain text input (kv-edit).
 *
 * Falls back to kv-edit if field_metadata is absent — zero risk.
 * All 12 lens content components call this instead of inline mapping.
 */

import type { ActionPopupField } from './ActionPopup';

/** Fields the backend handles automatically — never shown in the form */
const BACKEND_AUTO = new Set(['yacht_id', 'signature', 'idempotency_key']);

interface FieldSchemaDef {
  name: string;
  type?: string;
  label?: string;
  placeholder?: string;
  required?: boolean;
  options?: { value: string; label: string }[] | string[];
  search_domain?: string;
}

interface ActionDef {
  action_id: string;
  label: string;
  required_fields: string[];
  /** Optional (non-blocking) fields the backend accepts but doesn't require */
  optional_fields?: string[];
  prefill: Record<string, unknown>;
  requires_signature: boolean;
  /** Legacy keyed-by-name format */
  field_metadata?: Record<string, FieldSchemaDef>;
  /** New array format from ENGINEER01's field_schema */
  field_schema?: FieldSchemaDef[];
  signature_level?: number;
}

/**
 * Map an action definition's required_fields + field_metadata into
 * ActionPopupField[] for ActionPopup to render.
 */
export function mapActionFields(action: ActionDef): ActionPopupField[] {
  // Build lookup from field_schema array OR field_metadata record
  const schemaLookup: Record<string, FieldSchemaDef> = {};
  if (action.field_schema) {
    for (const s of action.field_schema) schemaLookup[s.name] = s;
  }
  if (action.field_metadata) {
    for (const [k, v] of Object.entries(action.field_metadata)) {
      if (!schemaLookup[k]) schemaLookup[k] = v;
    }
  }

  // Build deduplicated ordered list: required fields first, then optional fields.
  // Both lists exclude backend-auto fields and pre-filled fields.
  const requiredNames = action.required_fields.filter(
    (f) => !BACKEND_AUTO.has(f) && !(f in action.prefill)
  );
  const optionalNames = (action.optional_fields ?? []).filter(
    (f) => !BACKEND_AUTO.has(f) && !(f in action.prefill) && !requiredNames.includes(f)
  );
  const allFields = [
    ...requiredNames.map((f) => ({ name: f, isRequired: true })),
    ...optionalNames.map((f) => ({ name: f, isRequired: false })),
  ];

  return allFields.map(({ name: f, isRequired }) => {
      const meta = schemaLookup[f];

      // Map backend field type to ActionPopup field type
      let fieldType: ActionPopupField['type'] = 'kv-edit';
      if (meta?.type === 'select' || meta?.type === 'enum') fieldType = 'select';
      else if (meta?.type === 'text-area' || meta?.type === 'textarea') fieldType = 'text-area';
      else if (meta?.type === 'date' || meta?.type === 'date-pick') fieldType = 'date-pick';
      else if (meta?.type === 'entity-search') fieldType = 'entity-search';
      else if (meta?.type === 'person' || meta?.type === 'person-assign') fieldType = 'person-assign';
      else if (meta?.type === 'status') fieldType = 'status-set';
      else if (meta?.type === 'number') fieldType = 'kv-edit'; // number renders as text input with type hint
      else if (meta?.type === 'text') fieldType = 'kv-edit';
      else if (meta?.type) fieldType = meta.type as ActionPopupField['type'];

      // Normalise options: backend may send string[] or {value,label}[]
      let options: { value: string; label: string }[] | undefined;
      if (meta?.options) {
        options = meta.options.map((o) =>
          typeof o === 'string' ? { value: o, label: o.replace(/_/g, ' ') } : o
        );
      }

      return {
        name: f,
        label: (meta?.label || f.replace(/_/g, ' ')) + (!isRequired ? ' (optional)' : ''),
        type: fieldType,
        options,
        placeholder: meta?.placeholder || `Enter ${f.replace(/_/g, ' ')}...`,
        value: (action.prefill[f] as string) ?? '',
        search_domain: meta?.search_domain,
      };
    });
}

/** Check if an action has user-facing fields (required or optional, excluding backend-auto) */
export function actionHasFields(action: ActionDef): boolean {
  const hasRequired = action.required_fields.some((f) => !BACKEND_AUTO.has(f) && !(f in action.prefill));
  const hasOptional = (action.optional_fields ?? []).some((f) => !BACKEND_AUTO.has(f) && !(f in action.prefill));
  return hasRequired || hasOptional;
}

/** Get signature level from action definition */
export function getSignatureLevel(action: ActionDef): 0 | 1 | 2 | 3 | 4 | 5 {
  const level = action.signature_level ?? (action.requires_signature ? 3 : 0);
  return Math.min(5, Math.max(0, level)) as 0 | 1 | 2 | 3 | 4 | 5;
}
