'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { FilteredEntityList } from '@/features/entity-list/components/FilteredEntityList';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { EquipmentContent } from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';
import { equipmentToListResult } from '@/features/equipment/adapter';
import { EQUIPMENT_FILTERS } from '@/features/entity-list/types/filter-config';
import type { Equipment } from '@/features/equipment/types';

function LensContent() {
  return <div className={lensStyles.root}><EquipmentContent /></div>;
}

function EquipmentPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedId = searchParams.get('id');

  const handleSelect = React.useCallback(
    (id: string) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set('id', id);
      router.push(`/equipment?${params.toString()}`, { scroll: false });
    },
    [router, searchParams]
  );

  const handleCloseDetail = React.useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete('id');
    const qs = params.toString();
    router.push(`/equipment${qs ? `?${qs}` : ''}`, { scroll: false });
  }, [router, searchParams]);

  return (
    <div className="h-full bg-surface-base">
      <FilteredEntityList<Equipment>
        domain="equipment"
        queryKey={['equipment']}
        table="pms_equipment"
        columns="id, name, description, location, manufacturer, model, serial_number, status, criticality, attention_flag, attention_reason, created_at, updated_at"
        adapter={equipmentToListResult}
        filterConfig={EQUIPMENT_FILTERS}
        selectedId={selectedId}
        onSelect={handleSelect}
        emptyMessage="No equipment found"
        sortBy="name"
      />

      <EntityDetailOverlay isOpen={!!selectedId} onClose={handleCloseDetail}>
        {selectedId && (
          <EntityLensPage entityType="equipment" entityId={selectedId} content={LensContent} />
        )}
      </EntityDetailOverlay>
    </div>
  );
}

export default function EquipmentPage() {
  return (
    <React.Suspense
      fallback={
        <div className="h-full flex items-center justify-center bg-surface-base">
          <div style={{ width: '32px', height: '32px', border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%' }} className="animate-spin" />
        </div>
      }
    >
      <EquipmentPageContent />
    </React.Suspense>
  );
}
