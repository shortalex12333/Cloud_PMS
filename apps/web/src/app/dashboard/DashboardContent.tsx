'use client';

/**
 * DashboardContent
 * HOD/Management dashboard with Control Center-style modules
 */

import { withAuth } from '@/components/withAuth';
import { useAuth } from '@/hooks/useAuth';
import { isHOD } from '@/contexts/AuthContext';
import Link from 'next/link';
import { Search, Settings, Zap, ChevronLeft } from 'lucide-react';
import { ControlCenter } from '@/components/dashboard';
import { cn } from '@/lib/utils';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

function DashboardContent() {
  const { user } = useAuth();
  const router = useRouter();
  const canViewDashboard = isHOD(user);

  // Redirect non-HOD users to search
  useEffect(() => {
    if (user && !canViewDashboard) {
      router.replace('/search');
    }
  }, [user, canViewDashboard, router]);

  // Don't render until we confirm access
  if (!canViewDashboard) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50 dark:bg-zinc-950">
        <div className="text-center">
          <div className="h-8 w-8 border-2 border-zinc-300 border-t-zinc-600 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-sm text-zinc-500">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      {/* Top Navigation Bar */}
      <header className={cn(
        'sticky top-0 z-40',
        'border-b border-zinc-200/60 dark:border-zinc-800/60',
        'bg-white/80 dark:bg-zinc-900/80',
        'backdrop-blur-lg'
      )}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3">
          <div className="flex items-center justify-between">
            {/* Left: Back to Search */}
            <Link
              href="/search"
              className={cn(
                'flex items-center gap-2 px-3 py-1.5 rounded-lg',
                'text-sm font-medium',
                'text-zinc-600 dark:text-zinc-300',
                'hover:bg-zinc-100 dark:hover:bg-zinc-800',
                'transition-colors duration-150'
              )}
            >
              <ChevronLeft className="h-4 w-4" />
              <span>Search</span>
            </Link>

            {/* Center: Title */}
            <div className="text-center">
              <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
                Control Center
              </h1>
              {user && (
                <p className="text-xs text-zinc-500 dark:text-zinc-400">
                  {user.displayName || user.email}
                </p>
              )}
            </div>

            {/* Right: Quick Actions */}
            <div className="flex items-center gap-2">
              <Link
                href="/briefing"
                className={cn(
                  'flex items-center gap-2 px-3 py-1.5 rounded-lg',
                  'text-sm font-medium',
                  'text-zinc-600 dark:text-zinc-300',
                  'hover:bg-zinc-100 dark:hover:bg-zinc-800',
                  'transition-colors duration-150'
                )}
              >
                <Zap className="h-4 w-4" />
                <span className="hidden sm:inline">Briefing</span>
              </Link>
              <Link
                href="/settings"
                className={cn(
                  'flex items-center gap-2 px-3 py-1.5 rounded-lg',
                  'text-sm font-medium',
                  'text-zinc-600 dark:text-zinc-300',
                  'hover:bg-zinc-100 dark:hover:bg-zinc-800',
                  'transition-colors duration-150'
                )}
              >
                <Settings className="h-4 w-4" />
                <span className="hidden sm:inline">Settings</span>
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Control Center Dashboard */}
      <ControlCenter />
    </div>
  );
}

// Export with authentication protection
export default withAuth(DashboardContent);
