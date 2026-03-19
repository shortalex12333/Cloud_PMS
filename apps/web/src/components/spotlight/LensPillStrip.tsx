'use client';

/**
 * LensPillStrip — Quick filter pills below Smart Pointers
 * Per elegant.html prototype. All inline styles to avoid Tailwind cascade.
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
  borderTop: '1px solid rgba(255,255,255,0.11)',
  borderRight: '1px solid rgba(255,255,255,0.07)',
  borderBottom: '1px solid rgba(255,255,255,0.04)',
  borderLeft: '1px solid rgba(255,255,255,0.07)',
  background: '#181614', fontSize: 11, color: 'rgba(255,255,255,0.55)',
  cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
  whiteSpace: 'nowrap', fontFamily: 'var(--font-sans)',
};

export default function LensPillStrip() {
  const router = useRouter();
  return (
    <div style={{ marginTop: 20, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, flexWrap: 'wrap' }}>
      {PILLS.map(pill => (
        <button key={pill.label} style={pillStyle}
          onClick={() => router.push(pill.route)}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(58,124,157,0.10)';
            e.currentTarget.style.color = '#5AABCC';
            e.currentTarget.style.borderColor = 'rgba(90,171,204,0.30)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = '#181614';
            e.currentTarget.style.color = 'rgba(255,255,255,0.55)';
            e.currentTarget.style.borderTop = '1px solid rgba(255,255,255,0.11)';
            e.currentTarget.style.borderRight = '1px solid rgba(255,255,255,0.07)';
            e.currentTarget.style.borderBottom = '1px solid rgba(255,255,255,0.04)';
            e.currentTarget.style.borderLeft = '1px solid rgba(255,255,255,0.07)';
          }}
        >{pill.label}</button>
      ))}
    </div>
  );
}
