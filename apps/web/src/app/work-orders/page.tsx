'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { EntityList } from '@/features/entity-list/components/EntityList';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { fetchWorkOrders } from '@/features/work-orders/api';
import { workOrderToListResult } from '@/features/work-orders/adapter';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { WorkOrderLensContent } from '@/components/lens/WorkOrderLensContent';
import type { WorkOrder } from '@/features/work-orders/types';

// Main page content
function WorkOrdersPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedId = searchParams.get('id');
  const activeFilter = searchParams.get('filter');

  const handleSelect = React.useCallback(
    (id: string) => {
      const params = new URLSearchParams();
      params.set('id', id);
      if (activeFilter) params.set('filter', activeFilter);
      router.push(`/work-orders?${params.toString()}`, { scroll: false });
    },
    [router, activeFilter]
  );

  const handleCloseDetail = React.useCallback(() => {
    const params = activeFilter ? `?filter=${activeFilter}` : '';
    router.push(`/work-orders${params}`, { scroll: false });
  }, [router, activeFilter]);

  const handleClearFilter = React.useCallback(() => {
    router.push('/work-orders', { scroll: false });
  }, [router]);

  return (
    <div className="h-screen bg-surface-base">
      <EntityList<WorkOrder>
        queryKey={['work-orders']}
        fetchFn={fetchWorkOrders}
        adapter={workOrderToListResult}
        selectedId={selectedId}
        onSelect={handleSelect}
        emptyMessage="No work orders found"
        filter={activeFilter}
        filterDomain="work-orders"
        onClearFilter={handleClearFilter}
      />

      <EntityDetailOverlay
        isOpen={!!selectedId}
        onClose={handleCloseDetail}
      >
        {selectedId && (
          <EntityLensPage
            entityType="work_order"
            entityId={selectedId}
            content={WorkOrderLensContent}
          />
        )}
      </EntityDetailOverlay>
    </div>
  );
}

export default function WorkOrdersPage() {
  return (
    <React.Suspense
      fallback={
        <div className="h-screen flex items-center justify-center bg-surface-base">
          <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
        </div>
      }
    >
      <WorkOrdersPageContent />
    </React.Suspense>
  );
}
