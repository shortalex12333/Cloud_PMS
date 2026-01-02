/**
 * SearchPage
 * Apple Spotlight-style search interface
 */

import { Suspense } from 'react';
import SearchContent from './SearchContent';

// Force dynamic rendering (required for Supabase auth)
export const dynamic = 'force-dynamic';

// Loading fallback - matches Spotlight panel
function SearchLoading() {
  return (
    <div className="min-h-screen bg-[#1c1c1e] flex items-start justify-center pt-[18vh]">
      <div className="w-full max-w-[680px] mx-auto px-4">
        <div className="spotlight-panel h-[52px] animate-pulse" />
      </div>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<SearchLoading />}>
      <SearchContent />
    </Suspense>
  );
}
