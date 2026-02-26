'use client';

/**
 * Work Order Detail Page - /work-orders/[id]
 *
 * Tier 1 fragmented route for viewing a single work order.
 * Provides a full-page detail view with deep linking support.
 *
 * @see REQUIREMENTS_TABLE.md - T1-WO-02
 */

import * as React from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { RouteLayout } from '@/components/layout';
import { isFragmentedRoutesEnabled } from '@/lib/featureFlags';
import { useAuth } from '@/hooks/useAuth';
import { StatusPill } from '@/components/ui/StatusPill';

// Feature flag guard
function FeatureFlagGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const params = useParams();

  React.useEffect(() => {
    if (!isFragmentedRoutesEnabled()) {
      // Redirect to legacy route with entity params
      const id = params.id as string;
      router.replace(`/app?entity=work_order&id=${id}`);
    }
  }, [router, params]);

  if (!isFragmentedRoutesEnabled()) {
    return (
      <div className="h-screen flex items-center justify-center bg-surface-base">
        <p className="text-white/60">Redirecting...</p>
      </div>
    );
  }

  return <>{children}</>;
}

// Fetch work order detail
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

// Loading state
function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
        <p className="text-sm text-white/60">Loading work order...</p>
      </div>
    </div>
  );
}

// Error state
function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center mb-4">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-red-400">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 8v4M12 16h.01" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-white mb-2">Failed to Load</h3>
      <p className="text-sm text-white/60 max-w-sm mb-4">{message}</p>
      <button
        onClick={onRetry}
        className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors"
      >
        Try Again
      </button>
    </div>
  );
}

// Not found state
function NotFoundState() {
  const router = useRouter();

  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-white/40">
          <path d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-white mb-2">Work Order Not Found</h3>
      <p className="text-sm text-white/60 max-w-sm mb-4">
        This work order may have been deleted or you may not have access.
      </p>
      <button
        onClick={() => router.push('/work-orders')}
        className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors"
      >
        Back to Work Orders
      </button>
    </div>
  );
}

// Work order detail content
function WorkOrderContent({
  data,
  onBack,
  onNavigate,
}: {
  data: Record<string, unknown>;
  onBack: () => void;
  onNavigate: (entityType: string, entityId: string) => void;
}) {
  const title = (data?.title || 'Work Order') as string;
  const woNumber = data?.wo_number as string;
  const status = (data?.status || '') as string;
  const priority = (data?.priority || '') as string;
  const description = data?.description as string;
  const equipmentId = data?.equipment_id as string;
  const equipmentName = data?.equipment_name as string;
  const assignedTo = data?.assigned_to_name as string;
  const createdAt = data?.created_at as string;
  const notes = (data?.notes || []) as Array<{ id: string; note_text: string; created_at: string }>;

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <p className="text-xs text-white/40 font-mono">{woNumber}</p>
        <h1 className="text-2xl font-semibold text-white">{title}</h1>
        <div className="flex gap-2">
          <StatusPill status={getStatusColor(status)} label={status.replace(/_/g, ' ')} />
          {priority && (
            <StatusPill
              status={priority === 'critical' || priority === 'emergency' ? 'critical' : priority === 'high' ? 'warning' : 'neutral'}
              label={priority}
            />
          )}
        </div>
      </div>

      {/* Description */}
      {description && (
        <div className="space-y-2">
          <h2 className="text-sm font-medium text-white/60 uppercase tracking-wider">Description</h2>
          <p className="text-white/80">{description}</p>
        </div>
      )}

      {/* Metadata */}
      <div className="grid grid-cols-2 gap-4">
        {equipmentId && (
          <div className="space-y-1">
            <p className="text-xs text-white/40">Equipment</p>
            <button
              onClick={() => onNavigate('equipment', equipmentId)}
              className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
              data-testid="equipment-link"
              data-navigate="equipment"
            >
              {equipmentName || equipmentId}
            </button>
          </div>
        )}
        {assignedTo && (
          <div className="space-y-1">
            <p className="text-xs text-white/40">Assigned To</p>
            <p className="text-sm text-white/80">{assignedTo}</p>
          </div>
        )}
        {createdAt && (
          <div className="space-y-1">
            <p className="text-xs text-white/40">Created</p>
            <p className="text-sm text-white/80">{new Date(createdAt).toLocaleDateString()}</p>
          </div>
        )}
      </div>

      {/* Notes */}
      {notes.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-white/60 uppercase tracking-wider">Notes</h2>
          <div className="space-y-2">
            {notes.map((note) => (
              <div key={note.id} className="p-3 bg-white/5 rounded-lg">
                <p className="text-sm text-white/80">{note.note_text}</p>
                <p className="text-xs text-white/40 mt-1">
                  {new Date(note.created_at).toLocaleString()}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 pt-4 border-t border-white/10">
        <button className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors">
          Add Note
        </button>
        <button className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors">
          Mark Complete
        </button>
      </div>
    </div>
  );
}

// Main page content
function WorkOrderDetailPageContent() {
  const router = useRouter();
  const params = useParams();
  const { session } = useAuth();
  const token = session?.access_token;

  const workOrderId = params.id as string;

  // Fetch work order
  const {
    data: workOrder,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['work-order', workOrderId],
    queryFn: () => fetchWorkOrderDetail(workOrderId, token || ''),
    enabled: !!workOrderId && !!token,
    staleTime: 30000,
    retry: 1,
  });

  // Handle back navigation
  const handleBack = React.useCallback(() => {
    router.back();
  }, [router]);

  // Handle close (go to list)
  const handleClose = React.useCallback(() => {
    router.push('/work-orders');
  }, [router]);

  // Handle refresh
  const handleRefresh = React.useCallback(() => {
    refetch();
  }, [refetch]);

  // Handle cross-entity navigation
  const handleNavigate = React.useCallback(
    (entityType: string, entityId: string) => {
      if (isFragmentedRoutesEnabled()) {
        switch (entityType) {
          case 'equipment':
            router.push(`/equipment/${entityId}`);
            break;
          case 'fault':
            router.push(`/faults/${entityId}`);
            break;
          case 'part':
            router.push(`/inventory/${entityId}`);
            break;
          default:
            router.push(`/app?entity=${entityType}&id=${entityId}`);
        }
      } else {
        router.push(`/app?entity=${entityType}&id=${entityId}`);
      }
    },
    [router]
  );

  // Derive display values
  const payload = workOrder?.payload as Record<string, unknown> | undefined;
  const title = (workOrder?.title || payload?.title || 'Work Order') as string;
  const woNumber = (workOrder?.wo_number || payload?.wo_number) as string | undefined;

  // Render content based on state
  let content: React.ReactNode;

  if (isLoading) {
    content = <LoadingState />;
  } else if (error) {
    const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';
    if (errorMessage.includes('404')) {
      content = <NotFoundState />;
    } else {
      content = <ErrorState message={errorMessage} onRetry={handleRefresh} />;
    }
  } else if (!workOrder) {
    content = <NotFoundState />;
  } else {
    content = (
      <WorkOrderContent
        data={workOrder}
        onBack={handleBack}
        onNavigate={handleNavigate}
      />
    );
  }

  return (
    <RouteLayout
      pageTitle={woNumber ? `${woNumber} — ${title}` : title}
      showTopNav={true}
      topNavContent={
        <div className="flex items-center gap-4">
          <button
            onClick={handleBack}
            className="p-2 hover:bg-white/5 rounded-lg transition-colors"
            aria-label="Back"
            data-testid="back-button"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-white/60">
              <path d="M15 18l-6-6 6-6" />
            </svg>
          </button>
          <div>
            <p className="text-xs text-white/40 uppercase tracking-wider">Work Order</p>
            <h1 className="text-lg font-semibold text-white truncate max-w-md">
              {woNumber ? `${woNumber} — ${title}` : title}
            </h1>
          </div>
        </div>
      }
    >
      {content}
    </RouteLayout>
  );
}

// Export with feature flag guard
export default function WorkOrderDetailPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense fallback={<LoadingState />}>
        <WorkOrderDetailPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
