'use client';

/**
 * EmailOverlay - Full-width email panel that slides from left
 *
 * Wraps EmailSurface in an overlay for single-surface architecture.
 * Uses portal to document.body to avoid z-index/overflow issues.
 * Width: 95% viewport, max 1400px
 * Triggered by: Email scope toggle in SpotlightSearch
 */

import { useCallback, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import EmailSurface from '@/components/email/EmailSurface';

interface EmailOverlayProps {
  open: boolean;
  initialThreadId?: string | null;
  initialFolder?: 'inbox' | 'sent';
  onClose: () => void;
}

export default function EmailOverlay({
  open,
  initialThreadId,
  initialFolder = 'inbox',
  onClose,
}: EmailOverlayProps) {
  const [mounted, setMounted] = useState(false);

  // Handle client-side mounting for portal
  useEffect(() => {
    setMounted(true);
  }, []);

  // Handle ESC key to close overlay
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) {
        onClose();
      }
    };

    if (open) {
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }
  }, [open, onClose]);

  // Handle backdrop click
  const handleBackdropClick = useCallback(() => {
    onClose();
  }, [onClose]);

  // Don't render anything on server or if not mounted
  if (!mounted || typeof window === 'undefined') {
    return null;
  }

  // Don't render if not open
  if (!open) {
    return null;
  }

  const overlayContent = (
    <>
      {/* Backdrop */}
      <div
        data-testid="email-overlay-backdrop"
        className="fixed inset-0 z-[1000] bg-black/50 transition-opacity duration-300"
        onClick={handleBackdropClick}
        aria-hidden="true"
      />

      {/* Email Panel */}
      <div
        data-testid="email-overlay"
        className="fixed inset-y-0 left-0 z-[1001] w-[95vw] max-w-[1400px] bg-[#1c1c1e] shadow-2xl transform transition-transform duration-300 ease-out translate-x-0"
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 z-[1002] p-2 rounded-lg bg-gray-800/80 hover:bg-gray-700 text-gray-300 hover:text-white transition-colors"
          aria-label="Close email overlay"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>

        <EmailSurface
          className="h-full"
          initialThreadId={initialThreadId || undefined}
          initialFolder={initialFolder}
          onClose={onClose}
        />
      </div>
    </>
  );

  // Portal to document.body to avoid z-index/overflow issues
  return createPortal(overlayContent, document.body);
}
