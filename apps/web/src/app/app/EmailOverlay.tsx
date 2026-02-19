'use client';

/**
 * EmailOverlay - Full-width email slide-in overlay
 *
 * Wraps EmailSurface in a fixed position overlay that slides in from the left.
 * Uses SurfaceContext for state management (no URL changes).
 *
 * Width: 95% viewport (allows 3-column EmailSurface to render properly)
 * vs narrow 384px panel which would force 1-column layout.
 */

import { useEffect, useCallback, useState } from 'react';
import { createPortal } from 'react-dom';
import { useSurface } from '@/contexts/SurfaceContext';
import EmailSurface from '@/components/email/EmailSurface';

export default function EmailOverlay() {
  const { emailPanel, hideEmail } = useSurface();
  const [mounted, setMounted] = useState(false);

  // Handle client-side mounting for portal
  useEffect(() => {
    setMounted(true);
  }, []);

  // ESC key to close
  useEffect(() => {
    if (!emailPanel.visible) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        hideEmail();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [emailPanel.visible, hideEmail]);

  // Prevent body scroll when overlay is open
  useEffect(() => {
    if (emailPanel.visible) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [emailPanel.visible]);

  // Don't render anything on server or if not mounted
  if (!mounted || typeof window === 'undefined') {
    return null;
  }

  if (!emailPanel.visible) return null;

  const overlayContent = (
    <>
      {/* Backdrop */}
      <div
        data-testid="email-overlay-backdrop"
        className="fixed inset-0 z-[1000] bg-black/60 backdrop-blur-sm transition-opacity duration-300"
        onClick={hideEmail}
        aria-hidden="true"
      />

      {/* Email Surface Overlay */}
      <div
        data-testid="email-overlay"
        className="fixed inset-y-0 left-0 z-[1001] w-[95vw] max-w-[1400px] bg-surface-base border-r border-[#e7e7e7] dark:border-[#404040] transform transition-transform duration-300 ease-out translate-x-0"
      >
        <EmailSurface
          className="h-full"
          initialThreadId={emailPanel.threadId}
          onClose={hideEmail}
        />
      </div>
    </>
  );

  // Portal to document.body to avoid z-index/overflow issues
  return createPortal(overlayContent, document.body);
}
