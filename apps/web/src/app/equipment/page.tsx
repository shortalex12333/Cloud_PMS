'use client';

/**
 * Equipment List Page - /equipment
 *
 * Tier 1 fragmented route for equipment.
 *
 * @see REQUIREMENTS_TABLE.md - T1-EQ-01
 */

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { RouteLayout } from '@/components/layout';
import { isFragmentedRoutesEnabled } from '@/lib/featureFlags';
import { useAuth } from '@/hooks/useAuth';
import { StatusPill } from '@/components/ui/StatusPill';
import { cn } from '@/lib/utils';

function FeatureFlagGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  React.useEffect(() => { if (!isFragmentedRoutesEnabled()) router.replace('/app'); }, [router]);
  if (!isFragmentedRoutesEnabled()) return <div className="h-screen flex items-center justify-center bg-surface-base"><p className="text-white/60">Redirecting...</p></div>;
  return <>{children}</>;
}

interface EquipmentListItem {
  id: string;
  name: string;
  equipment_type: string;
  status: string;
  location?: string;
  manufacturer?: string;
}

async function fetchEquipment(yachtId: string, token: string): Promise<EquipmentListItem[]> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/equipment?yacht_id=${yachtId}`, {
    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(`Failed to fetch equipment: ${response.status}`);
  const data = await response.json();
  return data.equipment || data.items || data || [];
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

function EquipmentRow({ item, isSelected, onClick }: { item: EquipmentListItem; isSelected: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full text-left px-6 py-4 border-b border-white/5',
        'hover:bg-white/5 transition-colors focus:outline-none focus:bg-white/5',
        isSelected && 'bg-white/10'
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-white/40">{item.equipment_type}</span>
            <StatusPill status={getStatusColor(item.status)} label={(item.status || '').replace(/_/g, ' ')} />
          </div>
          <h3 className="text-sm font-medium text-white truncate">{item.name}</h3>
          {item.location && <p className="text-xs text-white/50 mt-1 truncate">{item.location}</p>}
        </div>
        {item.manufacturer && <div className="text-xs text-white/40 whitespace-nowrap">{item.manufacturer}</div>}
      </div>
    </button>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-white/40">
          <path d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-white mb-2">No Equipment</h3>
      <p className="text-sm text-white/60 max-w-sm">Equipment items will appear here once added.</p>
    </div>
  );
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

function EquipmentDetailContent({ data, onBack }: { data: Record<string, unknown>; onBack: () => void }) {
  const name = (data?.name || 'Equipment') as string;
  const equipmentType = (data?.equipment_type || '') as string;
  const status = (data?.status || '') as string;
  const manufacturer = data?.manufacturer as string;
  const model = data?.model as string;

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-4">
        <button onClick={onBack} className="p-2 hover:bg-white/5 rounded-lg transition-colors" aria-label="Back">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-white/60"><path d="M15 18l-6-6 6-6" /></svg>
        </button>
        <div>
          <p className="text-xs text-white/40">{equipmentType}</p>
          <h2 className="text-lg font-semibold text-white">{name}</h2>
        </div>
      </div>
      <div className="flex gap-2">
        <StatusPill status={getStatusColor(status)} label={status.replace(/_/g, ' ')} />
      </div>
      {(manufacturer || model) && (
        <p className="text-sm text-white/60">{[manufacturer, model].filter(Boolean).join(' - ')}</p>
      )}
    </div>
  );
}

function EquipmentPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, session } = useAuth();
  const token = session?.access_token;
  const selectedId = searchParams.get('id');

  const { data: equipment, isLoading: isLoadingList, error: listError } = useQuery({
    queryKey: ['equipment', user?.yachtId],
    queryFn: () => fetchEquipment(user?.yachtId || '', token || ''),
    enabled: !!user?.yachtId && !!token,
    staleTime: 30000,
  });

  const { data: selectedEquipment, isLoading: isLoadingDetail } = useQuery({
    queryKey: ['equipment-detail', selectedId],
    queryFn: () => fetchEquipmentDetail(selectedId!, token || ''),
    enabled: !!selectedId && !!token,
    staleTime: 30000,
  });

  const handleSelect = React.useCallback((id: string) => router.push(`/equipment?id=${id}`, { scroll: false }), [router]);
  const handleCloseDetail = React.useCallback(() => router.push('/equipment', { scroll: false }), [router]);
  const handleBack = React.useCallback(() => router.back(), [router]);

  const listContent = React.useMemo(() => {
    if (isLoadingList) return <LoadingState />;
    if (listError) return <div className="flex items-center justify-center h-full"><p className="text-red-400">Failed to load equipment</p></div>;
    if (!equipment || equipment.length === 0) return <EmptyState />;
    return (
      <div className="divide-y divide-white/5">
        {equipment.map((eq) => (
          <EquipmentRow key={eq.id} item={eq} isSelected={eq.id === selectedId} onClick={() => handleSelect(eq.id)} />
        ))}
      </div>
    );
  }, [equipment, isLoadingList, listError, selectedId, handleSelect]);

  return (
    <RouteLayout
      pageTitle="Equipment"
      showTopNav={true}
      topNavContent={<div className="flex items-center gap-4"><h1 className="text-lg font-semibold text-white">Equipment</h1></div>}
      primaryPanel={selectedId ? {
        visible: true,
        title: selectedEquipment?.name as string || 'Equipment',
        subtitle: selectedEquipment?.equipment_type as string,
        children: isLoadingDetail ? <LoadingState /> : selectedEquipment ? <EquipmentDetailContent data={selectedEquipment} onBack={handleBack} /> : null,
      } : undefined}
      onClosePrimaryPanel={handleCloseDetail}
    >
      {listContent}
    </RouteLayout>
  );
}

export default function EquipmentPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense fallback={<LoadingState />}>
        <EquipmentPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
