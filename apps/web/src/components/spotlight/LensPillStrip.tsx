'use client';

/**
 * LensPillStrip — Role-filtered pills with dynamic counts.
 * All values via CSS tokens — swaps dark/light automatically.
 */

import React from 'react';
import { useRouter } from 'next/navigation';
import type { AttentionCounts, CrewRole } from '@/lib/attention/types';
import { ROLE_PILLS } from '@/lib/attention/scoring';

interface LensPillStripProps {
  counts: AttentionCounts;
  role: CrewRole;
}

const pillStyle: React.CSSProperties = {
  height: 28, padding: '0 11px', borderRadius: 3,
  borderTop: '1px solid var(--pill-border-t)',
  borderRight: '1px solid var(--pill-border-s)',
  borderBottom: '1px solid var(--pill-border-b)',
  borderLeft: '1px solid var(--pill-border-s)',
  background: 'var(--pill-bg)',
  boxShadow: 'var(--pill-shadow)',
  fontSize: 11, color: 'var(--pill-color)',
  cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
  whiteSpace: 'nowrap', fontFamily: 'var(--font-sans)',
  transition: 'background 100ms, color 100ms, border-color 100ms',
};

const actionPillStyle: React.CSSProperties = {
  ...pillStyle,
  background: 'var(--teal)',
  color: 'var(--surface)',
  borderColor: 'var(--teal)',
};

const countBadgeStyle: React.CSSProperties = {
  fontFamily: 'var(--font-mono)',
  fontSize: 10,
  opacity: 0.8,
};

const highCountBadgeStyle: React.CSSProperties = {
  ...countBadgeStyle,
  color: 'var(--red)',
  opacity: 1,
};

export default function LensPillStrip({ counts, role }: LensPillStripProps) {
  const router = useRouter();
  const pills = ROLE_PILLS[role] || ROLE_PILLS.crew;

  return (
    <div style={{ marginTop: 20, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, flexWrap: 'wrap' }}>
      {pills.map(pill => {
        const count = pill.countKey ? counts[pill.countKey] : null;
        const isAction = !!pill.action;
        const style = isAction ? actionPillStyle : pillStyle;

        return (
          <button
            key={pill.label}
            style={style}
            onClick={() => router.push(pill.route)}
            onMouseEnter={(e) => {
              if (!isAction) {
                e.currentTarget.style.background = 'var(--pill-hover-bg)';
                e.currentTarget.style.color = 'var(--pill-hover-color)';
                e.currentTarget.style.borderColor = 'var(--pill-hover-border)';
                e.currentTarget.style.boxShadow = 'none';
              }
            }}
            onMouseLeave={(e) => {
              if (!isAction) {
                e.currentTarget.style.background = 'var(--pill-bg)';
                e.currentTarget.style.color = 'var(--pill-color)';
                e.currentTarget.style.borderTop = '1px solid var(--pill-border-t)';
                e.currentTarget.style.borderRight = '1px solid var(--pill-border-s)';
                e.currentTarget.style.borderBottom = '1px solid var(--pill-border-b)';
                e.currentTarget.style.borderLeft = '1px solid var(--pill-border-s)';
                e.currentTarget.style.boxShadow = 'var(--pill-shadow)';
              }
            }}
          >
            {pill.label}
            {count != null && count > 0 && (
              <span style={count >= 10 ? highCountBadgeStyle : countBadgeStyle}>
                · {count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
