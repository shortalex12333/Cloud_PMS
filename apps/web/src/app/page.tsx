'use client';

/**
 * CelesteOS Root Page
 *
 * Search-first landing. SpotlightSearch navigates to fragmented entity routes.
 * No panels, no overlays, no state-based navigation.
 */

import { Suspense } from 'react';
import SpotlightSearch from '@/components/spotlight/SpotlightSearch';

export const dynamic = 'force-dynamic';

export default function RootPage() {
  return (
    <main className="min-h-screen bg-surface-base">
      <div className="relative flex h-screen overflow-hidden">
        <div className="flex-1 flex items-start justify-center pt-[15vh]">
          <div className="w-full max-w-[var(--celeste-spotlight-width)] px-4">
            <Suspense fallback={<div className="h-14 bg-surface-hover rounded-full" />}>
              <SpotlightSearch />
            </Suspense>
          </div>
        </div>
      </div>
    </main>
  );
}
