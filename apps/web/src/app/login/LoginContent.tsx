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
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { isHOD, isFullyActivated } from '@/contexts/AuthContext';
import { Loader2 } from 'lucide-react';

export default function LoginContent() {
  const router = useRouter();
  const { user, login, loading: authLoading, bootstrapping, error: authError } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Redirect when user is authenticated and fully activated
  useEffect(() => {
    if (!authLoading && user) {
      console.log('[LoginPage] User state:', user.bootstrapStatus);

      // Wait for bootstrap to complete before deciding where to redirect
      if (bootstrapping) {
        console.log('[LoginPage] Waiting for bootstrap...');
        return;
      }

      // If fully activated, redirect to the single surface app
      if (isFullyActivated(user)) {
        console.log('[LoginPage] User fully activated, redirecting to /app');
        router.replace('/app');
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
  }, [user, authLoading, bootstrapping, router]);

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

  // Show loading while auth is initializing
  if (authLoading) {
    return (
      <div className="min-h-screen bg-[#000000] flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <Loader2 className="w-8 h-8 text-[#0a84ff] animate-spin" />
          <p className="text-sm text-[#98989f]">Loading...</p>
        </div>
      </div>
    );
  }

  // If user exists but still bootstrapping, show loading
  if (user && bootstrapping) {
    return (
      <div className="min-h-screen bg-[#000000] flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <Loader2 className="w-8 h-8 text-[#0a84ff] animate-spin" />
          <p className="text-sm text-[#98989f]">Loading your account...</p>
        </div>
      </div>
    );
  }

  // If user is fully activated, show redirecting state
  if (user && isFullyActivated(user)) {
    return (
      <div className="min-h-screen bg-[#000000] flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <Loader2 className="w-8 h-8 text-[#0a84ff] animate-spin" />
          <p className="text-sm text-[#98989f]">Redirecting...</p>
        </div>
      </div>
    );
  }

  // If user exists but pending activation
  if (user && user.bootstrapStatus === 'pending') {
    return (
      <div className="min-h-screen bg-[#000000] flex items-center justify-center p-6">
        <div className="w-full max-w-[320px] text-center">
          <div className="w-16 h-16 rounded-full bg-[#1c1c1e] border border-[#3d3d3f] flex items-center justify-center mx-auto mb-6">
            <span className="text-2xl">⏳</span>
          </div>
          <h1 className="text-xl font-semibold text-white mb-2">Awaiting Activation</h1>
          <p className="text-sm text-[#98989f] mb-6">
            Your account is pending activation. Please contact your administrator to complete setup.
          </p>
          <p className="text-xs text-[#636366]">
            Signed in as {user.email}
          </p>
        </div>
      </div>
    );
  }

  // If yacht is inactive
  if (user && user.bootstrapStatus === 'inactive') {
    return (
      <div className="min-h-screen bg-[#000000] flex items-center justify-center p-6">
        <div className="w-full max-w-[320px] text-center">
          <div className="w-16 h-16 rounded-full bg-[#1c1c1e] border border-[#3d3d3f] flex items-center justify-center mx-auto mb-6">
            <span className="text-2xl">🚢</span>
          </div>
          <h1 className="text-xl font-semibold text-white mb-2">Yacht Inactive</h1>
          <p className="text-sm text-[#98989f] mb-6">
            The yacht associated with your account is currently inactive.
            {user.yachtName && <span className="block mt-1">{user.yachtName}</span>}
          </p>
          <p className="text-xs text-[#636366]">
            Contact support for assistance.
          </p>
        </div>
      </div>
    );
  }

  // If bootstrap error (will auto-retry)
  if (user && user.bootstrapStatus === 'error') {
    return (
      <div className="min-h-screen bg-[#000000] flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <Loader2 className="w-8 h-8 text-[#0a84ff] animate-spin" />
          <p className="text-sm text-[#98989f]">Connecting to server...</p>
          <p className="text-xs text-[#636366]">Retrying...</p>
        </div>
      </div>
    );
  }

  // Display error from auth context or local error
  const displayError = error || authError;

  return (
    <div className="min-h-screen bg-[#000000] flex items-center justify-center p-6">
      <div className="w-full max-w-[280px]">
        {/* Logo */}
        <div className="flex justify-center mb-8">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-b from-[#3d3d3f] to-[#1c1c1e] flex items-center justify-center">
            <span className="text-white text-xl font-semibold">C</span>
          </div>
        </div>

        {/* Title */}
        <h1 className="text-2xl font-semibold text-white text-center mb-1 tracking-tight">
          Sign in
        </h1>
        <p className="text-base text-[#98989f] text-center mb-8">
          CelesteOS
        </p>

        {/* Form */}
        <form onSubmit={handleLogin} className="space-y-3">
          {/* Error */}
          {displayError && (
            <div className="px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20">
              <p className="text-sm text-red-500 text-center">{displayError}</p>
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
            className="w-full h-[44px] px-4 rounded-lg bg-[#1c1c1e] border border-[#3d3d3f] text-base text-white placeholder:text-[#636366] focus:outline-none focus:border-[#0a84ff] transition-colors disabled:opacity-50"
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
            className="w-full h-[44px] px-4 rounded-lg bg-[#1c1c1e] border border-[#3d3d3f] text-base text-white placeholder:text-[#636366] focus:outline-none focus:border-[#0a84ff] transition-colors disabled:opacity-50"
          />

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="w-full h-[44px] rounded-lg bg-[#0a84ff] hover:bg-[#0077ed] disabled:opacity-50 disabled:cursor-not-allowed text-base font-medium text-white transition-colors flex items-center justify-center gap-2"
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
        <p className="mt-8 text-xs text-[#636366] text-center">
          Secure crew access only
        </p>
      </div>
    </div>
  );
}
