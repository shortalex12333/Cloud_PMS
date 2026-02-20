'use client';

/**
 * LoginContent - Secure Login Page
 *
 * Architecture (2026-01-13):
 * - All login happens on app.celeste7.ai (no cross-domain)
 * - Uses non-blocking AuthContext
 * - Handles bootstrap status: active, pending, error
 */

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { isHOD, isFullyActivated } from '@/contexts/AuthContext';
import { Loader2 } from 'lucide-react';

export default function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, login, loading: authLoading, bootstrapping, error: authError } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [justLoggedOut, setJustLoggedOut] = useState(false);

  // Detect logout param and clear it from URL
  useEffect(() => {
    if (searchParams.get('logout') === '1') {
      setJustLoggedOut(true);
      // Clear the logout param from URL without triggering navigation
      window.history.replaceState({}, '', '/login');
      // Reset after a short delay to allow auth state to settle
      const timer = setTimeout(() => setJustLoggedOut(false), 2000);
      return () => clearTimeout(timer);
    }
  }, [searchParams]);

  // Redirect when user is authenticated and fully activated
  useEffect(() => {
    // Skip auto-redirect if user just logged out (prevents cache loop)
    if (justLoggedOut) {
      console.log('[LoginPage] Just logged out, skipping auto-redirect');
      return;
    }

    if (!authLoading && user) {
      console.log('[LoginPage] User state:', user.bootstrapStatus);

      // Wait for bootstrap to complete before deciding where to redirect
      if (bootstrapping) {
        console.log('[LoginPage] Waiting for bootstrap...');
        return;
      }

      // If fully activated, redirect to the single surface (root)
      if (isFullyActivated(user)) {
        console.log('[LoginPage] User fully activated, redirecting to /');
        router.replace('/');
        return;
      }

      // If pending, show pending screen
      if (user.bootstrapStatus === 'pending') {
        console.log('[LoginPage] User pending activation');
        // Stay on login page, show pending message
        return;
      }

      // If inactive yacht, show message
      if (user.bootstrapStatus === 'inactive') {
        console.log('[LoginPage] Yacht inactive');
        return;
      }

      // If error, will retry automatically, show loading
      if (user.bootstrapStatus === 'error') {
        console.log('[LoginPage] Bootstrap error, will retry');
        return;
      }
    }
  }, [user, authLoading, bootstrapping, router, justLoggedOut]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      console.log('[LoginPage] Attempting login:', email);
      await login(email, password);
      // Redirect happens via useEffect when user state updates
    } catch (err) {
      console.error('[LoginPage] Login failed:', err);
      setError(err instanceof Error ? err.message : 'Login failed');
      setLoading(false);
    }
  };

  // Show loading while auth is initializing (but not if just logged out)
  if (authLoading && !justLoggedOut) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <Loader2 className="w-8 h-8 text-celeste-accent animate-spin" />
          <p className="typo-body text-txt-secondary">Loading...</p>
        </div>
      </div>
    );
  }

  // If user exists but still bootstrapping, show loading (but not if just logged out)
  if (user && bootstrapping && !justLoggedOut) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <Loader2 className="w-8 h-8 text-celeste-accent animate-spin" />
          <p className="typo-body text-txt-secondary">Loading your account...</p>
        </div>
      </div>
    );
  }

  // If user is fully activated, show redirecting state (but not if just logged out)
  if (user && isFullyActivated(user) && !justLoggedOut) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <Loader2 className="w-8 h-8 text-celeste-accent animate-spin" />
          <p className="typo-body text-txt-secondary">Redirecting...</p>
        </div>
      </div>
    );
  }

  // If user exists but pending activation
  if (user && user.bootstrapStatus === 'pending') {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center p-6">
        <div className="w-full max-w-[320px] text-center">
          <div className="w-16 h-16 rounded-full bg-surface-base border border-surface-border flex items-center justify-center mx-auto mb-6">
            <span className="typo-title">⏳</span>
          </div>
          <h1 className="typo-title font-semibold text-white mb-2">Awaiting Activation</h1>
          <p className="typo-body text-txt-secondary mb-6">
            Your account is pending activation. Please contact your administrator to complete setup.
          </p>
          <p className="typo-meta text-txt-tertiary">
            Signed in as {user.email}
          </p>
        </div>
      </div>
    );
  }

  // If yacht is inactive
  if (user && user.bootstrapStatus === 'inactive') {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center p-6">
        <div className="w-full max-w-[320px] text-center">
          <div className="w-16 h-16 rounded-full bg-surface-base border border-surface-border flex items-center justify-center mx-auto mb-6">
            <span className="typo-title">🚢</span>
          </div>
          <h1 className="typo-title font-semibold text-white mb-2">Yacht Inactive</h1>
          <p className="typo-body text-txt-secondary mb-6">
            The yacht associated with your account is currently inactive.
            {user.yachtName && <span className="block mt-1">{user.yachtName}</span>}
          </p>
          <p className="typo-meta text-txt-tertiary">
            Contact support for assistance.
          </p>
        </div>
      </div>
    );
  }

  // If bootstrap error (will auto-retry)
  if (user && user.bootstrapStatus === 'error') {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <Loader2 className="w-8 h-8 text-celeste-accent animate-spin" />
          <p className="typo-body text-txt-secondary">Connecting to server...</p>
          <p className="typo-meta text-txt-tertiary">Retrying...</p>
        </div>
      </div>
    );
  }

  // Display error from auth context or local error
  const displayError = error || authError;

  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-6">
      <div className="w-full max-w-[280px]">
        {/* Logo */}
        <div className="flex justify-center mb-8">
          <div className="w-12 h-12 rounded-lg bg-gradient-to-b from-surface-border to-surface-base flex items-center justify-center">
            <span className="text-white typo-title font-semibold">C</span>
          </div>
        </div>

        {/* Title */}
        <h1 className="typo-title font-semibold text-white text-center mb-1 tracking-tight">
          Sign in
        </h1>
        <p className="typo-label text-txt-secondary text-center mb-8">
          CelesteOS
        </p>

        {/* Form */}
        <form onSubmit={handleLogin} className="space-y-3">
          {/* Error */}
          {displayError && (
            <div className="px-3 py-2 rounded-md bg-red-500/10 border border-red-500/20">
              <p className="typo-body text-red-500 text-center">{displayError}</p>
            </div>
          )}

          {/* Email */}
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            required
            autoComplete="email"
            disabled={loading}
            className="w-full h-11 px-4 rounded-md bg-surface-base border border-surface-border typo-label text-white placeholder:text-txt-tertiary focus:outline-none focus:border-brand-interactive transition-colors disabled:opacity-50"
          />

          {/* Password */}
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            required
            autoComplete="current-password"
            disabled={loading}
            className="w-full h-11 px-4 rounded-md bg-surface-base border border-surface-border typo-label text-white placeholder:text-txt-tertiary focus:outline-none focus:border-brand-interactive transition-colors disabled:opacity-50"
          />

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="w-full h-11 rounded-md bg-celeste-accent hover:bg-celeste-accent-hover disabled:opacity-50 disabled:cursor-not-allowed typo-label font-medium text-white transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Signing in...</span>
              </>
            ) : (
              'Sign In'
            )}
          </button>
        </form>

        {/* Footer */}
        <p className="mt-8 typo-meta text-txt-tertiary text-center">
          Secure crew access only
        </p>
      </div>
    </div>
  );
}
