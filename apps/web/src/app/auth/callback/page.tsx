'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { supabase } from '@/lib/supabaseClient';

/**
 * Auth Callback Page
 *
 * Handles session transfer from auth.celeste7.ai to app.celeste7.ai
 *
 * Flow:
 * 1. User logs in on auth.celeste7.ai
 * 2. Auth domain redirects to app.celeste7.ai/auth/callback?access_token=...&refresh_token=...
 * 3. This page extracts tokens and sets session in app domain
 * 4. Redirects to /search (or intended destination)
 *
 * Alternative: Can also handle Supabase OAuth callbacks
 */

export default function AuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function handleCallback() {
      try {
        console.log('[AuthCallback] Processing callback...');

        // Method 1: Session transfer from auth domain (custom flow)
        const accessToken = searchParams.get('access_token');
        const refreshToken = searchParams.get('refresh_token');

        if (accessToken && refreshToken) {
          console.log('[AuthCallback] Setting session from tokens...');

          // Set session in app domain
          const { data, error: sessionError } = await supabase.auth.setSession({
            access_token: accessToken,
            refresh_token: refreshToken,
          });

          if (sessionError) {
            console.error('[AuthCallback] Session error:', sessionError);
            setError(sessionError.message);
            setStatus('error');
            return;
          }

          console.log('[AuthCallback] Session set successfully:', data.session?.user?.email);
          setStatus('success');

          // Get intended destination or default to search
          const redirectTo = searchParams.get('redirect') || '/search';
          console.log('[AuthCallback] Redirecting to:', redirectTo);

          // Small delay to show success message
          setTimeout(() => {
            router.push(redirectTo);
          }, 500);

          return;
        }

        // Method 2: Supabase OAuth callback (standard flow)
        // Check for Supabase's hash-based tokens
        const hashParams = new URLSearchParams(window.location.hash.substring(1));
        const hashAccessToken = hashParams.get('access_token');
        const hashRefreshToken = hashParams.get('refresh_token');

        if (hashAccessToken && hashRefreshToken) {
          console.log('[AuthCallback] Setting session from hash tokens...');

          const { data, error: sessionError } = await supabase.auth.setSession({
            access_token: hashAccessToken,
            refresh_token: hashRefreshToken,
          });

          if (sessionError) {
            console.error('[AuthCallback] Hash session error:', sessionError);
            setError(sessionError.message);
            setStatus('error');
            return;
          }

          console.log('[AuthCallback] Hash session set successfully');
          setStatus('success');

          setTimeout(() => {
            router.push('/search');
          }, 500);

          return;
        }

        // Method 3: Check if already authenticated
        const { data: { session } } = await supabase.auth.getSession();

        if (session) {
          console.log('[AuthCallback] Already authenticated, redirecting...');
          setStatus('success');
          router.push('/search');
          return;
        }

        // No tokens found
        console.error('[AuthCallback] No tokens found in URL');
        setError('No authentication tokens found. Please try logging in again.');
        setStatus('error');
      } catch (err) {
        console.error('[AuthCallback] Unexpected error:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
        setStatus('error');
      }
    }

    handleCallback();
  }, [searchParams, router]);

  // Loading state
  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#1c1c1e]">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-celeste-blue border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-white text-lg">Completing sign in...</p>
        </div>
      </div>
    );
  }

  // Success state
  if (status === 'success') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#1c1c1e]">
        <div className="text-center">
          <div className="w-12 h-12 rounded-full bg-green-500 flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="text-white text-lg">Sign in successful!</p>
          <p className="text-gray-400 text-sm mt-2">Redirecting...</p>
        </div>
      </div>
    );
  }

  // Error state
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#1c1c1e]">
      <div className="text-center max-w-md px-4">
        <div className="w-12 h-12 rounded-full bg-red-500 flex items-center justify-center mx-auto mb-4">
          <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
        <p className="text-white text-lg mb-2">Authentication failed</p>
        <p className="text-gray-400 text-sm mb-4">{error}</p>
        <a
          href="https://auth.celeste7.ai"
          className="inline-block px-6 py-2 bg-celeste-blue hover:bg-celeste-blue-secondary rounded-md text-white transition-colors"
        >
          Return to Login
        </a>
      </div>
    </div>
  );
}
