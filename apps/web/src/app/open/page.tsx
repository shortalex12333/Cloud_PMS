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
 * 4. On success: redirect to entity's fragmented route (e.g. /work-orders/{id})
 * 5. On error: show error and redirect to /
 */

import { useEffect, useState, useCallback, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { resolveOpenToken, ResolveError } from '@/lib/handoverExportClient';
import { getEntityRoute } from '@/lib/featureFlags';
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
      setTimeout(() => router.replace('/'), 2000);
      return;
    }

    try {
      setStatus('loading');

      // Resolve the token
      const result = await resolveOpenToken(token);

      // Success — redirect directly to the entity's fragmented route
      setStatus('success');

      const entityRoute = getEntityRoute(
        result.focus.type as Parameters<typeof getEntityRoute>[0],
        result.focus.id
      );
      router.replace(entityRoute);
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

      // Auto-redirect to home after showing error
      setTimeout(() => router.replace('/'), 3000);
    }
  }, [token, router]);

  useEffect(() => {
    resolveToken();
  }, [resolveToken]);

  return (
    <div className="min-h-screen bg-surface-base flex items-center justify-center p-4">
      <div className="bg-surface-elevated rounded-lg p-8 max-w-md w-full border border-surface-border">
        {status === 'loading' && (
          <div className="text-center">
            <Loader2 className="w-12 h-12 text-brand-interactive animate-spin mx-auto mb-4" />
            <h2 className="typo-title font-semibold text-txt-primary mb-2">
              Opening Link
            </h2>
            <p className="text-txt-secondary typo-body">
              Resolving handover reference...
            </p>
          </div>
        )}

        {status === 'success' && (
          <div className="text-center">
            <ExternalLink className="w-12 h-12 text-status-success mx-auto mb-4" />
            <h2 className="typo-title font-semibold text-txt-primary mb-2">
              Link Resolved
            </h2>
            <p className="text-txt-secondary typo-body">
              Redirecting to item...
            </p>
          </div>
        )}

        {status === 'error' && (
          <div className="text-center">
            <AlertCircle className="w-12 h-12 text-status-critical mx-auto mb-4" />
            <h2 className="typo-title font-semibold text-txt-primary mb-2">
              Unable to Open Link
            </h2>
            <p className="text-txt-secondary typo-body mb-4">
              {errorMessage}
            </p>
            <button
              onClick={() => router.replace('/')}
              className="btn-primary"
            >
              Go to Home
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
        <div className="min-h-screen bg-surface-base flex items-center justify-center">
          <Loader2 className="w-12 h-12 text-brand-interactive animate-spin" />
        </div>
      }
    >
      <OpenTokenResolver />
    </Suspense>
  );
}
