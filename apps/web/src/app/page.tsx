'use client';

/**
 * CelesteOS Root Page
 *
 * Search-first landing. All visual values via CSS tokens in tokens.css.
 * Dark/light swap is automatic — tokens change, inline styles follow.
 */

import { Suspense } from 'react';
import SpotlightSearch from '@/components/spotlight/SpotlightSearch';
import { useAuth } from '@/hooks/useAuth';

export const dynamic = 'force-dynamic';

export default function RootPage() {
  const { user } = useAuth();

  const vesselName = user?.yachtName || 'Vessel';
  const roleName = user?.role
    ? user.role.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    : 'Member';

  return (
    <main style={{ fontFamily: 'var(--font-sans)', background: 'var(--surface-base)', color: 'var(--txt)', height: '100vh', overflow: 'hidden', display: 'flex', flexDirection: 'column', fontSize: 13, lineHeight: 1.5, WebkitFontSmoothing: 'antialiased' }}>

      {/* ── Orb Backdrop ── */}
      <div style={{ position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none', overflow: 'hidden', background: 'var(--backdrop-fill)' }}>
        <div style={{
          position: 'absolute', borderRadius: '50%', filter: 'blur(90px)', opacity: 0.5,
          width: '60vw', height: '60vw', top: '-20vw', left: '-8vw',
          background: 'var(--orb-1)',
        }} />
        <div style={{
          position: 'absolute', borderRadius: '50%', filter: 'blur(90px)', opacity: 0.5,
          width: '45vw', height: '45vw', bottom: '-12vw', right: '-5vw',
          background: 'var(--orb-2)',
        }} />
        <div style={{
          position: 'absolute', borderRadius: '50%', filter: 'blur(90px)', opacity: 0.5,
          width: '35vw', height: '35vw', top: '45%', left: '50%', transform: 'translate(-50%,-50%)',
          background: 'var(--orb-3)',
        }} />
      </div>

      {/* ── App Shell ── */}
      <div style={{ position: 'relative', zIndex: 1, display: 'flex', flexDirection: 'column', height: '100vh' }}>

        {/* ── Top Bar ── */}
        <header style={{
          height: 40, flexShrink: 0,
          display: 'flex', alignItems: 'center', padding: '0 20px', gap: 8,
          borderBottom: '1px solid var(--border-faint)',
          background: 'var(--topbar-bg)',
          backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)',
        }}>
          <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.16em', textTransform: 'uppercase', color: 'var(--topbar-brand-color)' }}>
            Celeste
          </div>
          <div style={{ width: 1, height: 12, background: 'var(--border-sub)', margin: '0 4px' }} />
          <div style={{ fontSize: 11, color: 'var(--txt3)' }}>
            <em style={{ fontStyle: 'normal', color: 'var(--topbar-vessel-em)' }}>SY {vesselName}</em>
          </div>
          <div style={{ flex: 1 }} />
          <div style={{
            fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase',
            color: 'var(--txt-ghost)',
            background: 'var(--topbar-role-bg)',
            border: '1px solid var(--border-sub)',
            borderRadius: 3, padding: '2px 7px',
          }}>
            {roleName}
          </div>
        </header>

        {/* ── Stage ── */}
        <div style={{
          flex: 1, display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'flex-start',
          paddingTop: '14vh',
          overflowY: 'auto',
        }}>
          <div style={{ width: '100%', maxWidth: 600, padding: '0 20px' }}>
            <Suspense fallback={<div style={{ height: 56, background: 'var(--surface-hover)', borderRadius: 4 }} />}>
              <SpotlightSearch />
            </Suspense>
          </div>
        </div>

      </div>
    </main>
  );
}
