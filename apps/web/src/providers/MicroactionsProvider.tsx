'use client';

import { useEffect, useRef } from 'react';
import { registerAllHandlers } from '@/lib/microactions';

/**
 * Microactions Provider
 *
 * Registers all microaction handlers on mount.
 * Must wrap any component that needs to execute microactions.
 */
export function MicroactionsProvider({ children }: { children: React.ReactNode }) {
  const registered = useRef(false);

  useEffect(() => {
    if (!registered.current) {
      registerAllHandlers();
      registered.current = true;
    }
  }, []);

  return <>{children}</>;
}
