'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { useState } from 'react';

/**
 * React Query Provider
 *
 * Provides QueryClient to the entire application for data fetching,
 * caching, and synchronization.
 *
 * Default Configuration:
 * - staleTime: 30s (data considered fresh for 30 seconds)
 * - gcTime: 5min (unused data garbage collected after 5 minutes)
 * - refetchOnWindowFocus: false (don't auto-refetch when window regains focus)
 * - retry: 1 (retry failed requests once)
 */
export function QueryProvider({ children }: { children: React.ReactNode }) {
  // Create QueryClient instance in state to ensure it persists across renders
  // but is created fresh for each user session
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // Data is considered fresh for 30 seconds
            staleTime: 30 * 1000,
            // Cached data is garbage collected after 5 minutes of being unused
            gcTime: 5 * 60 * 1000,
            // Don't refetch on window focus (better for yacht networks with spotty connections)
            refetchOnWindowFocus: false,
            // Retry failed requests once (avoid hammering slow yacht internet)
            retry: 1,
            // Don't retry on 4xx errors (client errors won't be fixed by retrying)
            retryOnMount: false,
          },
          mutations: {
            // Retry mutations once
            retry: 1,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {/* Only show devtools in development */}
      {process.env.NODE_ENV === 'development' && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  );
}
