'use client';

import * as React from 'react';
import type { SignalRelatedItem } from '@/hooks/useSignalRelated';

// ─── Per-type icons (14×14, stroke only) — from show-related.html prototype ─
const ICON_STYLE: React.CSSProperties = { width: 14, height: 14, flexShrink: 0, color: 'var(--txt3)' };

function EntityIcon({ type }: { type: string }) {
  switch (type) {
    case 'work_order':
      return <svg style={ICON_STYLE} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6"><rect x="4" y="2" width="8" height="2" rx="1" /><rect x="3" y="3.5" width="10" height="10.5" rx="1.5" /><path d="M5.5 8.5l2 2 3.5-3.5" /></svg>;
    case 'equipment':
      return <svg style={ICON_STYLE} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6"><circle cx="8" cy="8" r="2.5" /><path d="M13 9.5a1.1 1.1 0 00.22 1.22l.04.04a1.33 1.33 0 11-1.89 1.89l-.04-.04A1.1 1.1 0 0010 13v.17a1.33 1.33 0 01-2.67 0V13A1.1 1.1 0 006 11.63a1.1 1.1 0 00-1.22.22l-.04.04a1.33 1.33 0 11-1.89-1.89l.04-.04A1.1 1.1 0 003 8.73 1.1 1.1 0 001.83 8 1.33 1.33 0 011.83 5.33H2A1.1 1.1 0 003.37 6a1.1 1.1 0 00-.22-1.22l-.04-.04a1.33 1.33 0 111.89-1.89l.04.04A1.1 1.1 0 006 3.17 1.1 1.1 0 007.33 2a1.33 1.33 0 012.67 0v.06A1.1 1.1 0 0011.22 3a1.1 1.1 0 001.22-.22l.04-.04a1.33 1.33 0 111.89 1.89l-.04.04A1.1 1.1 0 0013 6a1.1 1.1 0 001 1.01h.17a1.33 1.33 0 010 2.67H14a1.1 1.1 0 00-1 .82z" /></svg>;
    case 'fault':
      return <svg style={ICON_STYLE} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M8 3L14 13H2L8 3Z" /><path d="M8 7v2.5M8 11.5v.5" /></svg>;
    case 'part':
    case 'inventory':
    case 'shopping_item':
      return <svg style={ICON_STYLE} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6"><rect x="2" y="6" width="12" height="8" rx="1" /><path d="M5 6V4.5a3 3 0 016 0V6" /></svg>;
    case 'document':
    case 'manual':
      return <svg style={ICON_STYLE} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6"><rect x="3" y="2" width="10" height="12" rx="1.5" /><path d="M6 6h4M6 9h2.5" /></svg>;
    case 'certificate':
      return <svg style={ICON_STYLE} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M8 2L13.5 4.5v4c0 3-2.5 4.8-5.5 5.5C3 13.3 2.5 11.5 2.5 8.5V4.5L8 2z" /></svg>;
    case 'email':
      return <svg style={ICON_STYLE} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6"><rect x="2" y="3.5" width="12" height="9" rx="1.5" /><path d="M2 5l6 4 6-4" /></svg>;
    case 'handover_item':
    case 'handover_export':
      return <svg style={ICON_STYLE} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M4 2h8v12H4z" /><path d="M6 5h4M6 7.5h4M6 10h2" /></svg>;
    case 'receiving':
    case 'purchase_order':
      return <svg style={ICON_STYLE} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6"><rect x="2" y="4" width="12" height="10" rx="1.5" /><path d="M5 4V2.5a1 1 0 011-1h4a1 1 0 011 1V4" /><path d="M8 7v4M6 9h4" /></svg>;
    default:
      return <svg style={ICON_STYLE} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6"><circle cx="8" cy="8" r="6" /><path d="M8 5v3l2 2" /></svg>;
  }
}

// ─── Row button style ────────────────────────────────────────────────────────
const ROW_STYLE_BASE: React.CSSProperties = {
  width: '100%',
  textAlign: 'left',
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
  padding: '8px 12px',
  cursor: 'pointer',
  minHeight: '44px',
  transition: 'background 60ms',
  background: 'none',
};

// ─── Staged progress labels ─────────────────────────────────────────────────
const STAGES = [
  { label: 'Extracting entity\u2026', at: 0 },
  { label: 'Generating embedding\u2026', at: 800 },
  { label: 'Searching entities\u2026', at: 3500 },
  { label: 'Ranking results\u2026', at: 8000 },
];

function useStagedProgress(loading: boolean) {
  const [stage, setStage] = React.useState(0);

  React.useEffect(() => {
    if (!loading) {
      setStage(0);
      return;
    }

    const timers: ReturnType<typeof setTimeout>[] = [];
    for (let i = 1; i < STAGES.length; i++) {
      timers.push(setTimeout(() => setStage(i), STAGES[i].at));
    }
    return () => timers.forEach(clearTimeout);
  }, [loading]);

  return STAGES[stage].label;
}

// ─── Term highlighting ──────────────────────────────────────────────────────
// Extract significant words from the source entity's text, then wrap matches
// in result titles with <mark> — brand teal + weight 600, no background.
const STOP_WORDS = new Set([
  'the','a','an','and','or','of','in','on','at','to','for','is','are','was',
  'were','be','been','with','from','by','as','this','that','it','its','has',
  'have','had','not','but','if','no','all','any','can','do','does','did',
  'will','would','should','could','may','status','type','ref','supplier',
  'true','false','null','draft','candidate',
]);

function extractTerms(entityText: string): string[] {
  if (!entityText) return [];
  return [...new Set(
    entityText
      .replace(/[;:,.()\[\]{}]/g, ' ')
      .split(/\s+/)
      .filter(w => w.length >= 3 && !STOP_WORDS.has(w.toLowerCase()))
      .map(w => w.toLowerCase())
  )];
}

const MARK_STYLE: React.CSSProperties = {
  background: 'none',
  color: 'var(--mark)',
  fontWeight: 600,
};

function highlightTerms(text: string, terms: string[]): React.ReactNode {
  if (!terms.length || !text) return text;
  // Build regex matching any term (word-boundary, case-insensitive)
  const escaped = terms.map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const re = new RegExp(`(${escaped.join('|')})`, 'gi');
  const parts = text.split(re);
  if (parts.length === 1) return text;
  return parts.map((part, i) =>
    i % 2 === 1
      ? <mark key={i} style={MARK_STYLE}>{part}</mark>
      : part
  );
}

interface RelatedDrawerProps {
  onNavigate: (entityType: string, entityId: string) => void;
  /** Signal-discovered items */
  signalItems?: SignalRelatedItem[];
  /** True while the signal fetch is in-flight */
  signalLoading?: boolean;
  /** Source entity's serialized text — used to highlight matching terms */
  entityText?: string;
}

export function RelatedDrawer({
  onNavigate,
  signalItems,
  signalLoading,
  entityText,
}: RelatedDrawerProps) {
  const items = signalItems ?? [];
  const loading = signalLoading ?? false;
  const stageLabel = useStagedProgress(loading);
  const terms = React.useMemo(() => extractTerms(entityText ?? ''), [entityText]);

  // Empty state: no items and not loading
  if (!loading && items.length === 0) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }}>
        <p style={{ fontSize: '13px', color: 'var(--txt2)' }}>No related items found.</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '12px 12px 16px', flex: 1, overflowY: 'auto', background: 'var(--surface-base)' }}>
      <section
        data-testid="signal-also-related"
        style={{
          background: 'var(--surface)',
          borderTop: '1px solid rgba(255,255,255,0.09)',
          borderRight: '1px solid rgba(255,255,255,0.05)',
          borderBottom: '1px solid rgba(255,255,255,0.03)',
          borderLeft: '1px solid rgba(255,255,255,0.05)',
          borderRadius: '4px',
          overflow: 'hidden',
          marginBottom: '6px',
        }}
      >
        <div style={{ fontSize: '9px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--txt)', padding: '8px 12px 4px' }}>
          Related
          {!loading && (
            <span style={{ fontFamily: "'SF Mono', 'Fira Code', 'Courier New', monospace", fontWeight: 400, marginLeft: '4px' }}>{items.length}</span>
          )}
        </div>
        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px' }}>
            <div style={{ width: '12px', height: '12px', border: '1.5px solid var(--border-sub)', borderTopColor: 'var(--txt3)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
            <span data-testid="signal-stage-label" style={{ fontSize: '11px', color: 'var(--txt3)', fontFamily: "'SF Mono', 'Fira Code', 'Courier New', monospace" }}>{stageLabel}</span>
          </div>
        ) : (
          <div>
            {items.map((item, idx) => (
              <button
                key={item.entity_id}
                type="button"
                onClick={() => onNavigate(item.entity_type, item.entity_id)}
                data-testid={`signal-item-${item.entity_type}-${item.entity_id}`}
                style={{
                  ...ROW_STYLE_BASE,
                  borderTop: idx > 0 ? '1px solid rgba(255,255,255,0.04)' : 'none',
                  border: idx > 0 ? undefined : 'none',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'none'; }}
              >
                <EntityIcon type={item.entity_type} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: '13px', fontWeight: 500, color: 'var(--txt)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', lineHeight: 1.4 }}>
                    {highlightTerms(item.title, terms)}
                  </div>
                  <div style={{ fontSize: '10.5px', color: 'var(--txt2)', fontFamily: "'SF Mono', 'Fira Code', 'Courier New', monospace", letterSpacing: '0.03em', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', marginTop: '1px', textTransform: 'uppercase' }}>
                    <span>{item.entity_type.replace(/_/g, ' ')}</span>{item.subtitle ? <><span> · </span><span>{item.subtitle}</span></> : null}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </section>

    </div>
  );
}
