'use client';

/**
 * ShellWrapper — Conditionally wraps children in AppShell
 *
 * Renders AppShell for all authenticated routes.
 * Passes through without shell for: /login, /auth/*, /open/*
 *
 * Placed in the root layout to provide the persistent shell
 * across all authenticated pages.
 */

import * as React from 'react';
import { usePathname } from 'next/navigation';
import { AppShell } from './AppShell';

const SHELL_EXCLUDED_ROUTES = ['/login', '/auth/', '/open/'];

export function ShellWrapper({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  const shouldExclude = SHELL_EXCLUDED_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(route)
  );

  if (shouldExclude) {
    return <>{children}</>;
  }

  return <AppShell>{children}</AppShell>;
}
