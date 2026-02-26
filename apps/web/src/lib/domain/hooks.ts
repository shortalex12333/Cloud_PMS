'use client';

import { useContext } from 'react';
import { DomainContext, DomainContextValue } from './context';

/**
 * Hook to access current domain context
 * Returns null values when not within a DomainProvider
 */
export function useDomain(): DomainContextValue {
  return useContext(DomainContext);
}

/**
 * Hook to check if currently in a domain-scoped context
 */
export function useIsInDomain(): boolean {
  const { route } = useDomain();
  return route !== null;
}
