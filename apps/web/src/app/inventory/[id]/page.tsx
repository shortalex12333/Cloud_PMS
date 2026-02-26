'use client';

/**
 * Inventory Detail Page - /inventory/[id]
 *
 * Tier 1 fragmented route for viewing a single inventory item/part.
 *
 * @see REQUIREMENTS_TABLE.md - T1-INV-02
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
  React.useEffect(() => { if (!isFragmentedRoutesEnabled()) router.replace(`/app?entity=part&id=${params.id}`); }, [router, params]);
  if (!isFragmentedRoutesEnabled()) return <div className="h-screen flex items-center justify-center bg-surface-base"><p className="text-white/60">Redirecting...</p></div>;
  return <>{children}</>;
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

function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
        <p className="text-sm text-white/60">Loading part...</p>
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
      <h3 className="text-lg font-medium text-white mb-2">Part Not Found</h3>
      <p className="text-sm text-white/60 max-w-sm mb-4">This part may have been removed or you may not have access.</p>
      <button onClick={() => router.push('/inventory')} className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors">Back to Inventory</button>
    </div>
  );
}

function PartContent({ data, onNavigate }: { data: Record<string, unknown>; onNavigate: (type: string, id: string) => void }) {
  const name = (data?.name || data?.part_name || 'Part') as string;
  const partNumber = data?.part_number as string;
  const qty = (data?.quantity_on_hand || data?.stock_quantity || 0) as number;
  const minQty = (data?.minimum_quantity || 0) as number;
  const unit = (data?.unit || 'units') as string;
  const category = data?.category as string;
  const manufacturer = data?.manufacturer as string;
  const location = data?.location as string;
  const transactions = (data?.transactions || []) as Array<{ id: string; type: string; quantity: number; created_at: string }>;
  const linkedEquipment = (data?.equipment || []) as Array<{ id: string; name: string }>;

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <div className="space-y-2">
        {partNumber && <p className="text-xs text-white/40 font-mono">{partNumber}</p>}
        <h1 className="text-2xl font-semibold text-white">{name}</h1>
        <div className="flex gap-2">
          <StatusPill status={getStockStatus(qty, minQty)} label={getStockLabel(qty, minQty)} />
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-white/5 rounded-lg">
        <div className="text-center">
          <p className="text-2xl font-bold text-white">{qty}</p>
          <p className="text-xs text-white/40">On Hand</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-white">{minQty}</p>
          <p className="text-xs text-white/40">Minimum</p>
        </div>
        <div className="text-center col-span-2">
          <p className="text-sm text-white/60">{unit}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {category && <div className="space-y-1"><p className="text-xs text-white/40">Category</p><p className="text-sm text-white/80">{category}</p></div>}
        {manufacturer && <div className="space-y-1"><p className="text-xs text-white/40">Manufacturer</p><p className="text-sm text-white/80">{manufacturer}</p></div>}
        {location && <div className="space-y-1"><p className="text-xs text-white/40">Location</p><p className="text-sm text-white/80">{location}</p></div>}
      </div>

      {linkedEquipment.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-white/60 uppercase tracking-wider">Used By Equipment</h2>
          <div className="flex flex-wrap gap-2">
            {linkedEquipment.map((eq) => (
              <button key={eq.id} onClick={() => onNavigate('equipment', eq.id)} className="px-3 py-1 bg-white/5 rounded-full text-sm text-white/80 hover:bg-white/10 transition-colors">
                {eq.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {transactions.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-white/60 uppercase tracking-wider">Recent Transactions</h2>
          <div className="space-y-2">
            {transactions.slice(0, 5).map((tx) => (
              <div key={tx.id} className="flex justify-between items-center p-3 bg-white/5 rounded-lg">
                <div>
                  <p className="text-sm text-white/80 capitalize">{tx.type.replace(/_/g, ' ')}</p>
                  <p className="text-xs text-white/40">{new Date(tx.created_at).toLocaleString()}</p>
                </div>
                <p className={`text-sm font-mono ${tx.quantity > 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {tx.quantity > 0 ? '+' : ''}{tx.quantity}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-3 pt-4 border-t border-white/10">
        <button className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors">Log Usage</button>
        <button className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white transition-colors">Count Stock</button>
        {qty < minQty && (
          <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm text-white transition-colors">Add to Shopping List</button>
        )}
      </div>
    </div>
  );
}

function InventoryDetailPageContent() {
  const router = useRouter();
  const params = useParams();
  const { session } = useAuth();
  const token = session?.access_token;
  const partId = params.id as string;

  const { data: part, isLoading, error, refetch } = useQuery({
    queryKey: ['part', partId],
    queryFn: () => fetchPartDetail(partId, token || ''),
    enabled: !!partId && !!token,
    staleTime: 30000,
    retry: 1,
  });

  const handleBack = React.useCallback(() => router.back(), [router]);
  const handleRefresh = React.useCallback(() => refetch(), [refetch]);
  const handleNavigate = React.useCallback((entityType: string, entityId: string) => {
    if (isFragmentedRoutesEnabled()) {
      switch (entityType) {
        case 'equipment': router.push(`/equipment/${entityId}`); break;
        case 'work_order': router.push(`/work-orders/${entityId}`); break;
        default: router.push(`/app?entity=${entityType}&id=${entityId}`);
      }
    } else {
      router.push(`/app?entity=${entityType}&id=${entityId}`);
    }
  }, [router]);

  const name = (part?.name || part?.part_name || 'Part') as string;
  const partNumber = part?.part_number as string;

  let content: React.ReactNode;
  if (isLoading) content = <LoadingState />;
  else if (error) {
    const msg = error instanceof Error ? error.message : 'An error occurred';
    content = msg.includes('404') ? <NotFoundState /> : <ErrorState message={msg} onRetry={handleRefresh} />;
  }
  else if (!part) content = <NotFoundState />;
  else content = <PartContent data={part} onNavigate={handleNavigate} />;

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
            <p className="text-xs text-white/40 uppercase tracking-wider">{partNumber || 'Part'}</p>
            <h1 className="text-lg font-semibold text-white truncate max-w-md">{name}</h1>
          </div>
        </div>
      }
    >
      {content}
    </RouteLayout>
  );
}

export default function InventoryDetailPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense fallback={<LoadingState />}>
        <InventoryDetailPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
