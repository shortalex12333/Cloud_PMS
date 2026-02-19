'use client';

/**
 * CelesteOS Single Surface
 *
 * The one URL - /app
 * All interaction through state-based panels, no navigation.
 *
 * Layout:
 * - SpotlightSearch: Always visible, centered (email inline beneath search bar)
 * - ContextPanel: Slides from right when context-open
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
 * - /app?entity=fault&id=xxx - Opens fault detail view
 * - /app?entity=work_order&id=xxx - Opens work order detail view
 * - /app?entity=equipment&id=xxx - Opens equipment detail view
 */

import { Suspense } from 'react';
import { SurfaceProvider } from '@/contexts/SurfaceContext';
import { NavigationProvider } from '@/contexts/NavigationContext';
import SpotlightSearch from '@/components/spotlight/SpotlightSearch';
import ContextPanel from './ContextPanel';
import DeepLinkHandler from './DeepLinkHandler';
import EmailOverlay from './EmailOverlay';
import { AuthProvider } from '@/contexts/AuthContext';

// Inner component that uses the SurfaceContext
function SurfaceContent() {
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
          <div className="w-full max-w-2xl px-4">
            <Suspense fallback={<div className="h-14 bg-celeste-bg-tertiary/50 rounded-lg" />}>
              <SpotlightSearch />
            </Suspense>
          </div>
        </div>

        {/* Context Panel - slides from right */}
        <Suspense fallback={<div className="w-96 bg-celeste-bg-tertiary/50" />}>
          <ContextPanel />
        </Suspense>

        {/* Email Overlay - full-width slide-in from left */}
        <Suspense fallback={null}>
          <EmailOverlay />
        </Suspense>

      </div>
    </main>
  );
}

export default function AppSurface() {
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
