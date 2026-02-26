'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { isFragmentedRoutesEnabled } from '@/lib/featureFlags';
import { useAuth } from '@/hooks/useAuth';
import { EntityList } from '@/features/entity-list/components/EntityList';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { fetchWorkOrders, fetchWorkOrder } from '@/features/work-orders/api';
import { workOrderToListResult } from '@/features/work-orders/adapter';
import { WorkOrderLensContent } from '@/components/lens/WorkOrderLensContent';
import type { WorkOrder } from '@/features/work-orders/types';

// Feature flag guard
function FeatureFlagGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  React.useEffect(() => {
    if (!isFragmentedRoutesEnabled()) {
      router.replace('/app');
    }
  }, [router]);

  if (!isFragmentedRoutesEnabled()) {
    return (
      <div className="h-screen flex items-center justify-center bg-surface-base">
        <p className="text-white/60">Redirecting...</p>
      </div>
    );
  }

  return <>{children}</>;
}

// Main page content
function WorkOrdersPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { session } = useAuth();
  const token = session?.access_token;
  const selectedId = searchParams.get('id');
  const activeFilter = searchParams.get('filter');

  // Fetch work order data when selectedId is present
  const { data: workOrderData, isLoading, error } = useQuery({
    queryKey: ['work-order', selectedId],
    queryFn: () => fetchWorkOrder(selectedId!, token || ''),
    enabled: !!token && !!selectedId,
    staleTime: 30000,
  });

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

  const handleRefresh = React.useCallback(() => {
    if (selectedId) {
      queryClient.invalidateQueries({ queryKey: ['work-order', selectedId] });
    }
    queryClient.invalidateQueries({ queryKey: ['work-orders'] });
  }, [queryClient, selectedId]);

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
          isLoading ? (
            <div className="flex items-center justify-center h-full">
              <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
            </div>
          ) : error || !workOrderData ? (
            <div className="flex items-center justify-center h-full">
              <p className="text-red-400">Failed to load work order</p>
            </div>
          ) : (
            <WorkOrderLensContent
              id={selectedId}
              data={workOrderData as unknown as Record<string, unknown>}
              onBack={handleCloseDetail}
              onClose={handleCloseDetail}
              onRefresh={handleRefresh}
            />
          )
        )}
      </EntityDetailOverlay>
    </div>
  );
}

export default function WorkOrdersPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense
        fallback={
          <div className="h-screen flex items-center justify-center bg-surface-base">
            <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
          </div>
        }
      >
        <WorkOrdersPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
