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
  /**
   * Server-populated context for the action (e.g. equipment.code,
   * equipment.name, criticality, running_hours…). Keys NOT mapped to a
   * user-editable field in `fields[]` render as a read-only "Source" block
   * at the top of the popup. Keys that ARE editable fields are skipped here
   * (the field editor renders them). Back-end-only keys are never rendered.
   */
  prefill?: Record<string, unknown>;
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
// Source-context block (renders prefill keys NOT in fields[])
// ---------------------------------------------------------------------------

/** Keys that are backend-only plumbing and must NEVER surface to the user. */
const SOURCE_NEVER_RENDER = new Set<string>([
  // Generic plumbing
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
  // Foreign-key UUIDs. Each of these is expected to come alongside a
  // human-readable *_name (e.g. `equipment_id` + `equipment_name`). The UUID
  // is routing plumbing; only the name belongs in the Source block.
  // Per FAULT05 cohort review of PR #704 (2026-04-24): skipping UUID surfacing.
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

/** Keys whose values are machine identifiers and should render in monospace. */
const SOURCE_MONO_KEYS = new Set<string>([
  'code',
  'part_number',
  'wonumber',
  'fault_code',
  'po_number',
  'serial_number',
]);

/**
 * Per-key label overrides for prefill keys whose humanised form reads weakly
 * because of an embedded acronym (e.g. "Po number" vs "PO number"). Keep this
 * narrow — only add overrides when the default humanise produces something
 * genuinely worse. Per PURCHASE05 cohort review of PR #704 (2026-04-24).
 */
const SOURCE_LABEL_OVERRIDES: Record<string, string> = {
  po_number: 'PO number',
  wonumber: 'WO number',
  wo_number: 'WO number',
  sku: 'SKU',
};

/** `serial_number` -> "Serial number"; "running_hours" -> "Running hours". */
function humanizeKey(key: string): string {
  const override = SOURCE_LABEL_OVERRIDES[key];
  if (override) return override;
  const spaced = key.replace(/_/g, ' ').trim();
  if (!spaced) return key;
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

interface SourceRow {
  key: string;
  label: string;
  value: string;
  mono: boolean;
}

function buildSourceRows(
  prefill: Record<string, unknown> | undefined,
  fieldNames: Set<string>,
): SourceRow[] {
  if (!prefill) return [];
  const rows: SourceRow[] = [];
  // Insertion order — Object.keys preserves it for string keys.
  for (const key of Object.keys(prefill)) {
    if (SOURCE_NEVER_RENDER.has(key)) continue;
    if (fieldNames.has(key)) continue;
    const raw = prefill[key];
    if (raw === null || raw === undefined) continue;

    let value: string;
    let mono = SOURCE_MONO_KEYS.has(key);

    if (typeof raw === 'string') {
      value = raw;
    } else if (typeof raw === 'number') {
      value = String(raw);
      mono = true;
    } else if (typeof raw === 'boolean') {
      value = raw ? 'Yes' : 'No';
    } else {
      // array / object — last-resort stringify, truncated.
      const json = JSON.stringify(raw);
      value = json && json.length > 60 ? json.slice(0, 60) + '…' : json ?? '';
    }

    rows.push({ key, label: humanizeKey(key), value, mono });
  }
  return rows;
}

function SourceBlock({ rows }: { rows: SourceRow[] }) {
  return (
    <div
      data-testid="action-popup-source"
      style={{
        margin: '0 24px',
        padding: '12px 0 12px 0',
        borderBottom: '1px solid var(--border-faint)',
      }}
    >
      <div
        style={{
          fontSize: 10,
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          color: 'var(--txt3)',
          marginBottom: 8,
          fontFamily: 'var(--font-sans)',
        }}
      >
        Source
      </div>
      {rows.map((row) => (
        <div
          key={row.key}
          data-testid={`action-popup-source-row-${row.key}`}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            minHeight: 44,
            fontSize: 12,
          }}
        >
          <span
            style={{
              color: 'var(--txt3)',
              minWidth: 112,
              fontSize: 10,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              fontFamily: 'var(--font-sans)',
            }}
          >
            {row.label}
          </span>
          <span
            data-testid={`action-popup-source-val-${row.key}`}
            style={{
              color: 'var(--txt2)',
              fontFamily: row.mono ? 'var(--font-mono)' : 'var(--font-sans)',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {row.value}
          </span>
        </div>
      ))}
    </div>
  );
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

// ── Domain icon SVGs (matches SpotlightResultRow icons) ──────────────────────
function DomainIcon({ domain }: { domain: string }) {
  const d = domain.toLowerCase();
  if (d.includes('part') || d.includes('inventory'))
    return <svg viewBox="0 0 16 16" fill="none" style={{ width: 14, height: 14, flexShrink: 0, color: 'var(--txt-secondary)' }}><rect x="2" y="5" width="12" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.3"/><path d="M5 5V3.5A1.5 1.5 0 016.5 2h3A1.5 1.5 0 0111 3.5V5" stroke="currentColor" strokeWidth="1.3"/></svg>;
  if (d.includes('equipment'))
    return <svg viewBox="0 0 16 16" fill="none" style={{ width: 14, height: 14, flexShrink: 0, color: 'var(--txt-secondary)' }}><circle cx="8" cy="8" r="2.5" stroke="currentColor" strokeWidth="1.3"/><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.42 1.42M11.53 11.53l1.42 1.42M3.05 12.95l1.42-1.42M11.53 4.47l1.42-1.42" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>;
  if (d.includes('fault'))
    return <svg viewBox="0 0 16 16" fill="none" style={{ width: 14, height: 14, flexShrink: 0, color: 'var(--txt-secondary)' }}><path d="M8 2L14 13H2L8 2z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round"/><path d="M8 6v3M8 11v.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>;
  if (d.includes('work_order') || d.includes('workorder'))
    return <svg viewBox="0 0 16 16" fill="none" style={{ width: 14, height: 14, flexShrink: 0, color: 'var(--txt-secondary)' }}><rect x="2" y="1" width="12" height="14" rx="1.5" stroke="currentColor" strokeWidth="1.3"/><path d="M5 5h6M5 8h6M5 11h4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>;
  if (d.includes('crew') || d.includes('person'))
    return <svg viewBox="0 0 16 16" fill="none" style={{ width: 14, height: 14, flexShrink: 0, color: 'var(--txt-secondary)' }}><circle cx="8" cy="5" r="3" stroke="currentColor" strokeWidth="1.3"/><path d="M2.5 14c0-3 2.5-5 5.5-5s5.5 2 5.5 5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>;
  // generic
  return <svg viewBox="0 0 16 16" fill="none" style={{ width: 14, height: 14, flexShrink: 0, color: 'var(--txt-secondary)' }}><rect x="2" y="2" width="12" height="12" rx="2" stroke="currentColor" strokeWidth="1.3"/></svg>;
}

// Build rich subtitle from raw domain record fields
function buildResultSubtitle(r: Record<string, unknown>, domain: string): string {
  const meta: string[] = [];
  if (r.part_number)      meta.push(`P/N ${r.part_number}`);
  if (r.wo_number)        meta.push(String(r.wo_number));
  if (r.fault_code)       meta.push(String(r.fault_code));
  if (r.code && !r.part_number && !r.wo_number) meta.push(String(r.code));
  if (r.manufacturer)     meta.push(String(r.manufacturer));
  if (r.location)         meta.push(String(r.location));
  if (r.category)         meta.push(String(r.category));
  if (r.status)           meta.push(String(r.status).replace(/_/g, ' '));
  if (r.quantity_on_hand !== undefined && r.quantity_on_hand !== null)
                          meta.push(`Qty: ${r.quantity_on_hand}`);
  if (r.serial_number && meta.length < 3) meta.push(String(r.serial_number));
  if (r.priority && meta.length < 3)     meta.push(String(r.priority));
  // Fallback: description snippet
  if (meta.length === 0 && r.description)
    return String(r.description).slice(0, 80);
  return meta.slice(0, 4).join(' · ');
}

interface EntitySearchResult {
  id: string;
  title: string;
  subtitle: string;
  object_type: string;
}

function mapDomainRecord(r: Record<string, unknown>, domain: string): EntitySearchResult {
  const title = String(
    r.title || r.name || r.equipment_name || r.part_name ||
    r.section_title || r.document_name || r.filename || r.id || ''
  ).trim() || String(r.id || '');
  return {
    id: String(r.id || r.primary_id || ''),
    title,
    subtitle: buildResultSubtitle(r, domain),
    object_type: String(r.object_type || r.type || domain),
  };
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
  const [results, setResults] = React.useState<EntitySearchResult[]>([]);
  const [showDropdown, setShowDropdown] = React.useState(false);
  const [activeIdx, setActiveIdx] = React.useState(-1);
  const debounceRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const domain = field.search_domain || 'equipment';

  const handleSearch = React.useCallback(
    (q: string) => {
      setQuery(q);
      setActiveIdx(-1);
      if (debounceRef.current) clearTimeout(debounceRef.current);
      if (!q || q.length < 2) { setResults([]); setShowDropdown(false); return; }
      debounceRef.current = setTimeout(async () => {
        try {
          const yachtId = user?.yachtId || '';
          const jwt = session?.access_token || '';
          if (!yachtId) { setResults([]); setShowDropdown(false); return; }
          const apiBase = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
          const resp = await fetch(
            `${apiBase}/api/vessel/${yachtId}/domain/${domain}/records?q=${encodeURIComponent(q)}&limit=15`,
            { headers: jwt ? { Authorization: `Bearer ${jwt}` } : {} },
          );
          if (resp.ok) {
            const data = await resp.json();
            const records: Record<string, unknown>[] = data.records || data.results || [];
            const mapped = records.map((r) => mapDomainRecord(r, domain)).filter((r) => r.id);
            setResults(mapped.slice(0, 10));
            setShowDropdown(mapped.length > 0);
          }
        } catch { setResults([]); setShowDropdown(false); }
      }, 250);
    },
    [domain, user?.yachtId, session?.access_token]
  );

  const handleSelect = React.useCallback(
    (item: EntitySearchResult) => {
      onChange(item.id);
      setDisplayLabel(item.title);
      setQuery(item.title);
      setShowDropdown(false);
      setActiveIdx(-1);
    },
    [onChange]
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showDropdown) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); setActiveIdx((i) => Math.min(i + 1, results.length - 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActiveIdx((i) => Math.max(i - 1, 0)); }
    else if (e.key === 'Enter' && activeIdx >= 0) { e.preventDefault(); handleSelect(results[activeIdx]); }
    else if (e.key === 'Escape') { setShowDropdown(false); }
  };

  return (
    <div className={s.entitySearchWrap} style={{ position: 'relative' }}>
      <svg className={s.entitySearchIcon} viewBox="0 0 16 16" fill="none">
        <circle cx="7" cy="7" r="4.5" stroke="currentColor" strokeWidth="1.3" />
        <path d="M10.5 10.5L14 14" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      </svg>
      <input
        type="text"
        value={displayLabel || query}
        placeholder={field.placeholder ?? `Search ${domain.replace(/_/g, ' ')}...`}
        onChange={(e) => {
          setDisplayLabel('');
          handleSearch(e.target.value);
          if (!e.target.value) onChange('');
        }}
        onFocus={() => results.length > 0 && setShowDropdown(true)}
        onBlur={() => setTimeout(() => setShowDropdown(false), 150)}
        onKeyDown={handleKeyDown}
      />
      {showDropdown && results.length > 0 && (
        <div style={{
          position: 'absolute', top: 'calc(100% + 4px)', left: 0, right: 0,
          maxHeight: 360, overflowY: 'auto',
          background: 'var(--surface-elevated)',
          border: '1px solid var(--surface-border)',
          borderRadius: 8,
          boxShadow: '0 8px 24px rgba(0,0,0,0.28), 0 2px 6px rgba(0,0,0,0.16)',
          zIndex: 200,
        }}>
          {results.map((item, idx) => (
            <div
              key={item.id}
              onMouseDown={() => handleSelect(item)}
              onMouseEnter={() => setActiveIdx(idx)}
              style={{
                display: 'flex', alignItems: 'flex-start', gap: 10,
                padding: '10px 14px',
                cursor: 'pointer',
                background: idx === activeIdx ? 'var(--surface-hover)' : 'transparent',
                borderBottom: idx < results.length - 1 ? '1px solid var(--surface-border)' : 'none',
                transition: 'background 80ms',
              }}
            >
              <div style={{ marginTop: 2 }}>
                <DomainIcon domain={item.object_type || domain} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--txt-primary)', lineHeight: 1.4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {item.title}
                </div>
                {item.subtitle && (
                  <div style={{ fontSize: 11, color: 'var(--txt-secondary)', lineHeight: 1.5, marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', letterSpacing: '0.01em' }}>
                    {item.subtitle}
                  </div>
                )}
              </div>
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
  prefill,
}: ActionPopupProps) {
  // L0 = tap only — execute inline, no modal needed
  // L0 = fire-and-forget (no form, no signature). Only auto-submit if there
  // are genuinely no fields to show — otherwise we'd skip the user's form.
  const isL0 = mode === 'mutate' && signatureLevel === 0 && fields.length === 0;
  const hasEntitySearch = fields.some((f) => f.type === 'entity-search');

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

  // Source-context rows: prefill keys NOT mapped to a user-editable field.
  // Invisible when no usable rows remain.
  const sourceRows = React.useMemo(() => {
    const fieldNames = new Set(fields.map((f) => f.name));
    return buildSourceRows(prefill, fieldNames);
  }, [prefill, fields]);

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
    // Backend SIGNED actions require `signature` (JSON object) in the payload.
    // Map frontend signature levels to the backend contract shape.
    if (signatureLevel === 3) {
      result.signature = {
        method: 'pin',
        pin,
        signed_at: new Date().toISOString(),
      };
    }
    if (signatureLevel === 2 || signatureLevel === 4) {
      result.signature = {
        method: 'name',
        name: sigName,
        signed_at: new Date().toISOString(),
      };
    }
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
        style={hasEntitySearch ? { maxWidth: 640 } : undefined}
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

        {/* Source-context block — prefill keys that are not editable fields. */}
        {sourceRows.length > 0 && <SourceBlock rows={sourceRows} />}

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
