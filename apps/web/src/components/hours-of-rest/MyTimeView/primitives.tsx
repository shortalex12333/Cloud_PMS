'use client';

import * as React from 'react';

export function Skeleton({ w = '100%', h = 16 }: { w?: string | number; h?: number }) {
  return (
    <div style={{
      width: w,
      height: h,
      background: 'var(--surface-subtle)',
      borderRadius: 'var(--radius-pill)',
      animation: 'pulse 1.5s ease-in-out infinite',
    }} />
  );
}

export function SectionCard({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border-sub)',
      borderRadius: 'var(--radius-sm)',
      overflow: 'hidden',
      marginBottom: 'var(--space-3)',
      ...style,
    }}>
      {children}
    </div>
  );
}

export function SectionHeader({ label, right }: { label: React.ReactNode; right?: React.ReactNode }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '10px 16px 8px',
      borderBottom: '1px solid var(--surface-subtle)',
    }}>
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 9,
        fontWeight: 600,
        letterSpacing: '0.14em',
        textTransform: 'uppercase' as const,
        color: 'var(--txt-ghost)',
      }}>{label}</span>
      {right}
    </div>
  );
}

export function StatusBadge({ ok, label }: { ok: boolean | null; label?: string }) {
  if (ok === null) return <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--txt-ghost)' }}>—</span>;
  return (
    <span style={{
      fontFamily: 'var(--font-mono)',
      fontSize: 9,
      fontWeight: 600,
      color: ok ? 'var(--green)' : 'var(--red)',
    }}>
      {ok ? '✓' : '⚠'} {label}
    </span>
  );
}
