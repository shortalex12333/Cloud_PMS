/**
 * DashboardPage
 *
 * Server Component wrapper that handles dynamic rendering
 * for the client-side DashboardContent component.
 */

import { Suspense } from 'react';
import DashboardContent from './DashboardContent';

// Force dynamic rendering (required for Supabase auth)
export const dynamic = 'force-dynamic';

// Loading fallback for Suspense
function DashboardLoading() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="h-8 w-32 skeleton rounded" />
              <div className="h-4 w-48 skeleton rounded mt-2" />
            </div>
          </div>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-48 skeleton rounded-lg" />
          <div className="h-48 skeleton rounded-lg" />
          <div className="h-48 skeleton rounded-lg" />
          <div className="h-48 skeleton rounded-lg" />
        </div>
      </main>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<DashboardLoading />}>
      <DashboardContent />
    </Suspense>
  );
}
