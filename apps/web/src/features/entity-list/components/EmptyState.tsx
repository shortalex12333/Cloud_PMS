'use client';

import { useDomain } from '@/lib/domain/hooks';

interface EmptyStateProps {
  message?: string;
}

export function EmptyState({ message }: EmptyStateProps) {
  const { label } = useDomain();
  const domainName = label?.toLowerCase() || 'records';

  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6" data-testid="empty-state">
      <div className="w-16 h-16 rounded-full flex items-center justify-center mb-4" style={{ background: 'var(--split-bg)' }}>
        <svg
          width="32"
          height="32"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="text-txt-tertiary"
        >
          <circle cx="11" cy="11" r="8" />
          <path d="M21 21l-4.35-4.35" />
        </svg>
      </div>
      <h3 style={{ fontSize: 15, fontWeight: 500, color: 'var(--txt3)', marginBottom: 4 }}>
        {message || `No ${domainName} recorded`}
      </h3>
    </div>
  );
}
