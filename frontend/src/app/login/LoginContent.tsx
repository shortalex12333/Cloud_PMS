'use client';

/**
 * LoginContent
 * Apple-inspired login page with glassmorphic card
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { isHOD } from '@/contexts/AuthContext';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function LoginContent() {
  const router = useRouter();
  const { user, login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Redirect if already logged in
  useEffect(() => {
    if (user) {
      console.log('[LoginPage] User already logged in, redirecting...');
      const redirectTo = isHOD(user) ? '/dashboard' : '/search';
      router.push(redirectTo);
    }
  }, [user, router]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await login(email, password);
      console.log('[LoginPage] Login successful');
    } catch (err) {
      console.error('[LoginPage] Login failed:', err);
      setError(err instanceof Error ? err.message : 'Login failed');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-50 dark:bg-zinc-950 p-4">
      <div className="w-full max-w-[400px] space-y-8">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-[32px] font-bold tracking-[-0.02em] text-zinc-900 dark:text-zinc-100">
            CelesteOS
          </h1>
          <p className="mt-2 text-[15px] text-zinc-500 dark:text-zinc-400">
            Engineering Intelligence for Yachts
          </p>
        </div>

        {/* Login Card - Glassmorphic */}
        <div className={cn(
          'celeste-card p-8',
          'bg-white/90 dark:bg-zinc-900/90',
          'backdrop-blur-xl',
          'shadow-[var(--shadow-lg)]'
        )}>
          <form onSubmit={handleLogin} className="space-y-5">
            {/* Error Message */}
            {error && (
              <div className={cn(
                'p-3 rounded-[var(--radius-button)]',
                'bg-[--system-red-light] border border-[--system-red]/20',
                'text-[14px] text-[--system-red]'
              )}>
                {error}
              </div>
            )}

            {/* Email Field */}
            <div>
              <label
                htmlFor="email"
                className="block text-[13px] font-medium text-zinc-700 dark:text-zinc-300 mb-2"
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="celeste-input h-11"
                placeholder="alex@yacht.com"
              />
            </div>

            {/* Password Field */}
            <div>
              <label
                htmlFor="password"
                className="block text-[13px] font-medium text-zinc-700 dark:text-zinc-300 mb-2"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="celeste-input h-11"
                placeholder="••••••••"
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className={cn(
                'celeste-button celeste-button-primary w-full h-11 text-[15px]',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Signing in...</span>
                </>
              ) : (
                'Sign in'
              )}
            </button>
          </form>

          {/* Footer */}
          <p className="mt-6 text-center text-[12px] text-zinc-400 dark:text-zinc-500">
            Secure access for authorized crew only
          </p>
        </div>
      </div>
    </div>
  );
}
