'use client';

import * as React from 'react';
import s from './popup.module.css';
import { useAuth } from '@/hooks/useAuth';

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
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const BACKDROP_CLASS: Record<string, string> = {
  read: s.backdropRead,
  l0: s.backdropRead,
  l1: s.backdropL1,
  l2: s.backdropL2,
  l3: s.backdropL3,
  l4: s.backdropL4,
  l5: s.backdropL5,
};

function backdropClass(mode: 'read' | 'mutate', level: number): string {
  if (mode === 'read') return BACKDROP_CLASS.read;
  return BACKDROP_CLASS[`l${level}`] ?? BACKDROP_CLASS.l1;
}

// ---------------------------------------------------------------------------
// Sub-components: Field renderers
// ---------------------------------------------------------------------------

function FieldKvRead({ field }: { field: ActionPopupField }) {
  return (
    <div className={s.fieldValue}>
      {field.entityRef ? (
        <span className={s.fieldValueEntityRef}>{field.entityRef.label}</span>
      ) : (
        field.value ?? '\u2014'
      )}
    </div>
  );
}

function FieldKvEdit({
  field,
  value,
  onChange,
}: {
  field: ActionPopupField;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className={s.fieldInput}>
      <input
        type="text"
        value={value}
        placeholder={field.placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

function FieldTextArea({
  field,
  value,
  onChange,
}: {
  field: ActionPopupField;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className={s.fieldInput}>
      <textarea
        value={value}
        placeholder={field.placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

function FieldSelect({
  field,
  value,
  onChange,
}: {
  field: ActionPopupField;
  value: string;
  onChange: (v: string) => void;
}) {
  const selectedLabel = field.options?.find((o) => o.value === value)?.label;
  return (
    <div className={s.selectDisplay}>
      {selectedLabel ? (
        <span className={s.selectDisplayText}>{selectedLabel}</span>
      ) : (
        <span className={s.selectDisplayPlaceholder}>
          {field.placeholder ?? 'Select...'}
        </span>
      )}
      <svg className={s.selectDisplayIcon} viewBox="0 0 12 12" fill="none">
        <path d="M3 5l3 3 3-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <select
        className={s.selectNative}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">{field.placeholder ?? 'Select...'}</option>
        {field.options?.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}

function FieldDatePick({
  field,
  value,
  onChange,
}: {
  field: ActionPopupField;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className={s.dateDisplay}>
      <svg className={s.dateDisplayIcon} viewBox="0 0 16 16" fill="none">
        <rect x="2" y="3" width="12" height="11" rx="2" stroke="currentColor" strokeWidth="1.3" />
        <path d="M2 7h12M5 1v4M11 1v4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      </svg>
      {value ? (
        <span className={s.dateDisplayValue}>{value}</span>
      ) : (
        <span className={s.dateDisplayPlaceholder}>
          {field.placeholder ?? 'Pick date...'}
        </span>
      )}
      <input
        type="date"
        className={s.dateNative}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

function FieldEntitySearch({
  field,
  value,
  onChange,
}: {
  field: ActionPopupField;
  value: string;
  onChange: (v: string) => void;
}) {
  const { user, session } = useAuth();
  const [query, setQuery] = React.useState('');
  const [displayLabel, setDisplayLabel] = React.useState('');
  const [results, setResults] = React.useState<Array<{ id: string; title: string }>>([]);
  const [showDropdown, setShowDropdown] = React.useState(false);
  const debounceRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleSearch = React.useCallback(
    (q: string) => {
      setQuery(q);
      if (debounceRef.current) clearTimeout(debounceRef.current);
      if (!q || q.length < 2) {
        setResults([]);
        setShowDropdown(false);
        return;
      }
      debounceRef.current = setTimeout(async () => {
        try {
          const yachtId = user?.yachtId || '';
          const jwt = session?.access_token || '';
          if (!yachtId) {
            console.warn('[FieldEntitySearch] No yacht_id — user not bootstrapped');
            setResults([]);
            setShowDropdown(false);
            return;
          }
          const apiBase = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
          const domain = field.search_domain || 'equipment';
          const resp = await fetch(
            `${apiBase}/api/vessel/${yachtId}/domain/${domain}/records?search=${encodeURIComponent(q)}&limit=15`,
            {
              method: 'GET',
              headers: jwt ? { Authorization: `Bearer ${jwt}` } : {},
            },
          );
          if (resp.ok) {
            const data = await resp.json();
            // Domain records endpoint returns {records: [{id, title, ...}]}
            // Fallback search returns {results: [{id, title, object_type, ...}]}
            const records = data.records || data.results || [];
            const mapped = records.map((r: Record<string, unknown>) => ({
              id: (r.id || r.primary_id || '') as string,
              title: (r.title || r.name || r.equipment_name || r.filename || r.id || '') as string,
              object_type: (r.object_type || r.type || field.search_domain || '') as string,
            }));
            setResults(mapped.slice(0, 10));
            setShowDropdown(mapped.length > 0);
          }
        } catch {
          setResults([]);
          setShowDropdown(false);
        }
      }, 250);
    },
    [field.search_domain, user?.yachtId, session?.access_token]
  );

  const handleSelect = React.useCallback(
    (item: { id: string; title: string }) => {
      onChange(item.id);
      setDisplayLabel(item.title);
      setQuery(item.title);
      setShowDropdown(false);
    },
    [onChange]
  );

  return (
    <div className={s.entitySearchWrap} style={{ position: 'relative' }}>
      <svg className={s.entitySearchIcon} viewBox="0 0 16 16" fill="none">
        <circle cx="7" cy="7" r="4.5" stroke="currentColor" strokeWidth="1.3" />
        <path d="M10.5 10.5L14 14" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      </svg>
      <input
        type="text"
        value={displayLabel || query}
        placeholder={field.placeholder ?? `Search ${field.search_domain || 'entity'}...`}
        onChange={(e) => {
          setDisplayLabel('');
          handleSearch(e.target.value);
          if (!e.target.value) onChange('');
        }}
        onFocus={() => results.length > 0 && setShowDropdown(true)}
        onBlur={() => setTimeout(() => setShowDropdown(false), 200)}
      />
      {showDropdown && results.length > 0 && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            maxHeight: 200,
            overflowY: 'auto',
            background: 'var(--surface-elevated, #1a1a2e)',
            border: '1px solid var(--surface-border, #333)',
            borderRadius: 6,
            zIndex: 100,
            marginTop: 2,
          }}
        >
          {results.map((item) => (
            <div
              key={item.id}
              onMouseDown={() => handleSelect(item)}
              style={{
                padding: '8px 12px',
                cursor: 'pointer',
                fontSize: 13,
                color: 'var(--txt-primary, #eee)',
                borderBottom: '1px solid var(--surface-border, #222)',
              }}
              onMouseEnter={(e) => {
                (e.target as HTMLElement).style.background = 'var(--surface-hover, #252540)';
              }}
              onMouseLeave={(e) => {
                (e.target as HTMLElement).style.background = 'transparent';
              }}
            >
              {item.title || item.id}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function FieldPersonAssign({ field }: { field: ActionPopupField }) {
  return (
    <div className={s.personDisplay}>
      <div className={s.personAvatar}>
        <svg className={s.personAvatarIcon} viewBox="0 0 16 16" fill="none">
          <circle cx="8" cy="5" r="3" stroke="currentColor" strokeWidth="1.3" />
          <path d="M2.5 14c0-3 2.5-5 5.5-5s5.5 2 5.5 5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
        </svg>
      </div>
      <span className={s.personName}>{field.value ?? field.placeholder ?? 'Assign...'}</span>
    </div>
  );
}

function FieldAttachment() {
  return (
    <div className={s.uploadZone}>
      <svg className={s.uploadZoneIcon} viewBox="0 0 20 20" fill="none">
        <path d="M10 4v8M6 8l4-4 4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M3 14v2a2 2 0 002 2h10a2 2 0 002-2v-2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
      <div className={s.uploadText}>
        <span className={s.uploadTextTeal}>Click to upload</span> or drag and drop
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components: Signature levels
// ---------------------------------------------------------------------------

function SigL1() {
  return null; // L1 just uses the Confirm footer button
}

function SigL2({
  sigName,
  onSigNameChange,
}: {
  sigName: string;
  onSigNameChange: (v: string) => void;
}) {
  return (
    <div className={s.popupSig}>
      <div className={s.sigLabel}>Attestation</div>
      <div className={s.sigDeclaration}>
        <div className={s.sigDeclarationText}>
          I confirm that the information provided is accurate and complete to the
          best of my knowledge, and I accept responsibility for this action.
        </div>
      </div>
      <input
        className={s.sigNameInput}
        type="text"
        placeholder="Type your full name to confirm"
        value={sigName}
        onChange={(e) => onSigNameChange(e.target.value)}
      />
      <div className={s.sigNameHint}>
        Name must match your account profile
      </div>
    </div>
  );
}

function SigL3({
  pin,
  onPinChange,
}: {
  pin: string;
  onPinChange: (v: string) => void;
}) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const digits = pin.padEnd(4, ' ').slice(0, 4).split('');

  const handleClick = () => inputRef.current?.focus();

  return (
    <div className={s.popupSig}>
      <div className={s.sigLabel}>Verification</div>
      <div className={s.sigPinLabel}>Enter your 4-digit PIN</div>
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions */}
      <div className={s.sigPin} onClick={handleClick}>
        {digits.map((d, i) => {
          const filled = d !== ' ';
          const active = i === pin.length && pin.length < 4;
          const cls = [
            s.pinDigit,
            filled ? s.pinDigitFilled : s.pinDigitEmpty,
            active ? s.pinDigitActive : '',
          ]
            .filter(Boolean)
            .join(' ');
          return (
            <div key={i} className={cls}>
              {filled ? '\u2022' : ''}
            </div>
          );
        })}
        <input
          ref={inputRef}
          className={s.pinHiddenInput}
          type="password"
          inputMode="numeric"
          maxLength={4}
          value={pin}
          onChange={(e) => {
            const v = e.target.value.replace(/\D/g, '').slice(0, 4);
            onPinChange(v);
          }}
          autoFocus
          data-testid="signature-pin-input"
        />
      </div>
    </div>
  );
}

function SigL4({
  sigName,
  onSigNameChange,
  onClearPad,
}: {
  sigName: string;
  onSigNameChange: (v: string) => void;
  onClearPad?: () => void;
}) {
  return (
    <div className={s.popupSig}>
      <div className={s.sigLabel}>Wet Signature</div>
      <div className={s.sigPad}>
        <span className={s.sigPadHint}>Draw signature here</span>
        <button
          type="button"
          className={s.sigPadClear}
          onClick={onClearPad}
        >
          Clear
        </button>
      </div>
      <div className={s.sigPadMeta}>
        <input
          type="text"
          placeholder="Printed name"
          value={sigName}
          onChange={(e) => onSigNameChange(e.target.value)}
        />
        <input
          type="text"
          className={s.sigPadAutoDate}
          value={new Date().toISOString().slice(0, 10)}
          readOnly
        />
      </div>
    </div>
  );
}

function SigL5() {
  return (
    <div className={s.popupSig}>
      <div className={s.sigLabel}>Approval Chain</div>
      <div className={s.chainProgress}>
        {/* Example chain — in production this would be driven by data */}
        <div className={`${s.chainStep}`}>
          <div className={`${s.chainDot} ${s.chainDotDone}`}>
            <svg className={s.chainDotIcon} viewBox="0 0 14 14" fill="none">
              <path d="M3 7l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div className={s.chainRole}>Requester</div>
          <div className={s.chainStatus}>Submitted</div>
        </div>
        <div className={`${s.chainLine} ${s.chainLineDone}`} />
        <div className={`${s.chainStep} ${s.chainStepCurrent}`}>
          <div className={`${s.chainDot} ${s.chainDotCurrent}`}>2</div>
          <div className={s.chainRole}>HOD</div>
          <div className={s.chainStatus}>Awaiting</div>
        </div>
        <div className={s.chainLine} />
        <div className={s.chainStep}>
          <div className={`${s.chainDot} ${s.chainDotPending}`}>3</div>
          <div className={s.chainRole}>Captain</div>
          <div className={s.chainStatus}>Pending</div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function ActionPopup({
  mode,
  title,
  subtitle,
  fields,
  gates,
  signatureLevel = 1,
  submitLabel,
  submitDisabled,
  onSubmit,
  onClose,
  previewRows,
}: ActionPopupProps) {
  // L0 = tap only — execute inline, no modal needed
  // L0 = fire-and-forget (no form, no signature). Only auto-submit if there
  // are genuinely no fields to show — otherwise we'd skip the user's form.
  const isL0 = mode === 'mutate' && signatureLevel === 0 && fields.length === 0;

  // Internal form state (hooks must be called unconditionally)
  const [values, setValues] = React.useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    for (const f of fields) {
      init[f.name] = f.value ?? '';
    }
    return init;
  });
  const [pin, setPin] = React.useState('');
  const [sigName, setSigName] = React.useState('');

  const setValue = (name: string, value: string) =>
    setValues((prev) => ({ ...prev, [name]: value }));

  // Compute whether all gates are satisfied
  const allGatesSatisfied = !gates || gates.every((g) => g.satisfied);

  // Compute submit-ready state
  const computedDisabled = React.useMemo(() => {
    if (submitDisabled) return true;
    if (!allGatesSatisfied) return true;
    // Check required fields
    for (const f of fields) {
      if (f.required && !values[f.name]) return true;
    }
    // Signature checks
    if (signatureLevel === 2 && !sigName) return true;
    if (signatureLevel === 3 && pin.length < 4) return true;
    if (signatureLevel === 4 && !sigName) return true;
    return false;
  }, [submitDisabled, allGatesSatisfied, fields, values, signatureLevel, sigName, pin]);

  // L0: fire onSubmit immediately, render nothing
  React.useEffect(() => {
    if (isL0) {
      onSubmit({});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isL0]);
  if (isL0) return null;

  const handleSubmit = () => {
    if (computedDisabled) return;
    const result: Record<string, unknown> = { ...values };
    if (signatureLevel === 3) result.pin = pin;
    if (signatureLevel === 2 || signatureLevel === 4) result.signature_name = sigName;
    onSubmit(result);
  };

  // Resolve submit label
  const resolvedSubmitLabel =
    submitLabel ??
    (mode === 'read'
      ? 'Close'
      : signatureLevel === 3
        ? 'Verify'
        : signatureLevel === 4
          ? 'Sign'
          : 'Confirm');

  // Backdrop click closes
  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions
    <div
      className={`${s.backdrop} ${backdropClass(mode, signatureLevel)}`}
      onClick={handleBackdropClick}
      data-testid="action-popup-backdrop"
    >
      <div
        className={`${s.popup} ${mode === 'read' ? s.popupRead : s.popupMutate}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        data-testid="action-popup"
      >
        {/* Header */}
        <div className={s.popupHdr}>
          <div className={s.popupHdrText}>
            <div className={s.popupTitle}>{title}</div>
            {subtitle && <div className={s.popupSubtitle}>{subtitle}</div>}
          </div>
          <button
            className={s.popupClose}
            onClick={onClose}
            aria-label="Close"
            data-testid="action-popup-close"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M12 4L4 12M4 4l8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        {/* Divider (mutate only) */}
        {mode === 'mutate' && <div className={s.popupDivider} />}

        {/* Body — fields */}
        <div className={mode === 'read' ? s.popupBodyRead : s.popupBody}>
          {fields.map((field) => (
            <div
              key={field.name}
              className={s.field}
              data-testid={`popup-field-${field.name}`}
            >
              <div className={s.fieldLabel}>{field.label}</div>
              {renderField(field, values[field.name] ?? '', (v) =>
                setValue(field.name, v)
              )}
            </div>
          ))}
        </div>

        {/* Data gates */}
        {gates && gates.length > 0 && (
          <div className={s.popupGates}>
            {gates.map((gate, i) => (
              <div
                key={i}
                className={`${s.gate} ${gate.satisfied ? s.gateSatisfied : s.gatePending}`}
              >
                {gate.satisfied ? (
                  <svg className={s.gateIcon} viewBox="0 0 14 14" fill="none">
                    <path d="M3 7l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : (
                  <svg className={s.gateIcon} viewBox="0 0 14 14" fill="none">
                    <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.3" />
                    <path d="M7 4v4M7 10v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                  </svg>
                )}
                {gate.label}
              </div>
            ))}
          </div>
        )}

        {/* Preview summary */}
        {previewRows && previewRows.length > 0 && (
          <div className={s.popupPreview}>
            <div className={s.previewBox}>
              <div className={s.previewHeading}>Summary</div>
              {previewRows.map((row, i) => (
                <div key={i} className={s.previewRow}>
                  <span className={s.previewKey}>{row.key}</span>
                  <span className={s.previewVal}>{row.value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Signature section */}
        {mode === 'mutate' && signatureLevel === 1 && <SigL1 />}
        {mode === 'mutate' && signatureLevel === 2 && (
          <SigL2 sigName={sigName} onSigNameChange={setSigName} />
        )}
        {mode === 'mutate' && signatureLevel === 3 && (
          <SigL3 pin={pin} onPinChange={setPin} />
        )}
        {mode === 'mutate' && signatureLevel === 4 && (
          <SigL4
            sigName={sigName}
            onSigNameChange={setSigName}
            onClearPad={() => setSigName('')}
          />
        )}
        {mode === 'mutate' && signatureLevel === 5 && <SigL5 />}

        {/* Footer */}
        {mode === 'read' ? (
          <div className={s.popupFooterRead}>
            <button className={s.btnCancel} onClick={onClose}>
              Close
            </button>
          </div>
        ) : (
          <div className={s.popupFooter}>
            <button className={s.btnCancel} onClick={onClose}>
              Cancel
            </button>
            <button
              className={`${s.btnSubmit} ${computedDisabled ? s.btnSubmitDisabled : ''}`}
              disabled={computedDisabled}
              onClick={handleSubmit}
              data-testid="signature-confirm-button"
            >
              {resolvedSubmitLabel}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Field dispatcher
// ---------------------------------------------------------------------------

function renderField(
  field: ActionPopupField,
  value: string,
  onChange: (v: string) => void
): React.ReactNode {
  switch (field.type) {
    case 'kv-read':
      return <FieldKvRead field={field} />;
    case 'kv-edit':
      return <FieldKvEdit field={field} value={value} onChange={onChange} />;
    case 'text-area':
      return <FieldTextArea field={field} value={value} onChange={onChange} />;
    case 'select':
    case 'status-set':
      return <FieldSelect field={field} value={value} onChange={onChange} />;
    case 'date-pick':
      return <FieldDatePick field={field} value={value} onChange={onChange} />;
    case 'entity-search':
      return <FieldEntitySearch field={field} value={value} onChange={onChange} />;
    case 'person-assign':
      return <FieldPersonAssign field={field} />;
    case 'attachment':
      return <FieldAttachment />;
    case 'signature':
      // Signature fields are handled by the SigLX components, not inline
      return <FieldKvRead field={field} />;
    default:
      return <FieldKvRead field={field} />;
  }
}
