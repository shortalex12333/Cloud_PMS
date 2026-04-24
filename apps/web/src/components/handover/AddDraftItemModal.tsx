'use client';

/**
 * AddDraftItemModal — "+ Add Draft Item" modal for the handover draft panel.
 *
 * Replaces the old "Add Note" ItemPopup add-mode with a key/value entity
 * selector as mandated by HANDOVER08 Issue 8b.
 *
 * Behaviour:
 * 1. User picks a KEY (domain): Work Order · Equipment · Parts · Fault · Location.
 * 2. A VALUE field is rendered appropriate to the key:
 *    - Entity keys: searchable type-to-filter list, loaded from
 *      `GET /v1/handover/pickers/{entity_type}` (yacht-scoped, alphabetical).
 *    - Location: free text input (no location table exists by design).
 * 3. Required summary textarea (3–2000 chars per canonical handler).
 * 4. Optional notes textarea (stored in the summary tail for now — kept
 *    separate in UI for future expansion to a structured notes column).
 *
 * Submit path:
 *   POST /v1/actions/execute  { action: 'add_to_handover', payload: {...} }
 *
 *   - Entity keys (work_order / equipment / part / fault):
 *        entity_type = <key>, entity_id = <picked UUID>, summary = <text>.
 *   - Location:
 *        entity_type = 'note', entity_id = null,
 *        summary = "[Location: <label>] " + <text>.
 *     The canonical handler already accepts entity_type='note' with a null
 *     entity_id, so no backend contract extension is required.
 *
 * Styling: tokenised CSS vars only. Teal accent, 44-px row heights in the
 * picker, monospace for codes + timestamps. Matches HandoverDraftPanel's
 * existing design language.
 *
 * Keyboard:
 *   - Escape: close.
 *   - Enter (while summary focused with value valid): submit.
 */

import * as React from 'react';
import { X, Plus, Wrench, Package, AlertTriangle, FileText, MapPin, Check, type LucideIcon } from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

export type AddDraftEntityKey =
  | 'work_order'
  | 'equipment'
  | 'part'
  | 'fault'
  | 'location';

export interface AddDraftPickerItem {
  id: string;
  code?: string | null;
  title?: string | null;
  sub_a?: string | null;
  sub_b?: string | null;
}

export interface AddDraftItemSubmitPayload {
  entity_type: 'work_order' | 'equipment' | 'part' | 'fault' | 'note';
  entity_id: string | null;
  summary: string;
  notes?: string;
  /** Only present when the user chose the Location key. */
  location_label?: string;
}

export interface AddDraftItemModalProps {
  open: boolean;
  onClose: () => void;
  /**
   * Loader invoked each time the user switches the KEY dropdown to an entity
   * type. Parent is responsible for auth + API base URL + yacht scoping.
   * Must resolve with a yacht-scoped, alphabetical list.
   */
  loadEntities: (key: Exclude<AddDraftEntityKey, 'location'>) => Promise<AddDraftPickerItem[]>;
  /**
   * Called with the final payload. Modal closes on resolve; on reject an
   * inline error is surfaced and the modal stays open.
   */
  onSubmit: (payload: AddDraftItemSubmitPayload) => Promise<void>;
  /** Disable submit while user context is still loading. */
  userReady?: boolean;
}

// ─── Static config ────────────────────────────────────────────────────────────

const KEY_OPTIONS: { value: AddDraftEntityKey; label: string; Icon: LucideIcon }[] = [
  { value: 'work_order', label: 'Work Order', Icon: Wrench },
  { value: 'equipment',  label: 'Equipment',  Icon: Package },
  { value: 'part',       label: 'Parts',      Icon: Package },
  { value: 'fault',      label: 'Fault',      Icon: AlertTriangle },
  { value: 'location',   label: 'Location',   Icon: MapPin },
];

const SUMMARY_MIN = 3;
const SUMMARY_MAX = 2000;

// ─── Styles ───────────────────────────────────────────────────────────────────

const S = {
  overlay: {
    position: 'fixed' as const, inset: 0, zIndex: 200,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    padding: 16,
  },
  backdrop: {
    position: 'absolute' as const, inset: 0,
    background: 'var(--overlay-bg)',
  },
  modal: {
    position: 'relative' as const, width: '100%', maxWidth: 560,
    maxHeight: '90vh',
    background: 'var(--surface-el)',
    borderRadius: 12,
    borderTop: '1px solid var(--border-top)',
    borderRight: '1px solid var(--border-side)',
    borderBottom: '1px solid var(--border-bottom)',
    borderLeft: '1px solid var(--border-side)',
    boxShadow: 'var(--shadow-panel)',
    display: 'flex', flexDirection: 'column' as const, overflow: 'hidden',
  },
  header: {
    display: 'flex', alignItems: 'flex-start', gap: 12,
    padding: '20px 24px 16px',
    borderBottom: '1px solid var(--border-sub)',
  },
  headerIcon: {
    width: 32, height: 32, borderRadius: 8,
    background: 'var(--teal-bg)', color: 'var(--mark)',
    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
  },
  title: { fontSize: 18, fontWeight: 600, color: 'var(--txt)' },
  subtitle: { fontSize: 13, color: 'var(--txt2)', marginTop: 3 },
  closeBtn: {
    width: 36, height: 36, borderRadius: 8,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    cursor: 'pointer', color: 'var(--txt-ghost)',
    background: 'none', border: 'none',
  },
  body: {
    padding: '16px 24px',
    overflowY: 'auto' as const, flex: 1,
  },
  fieldLabel: {
    fontSize: 11, fontWeight: 500, color: 'var(--txt3)',
    textTransform: 'uppercase' as const, letterSpacing: '0.04em',
    marginBottom: 8,
  },
  keyRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(5, 1fr)',
    gap: 6,
    marginBottom: 16,
  },
  keyOption: (selected: boolean) => ({
    display: 'flex', flexDirection: 'column' as const,
    alignItems: 'center', justifyContent: 'center', gap: 4,
    padding: '10px 6px', borderRadius: 6,
    cursor: 'pointer', userSelect: 'none' as const,
    border: `1px solid ${selected ? 'var(--mark-underline)' : 'var(--border-sub)'}`,
    background: selected ? 'var(--teal-bg)' : 'transparent',
    color: selected ? 'var(--mark)' : 'var(--txt2)',
    fontSize: 11, fontWeight: selected ? 600 : 500,
    transition: 'background 80ms, border-color 80ms, color 80ms',
  }),
  searchInput: {
    width: '100%', boxSizing: 'border-box' as const,
    background: 'var(--surface-base)',
    border: '1px solid var(--border-chrome)',
    borderRadius: 6,
    padding: '10px 12px',
    fontSize: 13, color: 'var(--txt)',
    fontFamily: 'var(--font-sans)', outline: 'none',
  },
  list: {
    marginTop: 8,
    maxHeight: 240, overflowY: 'auto' as const,
    border: '1px solid var(--border-sub)',
    borderRadius: 6,
    background: 'var(--surface-base)',
  },
  listItem: (selected: boolean, hover: boolean) => ({
    display: 'flex', alignItems: 'center', gap: 10,
    minHeight: 44,
    padding: '8px 12px',
    cursor: 'pointer',
    borderBottom: '1px solid var(--border-faint)',
    background: selected
      ? 'var(--teal-bg)'
      : (hover ? 'var(--surface-hover)' : 'transparent'),
    transition: 'background 60ms',
  }),
  listItemCode: {
    fontFamily: 'var(--font-mono)',
    fontSize: 11,
    color: 'var(--txt3)',
    letterSpacing: '0.02em',
    flexShrink: 0,
  },
  listItemTitle: {
    fontSize: 13, fontWeight: 500, color: 'var(--txt)',
    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' as const,
  },
  listItemSubline: {
    fontSize: 11, color: 'var(--txt2)',
    marginTop: 1, display: 'flex', alignItems: 'center', gap: 8,
    overflow: 'hidden', whiteSpace: 'nowrap' as const,
  },
  listStateMsg: {
    padding: '24px 16px', textAlign: 'center' as const,
    fontSize: 12, color: 'var(--txt3)',
  },
  textarea: {
    width: '100%', boxSizing: 'border-box' as const,
    background: 'var(--surface-base)',
    border: '1px solid var(--border-chrome)',
    borderRadius: 6,
    padding: '10px 12px',
    fontSize: 13, color: 'var(--txt)',
    fontFamily: 'var(--font-sans)',
    lineHeight: 1.5, outline: 'none',
    resize: 'vertical' as const,
  },
  charCount: {
    fontSize: 10, fontFamily: 'var(--font-mono)',
    color: 'var(--txt-ghost)', marginTop: 4, textAlign: 'right' as const,
  },
  errorMsg: {
    fontSize: 12, color: 'var(--red)',
    marginTop: 8,
  },
  footer: {
    display: 'flex', alignItems: 'center', gap: 8,
    padding: '16px 24px',
    borderTop: '1px solid var(--border-sub)',
    flexShrink: 0,
  },
  btnPrimary: {
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '9px 16px', borderRadius: 8,
    fontSize: 13, fontWeight: 600,
    cursor: 'pointer',
    border: '1px solid var(--mark-underline)',
    background: 'var(--teal-bg)', color: 'var(--mark)',
    fontFamily: 'var(--font-sans)', minHeight: 40,
  },
  btnSecondary: {
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '9px 16px', borderRadius: 8,
    fontSize: 13, fontWeight: 500,
    cursor: 'pointer',
    border: '1px solid var(--border-sub)',
    background: 'none', color: 'var(--txt2)',
    fontFamily: 'var(--font-sans)', minHeight: 40,
  },
};

// ─── Component ───────────────────────────────────────────────────────────────

export function AddDraftItemModal({
  open, onClose, loadEntities, onSubmit, userReady = true,
}: AddDraftItemModalProps) {
  const [entityKey, setEntityKey] = React.useState<AddDraftEntityKey | null>(null);

  // Entity picker state
  const [items, setItems] = React.useState<AddDraftPickerItem[] | null>(null);
  const [loadError, setLoadError] = React.useState<string | null>(null);
  const [loadingList, setLoadingList] = React.useState(false);
  const [query, setQuery] = React.useState('');
  const [selectedEntityId, setSelectedEntityId] = React.useState<string | null>(null);
  const [hoverId, setHoverId] = React.useState<string | null>(null);

  // Location state
  const [locationLabel, setLocationLabel] = React.useState('');

  // Summary + notes
  const [summary, setSummary] = React.useState('');
  const [notes, setNotes] = React.useState('');

  // Submit state
  const [submitting, setSubmitting] = React.useState(false);
  const [submitError, setSubmitError] = React.useState<string | null>(null);

  const summaryRef = React.useRef<HTMLTextAreaElement>(null);
  const searchRef = React.useRef<HTMLInputElement>(null);
  const locationRef = React.useRef<HTMLInputElement>(null);

  // Reset on open
  React.useEffect(() => {
    if (open) {
      setEntityKey(null);
      setItems(null);
      setLoadError(null);
      setLoadingList(false);
      setQuery('');
      setSelectedEntityId(null);
      setLocationLabel('');
      setSummary('');
      setNotes('');
      setSubmitting(false);
      setSubmitError(null);
    }
  }, [open]);

  // Escape closes
  React.useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  // Load entity list when key changes to a non-location type
  React.useEffect(() => {
    if (!open) return;
    if (!entityKey || entityKey === 'location') {
      setItems(null);
      setLoadError(null);
      return;
    }
    let cancelled = false;
    setLoadingList(true);
    setLoadError(null);
    setItems(null);
    setSelectedEntityId(null);
    setQuery('');
    loadEntities(entityKey)
      .then((rows) => {
        if (cancelled) return;
        setItems(rows);
        // Autofocus search once the list arrives.
        requestAnimationFrame(() => searchRef.current?.focus());
      })
      .catch((err) => {
        if (cancelled) return;
        setLoadError(err instanceof Error ? err.message : 'Failed to load list');
      })
      .finally(() => { if (!cancelled) setLoadingList(false); });
    return () => { cancelled = true; };
  }, [entityKey, open, loadEntities]);

  // Focus location input when user flips to location key
  React.useEffect(() => {
    if (open && entityKey === 'location') {
      requestAnimationFrame(() => locationRef.current?.focus());
    }
  }, [entityKey, open]);

  // Client-side filter
  const filteredItems = React.useMemo(() => {
    if (!items) return [];
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((it) => {
      return (
        (it.code ?? '').toLowerCase().includes(q) ||
        (it.title ?? '').toLowerCase().includes(q) ||
        (it.sub_a ?? '').toLowerCase().includes(q) ||
        (it.sub_b ?? '').toLowerCase().includes(q)
      );
    });
  }, [items, query]);

  // Validation
  const summaryTrimmed = summary.trim();
  const summaryValid = summaryTrimmed.length >= SUMMARY_MIN && summaryTrimmed.length <= SUMMARY_MAX;
  const entitySelected = entityKey === 'location'
    ? locationLabel.trim().length > 0
    : (entityKey !== null && selectedEntityId !== null);
  const canSubmit = entitySelected && summaryValid && !submitting && userReady;

  const buildPayload = React.useCallback((): AddDraftItemSubmitPayload | null => {
    if (!entityKey) return null;
    if (entityKey === 'location') {
      const label = locationLabel.trim();
      if (!label) return null;
      // entity_type='note' + prepended [Location: ...] is the simplest route
      // that needs no backend contract extension. The location label is also
      // returned separately so callers that want to persist it into metadata
      // can do so.
      return {
        entity_type: 'note',
        entity_id: null,
        summary: `[Location: ${label}] ${summaryTrimmed}`,
        notes: notes.trim() || undefined,
        location_label: label,
      };
    }
    if (!selectedEntityId) return null;
    return {
      entity_type: entityKey,
      entity_id: selectedEntityId,
      summary: summaryTrimmed,
      notes: notes.trim() || undefined,
    };
  }, [entityKey, selectedEntityId, locationLabel, summaryTrimmed, notes]);

  const handleSubmit = React.useCallback(async () => {
    if (!canSubmit) return;
    const payload = buildPayload();
    if (!payload) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await onSubmit(payload);
      onClose();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to add draft item');
    } finally {
      setSubmitting(false);
    }
  }, [canSubmit, buildPayload, onSubmit, onClose]);

  // Enter submits when summary valid and focus is in summary or textarea region
  const onSummaryKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  if (!open) return null;

  const keyMeta = entityKey ? KEY_OPTIONS.find((o) => o.value === entityKey) : null;

  return (
    <div style={S.overlay} role="dialog" aria-modal="true" aria-label="Add Draft Item">
      <div style={S.backdrop} onClick={onClose} />
      <div style={S.modal} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={S.header}>
          <div style={S.headerIcon}>
            <Plus size={16} />
          </div>
          <div style={{ flex: 1 }}>
            <div style={S.title}>Add Draft Item</div>
            <div style={S.subtitle}>
              Link a domain entity or a location label, then describe what the
              next crew needs to know.
            </div>
          </div>
          <button type="button" style={S.closeBtn} onClick={onClose} aria-label="Close">
            <X size={14} />
          </button>
        </div>

        {/* Body */}
        <div style={S.body}>
          {/* KEY picker */}
          <div>
            <div style={S.fieldLabel}>Key</div>
            <div style={S.keyRow}>
              {KEY_OPTIONS.map(({ value, label, Icon }) => {
                const selected = entityKey === value;
                return (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setEntityKey(value)}
                    style={S.keyOption(selected)}
                  >
                    <Icon size={14} />
                    {label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* VALUE picker */}
          {entityKey && (
            <div style={{ marginTop: 4 }}>
              <div style={S.fieldLabel}>Value</div>

              {entityKey === 'location' ? (
                <input
                  ref={locationRef}
                  type="text"
                  value={locationLabel}
                  onChange={(e) => setLocationLabel(e.target.value)}
                  placeholder="e.g. Sun deck, Engine room, Bridge"
                  style={S.searchInput}
                  maxLength={200}
                />
              ) : (
                <>
                  <input
                    ref={searchRef}
                    type="search"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder={`Search ${keyMeta?.label.toLowerCase() ?? 'list'}…`}
                    style={S.searchInput}
                    disabled={loadingList || !!loadError}
                  />
                  <div style={S.list}>
                    {loadingList && (
                      <div style={S.listStateMsg}>Loading…</div>
                    )}
                    {loadError && !loadingList && (
                      <div style={{ ...S.listStateMsg, color: 'var(--red)' }} role="alert">
                        {loadError}
                      </div>
                    )}
                    {!loadingList && !loadError && items && filteredItems.length === 0 && (
                      <div style={S.listStateMsg}>
                        {query ? 'No matches.' : 'No items on this vessel.'}
                      </div>
                    )}
                    {!loadingList && !loadError && filteredItems.map((it) => {
                      const selected = selectedEntityId === it.id;
                      const hover = hoverId === it.id;
                      return (
                        <div
                          key={it.id}
                          role="option"
                          aria-selected={selected}
                          onClick={() => setSelectedEntityId(it.id)}
                          onMouseEnter={() => setHoverId(it.id)}
                          onMouseLeave={() => setHoverId((h) => h === it.id ? null : h)}
                          style={S.listItem(selected, hover)}
                        >
                          {it.code && (
                            <span style={S.listItemCode}>{it.code}</span>
                          )}
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={S.listItemTitle}>
                              {it.title || '—'}
                            </div>
                            {(it.sub_a || it.sub_b) && (
                              <div style={S.listItemSubline}>
                                {it.sub_a && <span>{it.sub_a}</span>}
                                {it.sub_a && it.sub_b && <span style={{ opacity: 0.5 }}>·</span>}
                                {it.sub_b && (
                                  <span style={{
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    whiteSpace: 'nowrap',
                                  }}>
                                    {it.sub_b}
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                          {selected && (
                            <Check size={14} style={{ color: 'var(--mark)', flexShrink: 0 }} />
                          )}
                        </div>
                      );
                    })}
                  </div>
                </>
              )}
            </div>
          )}

          {/* Summary */}
          <div style={{ marginTop: 16 }}>
            <div style={S.fieldLabel}>Summary <span style={{ color: 'var(--red)' }}>*</span></div>
            <textarea
              ref={summaryRef}
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              onKeyDown={onSummaryKeyDown}
              placeholder="What does the incoming crew need to know?"
              style={{ ...S.textarea, minHeight: 80 }}
              maxLength={SUMMARY_MAX}
            />
            <div style={S.charCount}>
              {summaryTrimmed.length}/{SUMMARY_MAX}
              {summaryTrimmed.length > 0 && summaryTrimmed.length < SUMMARY_MIN && (
                <span style={{ color: 'var(--amber)', marginLeft: 8 }}>
                  (minimum {SUMMARY_MIN})
                </span>
              )}
            </div>
          </div>

          {/* Notes */}
          <div style={{ marginTop: 12 }}>
            <div style={S.fieldLabel}>Notes (optional)</div>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Additional context, observations, follow-up…"
              style={{ ...S.textarea, minHeight: 60 }}
              maxLength={2000}
            />
          </div>

          {submitError && (
            <div style={S.errorMsg} role="alert">{submitError}</div>
          )}
        </div>

        {/* Footer */}
        <div style={S.footer}>
          <button
            type="button"
            style={{ ...S.btnPrimary, opacity: canSubmit ? 1 : 0.5, cursor: canSubmit ? 'pointer' : 'not-allowed' }}
            onClick={handleSubmit}
            disabled={!canSubmit}
          >
            <Plus size={14} />
            {submitting ? 'Adding…' : 'Add Draft Item'}
          </button>
          <button type="button" style={S.btnSecondary} onClick={onClose}>Cancel</button>
          <div style={{ flex: 1 }} />
          <div style={{ fontSize: 10, color: 'var(--txt-ghost)', fontFamily: 'var(--font-mono)' }}>
            <FileText size={10} style={{ verticalAlign: -1, marginRight: 4 }} />
            Cmd/Ctrl+Enter to submit
          </div>
        </div>
      </div>
    </div>
  );
}
