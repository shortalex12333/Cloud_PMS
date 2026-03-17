'use client';

import * as React from 'react';

interface ShowRelatedButtonProps {
  onClick: () => void;
  isOpen: boolean;
  count?: number;   // total related items — shown as badge when > 0
  isLoading?: boolean;
}

export function ShowRelatedButton({ onClick, isOpen, count, isLoading }: ShowRelatedButtonProps) {
  return (
    <button
      onClick={onClick}
      aria-label={isOpen ? 'Close related panel' : 'Show related'}
      aria-expanded={isOpen}
      data-testid="show-related-button"
      className={[
        'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors',
        isOpen
          ? 'bg-surface-elevated text-txt-primary'
          : 'hover:bg-surface-hover text-txt-secondary hover:text-txt-primary',
      ].join(' ')}
    >
      {/* Network/link icon */}
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="18" cy="5" r="3" />
        <circle cx="6" cy="12" r="3" />
        <circle cx="18" cy="19" r="3" />
        <path d="M8.59 13.51l6.83 3.98M15.41 6.51l-6.82 3.98" />
      </svg>
      <span>Related</span>
      {!isLoading && count != null && count > 0 && (
        <span className="px-1.5 py-0.5 bg-accent-primary/20 text-accent-primary rounded text-xs font-medium">
          {count}
        </span>
      )}
      {isLoading && (
        <span className="w-3 h-3 border border-txt-tertiary border-t-txt-secondary rounded-full animate-spin" />
      )}
    </button>
  );
}
