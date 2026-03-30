'use client';

/**
 * ShellWrapper — Conditionally wraps children in AppShell
 *
 * Renders AppShell for all authenticated routes.
 * Passes through without shell for: /login, /auth/*, /open/*
 *
 * Auth guard: redirects to /login if no active session.
 * This ensures domain pages (which query Supabase directly via
 * FilteredEntityList) always have a valid session available.
 */

import * as React from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { AppShell } from './AppShell';

const SHELL_EXCLUDED_ROUTES = ['/login', '/auth/', '/open/'];

export function ShellWrapper({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading } = useAuth();

  const shouldExclude = SHELL_EXCLUDED_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(route)
  );

  if (shouldExclude) {
    return <>{children}</>;
  }

  // Show nothing while auth is initializing (prevents flash of unauthenticated content)
  // This also prevents premature redirect before session is restored from localStorage
  if (loading) {
    return null;
  }

  // Auth guard: redirect to login if not authenticated (after loading completes)
  if (!user) {
    return <AuthRedirect />;
  }

  return <AppShell>{children}</AppShell>;
}

/** Separate component to handle redirect via useEffect (not during render) */
function AuthRedirect() {
  const router = useRouter();
  React.useEffect(() => {
    router.replace('/login');
  }, [router]);
  return null;
}
