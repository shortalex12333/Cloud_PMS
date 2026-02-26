'use client';

import { createContext, useMemo, ReactNode } from 'react';
import { DOMAIN_CATALOG, DomainRoute, ObjectType } from './catalog';

export interface DomainContextValue {
  route: DomainRoute | null;
  objectType: ObjectType | null;
  label: string | null;
  apiPath: string | null;
}

export const DomainContext = createContext<DomainContextValue>({
  route: null,
  objectType: null,
  label: null,
  apiPath: null,
});

interface DomainProviderProps {
  route: DomainRoute;
  children: ReactNode;
}

export function DomainProvider({ route, children }: DomainProviderProps) {
  const config = DOMAIN_CATALOG[route];

  const value = useMemo<DomainContextValue>(() => ({
    route,
    objectType: config.objectType,
    label: config.label,
    apiPath: config.apiPath,
  }), [route, config]);

  return (
    <DomainContext.Provider value={value}>
      {children}
    </DomainContext.Provider>
  );
}
