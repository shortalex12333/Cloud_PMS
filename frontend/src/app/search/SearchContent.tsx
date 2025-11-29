'use client';

/**
 * SearchContent
 * Main search page with Apple Spotlight-quality interface
 */

import { Suspense } from 'react';
import { withAuth } from '@/components/withAuth';
import { useAuth } from '@/hooks/useAuth';
import { isHOD } from '@/contexts/AuthContext';
import Link from 'next/link';
import { LayoutDashboard, Settings, Zap } from 'lucide-react';
import { SpotlightSearch } from '@/components/spotlight';
import { cn } from '@/lib/utils';

function SearchContent() {
  const { user } = useAuth();
  const showDashboard = isHOD(user);

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      {/* Main content area - centered */}
      <div className="spotlight-container pb-24">
        <div className="w-full max-w-[680px]">
          {/* Header */}
          <div className="mb-8 text-center">
            <h1 className="text-3xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
              CelesteOS
            </h1>
            <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-2">
              Search anything — manuals, faults, history, parts, or ask a question
            </p>
            {user && (
              <p className="text-xs text-zinc-400 dark:text-zinc-500 mt-2">
                {user.displayName || user.email} • {user.role}
              </p>
            )}
          </div>

          {/* Spotlight Search Interface */}
          <Suspense
            fallback={
              <div className="w-full h-14 skeleton rounded-[14px]" />
            }
          >
            <SpotlightSearch />
          </Suspense>
        </div>
      </div>

      {/* Bottom Navigation */}
      <nav className={cn(
        'fixed bottom-0 left-0 right-0',
        'border-t border-zinc-200/60 dark:border-zinc-800/60',
        'bg-white/80 dark:bg-zinc-900/80',
        'backdrop-blur-lg',
        'z-50'
      )}>
        <div className="max-w-4xl mx-auto px-4 py-3 flex justify-center gap-2">
          {showDashboard && (
            <>
              <Link
                href="/dashboard"
                className={cn(
                  'flex items-center gap-2 px-4 py-2 rounded-lg',
                  'text-sm font-medium',
                  'text-zinc-600 dark:text-zinc-300',
                  'hover:bg-zinc-100 dark:hover:bg-zinc-800',
                  'transition-colors duration-150'
                )}
              >
                <LayoutDashboard className="h-4 w-4" />
                <span>Dashboard</span>
              </Link>
              <Link
                href="/briefing"
                className={cn(
                  'flex items-center gap-2 px-4 py-2 rounded-lg',
                  'text-sm font-medium',
                  'text-zinc-600 dark:text-zinc-300',
                  'hover:bg-zinc-100 dark:hover:bg-zinc-800',
                  'transition-colors duration-150'
                )}
              >
                <Zap className="h-4 w-4" />
                <span>Briefing</span>
              </Link>
            </>
          )}
          <Link
            href="/settings"
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg',
              'text-sm font-medium',
              'text-zinc-600 dark:text-zinc-300',
              'hover:bg-zinc-100 dark:hover:bg-zinc-800',
              'transition-colors duration-150'
            )}
          >
            <Settings className="h-4 w-4" />
            <span>Settings</span>
          </Link>
        </div>
      </nav>
    </div>
  );
}

// Export with authentication protection (any authenticated user)
export default withAuth(SearchContent);
