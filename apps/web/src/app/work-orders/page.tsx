'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { FilteredEntityList } from '@/features/entity-list/components/FilteredEntityList';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { EntityLensPage } from '@/components/lens/EntityLensPage';
import { WorkOrderContent } from '@/components/lens-v2/entity';
import lensStyles from '@/components/lens-v2/lens.module.css';
import { workOrderToListResult } from '@/features/work-orders/adapter';
import { WORK_ORDER_FILTERS } from '@/features/entity-list/types/filter-config';
import type { WorkOrder } from '@/features/work-orders/types';

function LensContent() {
  return <div className={lensStyles.root}><WorkOrderContent /></div>;
}

function WorkOrdersPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedId = searchParams.get('id');

  const handleSelect = React.useCallback(
    (id: string) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set('id', id);
      router.push(`/work-orders?${params.toString()}`, { scroll: false });
    },
    [router, searchParams]
  );

  const handleCloseDetail = React.useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete('id');
    const qs = params.toString();
    router.push(`/work-orders${qs ? `?${qs}` : ''}`, { scroll: false });
  }, [router, searchParams]);

  return (
    <div className="h-full bg-surface-base">
      <FilteredEntityList<WorkOrder>
        domain="work-orders"
        queryKey={['work-orders']}
        table="v_work_orders_enriched"
        columns="id, title, description, status, priority, wo_number, equipment_id, equipment_name, assigned_to, assigned_to_name, due_date, created_at, updated_at"
        adapter={workOrderToListResult}
        filterConfig={WORK_ORDER_FILTERS}
        selectedId={selectedId}
        onSelect={handleSelect}
        emptyMessage="No work orders found"
        sortBy="created_at"
      />

      <EntityDetailOverlay isOpen={!!selectedId} onClose={handleCloseDetail}>
        {selectedId && (
          <EntityLensPage entityType="work_order" entityId={selectedId} content={LensContent} />
        )}
      </EntityDetailOverlay>
    </div>
  );
}

export default function WorkOrdersPage() {
  return (
    <React.Suspense
      fallback={
        <div className="h-full flex items-center justify-center bg-surface-base">
          <div style={{ width: '32px', height: '32px', border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%' }} className="animate-spin" />
        </div>
      }
    >
      <WorkOrdersPageContent />
    </React.Suspense>
  );
}
