'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { FilteredEntityList } from '@/features/entity-list/components/FilteredEntityList';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { FaultContent } from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';
import { faultToListResult } from '@/features/faults/adapter';
import { FAULT_FILTERS } from '@/features/entity-list/types/filter-config';
import type { Fault } from '@/features/faults/types';

function LensContent() {
  return <div className={lensStyles.root}><FaultContent /></div>;
}

function FaultsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedId = searchParams.get('id');

  const handleSelect = React.useCallback(
    (id: string) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set('id', id);
      router.push(`/faults?${params.toString()}`, { scroll: false });
    },
    [router, searchParams]
  );

  const handleCloseDetail = React.useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete('id');
    const qs = params.toString();
    router.push(`/faults${qs ? `?${qs}` : ''}`, { scroll: false });
  }, [router, searchParams]);

  return (
    <div className="h-full bg-surface-base">
      <FilteredEntityList<Fault>
        domain="faults"
        queryKey={['faults']}
        table="pms_faults"
        columns="id, title, description, status, severity, fault_code, equipment_id, detected_at, resolved_at, created_at, updated_at"
        adapter={faultToListResult}
        filterConfig={FAULT_FILTERS}
        selectedId={selectedId}
        onSelect={handleSelect}
        emptyMessage="No faults found"
        sortBy="created_at"
      />

      <EntityDetailOverlay isOpen={!!selectedId} onClose={handleCloseDetail}>
        {selectedId && (
          <EntityLensPage entityType="fault" entityId={selectedId} content={LensContent} />
        )}
      </EntityDetailOverlay>
    </div>
  );
}

export default function FaultsPage() {
  return (
    <React.Suspense
      fallback={
        <div className="h-full flex items-center justify-center bg-surface-base">
          <div style={{ width: '32px', height: '32px', border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%' }} className="animate-spin" />
        </div>
      }
    >
      <FaultsPageContent />
    </React.Suspense>
  );
}
