import SearchBar from '@/components/SearchBar';
import { Suspense } from 'react';

export default function SearchPage() {
  return (
    <div className="spotlight-container">
      <div className="w-full max-w-4xl">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-semibold mb-2">CelesteOS</h1>
          <p className="text-sm text-muted-foreground">
            Search anything — manuals, faults, history, parts, or ask a question
          </p>
        </div>

        {/* Search Interface */}
        <Suspense
          fallback={
            <div className="w-full h-12 skeleton rounded-lg" />
          }
        >
          <SearchBar />
        </Suspense>

        {/* Quick Actions (Optional) */}
        <div className="mt-8 flex justify-center gap-2 text-xs text-muted-foreground">
          <button className="px-3 py-1 rounded-md hover:bg-accent">
            Recent searches
          </button>
          <button className="px-3 py-1 rounded-md hover:bg-accent">
            Dashboard →
          </button>
        </div>
      </div>
    </div>
  );
}
