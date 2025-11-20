'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';

interface WithAuthOptions {
  requireHOD?: boolean;
}

/**
 * Higher-Order Component for route protection
 *
 * Usage:
 * - withAuth(Component) - requires any authenticated user
 * - withAuth(Component, { requireHOD: true }) - requires HOD role
 *
 * Behavior:
 * - Shows loading state while auth is loading
 * - Redirects to /login if no user
 * - If requireHOD and user.role !== 'HOD' → redirects to /search
 */
export function withAuth<P extends object>(
  Component: React.ComponentType<P>,
  options?: WithAuthOptions
) {
  return function AuthenticatedComponent(props: P) {
    const { user, loading } = useAuth();
    const router = useRouter();

    useEffect(() => {
      if (!loading) {
        // No user → redirect to login
        if (!user) {
          console.log('[withAuth] No user, redirecting to /login');
          router.push('/login');
          return;
        }

        // HOD required but user is not HOD → redirect to search
        if (options?.requireHOD && user.role !== 'HOD') {
          console.log('[withAuth] HOD required but user role is:', user.role);
          router.push('/search');
          return;
        }

        console.log('[withAuth] Access granted:', {
          userId: user.id,
          role: user.role,
          requireHOD: options?.requireHOD,
        });
      }
    }, [user, loading, router]);

    // Show loading state
    if (loading) {
      return (
        <div className="spotlight-container">
          <div className="flex flex-col items-center justify-center space-y-4">
            <div className="h-12 w-12 border-4 border-primary border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-muted-foreground">Loading...</p>
          </div>
        </div>
      );
    }

    // Show nothing while redirecting
    if (!user) {
      return null;
    }

    // Check HOD requirement
    if (options?.requireHOD && user.role !== 'HOD') {
      return null;
    }

    // Render protected component
    return <Component {...props} />;
  };
}
