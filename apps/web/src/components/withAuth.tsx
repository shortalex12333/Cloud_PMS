'use client';

/**
 * withAuth - Higher-Order Component for Route Protection
 *
 * Security:
 * - Requires authenticated user with yacht assignment
 * - Redirects to /login if not authenticated
 * - Shows loading state while checking auth
 */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { isHOD } from '@/contexts/AuthContext';
import { Loader2 } from 'lucide-react';

interface WithAuthOptions {
  requireHOD?: boolean;
}

export function withAuth<P extends object>(
  Component: React.ComponentType<P>,
  options?: WithAuthOptions
) {
  return function AuthenticatedComponent(props: P) {
    const { user, loading } = useAuth();
    const router = useRouter();

    useEffect(() => {
      if (!loading) {
        // No user or no yacht → redirect to login
        if (!user || !user.yachtId) {
          console.log('[withAuth] No valid user, redirecting to /login');
          router.replace('/login');
          return;
        }

        // HOD required but user is not HOD → redirect to search
        if (options?.requireHOD && !isHOD(user)) {
          console.log('[withAuth] HOD required, redirecting to /search');
          router.replace('/search');
          return;
        }

        console.log('[withAuth] Access granted:', user.email);
      }
    }, [user, loading, router]);

    // Show loading state
    if (loading) {
      return (
        <div className="min-h-screen bg-[#1c1c1e] flex items-center justify-center">
          <div className="flex flex-col items-center space-y-4">
            <Loader2 className="w-8 h-8 text-[#0a84ff] animate-spin" />
            <p className="text-sm text-[#98989f]">Loading...</p>
          </div>
        </div>
      );
    }

    // Don't render if no valid user
    if (!user || !user.yachtId) {
      return (
        <div className="min-h-screen bg-[#1c1c1e] flex items-center justify-center">
          <div className="flex flex-col items-center space-y-4">
            <Loader2 className="w-8 h-8 text-[#0a84ff] animate-spin" />
            <p className="text-sm text-[#98989f]">Redirecting...</p>
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
