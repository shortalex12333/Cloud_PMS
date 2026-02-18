import { Suspense } from 'react';
import AuthCallbackClient from './AuthCallbackClient';

// Force dynamic rendering - this page needs runtime access to URL params
export const dynamic = 'force-dynamic';

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-surface-base">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-celeste-blue border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-white text-lg">Loading...</p>
          </div>
        </div>
      }
    >
      <AuthCallbackClient />
    </Suspense>
  );
}
