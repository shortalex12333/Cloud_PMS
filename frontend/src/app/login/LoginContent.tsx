'use client';

/**
 * LoginContent
 * Apple-style minimal login
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { isHOD } from '@/contexts/AuthContext';
import { Loader2 } from 'lucide-react';

export default function LoginContent() {
  const router = useRouter();
  const { user, login, loading: authLoading } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Redirect if already logged in
  useEffect(() => {
    if (user) {
      console.log('[LoginPage] Redirecting logged in user');
      router.push(isHOD(user) ? '/dashboard' : '/search');
    }
  }, [user, router]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
      setLoading(false);
    }
  };

  // Show loading while checking auth
  if (authLoading) {
    return (
      <div className="min-h-screen bg-[#000000] flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-[#86868b] animate-spin" />
      </div>
    );
  }

  return (
    <div
      className="min-h-screen bg-[#000000] flex items-center justify-center p-6"
      style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif' }}
    >
      <div className="w-full max-w-[280px]">
        {/* Apple Logo placeholder */}
        <div className="flex justify-center mb-8">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-b from-[#3d3d3f] to-[#1c1c1e] flex items-center justify-center">
            <span className="text-white text-xl font-semibold">C</span>
          </div>
        </div>

        {/* Title */}
        <h1 className="text-[21px] font-semibold text-white text-center mb-1 tracking-[-0.01em]">
          Sign in
        </h1>
        <p className="text-[13px] text-[#86868b] text-center mb-8">
          CelesteOS
        </p>

        {/* Form */}
        <form onSubmit={handleLogin} className="space-y-3">
          {/* Error */}
          {error && (
            <div className="px-3 py-2 rounded-lg bg-[#FF453A]/10 border border-[#FF453A]/20">
              <p className="text-[13px] text-[#FF453A] text-center">{error}</p>
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
            className="w-full h-[44px] px-4 rounded-xl bg-[#1c1c1e] border border-[#3d3d3f] text-[15px] text-white placeholder:text-[#636366] focus:outline-none focus:border-[#0A84FF] transition-colors"
          />

          {/* Password */}
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            required
            autoComplete="current-password"
            className="w-full h-[44px] px-4 rounded-xl bg-[#1c1c1e] border border-[#3d3d3f] text-[15px] text-white placeholder:text-[#636366] focus:outline-none focus:border-[#0A84FF] transition-colors"
          />

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="w-full h-[44px] rounded-xl bg-[#0A84FF] hover:bg-[#0077ED] disabled:opacity-50 disabled:cursor-not-allowed text-[15px] font-medium text-white transition-colors flex items-center justify-center gap-2"
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
        <p className="mt-8 text-[11px] text-[#48484a] text-center">
          Secure crew access only
        </p>
      </div>
    </div>
  );
}
