'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { EntityList } from '@/features/entity-list/components/EntityList';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { FaultLensContent } from '@/components/lens/FaultLensContent';
import { fetchFaults } from '@/features/faults/api';
import { faultToListResult } from '@/features/faults/adapter';
import type { Fault } from '@/features/faults/types';

interface FaultDetailContentProps {
  id: string;
  onClose: () => void;
}

function FaultDetailContent({ id }: FaultDetailContentProps) {
  return <EntityLensPage entityType="fault" entityId={id} content={FaultLensContent} />;
}

function FaultsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedId = searchParams.get('id');
  const activeFilter = searchParams.get('filter');

  const handleSelect = React.useCallback(
    (id: string) => {
      const params = new URLSearchParams();
      params.set('id', id);
      if (activeFilter) params.set('filter', activeFilter);
      router.push(`/faults?${params.toString()}`, { scroll: false });
    },
    [router, activeFilter]
  );

  const handleCloseDetail = React.useCallback(() => {
    const params = activeFilter ? `?filter=${activeFilter}` : '';
    router.push(`/faults${params}`, { scroll: false });
  }, [router, activeFilter]);

  const handleClearFilter = React.useCallback(() => {
    router.push('/faults', { scroll: false });
  }, [router]);

  return (
    <div className="h-screen bg-surface-base">
      <EntityList<Fault>
        queryKey={['faults']}
        fetchFn={fetchFaults}
        adapter={faultToListResult}
        selectedId={selectedId}
        onSelect={handleSelect}
        emptyMessage="No faults found"
        filter={activeFilter}
        filterDomain="faults"
        onClearFilter={handleClearFilter}
      />

      <EntityDetailOverlay isOpen={!!selectedId} onClose={handleCloseDetail}>
        {selectedId && <FaultDetailContent id={selectedId} onClose={handleCloseDetail} />}
      </EntityDetailOverlay>
    </div>
  );
}

export default function FaultsPage() {
  return (
    <React.Suspense
      fallback={
        <div className="h-screen flex items-center justify-center bg-surface-base">
          <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
        </div>
      }
    >
      <FaultsPageContent />
    </React.Suspense>
  );
}
