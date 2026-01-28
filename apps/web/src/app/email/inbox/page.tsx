'use client';

/**
 * Email Inbox Page
 *
 * Outlook-style three-column email interface:
 * - Left: Thread list with search
 * - Center: Selected email body (full HTML render)
 * - Right: Attachments
 */

import { Suspense } from 'react';
import { Loader2 } from 'lucide-react';
import EmailSurface from '@/components/email/EmailSurface';
import { AuthProvider } from '@/contexts/AuthContext';

// Loading fallback
function EmailInboxLoading() {
  return (
    <div className="min-h-screen bg-[#1c1c1e] flex items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-[#98989f]" />
    </div>
  );
}

export default function EmailInboxPage() {
  return (
    <AuthProvider>
      <div className="min-h-screen bg-[#1c1c1e]">
        <Suspense fallback={<EmailInboxLoading />}>
          <EmailSurface />
        </Suspense>
      </div>
    </AuthProvider>
  );
}
