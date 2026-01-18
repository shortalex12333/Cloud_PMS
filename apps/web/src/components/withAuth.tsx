'use client';

/**
 * withAuth - Higher-Order Component for Route Protection
 *
 * Security:
 * - Requires authenticated user with yacht assignment
 * - Redirects to /login if not authenticated
 * - Shows loading state while checking auth
 *
 * Architecture (2026-01-16):
 * - MUST wait for BOTH loading AND bootstrapping to complete
 * - Session exists immediately from localStorage (loading = false)
 * - But yachtId comes from bootstrap RPC (bootstrapping = false)
 * - Redirecting before bootstrap completes causes auth_resume failures
 */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { isHOD, isFullyActivated } from '@/contexts/AuthContext';
import { Loader2 } from 'lucide-react';

interface WithAuthOptions {
  requireHOD?: boolean;
}

export function withAuth<P extends object>(
  Component: React.ComponentType<P>,
  options?: WithAuthOptions
) {
  return function AuthenticatedComponent(props: P) {
    const { user, loading, bootstrapping } = useAuth();
    const router = useRouter();

    // Determine if we're still initializing (auth OR bootstrap)
    const isInitializing = loading || bootstrapping;

    useEffect(() => {
      // CRITICAL: Don't make redirect decisions until BOTH loading AND bootstrapping are done
      if (isInitializing) {
        return;
      }

      // No user at all → redirect to login
      if (!user) {
        console.log('[withAuth] No user, redirecting to /login');
        router.replace('/login');
        return;
      }

      // User exists but bootstrap status indicates they need to login
      // (pending activation is handled by login page)
      if (user.bootstrapStatus === 'pending' || user.bootstrapStatus === 'inactive') {
        console.log('[withAuth] User status:', user.bootstrapStatus, ', redirecting to /login');
        router.replace('/login');
        return;
      }

      // User exists but no yacht (shouldn't happen after bootstrap, but safety check)
      if (!user.yachtId && user.bootstrapStatus === 'active') {
        console.log('[withAuth] No yacht assignment, redirecting to /login');
        router.replace('/login');
        return;
      }

      // Bootstrap error - keep user logged in, don't redirect (will retry)
      if (user.bootstrapStatus === 'error') {
        console.log('[withAuth] Bootstrap error, staying on page (will retry)');
        // Don't redirect - the user IS authenticated, just bootstrap failed
        return;
      }

      // HOD required but user is not HOD → redirect to app
      if (options?.requireHOD && !isHOD(user)) {
        console.log('[withAuth] HOD required, redirecting to /app');
        router.replace('/app');
        return;
      }

      console.log('[withAuth] Access granted:', user.email, 'yacht:', user.yachtId);
    }, [user, isInitializing, router]);

    // Show loading state while auth OR bootstrap is in progress
    if (isInitializing) {
      return (
        <div className="min-h-screen bg-[#1c1c1e] flex items-center justify-center">
          <div className="flex flex-col items-center space-y-4">
            <Loader2 className="w-8 h-8 text-[#0a84ff] animate-spin" />
            <p className="text-sm text-[#98989f]">
              {loading ? 'Loading...' : 'Connecting...'}
            </p>
          </div>
        </div>
      );
    }

    // No user after initialization → show redirecting (redirect happens in useEffect)
    if (!user) {
      return (
        <div className="min-h-screen bg-[#1c1c1e] flex items-center justify-center">
          <div className="flex flex-col items-center space-y-4">
            <Loader2 className="w-8 h-8 text-[#0a84ff] animate-spin" />
            <p className="text-sm text-[#98989f]">Redirecting...</p>
          </div>
        </div>
      );
    }

    // Pending/inactive users → show redirecting
    if (user.bootstrapStatus === 'pending' || user.bootstrapStatus === 'inactive') {
      return (
        <div className="min-h-screen bg-[#1c1c1e] flex items-center justify-center">
          <div className="flex flex-col items-center space-y-4">
            <Loader2 className="w-8 h-8 text-[#0a84ff] animate-spin" />
            <p className="text-sm text-[#98989f]">Redirecting...</p>
          </div>
        </div>
      );
    }

    // Bootstrap error - show error state but allow page to render
    // (bootstrap will auto-retry, better UX than redirecting)
    if (user.bootstrapStatus === 'error' && !user.yachtId) {
      return (
        <div className="min-h-screen bg-[#1c1c1e] flex items-center justify-center">
          <div className="flex flex-col items-center space-y-4">
            <Loader2 className="w-8 h-8 text-[#0a84ff] animate-spin" />
            <p className="text-sm text-[#98989f]">Reconnecting...</p>
            <p className="text-xs text-[#636366]">Please wait...</p>
          </div>
        </div>
      );
    }

    // Check HOD requirement
    if (options?.requireHOD && !isHOD(user)) {
      return null;
    }

    // Render protected component
    return <Component {...props} />;
  };
}
