/**
 * LinkedInCallbackPage
 *
 * Server Component wrapper that handles dynamic rendering
 * for the OAuth callback client component.
 */

import { Suspense } from 'react';
import LinkedInCallbackContent from './LinkedInCallbackContent';

// Force dynamic rendering (required for OAuth callback with useSearchParams)
export const dynamic = 'force-dynamic';

// Loading fallback for Suspense
function CallbackLoading() {
  return (
    <div className="spotlight-container">
      <div className="w-full max-w-md text-center">
        <div className="bg-card border border-border rounded-lg p-8">
          <div className="h-12 w-12 mx-auto mb-4 border-4 border-primary border-t-transparent rounded-full animate-spin" />
          <h2 className="typo-title font-semibold mb-2">Loading...</h2>
        </div>
      </div>
    </div>
  );
}

export default function LinkedInCallbackPage() {
  return (
    <Suspense fallback={<CallbackLoading />}>
      <LinkedInCallbackContent />
    </Suspense>
  );
}
