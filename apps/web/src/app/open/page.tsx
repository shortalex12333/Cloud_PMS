'use client';

/**
 * /open - Link Token Resolution Page
 *
 * Handles links from handover export PDFs/HTMLs:
 * https://app.celeste7.ai/open?t=<token>
 *
 * Flow:
 * 1. Extract token from URL
 * 2. Check authentication (redirect to login if needed)
 * 3. Call POST /api/v1/open/resolve with token
 * 4. On success: redirect to /app with entity focus
 * 5. On error: show error and redirect to /app
 */

import { useEffect, useState, useCallback, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { resolveOpenToken, ResolveError } from '@/lib/handoverExportClient';
import { Loader2, AlertCircle, ExternalLink } from 'lucide-react';

function OpenTokenResolver() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('t');

  const [status, setStatus] = useState<'loading' | 'error' | 'success'>('loading');
  const [errorMessage, setErrorMessage] = useState<string>('');

  const resolveToken = useCallback(async () => {
    // No token provided
    if (!token) {
      setStatus('error');
      setErrorMessage('No link token provided');
      setTimeout(() => router.replace('/app'), 2000);
      return;
    }

    try {
      setStatus('loading');

      // Resolve the token
      const result = await resolveOpenToken(token);

      // Success - redirect to /app with open_token for the shell to handle
      // The shell will call showContext with the resolved entity
      setStatus('success');

      // Store resolution result in sessionStorage for the app shell
      sessionStorage.setItem('handover_open_result', JSON.stringify(result));

      // Redirect to app - remove token from URL
      router.replace('/app?open_resolved=1');
    } catch (error) {
      setStatus('error');

      if (error instanceof ResolveError) {
        setErrorMessage(error.message);

        // If auth required, redirect to login with return URL
        if (error.status === 401) {
          const returnUrl = encodeURIComponent(`/open?t=${token}`);
          router.replace(`/login?returnUrl=${returnUrl}`);
          return;
        }
      } else {
        setErrorMessage('An unexpected error occurred');
      }

      // Auto-redirect to app after showing error
      setTimeout(() => router.replace('/app'), 3000);
    }
  }, [token, router]);

  useEffect(() => {
    resolveToken();
  }, [resolveToken]);

  return (
    <div className="min-h-screen bg-celeste-black flex items-center justify-center p-4">
      <div className="bg-celeste-bg-tertiary rounded-lg p-8 max-w-md w-full shadow-xl border border-celeste-text-secondary">
        {status === 'loading' && (
          <div className="text-center">
            <Loader2 className="w-12 h-12 text-celeste-accent animate-spin mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">
              Opening Link
            </h2>
            <p className="text-celeste-text-muted text-sm">
              Resolving handover reference...
            </p>
          </div>
        )}

        {status === 'success' && (
          <div className="text-center">
            <ExternalLink className="w-12 h-12 text-green-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">
              Link Resolved
            </h2>
            <p className="text-celeste-text-muted text-sm">
              Redirecting to item...
            </p>
          </div>
        )}

        {status === 'error' && (
          <div className="text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">
              Unable to Open Link
            </h2>
            <p className="text-celeste-text-muted text-sm mb-4">
              {errorMessage}
            </p>
            <button
              onClick={() => router.replace('/app')}
              className="px-4 py-2 bg-celeste-accent hover:bg-celeste-accent-hover text-white rounded-lg transition-colors"
            >
              Go to App
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function OpenPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-celeste-black flex items-center justify-center">
          <Loader2 className="w-12 h-12 text-celeste-accent animate-spin" />
        </div>
      }
    >
      <OpenTokenResolver />
    </Suspense>
  );
}
