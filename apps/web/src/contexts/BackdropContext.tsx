'use client';

import { createContext, useContext, useCallback, useRef, type ReactNode } from 'react';

interface BackdropContextValue {
  /** Call after a successful save/action to pulse the ambient orbs. */
  triggerPulse: () => void;
}

const BackdropContext = createContext<BackdropContextValue>({
  triggerPulse: () => {},
});

export function useBackdrop() {
  return useContext(BackdropContext);
}

interface BackdropProviderProps {
  children: ReactNode;
  /** Ref forwarded from LensBackdrop to call pulse on. */
  onPulse?: () => void;
}

export function BackdropProvider({ children, onPulse }: BackdropProviderProps) {
  const triggerPulse = useCallback(() => {
    onPulse?.();
  }, [onPulse]);

  return (
    <BackdropContext.Provider value={{ triggerPulse }}>
      {children}
    </BackdropContext.Provider>
  );
}
