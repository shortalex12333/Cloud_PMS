'use client';

import * as React from 'react';
import type { EntityType, AvailableAction, ActionResult } from '@/types/entity';

export interface EntityLensContextValue {
  entityType: EntityType;
  entityId: string;
  entity: Record<string, unknown> | null;
  availableActions: AvailableAction[];
  isLoading: boolean;
  error: string | null;
  executeAction: (actionId: string, payload?: Record<string, unknown>) => Promise<ActionResult>;
  refetch: () => void;
  /**
   * Returns the AvailableAction entry for this actionId, or null if the backend
   * omitted it (meaning the current role has no permission).
   * null = don't render the button at all.
   * { disabled: true } = render the button greyed out with disabled_reason tooltip.
   */
  getAction: (actionId: string) => AvailableAction | null;
}

const EntityLensContext = React.createContext<EntityLensContextValue | null>(null);

export function EntityLensProvider({
  children,
  value,
}: {
  children: React.ReactNode;
  value: EntityLensContextValue;
}) {
  const enriched = React.useMemo<EntityLensContextValue>(
    () => ({
      ...value,
      getAction: (actionId: string) =>
        value.availableActions.find((a) => a.action_id === actionId) ?? null,
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [value],
  );
  return <EntityLensContext.Provider value={enriched}>{children}</EntityLensContext.Provider>;
}

export function useEntityLensContext(): EntityLensContextValue {
  const ctx = React.useContext(EntityLensContext);
  if (!ctx) {
    throw new Error('useEntityLensContext must be used inside EntityLensProvider');
  }
  return ctx;
}
