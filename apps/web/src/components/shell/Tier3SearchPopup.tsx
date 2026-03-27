'use client';

/**
 * Tier3SearchPopup — Phase 2 of the Interface Pivot
 *
 * Inline relational search modal for cross-domain entity linking.
 * Triggered when a creation action requires linking an entity from
 * another domain (e.g., Create Work Order → Link Part).
 *
 * This is a PRE-STEP before the standard ActionPopup mutation ritual.
 * It does not modify data — it resolves which entity to link,
 * then passes prefill_fields to the creation form.
 *
 * Extends the existing L1/L2 popup pattern from popup-journeys.html
 * with a search step scoped to a single target domain.
 *
 * Spec: celeste-interface-pivot-spec.pdf §02 (Tier 3)
 * Prototype: vessel-surface-v2.html (visual reference only)
 */

import * as React from 'react';
import { Search, X, ExternalLink, Plus } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';

/* ─────────────────────────────────────────────
   TYPES
   ───────────────────────────────────────────── */

export interface Tier3Result {
  id: string;
  ref: string;
  display_name: string;
  meta: string;
  status_display?: string;
  status_level?: 'critical' | 'warning' | 'ok';
  addable: boolean;
  prefill_fields: Record<string, unknown>;
}

interface Tier3SearchPopupProps {
  /** Whether the popup is open */
  open: boolean;
  /** The entity type being created (e.g., "Work Order") */
  creatingType: string;
  /** The target domain to search (e.g., "parts") */
  targetDomain: string;
  /** Human-readable target label (e.g., "Part") */
  targetLabel: string;
  /** Called when a result is selected — returns prefill_fields */
  onSelect: (result: Tier3Result) => void;
  /** Called when user skips (no link) */
  onSkip: () => void;
  /** Called when popup is closed */
  onClose: () => void;
  /** API fetch function for search results */
  fetchResults: (query: string) => Promise<Tier3Result[]>;
}

export function Tier3SearchPopup({
  open,
  creatingType,
  targetDomain,
  targetLabel,
  onSelect,
  onSkip,
  onClose,
  fetchResults,
}: Tier3SearchPopupProps) {
  const [query, setQuery] = React.useState('');
  const [results, setResults] = React.useState<Tier3Result[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [focusedIndex, setFocusedIndex] = React.useState(0);
  const inputRef = React.useRef<HTMLInputElement>(null);

  // Focus input on open
  React.useEffect(() => {
    if (open) {
      setQuery('');
      setResults([]);
      setFocusedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [open]);

  // Debounced search — 250ms
  React.useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await fetchResults(query);
        setResults(res);
        setFocusedIndex(0);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [query, fetchResults]);

  // Keyboard navigation
  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setFocusedIndex((i) => Math.min(i + 1, results.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setFocusedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === 'Enter' && results[focusedIndex]?.addable) {
        e.preventDefault();
        onSelect(results[focusedIndex]);
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    },
    [results, focusedIndex, onSelect, onClose]
  );

  if (!open) return null;

  const statusColor = (level?: string) =>
    level === 'critical' ? 'var(--red)'
    : level === 'warning' ? 'var(--amber)'
    : level === 'ok' ? 'var(--green)'
    : 'var(--txt-ghost)';

  return (
    <>
      {/* Overlay */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 500,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--overlay-bg)',
          backdropFilter: 'blur(6px)',
          WebkitBackdropFilter: 'blur(6px)',
        }}
      >
        {/* Modal */}
        <div
          onClick={(e) => e.stopPropagation()}
          onKeyDown={handleKeyDown}
          style={{
            width: 500,
            background: 'var(--surface-el)',
            borderTop: '1px solid var(--border-top)',
            borderRight: '1px solid var(--border-side)',
            borderBottom: '1px solid var(--border-bottom)',
            borderLeft: '1px solid var(--border-side)',
            borderRadius: 6,
            boxShadow: 'var(--shadow-panel)',
            overflow: 'hidden',
          }}
        >
          {/* Header */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '11px 14px 9px',
              borderBottom: '1px solid var(--border-sub)',
            }}
          >
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--txt)', flex: 1 }}>
              Creating {creatingType}
            </span>
            <span
              style={{
                fontSize: 9,
                fontWeight: 600,
                color: 'var(--mark)',
                background: 'var(--teal-bg)',
                border: '1px solid var(--mark-hover)',
                borderRadius: 3,
                padding: '1px 6px',
              }}
            >
              + Link {targetLabel}
            </span>
            <button
              onClick={onClose}
              style={{
                width: 24,
                height: 24,
                borderRadius: 3,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--txt3)',
                cursor: 'pointer',
                background: 'transparent',
                border: 'none',
              }}
            >
              <X style={{ width: 12, height: 12 }} />
            </button>
          </div>

          {/* Search input */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 14px',
              borderBottom: '1px solid var(--border-faint)',
            }}
          >
            <Search style={{ width: 13, height: 13, color: 'var(--txt-ghost)', flexShrink: 0 }} />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={`Search ${targetDomain}\u2026`}
              style={{
                flex: 1,
                fontSize: 13,
                color: 'var(--txt)',
                background: 'transparent',
                border: 'none',
                outline: 'none',
                caretColor: 'var(--mark)',
              }}
            />
            {loading && (
              <div
                style={{
                  width: 14,
                  height: 14,
                  border: '2px solid var(--border-sub)',
                  borderTopColor: 'var(--mark)',
                  borderRadius: '50%',
                  animation: 'spin 0.6s linear infinite',
                }}
              />
            )}
          </div>

          {/* Results */}
          <div style={{ maxHeight: 300, overflowY: 'auto' }}>
            {results.length === 0 && query.trim() && !loading && (
              <div
                style={{
                  padding: '20px 14px',
                  textAlign: 'center',
                  color: 'var(--txt-ghost)',
                  fontSize: 12,
                }}
              >
                No {targetDomain} found
              </div>
            )}

            {results.length === 0 && !query.trim() && (
              <div
                style={{
                  padding: '20px 14px',
                  textAlign: 'center',
                  color: 'var(--txt-ghost)',
                  fontSize: 11,
                }}
              >
                Type to search {targetDomain}
              </div>
            )}

            {results.map((result, i) => (
              <div
                key={result.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '8px 14px',
                  borderTop: i > 0 ? '1px solid var(--border-faint)' : undefined,
                  background: i === focusedIndex ? 'var(--surface-hover)' : 'transparent',
                  cursor: result.addable ? 'pointer' : 'not-allowed',
                  opacity: result.addable ? 1 : 0.4,
                  transition: 'background 60ms',
                }}
                onClick={() => result.addable && onSelect(result)}
                onMouseEnter={() => setFocusedIndex(i)}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--txt)' }}>
                    <span style={{ color: 'var(--mark)', fontSize: 11 }}>{result.ref}</span>{' '}
                    {result.display_name}
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--txt3)', fontFamily: 'var(--font-mono, ui-monospace, monospace)', marginTop: 1 }}>
                    {result.meta}
                  </div>
                </div>

                {result.status_display && (
                  <span style={{ fontSize: 10, color: statusColor(result.status_level), fontWeight: 500, flexShrink: 0 }}>
                    {result.status_display}
                  </span>
                )}

                {result.addable && (
                  <button
                    onClick={(e) => { e.stopPropagation(); onSelect(result); }}
                    style={{
                      height: 22,
                      padding: '0 8px',
                      borderRadius: 3,
                      background: 'var(--teal-bg)',
                      border: '1px solid var(--mark-hover)',
                      fontSize: 10,
                      fontWeight: 500,
                      color: 'var(--mark)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 3,
                      cursor: 'pointer',
                      flexShrink: 0,
                    }}
                  >
                    <Plus style={{ width: 9, height: 9 }} />
                    Add
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* Footer — keyboard hints + skip */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '8px 14px',
              borderTop: '1px solid var(--border-sub)',
              background: 'var(--surface-base)',
            }}
          >
            <div style={{ display: 'flex', gap: 10, fontSize: 9, color: 'var(--txt-ghost)', fontFamily: 'var(--font-mono, ui-monospace, monospace)' }}>
              <span>\u2191\u2193 navigate</span>
              <span>\u21B5 add</span>
              <span>esc close</span>
            </div>
            <button
              onClick={onSkip}
              style={{
                fontSize: 10,
                color: 'var(--txt3)',
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                textDecoration: 'underline',
                textUnderlineOffset: 2,
              }}
            >
              Skip \u2014 no link
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
