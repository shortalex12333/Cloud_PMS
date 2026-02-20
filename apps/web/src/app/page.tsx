'use client';

/**
 * CelesteOS Single Surface - Root Page
 *
 * The one URL - /
 * All interaction through state-based panels, no navigation.
 *
 * Layout:
 * - SpotlightSearch: Always visible, centered (email inline beneath search bar)
 * - ContextPanel: Slides from right when context-open
 * - EmailOverlay: Full-width slide from left (portal to body)
 *
 * UX Doctrine:
 * - NO left sidebar inbox - email is inline beneath search bar only
 * - Single surface, single search bar, all content flows beneath it
 *
 * Transitions:
 * - 300ms ease-out CSS transforms
 * - Hardware accelerated with translateX
 *
 * Deep Linking (E2E Support):
 * - /?entity=fault&id=xxx - Opens fault detail view
 * - /?entity=work_order&id=xxx - Opens work order detail view
 * - /?entity=equipment&id=xxx - Opens equipment detail view
 */

import { Suspense } from 'react';
import nextDynamic from 'next/dynamic';
import { SurfaceProvider, useSurface } from '@/contexts/SurfaceContext';
import { NavigationProvider } from '@/contexts/NavigationContext';
import SpotlightSearch from '@/components/spotlight/SpotlightSearch';
import ContextPanel from './app/ContextPanel';
import { DeepLinkHandler } from './app/DeepLinkHandler';
import { AuthProvider } from '@/contexts/AuthContext';

// Dynamic import with SSR disabled for portal-based overlay
const EmailOverlay = nextDynamic(() => import('./app/EmailOverlay'), { ssr: false });

// Force dynamic rendering
export const dynamic = 'force-dynamic';

// Inner component that uses the SurfaceContext
function SurfaceContent() {
  const { emailPanel, hideEmail } = useSurface();

  return (
    <main className="min-h-screen bg-gradient-to-br from-celeste-black via-celeste-bg-tertiary to-celeste-black">
      {/* Deep Link Handler - processes URL query params for E2E testing */}
      <Suspense fallback={null}>
        <DeepLinkHandler />
      </Suspense>

      {/* Main surface container */}
      <div className="relative flex h-screen overflow-hidden">
        {/* Center - Spotlight Search (email inline beneath search bar per UX doctrine) */}
        <div className="flex-1 flex items-start justify-center pt-[15vh]">
          <div className="w-full max-w-[var(--celeste-spotlight-width)] px-4">
            <Suspense fallback={<div className="h-14 bg-celeste-bg-tertiary/50 rounded-full" />}>
              <SpotlightSearch />
            </Suspense>
          </div>
        </div>

        {/* Context Panel - slides from right */}
        <Suspense fallback={<div className="w-96 bg-celeste-bg-tertiary/50" />}>
          <ContextPanel />
        </Suspense>
      </div>

      {/* Email Overlay - full-width slide from left (portal to body) */}
      <EmailOverlay />
    </main>
  );
}

export default function RootSurface() {
  return (
    <AuthProvider>
      <SurfaceProvider>
        <NavigationProvider>
          <SurfaceContent />
        </NavigationProvider>
      </SurfaceProvider>
    </AuthProvider>
  );
}
