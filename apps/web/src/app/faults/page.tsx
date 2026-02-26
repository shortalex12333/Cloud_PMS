'use client';

/**
 * Faults List Page - /faults
 *
 * Tier 1 fragmented route for faults.
 * Displays a list of faults with the ability to select and view details.
 *
 * @see REQUIREMENTS_TABLE.md - T1-F-01
 */

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { RouteLayout } from '@/components/layout';
import { isFragmentedRoutesEnabled } from '@/lib/featureFlags';
import { useAuth } from '@/hooks/useAuth';
import { StatusPill } from '@/components/ui/StatusPill';
import { cn } from '@/lib/utils';

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
      <div className="h-screen flex items-center justify-center bg-[#0a0a0a]">
        <p className="text-white/60">Redirecting...</p>
      </div>
    );
  }

  return <>{children}</>;
}

// Fault list item type
interface FaultListItem {
  id: string;
  title: string;
  severity: string;
  status: string;
  equipment_name?: string;
  reported_by_name?: string;
  reported_at: string;
}

// Fetch faults from API
async function fetchFaults(yachtId: string, token: string): Promise<FaultListItem[]> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/faults?yacht_id=${yachtId}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch faults: ${response.status}`);
  }

  const data = await response.json();
  return data.faults || data.items || data || [];
}

// Fetch single fault detail
async function fetchFaultDetail(id: string, token: string): Promise<Record<string, unknown>> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/entity/fault/${id}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch fault: ${response.status}`);
  }

  return response.json();
}

// Severity color mapping
function getSeverityColor(severity: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (severity?.toLowerCase()) {
    case 'critical':
    case 'high':
      return 'critical';
    case 'medium':
      return 'warning';
    case 'low':
      return 'success';
    default:
      return 'neutral';
  }
}

// Status color mapping
function getStatusColor(status: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status?.toLowerCase()) {
    case 'open':
    case 'reported':
      return 'critical';
    case 'in_progress':
    case 'investigating':
      return 'warning';
    case 'resolved':
    case 'closed':
      return 'success';
    default:
      return 'neutral';
  }
}

// Fault List Item Component
function FaultRow({
  item,
  isSelected,
  onClick,
}: {
  item: FaultListItem;
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
            <StatusPill status={getSeverityColor(item.severity)} label={item.severity || 'unknown'} />
            <StatusPill status={getStatusColor(item.status)} label={(item.status || '').replace(/_/g, ' ')} />
          </div>
          <h3 className="text-sm font-medium text-white truncate">{item.title}</h3>
          {item.equipment_name && (
            <p className="text-xs text-white/50 mt-1 truncate">{item.equipment_name}</p>
          )}
        </div>
        <div className="text-xs text-white/40 whitespace-nowrap">
          {new Date(item.reported_at).toLocaleDateString()}
        </div>
      </div>
    </button>
  );
}

// Empty state
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-white/40">
          <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-white mb-2">No Faults Reported</h3>
      <p className="text-sm text-white/60 max-w-sm">
        When equipment issues are reported, they will appear here.
      </p>
    </div>
  );
}

// Loading state
function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
        <p className="text-sm text-white/60">Loading faults...</p>
      </div>
    </div>
  );
}

// Fault detail content
function FaultDetailContent({
  data,
  onBack,
  onClose,
}: {
  data: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
}) {
  const title = (data?.title || 'Fault') as string;
  const severity = (data?.severity || '') as string;
  const status = (data?.status || '') as string;
  const description = data?.description as string;

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-4">
        <button onClick={onBack} className="p-2 hover:bg-white/5 rounded-lg transition-colors" aria-label="Back">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-white/60">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
        <div>
          <h2 className="text-lg font-semibold text-white">{title}</h2>
        </div>
      </div>
      <div className="flex gap-2">
        <StatusPill status={getSeverityColor(severity)} label={severity} />
        <StatusPill status={getStatusColor(status)} label={status.replace(/_/g, ' ')} />
      </div>
      {description && <p className="text-sm text-white/60">{description}</p>}
    </div>
  );
}

// Main page component
function FaultsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, session } = useAuth();
  const token = session?.access_token;

  const selectedId = searchParams.get('id');

  const { data: faults, isLoading: isLoadingList, error: listError, refetch: refetchList } = useQuery({
    queryKey: ['faults', user?.yachtId],
    queryFn: () => fetchFaults(user?.yachtId || '', token || ''),
    enabled: !!user?.yachtId && !!token,
    staleTime: 30000,
  });

  const { data: selectedFault, isLoading: isLoadingDetail, refetch: refetchDetail } = useQuery({
    queryKey: ['fault', selectedId],
    queryFn: () => fetchFaultDetail(selectedId!, token || ''),
    enabled: !!selectedId && !!token,
    staleTime: 30000,
  });

  const handleSelect = React.useCallback((id: string) => {
    router.push(`/faults?id=${id}`, { scroll: false });
  }, [router]);

  const handleCloseDetail = React.useCallback(() => {
    router.push('/faults', { scroll: false });
  }, [router]);

  const handleBack = React.useCallback(() => {
    router.back();
  }, [router]);

  const listContent = React.useMemo(() => {
    if (isLoadingList) return <LoadingState />;
    if (listError) return <div className="flex items-center justify-center h-full"><p className="text-red-400">Failed to load faults</p></div>;
    if (!faults || faults.length === 0) return <EmptyState />;

    return (
      <div className="divide-y divide-white/5">
        {faults.map((fault) => (
          <FaultRow key={fault.id} item={fault} isSelected={fault.id === selectedId} onClick={() => handleSelect(fault.id)} />
        ))}
      </div>
    );
  }, [faults, isLoadingList, listError, selectedId, handleSelect]);

  return (
    <RouteLayout
      pageTitle="Faults"
      showTopNav={true}
      topNavContent={<div className="flex items-center gap-4"><h1 className="text-lg font-semibold text-white">Faults</h1></div>}
      primaryPanel={selectedId ? {
        visible: true,
        title: selectedFault?.title as string || 'Fault',
        children: isLoadingDetail ? <LoadingState /> : selectedFault ? <FaultDetailContent data={selectedFault} onBack={handleBack} onClose={handleCloseDetail} /> : null,
      } : undefined}
      onClosePrimaryPanel={handleCloseDetail}
    >
      {listContent}
    </RouteLayout>
  );
}

export default function FaultsPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense fallback={<LoadingState />}>
        <FaultsPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
