'use client';

/**
 * Inventory List Page - /inventory
 *
 * Tier 1 fragmented route for inventory/parts.
 *
 * @see REQUIREMENTS_TABLE.md - T1-INV-01
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
  if (!isFragmentedRoutesEnabled()) return <div className="h-screen flex items-center justify-center bg-[#0a0a0a]"><p className="text-white/60">Redirecting...</p></div>;
  return <>{children}</>;
}

interface InventoryListItem {
  id: string;
  name: string;
  part_number?: string;
  quantity_on_hand: number;
  minimum_quantity: number;
  unit?: string;
  category?: string;
  location?: string;
}

async function fetchInventory(yachtId: string, token: string): Promise<InventoryListItem[]> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/parts?yacht_id=${yachtId}`, {
    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(`Failed to fetch inventory: ${response.status}`);
  const data = await response.json();
  return data.parts || data.items || data || [];
}

async function fetchPartDetail(id: string, token: string): Promise<Record<string, unknown>> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/entity/part/${id}`, {
    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(`Failed to fetch part: ${response.status}`);
  return response.json();
}

function getStockStatus(qty: number, min: number): 'critical' | 'warning' | 'success' | 'neutral' {
  if (qty <= 0) return 'critical';
  if (qty < min) return 'warning';
  return 'success';
}

function getStockLabel(qty: number, min: number): string {
  if (qty <= 0) return 'Out of Stock';
  if (qty < min) return 'Low Stock';
  return 'In Stock';
}

function InventoryRow({ item, isSelected, onClick }: { item: InventoryListItem; isSelected: boolean; onClick: () => void }) {
  const stockStatus = getStockStatus(item.quantity_on_hand, item.minimum_quantity);
  const stockLabel = getStockLabel(item.quantity_on_hand, item.minimum_quantity);

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
            {item.part_number && <span className="text-xs text-white/40 font-mono">{item.part_number}</span>}
            <StatusPill status={stockStatus} label={stockLabel} />
          </div>
          <h3 className="text-sm font-medium text-white truncate">{item.name}</h3>
          {item.category && <p className="text-xs text-white/50 mt-1 truncate">{item.category}</p>}
        </div>
        <div className="text-right">
          <p className="text-sm text-white font-mono">{item.quantity_on_hand} {item.unit || 'units'}</p>
          <p className="text-xs text-white/40">Min: {item.minimum_quantity}</p>
        </div>
      </div>
    </button>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-white/40">
          <path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-white mb-2">No Inventory Items</h3>
      <p className="text-sm text-white/60 max-w-sm">Parts and supplies will appear here once added to inventory.</p>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
        <p className="text-sm text-white/60">Loading inventory...</p>
      </div>
    </div>
  );
}

function PartDetailContent({ data, onBack }: { data: Record<string, unknown>; onBack: () => void }) {
  const name = (data?.name || data?.part_name || 'Part') as string;
  const partNumber = data?.part_number as string;
  const qty = (data?.quantity_on_hand || data?.stock_quantity || 0) as number;
  const minQty = (data?.minimum_quantity || 0) as number;
  const unit = (data?.unit || 'units') as string;

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-4">
        <button onClick={onBack} className="p-2 hover:bg-white/5 rounded-lg transition-colors" aria-label="Back">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-white/60"><path d="M15 18l-6-6 6-6" /></svg>
        </button>
        <div>
          {partNumber && <p className="text-xs text-white/40 font-mono">{partNumber}</p>}
          <h2 className="text-lg font-semibold text-white">{name}</h2>
        </div>
      </div>
      <div className="flex gap-2">
        <StatusPill status={getStockStatus(qty, minQty)} label={getStockLabel(qty, minQty)} />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1"><p className="text-xs text-white/40">Quantity</p><p className="text-lg text-white font-mono">{qty} {unit}</p></div>
        <div className="space-y-1"><p className="text-xs text-white/40">Minimum</p><p className="text-lg text-white font-mono">{minQty} {unit}</p></div>
      </div>
    </div>
  );
}

function InventoryPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, token } = useAuth();
  const selectedId = searchParams.get('id');

  const { data: inventory, isLoading: isLoadingList, error: listError } = useQuery({
    queryKey: ['inventory', user?.yachtId],
    queryFn: () => fetchInventory(user?.yachtId || '', token || ''),
    enabled: !!user?.yachtId && !!token,
    staleTime: 30000,
  });

  const { data: selectedPart, isLoading: isLoadingDetail } = useQuery({
    queryKey: ['part', selectedId],
    queryFn: () => fetchPartDetail(selectedId!, token || ''),
    enabled: !!selectedId && !!token,
    staleTime: 30000,
  });

  const handleSelect = React.useCallback((id: string) => router.push(`/inventory?id=${id}`, { scroll: false }), [router]);
  const handleCloseDetail = React.useCallback(() => router.push('/inventory', { scroll: false }), [router]);
  const handleBack = React.useCallback(() => router.back(), [router]);

  const listContent = React.useMemo(() => {
    if (isLoadingList) return <LoadingState />;
    if (listError) return <div className="flex items-center justify-center h-full"><p className="text-red-400">Failed to load inventory</p></div>;
    if (!inventory || inventory.length === 0) return <EmptyState />;
    return (
      <div className="divide-y divide-white/5">
        {inventory.map((item) => (
          <InventoryRow key={item.id} item={item} isSelected={item.id === selectedId} onClick={() => handleSelect(item.id)} />
        ))}
      </div>
    );
  }, [inventory, isLoadingList, listError, selectedId, handleSelect]);

  return (
    <RouteLayout
      pageTitle="Inventory"
      showTopNav={true}
      topNavContent={<div className="flex items-center gap-4"><h1 className="text-lg font-semibold text-white">Inventory</h1></div>}
      primaryPanel={selectedId ? {
        visible: true,
        title: (selectedPart?.name || selectedPart?.part_name || 'Part') as string,
        subtitle: selectedPart?.part_number as string,
        children: isLoadingDetail ? <LoadingState /> : selectedPart ? <PartDetailContent data={selectedPart} onBack={handleBack} /> : null,
      } : undefined}
      onClosePrimaryPanel={handleCloseDetail}
    >
      {listContent}
    </RouteLayout>
  );
}

export default function InventoryPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense fallback={<LoadingState />}>
        <InventoryPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
