/**
 * SettingsPage
 *
 * Server Component wrapper that handles dynamic rendering
 * for the client-side SettingsContent component.
 */

import { Suspense } from 'react';
import SettingsContent from './SettingsContent';

// Force dynamic rendering (required for useSearchParams and Supabase)
export const dynamic = 'force-dynamic';

// Loading fallback for Suspense
function SettingsLoading() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="h-8 w-32 skeleton rounded" />
              <div className="h-4 w-48 skeleton rounded mt-2" />
            </div>
          </div>
        </div>
      </header>
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="h-64 skeleton rounded-lg" />
      </main>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <Suspense fallback={<SettingsLoading />}>
      <SettingsContent />
    </Suspense>
  );
}
