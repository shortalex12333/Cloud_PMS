'use client';

/**
 * BackdropRoot
 *
 * Client-side root that holds the LensBackdrop ref and provides
 * BackdropContext so any component can call `useBackdrop().triggerPulse()`.
 *
 * Place this inside <body> in the root layout — it renders nothing visible
 * beyond the fixed backdrop layer.
 */

import { useRef, useCallback, type ReactNode } from 'react';
import LensBackdrop, { type LensBackdropHandle } from './LensBackdrop';
import { BackdropProvider } from '@/contexts/BackdropContext';

export default function BackdropRoot({ children }: { children: ReactNode }) {
  const backdropRef = useRef<LensBackdropHandle>(null);

  const handlePulse = useCallback(() => {
    backdropRef.current?.triggerPulse();
  }, []);

  return (
    <BackdropProvider onPulse={handlePulse}>
      <LensBackdrop ref={backdropRef} />
      {children}
    </BackdropProvider>
  );
}
