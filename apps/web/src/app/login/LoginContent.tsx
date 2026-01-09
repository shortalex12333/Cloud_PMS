'use client';

/**
 * LoginContent - Secure Login Page
 *
 * Security Requirements:
 * - Show login form if no valid session
 * - Redirect to /search only after confirmed valid session
 * - Clear error messages on auth failures
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { isHOD } from '@/contexts/AuthContext';
import { Loader2 } from 'lucide-react';
import AuthDebug from '@/components/AuthDebug';

export default function LoginContent() {
  const router = useRouter();
  const { user, login, loading: authLoading, error: authError } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Redirect when user is authenticated with yacht
  useEffect(() => {
    if (!authLoading && user && user.yachtId) {
      console.log('[LoginPage] User authenticated, redirecting...');
      const destination = isHOD(user) ? '/dashboard' : '/search';
      router.replace(destination);
    }
  }, [user, authLoading, router]);

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

  // If user is set, show redirecting state
  if (user && user.yachtId) {
    return (
      <div className="min-h-screen bg-[#000000] flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <Loader2 className="w-8 h-8 text-[#0a84ff] animate-spin" />
          <p className="text-sm text-[#98989f]">Redirecting...</p>
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

      {/* Debug panel - remove after fixing auth */}
      <AuthDebug />
    </div>
  );
}
