/**
 * BriefingPage
 *
 * Server Component wrapper for the HOD Daily Briefing.
 * This is NOT a dashboard - it's an intelligent, role-based briefing
 * that surfaces what changed, what matters, and what needs action.
 */

import { Suspense } from 'react';
import BriefingContent from './BriefingContent';

// Force dynamic rendering (required for Supabase auth)
export const dynamic = 'force-dynamic';

// Loading fallback for Suspense
function BriefingLoading() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <div className="h-6 w-32 skeleton rounded" />
          <div className="h-4 w-48 skeleton rounded mt-2" />
        </div>
      </header>
      <main className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        <div className="h-32 skeleton rounded-lg" />
        <div className="h-48 skeleton rounded-lg" />
        <div className="h-32 skeleton rounded-lg" />
        <div className="h-24 skeleton rounded-lg" />
      </main>
    </div>
  );
}

export default function BriefingPage() {
  return (
    <Suspense fallback={<BriefingLoading />}>
      <BriefingContent />
    </Suspense>
  );
}
