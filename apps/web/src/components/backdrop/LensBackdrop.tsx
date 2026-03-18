'use client';

/**
 * LensBackdrop
 *
 * Fixed full-screen layer (z-index: -1) behind all content.
 * Renders three blurred color orbs whose colors transition when the
 * active route changes — giving each lens its own ambient identity.
 *
 * Glass elements (`backdrop-filter: blur()`) refract this layer,
 * giving the frosted-glass effect depth and color.
 *
 * Usage: place once in the root layout, above <AuthDebug />.
 */

import { useEffect, useState, useCallback, useImperativeHandle, forwardRef } from 'react';
import { usePathname } from 'next/navigation';
import { matchLensPalette, type LensPalette } from './lensColors';

export interface LensBackdropHandle {
  triggerPulse: () => void;
}

const LensBackdrop = forwardRef<LensBackdropHandle>((_, ref) => {
  const pathname = usePathname();
  const [palette, setPalette] = useState<LensPalette>(matchLensPalette(pathname));
  const [isPulsing, setIsPulsing] = useState(false);

  // Update palette on route change
  useEffect(() => {
    setPalette(matchLensPalette(pathname));
  }, [pathname]);

  // Pulse: briefly brighten orbs on action confirmation
  const triggerPulse = useCallback(() => {
    setIsPulsing(true);
    const t = setTimeout(() => setIsPulsing(false), 900);
    return () => clearTimeout(t);
  }, []);

  useImperativeHandle(ref, () => ({ triggerPulse }), [triggerPulse]);

  const [primary, secondary, accent] = palette.orbs;

  // Pulse multiplies opacity by ~1.6 via scale — done via CSS class + keyframe
  return (
    <div
      aria-hidden="true"
      className={`lens-backdrop${isPulsing ? ' lens-backdrop--pulse' : ''}`}
    >
      {/* Orb 1 — top-left, largest */}
      <div
        className="lens-orb lens-orb--1"
        style={{ background: `radial-gradient(circle, ${primary} 0%, transparent 70%)` }}
      />
      {/* Orb 2 — bottom-right, medium */}
      <div
        className="lens-orb lens-orb--2"
        style={{ background: `radial-gradient(circle, ${secondary} 0%, transparent 70%)` }}
      />
      {/* Orb 3 — center, subtle */}
      <div
        className="lens-orb lens-orb--3"
        style={{ background: `radial-gradient(circle, ${accent} 0%, transparent 70%)` }}
      />
    </div>
  );
});

LensBackdrop.displayName = 'LensBackdrop';
export default LensBackdrop;
