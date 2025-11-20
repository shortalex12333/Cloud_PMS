'use client';

import SearchBar from '@/components/SearchBar';
import { Suspense } from 'react';
import { withAuth } from '@/components/withAuth';
import { useAuth } from '@/hooks/useAuth';
import { isHOD } from '@/contexts/AuthContext';
import Link from 'next/link';

function SearchPage() {
  const { user, logout } = useAuth();
  return (
    <div className="spotlight-container">
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

        {/* Quick Actions */}
        <div className="mt-8 flex justify-center gap-2 text-xs text-muted-foreground">
          {isHOD(user) && (
            <Link
              href="/dashboard"
              className="px-3 py-1 rounded-md hover:bg-accent"
            >
              Dashboard →
            </Link>
          )}
          <button
            onClick={() => logout()}
            className="px-3 py-1 rounded-md hover:bg-accent hover:text-destructive"
          >
            Logout
          </button>
        </div>
      </div>
    </div>
  );
}

// Export with authentication protection (any authenticated user)
export default withAuth(SearchPage);
