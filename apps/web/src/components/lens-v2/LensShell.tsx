'use client';

/**
 * LensShell — Outer shell for lens-v2 entity views.
 * Matches prototype panel: 720px, asymmetric borders, glass header, scroll body.
 * Wraps content in EntityLensProvider (same data contract as production).
 *
 * During Phase 3 (atomic swap), route pages change their import from
 * EntityLensPage to LensShell. Data layer is identical.
 */

import * as React from 'react';
import { useRouter } from 'next/navigation';
import styles from './lens.module.css';
import { LensGlassHeader } from './LensGlassHeader';
import { useEntityLens } from '@/hooks/useEntityLens';
import { EntityLensProvider } from '@/contexts/EntityLensContext';
import type { EntityType } from '@/types/entity';

export interface LensShellProps {
  /** Entity type for data fetch (e.g. 'work_order', 'equipment') */
  entityType: EntityType;
  /** Entity UUID */
  entityId: string;
  /** Display label for header (e.g. "Work Order", "Equipment") */
  entityLabel: string;
  /** The entity-specific content component */
  children: React.ReactNode;
}

export function LensShell({
  entityType,
  entityId,
  entityLabel,
  children,
}: LensShellProps) {
  const router = useRouter();
  const lens = useEntityLens(entityType, entityId);

  const handleBack = React.useCallback(() => router.back(), [router]);
  const handleClose = React.useCallback(() => {
    const listRoute = `/${entityType.replace(/_/g, '-')}s`;
    router.push(listRoute);
  }, [router, entityType]);

  // All hooks MUST be above any conditional return (React rules of hooks)
  const contextValue = React.useMemo(
    () => ({
      entityType,
      entityId,
      entity: lens.entity,
      availableActions: lens.availableActions,
      isLoading: lens.isLoading,
      error: lens.error,
      executeAction: lens.executeAction,
      refetch: lens.refetch,
      getAction: lens.getAction,
    }),
    [entityType, entityId, lens]
  );

  // Derive body content based on state
  let bodyContent: React.ReactNode;
  if (lens.isLoading && !lens.entity) {
    bodyContent = <div className={styles.emptyState}>Loading…</div>;
  } else if (lens.error) {
    bodyContent = (
      <div className={styles.emptyState}>
        {lens.error === 'not_found'
          ? `${entityLabel} not found.`
          : `Error loading ${entityLabel.toLowerCase()}.`}
      </div>
    );
  } else {
    bodyContent = (
      <EntityLensProvider value={contextValue}>
        {children}
      </EntityLensProvider>
    );
  }

  return (
    <div className={styles.root} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '24px 16px 48px', minHeight: '100vh' }}>
      <div className={styles.panel}>
        <LensGlassHeader
          entityType={entityLabel}
          onBack={handleBack}
          onClose={handleClose}
        />
        <div className={styles.lensBody}>
          {bodyContent}
        </div>
      </div>
    </div>
  );
}
