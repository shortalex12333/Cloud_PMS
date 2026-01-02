'use client';

/**
 * SearchContent
 * Pure Apple Spotlight-style search interface
 * No branding, no navigation - just search
 */

import { Suspense } from 'react';
import { withAuth } from '@/components/withAuth';
import { SpotlightSearch } from '@/components/spotlight';

function SearchContent() {
  return (
    <div className="min-h-screen bg-[#1c1c1e] flex items-start justify-center pt-[18vh]">
      {/* Pure Spotlight - no branding, no distractions */}
      <Suspense
        fallback={
          <div className="w-full max-w-[680px] mx-auto px-4">
            <div className="spotlight-panel h-[52px]" />
          </div>
        }
      >
        <div className="w-full px-4">
          <SpotlightSearch />
        </div>
      </Suspense>
    </div>
  );
}

// Export with authentication protection
export default withAuth(SearchContent);
