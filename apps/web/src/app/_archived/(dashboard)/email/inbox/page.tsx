/**
 * EmailInboxPage
 *
 * Server Component wrapper for the EmailInboxView.
 * Shows unlinked email threads with "Link to..." functionality.
 */

import { Suspense } from 'react';
import { Loader2 } from 'lucide-react';
import { EmailInboxView } from '@/components/email/EmailInboxView';

// Force dynamic rendering
export const dynamic = 'force-dynamic';

// Loading fallback
function EmailInboxLoading() {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
    </div>
  );
}

export default function EmailInboxPage() {
  return (
    <div className="container mx-auto py-6 px-4">
      <Suspense fallback={<EmailInboxLoading />}>
        <EmailInboxView />
      </Suspense>
    </div>
  );
}
