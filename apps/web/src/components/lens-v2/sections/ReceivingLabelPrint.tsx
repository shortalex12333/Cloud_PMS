'use client';

/**
 * ReceivingLabelPrint — Phase 6.
 *
 * Generates a PDF label sheet for accepted items. One page per line item,
 * sized to crew preference. PDF is a plain download — not sealed evidence.
 * The labels_generated ledger event fires server-side and appears in the
 * receiving single receipt's event timeline automatically.
 *
 * Visibility: only rendered when at least one item has quantity_accepted > 0.
 */

import * as React from 'react';
import { CollapsibleSection } from '../CollapsibleSection';

// ── Types ──────────────────────────────────────────────────────────────────

export interface LabelItem {
  id: string;
  description: string | null;
  quantityAccepted: number;
  location: string | null;
  partId: string | null;
}

export interface ReceivingLabelPrintProps {
  receivingId: string;
  yachtId: string;
  userId?: string;
  items: LabelItem[];
  apiBase: string;
}

// ── Size presets ───────────────────────────────────────────────────────────

type SizeKey = 'A4' | 'A5' | 'label_62' | 'label_36' | 'custom';

const SIZE_LABELS: Record<SizeKey, string> = {
  A4: 'A4',
  A5: 'A5',
  label_62: '62mm',
  label_36: '36mm',
  custom: 'Custom',
};

const LS_KEY = 'receiving_label_size';

// ── Section icon ────────────────────────────────────────────────────────────

const SECTION_ICON = (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
    <rect x="2" y="4" width="12" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.3" />
    <path d="M5 2v2M11 2v2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    <path d="M5 8h6M5 10.5h4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
  </svg>
);

// ── Component ───────────────────────────────────────────────────────────────

export function ReceivingLabelPrint({
  receivingId,
  yachtId,
  userId,
  items,
  apiBase,
}: ReceivingLabelPrintProps) {
  const acceptedItems = items.filter((i) => i.quantityAccepted > 0);
  if (acceptedItems.length === 0) return null;

  const [selectedSize, setSelectedSize] = React.useState<SizeKey>(() => {
    if (typeof window !== 'undefined') {
      return (localStorage.getItem(LS_KEY) as SizeKey | null) ?? 'A4';
    }
    return 'A4';
  });
  const [customW, setCustomW] = React.useState('100');
  const [customH, setCustomH] = React.useState('148');
  const [checkedIds, setCheckedIds] = React.useState<Set<string>>(
    () => new Set(acceptedItems.map((i) => i.id))
  );
  const [loading, setLoading] = React.useState(false);
  const [toast, setToast] = React.useState<string | null>(null);

  function persistSize(s: SizeKey) {
    setSelectedSize(s);
    if (typeof window !== 'undefined') localStorage.setItem(LS_KEY, s);
  }

  function toggleItem(id: string) {
    setCheckedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) { next.delete(id); } else { next.add(id); }
      return next;
    });
  }

  async function handleGenerate() {
    if (checkedIds.size === 0) return;
    setLoading(true);
    setToast(null);
    try {
      const params = new URLSearchParams({ yacht_id: yachtId, size: selectedSize });
      if (userId) params.set('user_id', userId);
      if (selectedSize === 'custom') {
        params.set('w', customW);
        params.set('h', customH);
      }
      params.set('item_ids', Array.from(checkedIds).join(','));

      const res = await fetch(`${apiBase}/v1/receiving/${receivingId}/labels?${params}`, {
        credentials: 'include',
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setToast((err as { detail?: string }).detail ?? 'Failed to generate labels');
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `labels_${receivingId.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      setToast('Labels downloaded — open to print.');
    } catch {
      setToast('Network error. Try again.');
    } finally {
      setLoading(false);
    }
  }

  const allChecked = checkedIds.size === acceptedItems.length;

  return (
    <CollapsibleSection
      id="sec-label-print"
      title="Print Labels"
      count={acceptedItems.length}
      icon={SECTION_ICON}
      defaultCollapsed={false}
    >
      {/* Size selector */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 16 }}>
        {(Object.keys(SIZE_LABELS) as SizeKey[]).map((key) => (
          <button
            key={key}
            onClick={() => persistSize(key)}
            style={{
              padding: '4px 10px',
              borderRadius: 4,
              border: `1px solid ${selectedSize === key ? 'var(--mark)' : 'var(--border-sub)'}`,
              background: selectedSize === key ? 'var(--mark-bg)' : 'transparent',
              color: selectedSize === key ? 'var(--mark)' : 'var(--txt2)',
              fontSize: 12,
              fontWeight: selectedSize === key ? 600 : 400,
              cursor: 'pointer',
            }}
          >
            {SIZE_LABELS[key]}
          </button>
        ))}
      </div>

      {/* Custom mm inputs */}
      {selectedSize === 'custom' && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center' }}>
          <label style={{ fontSize: 12, color: 'var(--txt2)' }}>W mm</label>
          <input
            type="number"
            value={customW}
            onChange={(e) => setCustomW(e.target.value)}
            style={{ width: 60, padding: '3px 6px', borderRadius: 4, border: '1px solid var(--border-sub)', fontSize: 12, background: 'var(--surface-elevated)', color: 'var(--txt)' }}
          />
          <label style={{ fontSize: 12, color: 'var(--txt2)' }}>H mm</label>
          <input
            type="number"
            value={customH}
            onChange={(e) => setCustomH(e.target.value)}
            style={{ width: 60, padding: '3px 6px', borderRadius: 4, border: '1px solid var(--border-sub)', fontSize: 12, background: 'var(--surface-elevated)', color: 'var(--txt)' }}
          />
        </div>
      )}

      {/* Select all row */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '6px 0',
          borderBottom: '1px solid var(--border-faint)',
          marginBottom: 4,
        }}
      >
        <input
          type="checkbox"
          checked={allChecked}
          onChange={() => {
            if (allChecked) { setCheckedIds(new Set()); }
            else { setCheckedIds(new Set(acceptedItems.map((i) => i.id))); }
          }}
          style={{ accentColor: 'var(--mark)', width: 14, height: 14 }}
        />
        <span style={{ fontSize: 11, color: 'var(--txt-ghost)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          {allChecked ? 'Deselect all' : 'Select all'}
        </span>
      </div>

      {/* Item list */}
      <div role="list" style={{ display: 'grid', rowGap: 2, marginBottom: 16 }}>
        {acceptedItems.map((item) => (
          <div
            key={item.id}
            role="listitem"
            onClick={() => toggleItem(item.id)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '8px 4px',
              borderBottom: '1px solid var(--border-faint)',
              cursor: 'pointer',
            }}
          >
            <input
              type="checkbox"
              checked={checkedIds.has(item.id)}
              onChange={() => toggleItem(item.id)}
              onClick={(e) => e.stopPropagation()}
              style={{ accentColor: 'var(--mark)', width: 14, height: 14, flexShrink: 0 }}
            />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 500,
                  color: 'var(--txt)',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {item.description ?? 'Item'}
              </div>
              <div style={{ fontSize: 11.5, color: 'var(--txt3)', marginTop: 1 }}>
                ×{item.quantityAccepted}
                {item.location ? (
                  <> · <span style={{ fontFamily: 'var(--font-mono)' }}>{item.location}</span></>
                ) : (
                  <> · <span style={{ color: 'var(--txt-ghost)' }}>Unassigned</span></>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Generate button */}
      <button
        onClick={handleGenerate}
        disabled={loading || checkedIds.size === 0}
        style={{
          padding: '8px 20px',
          borderRadius: 6,
          border: '1px solid var(--mark)',
          background: 'var(--mark)',
          color: '#fff',
          fontSize: 13,
          fontWeight: 600,
          cursor: loading || checkedIds.size === 0 ? 'not-allowed' : 'pointer',
          opacity: loading || checkedIds.size === 0 ? 0.5 : 1,
        }}
      >
        {loading ? 'Generating…' : `Generate Labels (${checkedIds.size})`}
      </button>

      {/* Toast feedback */}
      {toast && (
        <div
          style={{
            marginTop: 10,
            padding: '6px 12px',
            borderRadius: 4,
            background: 'var(--surface-elevated)',
            border: '1px solid var(--border-sub)',
            fontSize: 12,
            color: 'var(--txt2)',
          }}
        >
          {toast}
        </div>
      )}
    </CollapsibleSection>
  );
}
