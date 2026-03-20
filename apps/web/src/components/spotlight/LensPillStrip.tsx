'use client';

/**
 * LensPillStrip — Quick filter pills below Smart Pointers
 * All values via CSS tokens — swaps dark/light automatically.
 */

import React from 'react';
import { useRouter } from 'next/navigation';

const PILLS = [
  { label: 'Open Faults', route: '/faults' },
  { label: 'Overdue W/O', route: '/work-orders' },
  { label: 'Upcoming Tasks', route: '/work-orders' },
  { label: 'Shipment Arriving', route: '/receiving' },
  { label: 'Log HOR', route: '/hours-of-rest', action: true },
];

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

export default function LensPillStrip() {
  const router = useRouter();
  return (
    <div style={{ marginTop: 20, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, flexWrap: 'wrap' }}>
      {PILLS.map(pill => (
        <button key={pill.label} style={pillStyle}
          onClick={() => router.push(pill.route)}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'var(--pill-hover-bg)';
            e.currentTarget.style.color = 'var(--pill-hover-color)';
            e.currentTarget.style.borderColor = 'var(--pill-hover-border)';
            e.currentTarget.style.boxShadow = 'none';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'var(--pill-bg)';
            e.currentTarget.style.color = 'var(--pill-color)';
            e.currentTarget.style.borderTop = '1px solid var(--pill-border-t)';
            e.currentTarget.style.borderRight = '1px solid var(--pill-border-s)';
            e.currentTarget.style.borderBottom = '1px solid var(--pill-border-b)';
            e.currentTarget.style.borderLeft = '1px solid var(--pill-border-s)';
            e.currentTarget.style.boxShadow = 'var(--pill-shadow)';
          }}
        >{pill.label}</button>
      ))}
    </div>
  );
}
