/**
 * SearchPage
 *
 * Server Component wrapper that handles dynamic rendering
 * for the client-side SearchContent component.
 */

import { Suspense } from 'react';
import SearchContent from './SearchContent';

// Force dynamic rendering (required for Supabase auth)
export const dynamic = 'force-dynamic';

// Loading fallback for Suspense
function SearchLoading() {
  return (
    <div className="spotlight-container">
      <div className="w-full max-w-4xl">
        <div className="mb-8 text-center">
          <div className="h-8 w-32 skeleton rounded mx-auto mb-2" />
          <div className="h-4 w-64 skeleton rounded mx-auto" />
        </div>
        <div className="w-full h-12 skeleton rounded-lg" />
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
