'use client';

/**
 * CelesteOS Single Surface
 *
 * The one URL - /app
 * All interaction through state-based panels, no navigation.
 *
 * Layout:
 * - SpotlightSearch: Always visible, centered
 * - EmailPanel: Slides from left when email-present
 * - ContextPanel: Slides from right when context-open
 *
 * Transitions:
 * - 300ms ease-out CSS transforms
 * - Hardware accelerated with translateX
 */

import { Suspense } from 'react';
import { SurfaceProvider, useSurface } from '@/contexts/SurfaceContext';
import SpotlightSearch from '@/components/spotlight/SpotlightSearch';
import EmailPanel from './EmailPanel';
import ContextPanel from './ContextPanel';
import { AuthProvider } from '@/contexts/AuthContext';

// Inner component that uses the SurfaceContext
function SurfaceContent() {
  const { showEmail } = useSurface();

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Main surface container */}
      <div className="relative flex h-screen overflow-hidden">
        {/* Email Panel - slides from left */}
        <Suspense fallback={<div className="w-96 bg-gray-800/50" />}>
          <EmailPanel />
        </Suspense>

        {/* Center - Spotlight Search */}
        <div className="flex-1 flex items-start justify-center pt-[15vh]">
          <div className="w-full max-w-2xl px-4">
            <Suspense fallback={<div className="h-14 bg-gray-800/50 rounded-2xl" />}>
              <SpotlightSearch onEmailClick={() => showEmail()} />
            </Suspense>
          </div>
        </div>

        {/* Context Panel - slides from right */}
        <Suspense fallback={<div className="w-96 bg-gray-800/50" />}>
          <ContextPanel />
        </Suspense>
      </div>
    </main>
  );
}

export default function AppSurface() {
  return (
    <AuthProvider>
      <SurfaceProvider>
        <SurfaceContent />
      </SurfaceProvider>
    </AuthProvider>
  );
}
