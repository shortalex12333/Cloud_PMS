/**
 * Email Search Page
 *
 * Dark-themed email search interface with Spotlight-inspired design.
 * Shows all email threads with search functionality and click-on-demand rendering.
 */

import { Suspense } from 'react';
import { Loader2 } from 'lucide-react';
import EmailSearchView from '@/components/email/_legacy/EmailSearchView';

// Force dynamic rendering
export const dynamic = 'force-dynamic';

// Loading fallback
function EmailSearchLoading() {
  return (
    <div className="min-h-screen bg-[#1c1c1e] flex items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-[#98989f]" />
    </div>
  );
}

export default function EmailSearchPage() {
  return (
    <div className="min-h-screen bg-[#1c1c1e]">
      <Suspense fallback={<EmailSearchLoading />}>
        <EmailSearchView />
      </Suspense>
    </div>
  );
}
