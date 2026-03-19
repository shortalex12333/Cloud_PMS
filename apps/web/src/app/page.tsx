'use client';

/**
 * CelesteOS Root Page
 *
 * Search-first landing. Matches elegant.html prototype exactly:
 * - Fixed orb backdrop (3 teal radial-gradient orbs, blur 90px, opacity 0.5)
 * - Glass topbar (40px, brand "CELESTE", vessel name, role badge)
 * - Stage container centered at 14vh, 600px max-width
 * - All inline styles to avoid Tailwind cascade / sub-agent overwrites
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
      <div style={{ position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none', overflow: 'hidden', background: 'var(--surface-base)' }}>
        {/* Orb 1 — top-left, largest */}
        <div style={{
          position: 'absolute', borderRadius: '50%', filter: 'blur(90px)', opacity: 0.5,
          width: '60vw', height: '60vw', top: '-20vw', left: '-8vw',
          background: 'radial-gradient(circle, rgba(58,124,157,0.50) 0%, transparent 70%)',
        }} />
        {/* Orb 2 — bottom-right */}
        <div style={{
          position: 'absolute', borderRadius: '50%', filter: 'blur(90px)', opacity: 0.5,
          width: '45vw', height: '45vw', bottom: '-12vw', right: '-5vw',
          background: 'radial-gradient(circle, rgba(30,90,130,0.38) 0%, transparent 70%)',
        }} />
        {/* Orb 3 — center */}
        <div style={{
          position: 'absolute', borderRadius: '50%', filter: 'blur(90px)', opacity: 0.5,
          width: '35vw', height: '35vw', top: '45%', left: '50%', transform: 'translate(-50%,-50%)',
          background: 'radial-gradient(circle, rgba(20,60,100,0.22) 0%, transparent 70%)',
        }} />
      </div>

      {/* ── App Shell ── */}
      <div style={{ position: 'relative', zIndex: 1, display: 'flex', flexDirection: 'column', height: '100vh' }}>

        {/* ── Top Bar ── */}
        <header style={{
          height: 40, flexShrink: 0,
          display: 'flex', alignItems: 'center', padding: '0 20px', gap: 8,
          borderBottom: '1px solid var(--border-faint)',
          background: 'rgba(12,11,10,0.70)',
          backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)',
        }}>
          <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.16em', textTransform: 'uppercase', color: '#4A9EC0' }}>
            Celeste
          </div>
          <div style={{ width: 1, height: 12, background: 'var(--border-sub)', margin: '0 4px' }} />
          <div style={{ fontSize: 11, color: 'var(--txt3)' }}>
            <em style={{ fontStyle: 'normal', color: 'rgba(74,158,192,0.80)' }}>SY {vesselName}</em>
          </div>
          <div style={{ flex: 1 }} />
          <div style={{
            fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase',
            color: 'var(--txt-ghost)',
            background: 'var(--surface-el)',
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
