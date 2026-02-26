'use client';

import { useDomain } from '@/lib/domain/hooks';

interface EmptyStateProps {
  message?: string;
}

export function EmptyState({ message }: EmptyStateProps) {
  const { label } = useDomain();

  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4">
        <svg
          width="32"
          height="32"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="text-white/40"
        >
          <circle cx="11" cy="11" r="8" />
          <path d="M21 21l-4.35-4.35" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-white mb-2">
        {message || `No ${label || 'items'} found`}
      </h3>
      <p className="text-sm text-white/60 max-w-sm">
        Search is primary. Use the search bar above to find what you&apos;re looking for.
      </p>
    </div>
  );
}
