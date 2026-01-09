'use client';

/**
 * LoginContent - Secure Login Page
 *
 * Security Requirements:
 * - Always validate existing session on mount
 * - Only redirect to /search after confirmed valid session
 * - Show clear error messages for auth failures
 * - Never bypass login without valid session + database user
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { isHOD } from '@/contexts/AuthContext';
import { Loader2 } from 'lucide-react';

export default function LoginContent() {
  const router = useRouter();
  const { user, login, loading: authLoading, error: authError, validateSession } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);

  // On mount, validate any existing session
  useEffect(() => {
    const checkExistingSession = async () => {
      setIsCheckingSession(true);
      console.log('[LoginPage] Checking existing session...');

      // Validate session (this queries database, not just cache)
      const isValid = await validateSession();

      if (isValid) {
        console.log('[LoginPage] Valid session found, redirecting...');
        // User has valid session with yacht assignment
        router.replace(isHOD(user) ? '/dashboard' : '/search');
      } else {
        console.log('[LoginPage] No valid session, showing login form');
      }

      setIsCheckingSession(false);
    };

    // Wait for initial auth loading to complete
    if (!authLoading) {
      checkExistingSession();
    }
  }, [authLoading, validateSession, router, user]);

  // Watch for user changes after login
  useEffect(() => {
    if (!authLoading && !isCheckingSession && user && user.yachtId) {
      console.log('[LoginPage] User logged in, redirecting to:', isHOD(user) ? '/dashboard' : '/search');
      router.replace(isHOD(user) ? '/dashboard' : '/search');
    }
  }, [user, authLoading, isCheckingSession, router]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      console.log('[LoginPage] Attempting login:', email);
      await login(email, password);
      // Redirect happens via useEffect when user is set
    } catch (err) {
      console.error('[LoginPage] Login failed:', err);
      setError(err instanceof Error ? err.message : 'Login failed');
      setLoading(false);
    }
  };

  // Show loading while checking auth
  if (authLoading || isCheckingSession) {
    return (
      <div className="min-h-screen bg-celeste-black flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <Loader2 className="w-8 h-8 text-celeste-blue animate-spin" />
          <p className="text-sm text-celeste-text-muted">Verifying session...</p>
        </div>
      </div>
    );
  }

  // Display error from auth context if present
  const displayError = error || authError;

  return (
    <div
      className="min-h-screen bg-celeste-black flex items-center justify-center p-6 font-body"
    >
      <div className="w-full max-w-[280px]">
        {/* Logo */}
        <div className="flex justify-center mb-8">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-b from-celeste-bg-tertiary to-celeste-bg-primary flex items-center justify-center">
            <span className="text-celeste-white text-xl font-semibold">C</span>
          </div>
        </div>

        {/* Title */}
        <h1 className="text-celeste-2xl font-semibold text-celeste-white text-center mb-1 tracking-tight">
          Sign in
        </h1>
        <p className="text-celeste-base text-celeste-text-muted text-center mb-8">
          CelesteOS
        </p>

        {/* Form */}
        <form onSubmit={handleLogin} className="space-y-3">
          {/* Error */}
          {displayError && (
            <div className="px-3 py-2 rounded-celeste-md bg-restricted-red/10 border border-restricted-red/20">
              <p className="text-celeste-base text-restricted-red text-center">{displayError}</p>
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
            className="w-full h-[44px] px-4 rounded-celeste-lg bg-celeste-bg-primary border border-celeste-border text-celeste-lg text-celeste-white placeholder:text-celeste-text-disabled focus:outline-none focus:border-celeste-blue transition-colors disabled:opacity-50"
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
            className="w-full h-[44px] px-4 rounded-celeste-lg bg-celeste-bg-primary border border-celeste-border text-celeste-lg text-celeste-white placeholder:text-celeste-text-disabled focus:outline-none focus:border-celeste-blue transition-colors disabled:opacity-50"
          />

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="w-full h-[44px] rounded-celeste-lg bg-celeste-blue hover:bg-celeste-blue-secondary disabled:opacity-50 disabled:cursor-not-allowed text-celeste-lg font-medium text-celeste-white transition-colors flex items-center justify-center gap-2"
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
        <p className="mt-8 text-celeste-xs text-celeste-text-disabled text-center">
          Secure crew access only
        </p>
      </div>
    </div>
  );
}
