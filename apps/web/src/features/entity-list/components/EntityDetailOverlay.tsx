'use client';

import { useEffect, useCallback } from 'react';
import { cn } from '@/lib/utils';
import type { EntityDetailOverlayProps } from '../types';

export function EntityDetailOverlay({
  isOpen,
  onClose,
  children,
}: EntityDetailOverlayProps) {
  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Prevent body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop - 10% visibility of list behind */}
      <div
        className="absolute inset-0 bg-black/90"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Overlay content - 90% of screen */}
      <div
        className={cn(
          'relative z-10',
          'w-[90vw] h-[90vh]',
          'bg-surface-base',
          'rounded-lg',
          'shadow-2xl',
          'overflow-hidden',
          'flex flex-col'
        )}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className={cn(
            'absolute top-4 right-4 z-20',
            'p-2 rounded-lg',
            'hover:bg-white/10 transition-colors',
            'text-white/60 hover:text-white'
          )}
          aria-label="Close"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {children}
        </div>
      </div>
    </div>
  );
}
