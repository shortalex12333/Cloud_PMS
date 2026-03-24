'use client';

/**
 * CommandPalette — replaces bland Radix DropdownMenu hamburger.
 * Settings-style backdrop blur + centered card with icon-badged items.
 */

import React from 'react';
import { X, FileText, BookOpen, Package } from 'lucide-react';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onHandoverDraft: () => void;
  onLedger: () => void;
  onLogReceiving: () => void;
  handoverCount?: number;
}

export function CommandPalette({
  isOpen, onClose, onHandoverDraft, onLedger, onLogReceiving, handoverCount,
}: CommandPaletteProps) {
  if (!isOpen) return null;

  const S = {
    overlay: {
      position: 'fixed' as const, inset: 0, zIndex: 100,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    },
    bg: {
      position: 'absolute' as const, inset: 0,
      background: 'rgba(0,0,0,0.50)',
      backdropFilter: 'blur(6px)', WebkitBackdropFilter: 'blur(6px)',
    },
    card: {
      position: 'relative' as const, width: 420, maxHeight: 480,
      background: 'var(--surface-el, var(--surface-elevated))',
      borderTop: '1px solid rgba(255,255,255,0.10)',
      borderRight: '1px solid rgba(255,255,255,0.06)',
      borderBottom: '1px solid rgba(255,255,255,0.03)',
      borderLeft: '1px solid rgba(255,255,255,0.06)',
      borderRadius: 12,
      boxShadow: '0 0 0 1px rgba(0,0,0,0.50), 0 32px 100px rgba(0,0,0,0.70)',
      overflow: 'hidden', display: 'flex', flexDirection: 'column' as const,
    },
    hdr: {
      display: 'flex', alignItems: 'center', padding: '14px 16px',
      borderBottom: '1px solid var(--border-sub)', gap: 8, flexShrink: 0,
      background: 'rgba(255,255,255,0.02)',
    },
    hdrIcon: {
      width: 24, height: 24, borderRadius: 5,
      background: 'var(--teal-bg)', display: 'flex',
      alignItems: 'center', justifyContent: 'center',
    },
    title: {
      fontSize: 12, fontWeight: 600, textTransform: 'uppercase' as const,
      letterSpacing: '0.04em', color: 'var(--txt2)', flex: 1,
    },
    close: {
      width: 28, height: 28, borderRadius: 6, border: 'none',
      background: 'none', cursor: 'pointer', display: 'flex',
      alignItems: 'center', justifyContent: 'center',
      color: 'var(--txt-ghost)',
    },
    sect: {
      fontSize: 9, fontWeight: 600, letterSpacing: '0.12em',
      textTransform: 'uppercase' as const, color: 'var(--txt-ghost)',
      padding: '12px 16px 4px',
    },
    item: {
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '10px 12px', borderRadius: 6,
      cursor: 'pointer', minHeight: 44,
      border: 'none', background: 'none', width: '100%', textAlign: 'left' as const,
      fontFamily: 'var(--font-sans)',
      transition: 'background 60ms',
    },
    icon: (bg: string, color: string) => ({
      width: 28, height: 28, borderRadius: 6,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexShrink: 0, background: bg, color,
    }),
    name: { fontSize: 13, fontWeight: 500, color: 'var(--txt)' },
    desc: { fontSize: 11, color: 'var(--txt3)', marginTop: 1 },
    badge: {
      fontSize: 10, fontWeight: 600, fontFamily: 'var(--font-mono)',
      padding: '1px 6px', borderRadius: 4,
      background: 'var(--teal-bg)', color: 'var(--mark)',
    },
    chevron: { width: 12, height: 12, color: 'var(--txt-ghost)', flexShrink: 0 },
    sep: { height: 1, background: 'var(--border-sub)', margin: '4px 12px' },
    footer: {
      display: 'flex', alignItems: 'center', gap: 4,
      padding: '8px 16px', borderTop: '1px solid var(--border-sub)', flexShrink: 0,
    },
    hint: { display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: 'var(--txt-ghost)' },
    kbd: {
      background: 'var(--surface-el, var(--surface-elevated))',
      borderRadius: 3, padding: '1px 5px', fontSize: 10,
      color: 'var(--txt3)', fontFamily: 'var(--font-mono)',
      minWidth: 18, textAlign: 'center' as const,
      border: '1px solid var(--border-sub)',
    },
    hintSep: { width: 1, height: 10, background: 'var(--border-sub)', margin: '0 8px' },
  };

  const ChevronRight = () => (
    <svg style={S.chevron} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M9 18l6-6-6-6" /></svg>
  );

  const fire = (fn: () => void) => { onClose(); fn(); };

  return (
    <div style={S.overlay} onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={S.bg} onClick={onClose} />
      <div style={S.card}>

        <div style={S.hdr}>
          <div style={S.hdrIcon}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--mark)" strokeWidth="2" strokeLinecap="round"><line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" /></svg>
          </div>
          <span style={S.title}>Quick Actions</span>
          <button style={S.close} onClick={onClose}>
            <X size={12} />
          </button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '4px 8px 12px' }}>

          <div style={S.sect}>Actions</div>

          <button style={S.item} onClick={() => fire(onHandoverDraft)}
            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = 'var(--surface-hover)'; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'none'; }}
          >
            <div style={S.icon('var(--teal-bg)', 'var(--mark)')}><FileText size={14} /></div>
            <div style={{ flex: 1 }}>
              <div style={S.name}>Handover Draft</div>
              <div style={S.desc}>Review and export your handover notes</div>
            </div>
            {(handoverCount ?? 0) > 0 && <span style={S.badge}>{handoverCount}</span>}
            <ChevronRight />
          </button>

          <button style={S.item} onClick={() => fire(onLogReceiving)}
            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = 'var(--surface-hover)'; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'none'; }}
          >
            <div style={S.icon('var(--green-bg)', 'var(--green)')}><Package size={14} /></div>
            <div style={{ flex: 1 }}>
              <div style={S.name}>Log Receiving</div>
              <div style={S.desc}>Scan or upload delivery documents</div>
            </div>
            <ChevronRight />
          </button>

          <div style={S.sep} />
          <div style={S.sect}>Views</div>

          <button style={S.item} onClick={() => fire(onLedger)}
            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = 'var(--surface-hover)'; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'none'; }}
          >
            <div style={S.icon('var(--amber-bg)', 'var(--amber)')}><BookOpen size={14} /></div>
            <div style={{ flex: 1 }}>
              <div style={S.name}>Ledger</div>
              <div style={S.desc}>Activity timeline — yours and your department</div>
            </div>
            <ChevronRight />
          </button>

        </div>

        <div style={S.footer}>
          <span style={S.hint}><kbd style={S.kbd}>↑</kbd><kbd style={S.kbd}>↓</kbd> Navigate</span>
          <div style={S.hintSep} />
          <span style={S.hint}><kbd style={S.kbd}>↵</kbd> Open</span>
          <div style={S.hintSep} />
          <span style={S.hint}><kbd style={S.kbd}>Esc</kbd> Close</span>
        </div>

      </div>
    </div>
  );
}
