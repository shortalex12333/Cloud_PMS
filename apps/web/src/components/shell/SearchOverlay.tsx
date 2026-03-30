'use client';

/**
 * SearchOverlay — Global search overlay triggered from the Topbar
 *
 * Renders the existing SpotlightSearch in modal mode over the AppShell.
 * Triggered by:
 *   - Clicking the topbar search input
 *   - Pressing Cmd+K
 *
 * This reconnects the global search that was previously on the home
 * page to the new persistent topbar. Same search, different trigger.
 */

import * as React from 'react';
import dynamic from 'next/dynamic';

// Dynamic import to avoid SSR issues with SpotlightSearch's heavy dependencies
const SpotlightSearch = dynamic(
  () => import('@/components/spotlight/SpotlightSearch'),
  { ssr: false }
);

interface SearchOverlayProps {
  open: boolean;
  onClose: () => void;
}

export function SearchOverlay({ open, onClose }: SearchOverlayProps) {
  // Close on Escape
  React.useEffect(() => {
    if (!open) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    }
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 200,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'flex-start',
        paddingTop: '10vh',
        background: 'var(--overlay-bg)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
      }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '100%',
          maxWidth: 660,
          padding: '0 20px',
        }}
      >
        <SpotlightSearch onClose={onClose} isModal />
      </div>
    </div>
  );
}
