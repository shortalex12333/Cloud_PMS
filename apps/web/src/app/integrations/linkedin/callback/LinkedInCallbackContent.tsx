'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

export default function LinkedInCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [errorMessage, setErrorMessage] = useState<string>('');

  useEffect(() => {
    const handleCallback = async () => {
      // Get authorization code from URL
      const code = searchParams.get('code');
      const error = searchParams.get('error');
      const errorDescription = searchParams.get('error_description');

      // Handle OAuth errors from LinkedIn
      if (error) {
        console.error('[LinkedInCallback] OAuth error:', error, errorDescription);
        setStatus('error');
        setErrorMessage(errorDescription || error);
        setTimeout(() => {
          router.replace('/settings?error=linkedin');
        }, 2000);
        return;
      }

      // No code = invalid callback
      if (!code) {
        console.error('[LinkedInCallback] No authorization code received');
        setStatus('error');
        setErrorMessage('No authorization code received');
        setTimeout(() => {
          router.replace('/settings?error=linkedin');
        }, 2000);
        return;
      }

      try {
        console.log('[LinkedInCallback] Exchanging code for tokens...');

        // Call backend to exchange code for tokens
        // Backend will:
        // 1. Exchange code for access tokens
        // 2. Store tokens in Supabase api_tokens table
        // 3. Link to current user via JWT
        const response = await fetch(`/api/integrations/linkedin/callback?code=${encodeURIComponent(code)}`);

        if (!response.ok) {
          throw new Error(`Backend error: ${response.status}`);
        }

        const data = await response.json();
        console.log('[LinkedInCallback] Token exchange successful:', data);

        setStatus('success');

        // Redirect back to settings page
        setTimeout(() => {
          router.replace('/settings?connected=linkedin');
        }, 1000);
      } catch (error) {
        console.error('[LinkedInCallback] Error during token exchange:', error);
        setStatus('error');
        setErrorMessage(error instanceof Error ? error.message : 'Unknown error');

        setTimeout(() => {
          router.replace('/settings?error=linkedin');
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
              <h2 className="typo-title font-semibold mb-2">Connecting to LinkedIn</h2>
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
                {errorMessage || 'Unable to connect to LinkedIn'}
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
