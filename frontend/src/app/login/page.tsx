/**
 * LoginPage
 *
 * Server Component wrapper that handles dynamic rendering
 * for the client-side LoginContent component.
 */

import { Suspense } from 'react';
import LoginContent from './LoginContent';

// Force dynamic rendering (required for Supabase auth check)
export const dynamic = 'force-dynamic';

// Loading fallback for Suspense
function LoginLoading() {
  return (
    <div className="spotlight-container">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <div className="h-10 w-40 skeleton rounded mx-auto" />
          <div className="h-4 w-56 skeleton rounded mx-auto mt-2" />
        </div>
        <div className="bg-card border border-border rounded-lg shadow-lg p-8">
          <div className="space-y-6">
            <div className="h-10 skeleton rounded" />
            <div className="h-10 skeleton rounded" />
            <div className="h-10 skeleton rounded" />
          </div>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginLoading />}>
      <LoginContent />
    </Suspense>
  );
}
