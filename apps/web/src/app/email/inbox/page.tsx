'use client';

/**
 * Email Inbox Redirect
 *
 * Redirects to single surface with email overlay open.
 * Part of the single-URL architecture - all email UI is now in the overlay.
 */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';

export default function EmailInboxRedirect() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to single surface with openEmail flag
    router.replace('/app?openEmail=true');
  }, [router]);

  // Show loading while redirecting
  return (
    <div className="min-h-screen bg-celeste-black flex items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-celeste-text-muted" />
    </div>
  );
}
