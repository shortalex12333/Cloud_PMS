'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { EntityList } from '@/features/entity-list/components/EntityList';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { EquipmentLensContent } from '@/components/lens/EquipmentLensContent';
import { fetchEquipment } from '@/features/equipment/api';
import { equipmentToListResult } from '@/features/equipment/adapter';
import type { Equipment } from '@/features/equipment/types';

function EquipmentPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedId = searchParams.get('id');

  const handleSelect = React.useCallback(
    (id: string) => {
      router.push(`/equipment?id=${id}`, { scroll: false });
    },
    [router]
  );

  const handleCloseDetail = React.useCallback(() => {
    router.push('/equipment', { scroll: false });
  }, [router]);

  return (
    <div className="h-screen bg-surface-base">
      <EntityList<Equipment>
        queryKey={['equipment']}
        fetchFn={fetchEquipment}
        adapter={equipmentToListResult}
        selectedId={selectedId}
        onSelect={handleSelect}
        emptyMessage="No equipment found"
      />

      <EntityDetailOverlay isOpen={!!selectedId} onClose={handleCloseDetail}>
        {selectedId && (
          <EntityLensPage
            entityType="equipment"
            entityId={selectedId}
            content={EquipmentLensContent}
          />
        )}
      </EntityDetailOverlay>
    </div>
  );
}

export default function EquipmentPage() {
  return (
    <React.Suspense
      fallback={
        <div className="h-screen flex items-center justify-center bg-surface-base">
          <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
        </div>
      }
    >
      <EquipmentPageContent />
    </React.Suspense>
  );
}
