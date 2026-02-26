'use client';

/**
 * Equipment Detail Page - /equipment/[id]
 *
 * Tier 1 fragmented route for viewing a single equipment item.
 *
 * @see REQUIREMENTS_TABLE.md - T1-EQ-02
 */

import * as React from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { RouteLayout } from '@/components/layout';
import { isFragmentedRoutesEnabled } from '@/lib/featureFlags';
import { useAuth } from '@/hooks/useAuth';
import { StatusPill } from '@/components/ui/StatusPill';

function FeatureFlagGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const params = useParams();
  React.useEffect(() => { if (!isFragmentedRoutesEnabled()) router.replace(`/app?entity=equipment&id=${params.id}`); }, [router, params]);
  if (!isFragmentedRoutesEnabled()) return <div className="h-screen flex items-center justify-center bg-surface-base"><p className="text-white/60">Redirecting...</p></div>;
  return <>{children}</>;
}

async function fetchEquipmentDetail(id: string, token: string): Promise<Record<string, unknown>> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/entity/equipment/${id}`, {
    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(`Failed to fetch equipment: ${response.status}`);
  return response.json();
}

function getStatusColor(status: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status?.toLowerCase()) {
    case 'critical': case 'failed': case 'broken': return 'critical';
    case 'needs_maintenance': case 'degraded': return 'warning';
    case 'operational': case 'good': case 'active': return 'success';
    default: return 'neutral';
  }
}

function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
        <p className="text-sm text-white/60">Loading equipment...</p>
      </div>
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center mb-4">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-red-400">
          <circle cx="12" cy="12" r="10" /><path d="M12 8v4M12 16h.01" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-white mb-2">Failed to Load</h3>
      <p className="text-sm text-white/60 max-w-sm mb-4">{message}</p>
      <button onClick={onRetry} className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors">Try Again</button>
    </div>
  );
}

function NotFoundState() {
  const router = useRouter();
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-white/40">
          <path d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-white mb-2">Equipment Not Found</h3>
      <p className="text-sm text-white/60 max-w-sm mb-4">This equipment may have been removed or you may not have access.</p>
      <button onClick={() => router.push('/equipment')} className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors">Back to Equipment</button>
    </div>
  );
}

function EquipmentContent({ data, onNavigate }: { data: Record<string, unknown>; onNavigate: (type: string, id: string) => void }) {
  const name = (data?.name || 'Equipment') as string;
  const equipmentType = (data?.equipment_type || '') as string;
  const status = (data?.status || '') as string;
  const manufacturer = data?.manufacturer as string;
  const model = data?.model as string;
  const serialNumber = data?.serial_number as string;
  const location = data?.location as string;
  const linkedWorkOrders = (data?.work_orders || []) as Array<{ id: string; wo_number: string; title: string }>;
  const linkedFaults = (data?.faults || []) as Array<{ id: string; title: string }>;

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <div className="space-y-2">
        <p className="text-xs text-white/40">{equipmentType}</p>
        <h1 className="text-2xl font-semibold text-white">{name}</h1>
        <div className="flex gap-2">
          <StatusPill status={getStatusColor(status)} label={status.replace(/_/g, ' ')} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {manufacturer && <div className="space-y-1"><p className="text-xs text-white/40">Manufacturer</p><p className="text-sm text-white/80">{manufacturer}</p></div>}
        {model && <div className="space-y-1"><p className="text-xs text-white/40">Model</p><p className="text-sm text-white/80">{model}</p></div>}
        {serialNumber && <div className="space-y-1"><p className="text-xs text-white/40">Serial Number</p><p className="text-sm text-white/80 font-mono">{serialNumber}</p></div>}
        {location && <div className="space-y-1"><p className="text-xs text-white/40">Location</p><p className="text-sm text-white/80">{location}</p></div>}
      </div>

      {linkedWorkOrders.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-white/60 uppercase tracking-wider">Linked Work Orders</h2>
          <div className="space-y-2">
            {linkedWorkOrders.map((wo) => (
              <button key={wo.id} onClick={() => onNavigate('work_order', wo.id)} className="w-full text-left p-3 bg-white/5 rounded-lg hover:bg-white/10 transition-colors">
                <p className="text-xs text-white/40 font-mono">{wo.wo_number}</p>
                <p className="text-sm text-white/80">{wo.title}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      {linkedFaults.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-white/60 uppercase tracking-wider">Linked Faults</h2>
          <div className="space-y-2">
            {linkedFaults.map((fault) => (
              <button key={fault.id} onClick={() => onNavigate('fault', fault.id)} className="w-full text-left p-3 bg-white/5 rounded-lg hover:bg-white/10 transition-colors">
                <p className="text-sm text-white/80">{fault.title}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-3 pt-4 border-t border-white/10">
        <button className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors">Report Fault</button>
        <button className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors">Create Work Order</button>
      </div>
    </div>
  );
}

function EquipmentDetailPageContent() {
  const router = useRouter();
  const params = useParams();
  const { session } = useAuth();
  const equipmentId = params.id as string;
  const token = session?.access_token;

  const { data: equipment, isLoading, error, refetch } = useQuery({
    queryKey: ['equipment-detail', equipmentId],
    queryFn: () => fetchEquipmentDetail(equipmentId, token || ''),
    enabled: !!equipmentId && !!token,
    staleTime: 30000,
    retry: 1,
  });

  const handleBack = React.useCallback(() => router.back(), [router]);
  const handleRefresh = React.useCallback(() => refetch(), [refetch]);
  const handleNavigate = React.useCallback((entityType: string, entityId: string) => {
    if (isFragmentedRoutesEnabled()) {
      switch (entityType) {
        case 'work_order': router.push(`/work-orders/${entityId}`); break;
        case 'fault': router.push(`/faults/${entityId}`); break;
        case 'part': router.push(`/inventory/${entityId}`); break;
        default: router.push(`/app?entity=${entityType}&id=${entityId}`);
      }
    } else {
      router.push(`/app?entity=${entityType}&id=${entityId}`);
    }
  }, [router]);

  const name = (equipment?.name || 'Equipment') as string;
  const equipmentType = (equipment?.equipment_type || '') as string;

  let content: React.ReactNode;
  if (isLoading) content = <LoadingState />;
  else if (error) {
    const msg = error instanceof Error ? error.message : 'An error occurred';
    content = msg.includes('404') ? <NotFoundState /> : <ErrorState message={msg} onRetry={handleRefresh} />;
  }
  else if (!equipment) content = <NotFoundState />;
  else content = <EquipmentContent data={equipment} onNavigate={handleNavigate} />;

  return (
    <RouteLayout
      pageTitle={name}
      showTopNav={true}
      topNavContent={
        <div className="flex items-center gap-4">
          <button onClick={handleBack} className="p-2 hover:bg-white/5 rounded-lg transition-colors" aria-label="Back" data-testid="back-button">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-white/60"><path d="M15 18l-6-6 6-6" /></svg>
          </button>
          <div>
            <p className="text-xs text-white/40 uppercase tracking-wider">{equipmentType || 'Equipment'}</p>
            <h1 className="text-lg font-semibold text-white truncate max-w-md">{name}</h1>
          </div>
        </div>
      }
    >
      {content}
    </RouteLayout>
  );
}

export default function EquipmentDetailPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense fallback={<LoadingState />}>
        <EquipmentDetailPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
