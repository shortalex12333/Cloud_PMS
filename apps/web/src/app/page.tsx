'use client';

/**
 * CelesteOS Root Page — Vessel Surface
 *
 * The new home screen after the interface pivot.
 * Shows current vessel state: status rows, not a search void.
 * The topbar, sidebar, and search are provided by the AppShell wrapper.
 *
 * The orb backdrop is retained for visual continuity with the brand.
 */

import { VesselSurface } from '@/components/shell/VesselSurface';

export const dynamic = 'force-dynamic';

export default function RootPage() {
  return (
    <>
      {/* Orb backdrop — ambient brand atmosphere behind the surface */}
      <div style={{ position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none', overflow: 'hidden' }}>
        <div style={{
          position: 'absolute', borderRadius: '50%', filter: 'blur(90px)', opacity: 0.25,
          width: '50vw', height: '50vw', top: '-16vw', left: '-4vw',
          background: 'var(--orb-1)',
        }} />
        <div style={{
          position: 'absolute', borderRadius: '50%', filter: 'blur(90px)', opacity: 0.25,
          width: '32vw', height: '32vw', bottom: '-10vw', right: '-3vw',
          background: 'var(--orb-2)',
        }} />
      </div>

      {/* Vessel Surface content */}
      <VesselSurface />
    </>
  );
}
