'use client';

/**
 * LensGlassHeader — Glass nav bar for lens-v2.
 * Matches prototype lens-hdr: 56px, frosted glass, back/type/related/theme/close.
 */

import * as React from 'react';
import styles from './lens.module.css';

export interface LensGlassHeaderProps {
  entityType: string;
  onBack?: () => void;
  onShowRelated?: () => void;
  onClose?: () => void;
}

export function LensGlassHeader({
  entityType,
  onBack,
  onShowRelated,
  onClose,
}: LensGlassHeaderProps) {
  const handleThemeToggle = React.useCallback(() => {
    const html = document.documentElement;
    const current = html.getAttribute('data-theme');
    html.setAttribute('data-theme', current === 'light' ? 'dark' : 'light');
  }, []);

  return (
    <div className={styles.lensHdr}>
      {onBack && (
        <button className={styles.hdrBack} onClick={onBack} aria-label="Go back">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M10 12L6 8l4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      )}

      <span className={styles.hdrType}>{entityType}</span>

      <div className={styles.hdrActions}>
        {onShowRelated && (
          <button className={styles.hdrBtn} onClick={onShowRelated} aria-label="Show related">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
              <path d="M6.5 9.5l3-3M5.75 11.75L4 13.5a1.77 1.77 0 01-2.5-2.5l1.75-1.75M12.25 6.25L14 4.5A1.77 1.77 0 0011.5 2L9.75 3.75" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <span>Show Related</span>
          </button>
        )}

        <button className={styles.hdrBtn} onClick={handleThemeToggle} aria-label="Toggle theme">
          <svg className={styles.iconMoon} width="14" height="14" viewBox="0 0 16 16" fill="none">
            <path d="M14 8.5A6 6 0 117.5 2a4.5 4.5 0 006.5 6.5z" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <svg className={styles.iconSun} width="14" height="14" viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="8" r="3" stroke="currentColor" strokeWidth="1.3" />
            <path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41M3.05 12.95l1.41-1.41M11.54 4.46l1.41-1.41" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
          </svg>
        </button>

        {onClose && (
          <button className={styles.hdrClose} onClick={onClose} aria-label="Close">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
              <path d="M12 4L4 12M4 4l8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}
