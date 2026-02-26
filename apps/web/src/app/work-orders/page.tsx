'use client';

/**
 * Work Orders List Page - /work-orders
 *
 * Tier 1 fragmented route for work orders.
 * Displays a list of work orders with the ability to select and view details.
 *
 * @see REQUIREMENTS_TABLE.md - T1-WO-01
 */

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { RouteLayout } from '@/components/layout';
import { isFragmentedRoutesEnabled } from '@/lib/featureFlags';
import { useAuth } from '@/hooks/useAuth';
import { StatusPill } from '@/components/ui/StatusPill';
import { cn } from '@/lib/utils';

// Feature flag guard - redirect if disabled
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

// Work order list item type
interface WorkOrderListItem {
  id: string;
  wo_number: string;
  title: string;
  status: string;
  priority: string;
  equipment_name?: string;
  assigned_to_name?: string;
  created_at: string;
}

// Fetch work orders from API
async function fetchWorkOrders(yachtId: string, token: string): Promise<WorkOrderListItem[]> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/work-orders?yacht_id=${yachtId}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch work orders: ${response.status}`);
  }

  const data = await response.json();
  return data.work_orders || data.items || data || [];
}

// Fetch single work order detail
async function fetchWorkOrderDetail(id: string, token: string): Promise<Record<string, unknown>> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/entity/work_order/${id}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch work order: ${response.status}`);
  }

  return response.json();
}

// Status color mapping
function getStatusColor(status: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'overdue':
    case 'cancelled':
      return 'critical';
    case 'in_progress':
    case 'pending_parts':
      return 'warning';
    case 'completed':
    case 'closed':
      return 'success';
    default:
      return 'neutral';
  }
}

// Priority color mapping
function getPriorityColor(priority: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (priority) {
    case 'critical':
    case 'emergency':
      return 'critical';
    case 'high':
    case 'important':
      return 'warning';
    default:
      return 'neutral';
  }
}

// Work Order List Item Component
function WorkOrderRow({
  item,
  isSelected,
  onClick,
}: {
  item: WorkOrderListItem;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full text-left px-6 py-4 border-b border-white/5',
        'hover:bg-white/5 transition-colors',
        'focus:outline-none focus:bg-white/5',
        isSelected && 'bg-white/10'
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-white/40 font-mono">{item.wo_number}</span>
            <StatusPill status={getStatusColor(item.status)} label={item.status.replace(/_/g, ' ')} />
            <StatusPill status={getPriorityColor(item.priority)} label={item.priority} />
          </div>
          <h3 className="text-sm font-medium text-white truncate">{item.title}</h3>
          {item.equipment_name && (
            <p className="text-xs text-white/50 mt-1 truncate">{item.equipment_name}</p>
          )}
        </div>
        <div className="text-xs text-white/40 whitespace-nowrap">
          {new Date(item.created_at).toLocaleDateString()}
        </div>
      </div>
    </button>
  );
}

// Empty state component
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-white/40">
          <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-white mb-2">No Work Orders</h3>
      <p className="text-sm text-white/60 max-w-sm">
        Create a work order to track maintenance tasks, repairs, and equipment service.
      </p>
    </div>
  );
}

// Loading state component
function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
        <p className="text-sm text-white/60">Loading work orders...</p>
      </div>
    </div>
  );
}

// Work order detail content (simplified - will use WorkOrderLensContent when available)
function WorkOrderDetailContent({
  data,
  onBack,
  onClose,
}: {
  data: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
}) {
  const title = (data?.title || 'Work Order') as string;
  const woNumber = data?.wo_number as string;
  const status = data?.status as string;
  const description = data?.description as string;

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-4">
        <button
          onClick={onBack}
          className="p-2 hover:bg-white/5 rounded-lg transition-colors"
          aria-label="Back"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-white/60">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
        <div>
          <p className="text-xs text-white/40">{woNumber}</p>
          <h2 className="text-lg font-semibold text-white">{title}</h2>
        </div>
      </div>
      <div className="flex gap-2">
        <StatusPill status={getStatusColor(status || '')} label={(status || '').replace(/_/g, ' ')} />
      </div>
      {description && (
        <p className="text-sm text-white/60">{description}</p>
      )}
    </div>
  );
}

// Main page component
function WorkOrdersPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, session } = useAuth();
  const token = session?.access_token;

  // Get selected ID from URL params
  const selectedId = searchParams.get('id');

  // Fetch work orders list
  const {
    data: workOrders,
    isLoading: isLoadingList,
    error: listError,
    refetch: refetchList,
  } = useQuery({
    queryKey: ['work-orders', user?.yachtId],
    queryFn: () => fetchWorkOrders(user?.yachtId || '', token || ''),
    enabled: !!user?.yachtId && !!token,
    staleTime: 30000,
  });

  // Fetch selected work order detail
  const {
    data: selectedWorkOrder,
    isLoading: isLoadingDetail,
    refetch: refetchDetail,
  } = useQuery({
    queryKey: ['work-order', selectedId],
    queryFn: () => fetchWorkOrderDetail(selectedId!, token || ''),
    enabled: !!selectedId && !!token,
    staleTime: 30000,
  });

  // Handle work order selection
  const handleSelect = React.useCallback(
    (id: string) => {
      router.push(`/work-orders?id=${id}`, { scroll: false });
    },
    [router]
  );

  // Handle close detail panel
  const handleCloseDetail = React.useCallback(() => {
    router.push('/work-orders', { scroll: false });
  }, [router]);

  // Handle back navigation
  const handleBack = React.useCallback(() => {
    router.back();
  }, [router]);

  // Handle refresh
  const handleRefresh = React.useCallback(() => {
    refetchList();
    refetchDetail();
  }, [refetchList, refetchDetail]);

  // Render list content
  const listContent = React.useMemo(() => {
    if (isLoadingList) {
      return <LoadingState />;
    }

    if (listError) {
      return (
        <div className="flex items-center justify-center h-full">
          <p className="text-red-400">Failed to load work orders</p>
        </div>
      );
    }

    if (!workOrders || workOrders.length === 0) {
      return <EmptyState />;
    }

    return (
      <div className="divide-y divide-white/5">
        {workOrders.map((wo) => (
          <WorkOrderRow
            key={wo.id}
            item={wo}
            isSelected={wo.id === selectedId}
            onClick={() => handleSelect(wo.id)}
          />
        ))}
      </div>
    );
  }, [workOrders, isLoadingList, listError, selectedId, handleSelect]);

  return (
    <RouteLayout
      pageTitle="Work Orders"
      showTopNav={true}
      topNavContent={
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-semibold text-white">Work Orders</h1>
        </div>
      }
      primaryPanel={
        selectedId
          ? {
              visible: true,
              title: selectedWorkOrder?.title as string || 'Work Order',
              subtitle: selectedWorkOrder?.wo_number as string,
              children: isLoadingDetail ? (
                <LoadingState />
              ) : selectedWorkOrder ? (
                <WorkOrderDetailContent
                  data={selectedWorkOrder}
                  onBack={handleBack}
                  onClose={handleCloseDetail}
                />
              ) : null,
            }
          : undefined
      }
      onClosePrimaryPanel={handleCloseDetail}
    >
      {listContent}
    </RouteLayout>
  );
}

// Export with feature flag guard
export default function WorkOrdersPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense fallback={<LoadingState />}>
        <WorkOrdersPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
