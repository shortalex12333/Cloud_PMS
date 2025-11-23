'use client';

import SearchBar from '@/components/SearchBar';
import { Suspense } from 'react';
import { withAuth } from '@/components/withAuth';
import { useAuth } from '@/hooks/useAuth';
import { isHOD } from '@/contexts/AuthContext';
import Link from 'next/link';
import { LayoutDashboard, Settings } from 'lucide-react';

function SearchContent() {
  const { user } = useAuth();
  return (
    <div className="spotlight-container relative min-h-screen">
      <div className="w-full max-w-4xl">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-semibold mb-2">CelesteOS</h1>
          <p className="text-sm text-muted-foreground">
            Search anything — manuals, faults, history, parts, or ask a question
          </p>
          {user && (
            <p className="text-xs text-muted-foreground mt-2">
              {user.displayName || user.email} • {user.role}
            </p>
          )}
        </div>

        {/* Search Interface */}
        <Suspense
          fallback={
            <div className="w-full h-12 skeleton rounded-lg" />
          }
        >
          <SearchBar />
        </Suspense>
      </div>

      {/* Bottom Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 border-t border-border bg-background/95 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-4 py-3 flex justify-center gap-8">
          {isHOD(user) && (
            <Link
              href="/dashboard"
              className="flex items-center gap-2 px-4 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted rounded-md transition-colors"
            >
              <LayoutDashboard className="h-4 w-4" />
              <span>Dashboard</span>
            </Link>
          )}
          <Link
            href="/settings"
            className="flex items-center gap-2 px-4 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted rounded-md transition-colors"
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
