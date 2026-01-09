'use client';

/**
 * withAuth - Higher-Order Component for Route Protection
 *
 * Security Requirements:
 * - NEVER render protected content without validated user
 * - Always redirect to /login if no valid session
 * - Re-validate session on every mount (don't trust stale state)
 * - Require yacht assignment for access
 */

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { isHOD } from '@/contexts/AuthContext';

interface WithAuthOptions {
  requireHOD?: boolean;
}

/**
 * Higher-Order Component for route protection
 *
 * Usage:
 * - withAuth(Component) - requires authenticated user with yacht assignment
 * - withAuth(Component, { requireHOD: true }) - requires HOD role
 *
 * Security:
 * - Validates session on mount (even if user object exists)
 * - Redirects to /login if validation fails
 * - Never renders protected content until validation passes
 */
export function withAuth<P extends object>(
  Component: React.ComponentType<P>,
  options?: WithAuthOptions
) {
  return function AuthenticatedComponent(props: P) {
    const { user, loading, validateSession } = useAuth();
    const router = useRouter();
    const [isValidated, setIsValidated] = useState(false);
    const [isValidating, setIsValidating] = useState(true);

    useEffect(() => {
      const checkAuth = async () => {
        setIsValidating(true);

        // Always re-validate session on mount
        const isValid = await validateSession();

        if (!isValid) {
          console.log('[withAuth] Session invalid, redirecting to /login');
          router.replace('/login');
          return;
        }

        setIsValidated(true);
        setIsValidating(false);
      };

      // Don't check until initial auth loading is complete
      if (!loading) {
        checkAuth();
      }
    }, [loading, validateSession, router]);

    // Additional check when user changes
    useEffect(() => {
      if (!loading && !isValidating && isValidated) {
        // User was validated but is now null - redirect
        if (!user) {
          console.log('[withAuth] User became null, redirecting to /login');
          router.replace('/login');
          return;
        }

        // Check yacht assignment
        if (!user.yachtId) {
          console.log('[withAuth] No yacht assignment, redirecting to /login');
          router.replace('/login');
          return;
        }

        // Check HOD requirement
        if (options?.requireHOD && !isHOD(user)) {
          console.log('[withAuth] HOD required but user role is:', user.role);
          router.replace('/search');
          return;
        }

        console.log('[withAuth] Access granted:', {
          userId: user.id,
          email: user.email,
          yachtId: user.yachtId,
          role: user.role,
        });
      }
    }, [user, loading, isValidating, isValidated, router]);

    // Show loading state while validating
    if (loading || isValidating || !isValidated) {
      return (
        <div className="min-h-screen bg-[#1c1c1e] flex items-center justify-center">
          <div className="flex flex-col items-center justify-center space-y-4">
            <div className="h-10 w-10 border-3 border-[#0a84ff] border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-[#98989f]">Verifying access...</p>
          </div>
        </div>
      );
    }

    // Never render if no user or no yacht
    if (!user || !user.yachtId) {
      return null;
    }

    // Check HOD requirement
    if (options?.requireHOD && !isHOD(user)) {
      return null;
    }

    // Render protected component
    return <Component {...props} />;
  };
}
