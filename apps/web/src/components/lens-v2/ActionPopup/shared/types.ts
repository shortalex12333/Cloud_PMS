// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ActionPopupField {
  name: string;
  label: string;
  type:
    | 'kv-read'
    | 'kv-edit'
    | 'text-area'
    | 'select'
    | 'date-pick'
    | 'entity-search'
    | 'person-assign'
    | 'attachment'
    | 'status-set'
    | 'signature';
  value?: string;
  placeholder?: string;
  required?: boolean;
  options?: { value: string; label: string }[];
  entityRef?: { type: string; id: string; label: string };
  search_domain?: string;
}

export interface ActionPopupGate {
  label: string;
  satisfied: boolean;
}

export interface ActionPopupProps {
  /** Popup mode */
  mode: 'read' | 'mutate';
  /** Title */
  title: string;
  /** Subtitle / context */
  subtitle?: string;
  /** Fields to render */
  fields: ActionPopupField[];
  /** Data gates that block submission */
  gates?: ActionPopupGate[];
  /** Signature level (0-5) */
  signatureLevel?: 0 | 1 | 2 | 3 | 4 | 5;
  /** Submit button label */
  submitLabel?: string;
  /** Whether submit is disabled */
  submitDisabled?: boolean;
  /** Called with field values on submit */
  onSubmit: (values: Record<string, unknown>) => void;
  /** Called on cancel/close */
  onClose: () => void;
  /** Preview summary rows (shown above signature) */
  previewRows?: { key: string; value: string }[];
  /**
   * Server-populated context for the action (e.g. equipment.code,
   * equipment.name, criticality, running_hours…). Keys NOT mapped to a
   * user-editable field in `fields[]` render as a read-only "Source" block
   * at the top of the popup. Keys that ARE editable fields are skipped here
   * (the field editor renders them). Back-end-only keys are never rendered.
   */
  prefill?: Record<string, unknown>;
}
