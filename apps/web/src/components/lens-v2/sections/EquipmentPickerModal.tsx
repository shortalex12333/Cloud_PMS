'use client';

/**
 * EquipmentPickerModal — modal for picking an equipment row to link to the
 * current entity (certificate or document).
 *
 * Per doc_cert_ux_change.md:
 *   - Alphabetical list of ALL non-deleted pms_equipment rows for the yacht.
 *   - Each row uses the equipment-list card layout:
 *         @ {code} — {name}
 *         {manufacturer}      {description (truncated)}
 *   - Search filter narrows the list by code / name / manufacturer / description.
 *
 * Data flow: parent passes a loader that returns `EquipmentPickerItem[]` for
 * the yacht. This component does not hold yacht/tenant state itself — keeps
 * it testable and reusable across cert + doc lenses.
 */

import * as React from 'react';

export interface EquipmentPickerItem {
  id: string;
  code?: string | null;
  name: string;
  manufacturer?: string | null;
  description?: string | null;
}

export interface EquipmentPickerModalProps {
  open: boolean;
  onClose: () => void;
  /** Async loader returning all candidate equipment rows for the yacht. */
  loadEquipment: () => Promise<EquipmentPickerItem[]>;
  /**
   * IDs already linked to the current entity. These rows are still shown but
   * disabled (with an "Already linked" badge) to prevent duplicate inserts.
   */
  alreadyLinkedIds?: string[];
  /** Called with the chosen equipment id when the user confirms. */
  onSelect: (equipmentId: string) => void | Promise<void>;
  /** Optional: title override. Default "Link equipment". */
  title?: string;
}

function truncate(text: string | null | undefined, max: number): string {
  if (!text) return '';
  if (text.length <= max) return text;
  const cut = text.slice(0, max);
  const lastSpace = cut.lastIndexOf(' ');
  const base = lastSpace > max * 0.6 ? cut.slice(0, lastSpace) : cut;
  return `${base.trimEnd()}…`;
}

export function EquipmentPickerModal({
  open,
  onClose,
  loadEquipment,
  alreadyLinkedIds = [],
  onSelect,
  title = 'Link equipment',
}: EquipmentPickerModalProps) {
  const [items, setItems] = React.useState<EquipmentPickerItem[] | null>(null);
  const [loadError, setLoadError] = React.useState<string | null>(null);
  const [isLoading, setIsLoading] = React.useState(false);
  const [query, setQuery] = React.useState('');
  const [submitting, setSubmitting] = React.useState<string | null>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const linkedSet = React.useMemo(() => new Set(alreadyLinkedIds), [alreadyLinkedIds]);

  // Load when opened
  React.useEffect(() => {
    if (!open) return;
    setIsLoading(true);
    setLoadError(null);
    setQuery('');
    loadEquipment()
      .then((result) => {
        // Alphabetical by code then name (code may be absent)
        const sorted = [...result].sort((a, b) => {
          const ac = (a.code ?? '').toLowerCase();
          const bc = (b.code ?? '').toLowerCase();
          if (ac && bc && ac !== bc) return ac.localeCompare(bc);
          return a.name.toLowerCase().localeCompare(b.name.toLowerCase());
        });
        setItems(sorted);
      })
      .catch((err) => setLoadError(err?.message ?? 'Failed to load equipment'))
      .finally(() => setIsLoading(false));
  }, [open, loadEquipment]);

  // Autofocus search on open
  React.useEffect(() => {
    if (open) {
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  // Filter
  const filtered = React.useMemo(() => {
    if (!items) return [];
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((it) => {
      return (
        (it.code ?? '').toLowerCase().includes(q) ||
        it.name.toLowerCase().includes(q) ||
        (it.manufacturer ?? '').toLowerCase().includes(q) ||
        (it.description ?? '').toLowerCase().includes(q)
      );
    });
  }, [items, query]);

  // Close on escape
  React.useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  const handlePick = React.useCallback(
    async (item: EquipmentPickerItem) => {
      if (linkedSet.has(item.id) || submitting) return;
      setSubmitting(item.id);
      try {
        await onSelect(item.id);
        onClose();
      } catch (err) {
        setLoadError(err instanceof Error ? err.message : 'Failed to link');
      } finally {
        setSubmitting(null);
      }
    },
    [linkedSet, onSelect, onClose, submitting]
  );

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'var(--overlay-bg)',
        zIndex: 'var(--z-modal)' as unknown as number,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--space-4)',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'var(--surface-elevated)',
          border: '1px solid var(--border-sub)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-panel)',
          width: '100%',
          maxWidth: 640,
          maxHeight: '85vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <header
          style={{
            padding: 'var(--space-4) var(--space-6)',
            borderBottom: '1px solid var(--border-sub)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <h2 style={{ margin: 0, fontSize: 'var(--font-size-heading)', fontWeight: 'var(--font-weight-heading)' }}>
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="btn-icon"
            aria-label="Close"
            style={{ marginRight: -6 }}
          >
            ×
          </button>
        </header>

        {/* Search */}
        <div style={{ padding: 'var(--space-3) var(--space-6)', borderBottom: '1px solid var(--border-sub)' }}>
          <input
            ref={inputRef}
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by code, name, manufacturer…"
            className="input-field"
            style={{ width: '100%' }}
          />
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-2) 0' }}>
          {isLoading && (
            <div style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--text-secondary)' }}>
              Loading equipment…
            </div>
          )}
          {loadError && !isLoading && (
            <div
              role="alert"
              style={{
                padding: 'var(--space-4) var(--space-6)',
                color: 'var(--status-critical)',
                fontSize: 'var(--font-size-body)',
              }}
            >
              {loadError}
            </div>
          )}
          {!isLoading && !loadError && items && filtered.length === 0 && (
            <div style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--text-tertiary)' }}>
              {query ? 'No matches.' : 'No equipment to link.'}
            </div>
          )}
          {!isLoading &&
            !loadError &&
            filtered.map((eq) => {
              const alreadyLinked = linkedSet.has(eq.id);
              const isSubmitting = submitting === eq.id;
              return (
                <button
                  type="button"
                  key={eq.id}
                  onClick={() => handlePick(eq)}
                  disabled={alreadyLinked || isSubmitting || submitting !== null}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    background: 'transparent',
                    border: 0,
                    borderBottom: '1px solid var(--border-faint)',
                    padding: 'var(--space-3) var(--space-6)',
                    cursor: alreadyLinked || submitting !== null ? 'not-allowed' : 'pointer',
                    color: 'var(--text-primary)',
                    opacity: alreadyLinked ? 0.55 : 1,
                    transition: 'background var(--duration-fast) var(--ease-out)',
                  }}
                  onMouseEnter={(e) => {
                    if (!alreadyLinked && submitting === null) {
                      e.currentTarget.style.background = 'var(--surface-hover)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'transparent';
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 'var(--space-3)' }}>
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'baseline' }}>
                        {eq.code && (
                          <span
                            style={{
                              fontFamily: 'var(--font-mono)',
                              fontSize: 'var(--font-size-caption)',
                              color: 'var(--text-tertiary)',
                            }}
                          >
                            @ {eq.code}
                          </span>
                        )}
                        <span
                          style={{
                            fontSize: 'var(--font-size-body)',
                            fontWeight: 'var(--font-weight-body-strong)',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {eq.code && <span aria-hidden> — </span>}
                          {eq.name}
                        </span>
                      </div>
                      <div
                        style={{
                          display: 'flex',
                          gap: 'var(--space-4)',
                          marginTop: 2,
                          fontSize: 'var(--font-size-caption)',
                          color: 'var(--text-secondary)',
                        }}
                      >
                        {eq.manufacturer && <span style={{ minWidth: 90 }}>{eq.manufacturer}</span>}
                        {eq.description && (
                          <span
                            style={{
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}
                            title={eq.description}
                          >
                            {truncate(eq.description, 60)}
                          </span>
                        )}
                      </div>
                    </div>
                    {alreadyLinked && (
                      <span
                        style={{
                          fontSize: 'var(--font-size-caption)',
                          color: 'var(--text-tertiary)',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        Already linked
                      </span>
                    )}
                    {isSubmitting && (
                      <span
                        style={{
                          fontSize: 'var(--font-size-caption)',
                          color: 'var(--brand-interactive)',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        Linking…
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
        </div>
      </div>
    </div>
  );
}
