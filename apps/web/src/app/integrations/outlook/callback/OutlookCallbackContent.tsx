'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

export default function OutlookCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [errorMessage, setErrorMessage] = useState<string>('');

  useEffect(() => {
    const handleCallback = async () => {
      // Get authorization code and state from URL
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const error = searchParams.get('error');
      const errorDescription = searchParams.get('error_description');

      // Handle OAuth errors from Microsoft
      if (error) {
        console.error('[OutlookCallback] OAuth error:', error, errorDescription);
        setStatus('error');
        setErrorMessage(errorDescription || error);
        setTimeout(() => {
          router.replace('/settings?error=outlook');
        }, 2000);
        return;
      }

      // No code = invalid callback
      if (!code) {
        console.error('[OutlookCallback] No authorization code received');
        setStatus('error');
        setErrorMessage('No authorization code received');
        setTimeout(() => {
          router.replace('/settings?error=outlook');
        }, 2000);
        return;
      }

      // No state = CSRF issue or invalid flow
      if (!state) {
        console.error('[OutlookCallback] No state parameter received');
        setStatus('error');
        setErrorMessage('Invalid OAuth state - please try again');
        setTimeout(() => {
          router.replace('/settings?error=outlook');
        }, 2000);
        return;
      }

      try {
        console.log('[OutlookCallback] Exchanging code for tokens...');

        // Call backend to exchange code for tokens
        // Pass both code and state (state contains user_id for linking)
        const response = await fetch(
          `/api/integrations/outlook/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`
        );

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.error || `Backend error: ${response.status}`);
        }

        const data = await response.json();
        console.log('[OutlookCallback] Token exchange successful:', data.email);

        setStatus('success');

        // Redirect back to settings page
        setTimeout(() => {
          router.replace('/settings?connected=outlook');
        }, 1000);
      } catch (error) {
        console.error('[OutlookCallback] Error during token exchange:', error);
        setStatus('error');
        setErrorMessage(error instanceof Error ? error.message : 'Unknown error');

        setTimeout(() => {
          router.replace('/settings?error=outlook');
        }, 2000);
      }
    };

    handleCallback();
  }, [searchParams, router]);

  return (
    <div className="spotlight-container">
      <div className="w-full max-w-md text-center">
        <div className="bg-card border border-border rounded-lg p-8">
          {status === 'processing' && (
            <>
              <div className="h-12 w-12 mx-auto mb-4 border-4 border-primary border-t-transparent rounded-full animate-spin" />
              <h2 className="typo-title font-semibold mb-2">Connecting to Outlook</h2>
              <p className="typo-body text-muted-foreground">
                Exchanging authorization code for access tokens...
              </p>
            </>
          )}

          {status === 'success' && (
            <>
              <div className="h-12 w-12 mx-auto mb-4 bg-green-500/10 text-green-600 rounded-full flex items-center justify-center typo-title">
                ✓
              </div>
              <h2 className="typo-title font-semibold mb-2">Successfully Connected!</h2>
              <p className="typo-body text-muted-foreground">
                Redirecting you back to settings...
              </p>
            </>
          )}

          {status === 'error' && (
            <>
              <div className="h-12 w-12 mx-auto mb-4 bg-destructive/10 text-destructive rounded-full flex items-center justify-center typo-title">
                ✕
              </div>
              <h2 className="typo-title font-semibold mb-2">Connection Failed</h2>
              <p className="typo-body text-muted-foreground mb-4">
                {errorMessage || 'Unable to connect to Outlook'}
              </p>
              <p className="typo-meta text-muted-foreground">
                Redirecting back to settings...
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
