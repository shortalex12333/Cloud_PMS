'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { isFragmentedRoutesEnabled } from '@/lib/featureFlags';
import { useAuth } from '@/hooks/useAuth';
import { usePartActions, usePartPermissions } from '@/hooks/usePartActions';
import { EntityList } from '@/features/entity-list/components/EntityList';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { fetchParts, fetchPart } from '@/features/inventory/api';
import { partToListResult } from '@/features/inventory/adapter';
import { ConsumePartModal, ReceivePartModal, TransferPartModal, AdjustStockModal } from '@/features/inventory/components';
import type { Part } from '@/features/inventory/types';

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

function PartDetail({ id }: { id: string }) {
  const { session } = useAuth();
  const token = session?.access_token;
  const queryClient = useQueryClient();
  const permissions = usePartPermissions();
  const {
    isLoading: isActionLoading,
    consumePart,
    receivePart,
    transferPart,
    adjustStock,
    writeOff,
    addToShoppingList,
  } = usePartActions(id);

  // Modal state
  const [showConsumeModal, setShowConsumeModal] = React.useState(false);
  const [showReceiveModal, setShowReceiveModal] = React.useState(false);
  const [showTransferModal, setShowTransferModal] = React.useState(false);
  const [showAdjustStockModal, setShowAdjustStockModal] = React.useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ['part', id],
    queryFn: () => fetchPart(id, token || ''),
    enabled: !!token,
    staleTime: 30000,
  });

  // Action handlers with query invalidation
  const handleConsumeSubmit = React.useCallback(async (quantity: number, notes?: string) => {
    const result = await consumePart(quantity, notes);
    if (result.success) {
      queryClient.invalidateQueries({ queryKey: ['part', id] });
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
    }
    return result;
  }, [consumePart, queryClient, id]);

  // Receive modal submit handler
  const handleReceiveSubmit = React.useCallback(async (quantity: number, notes?: string) => {
    const result = await receivePart(quantity, notes);
    if (result.success) {
      queryClient.invalidateQueries({ queryKey: ['part', id] });
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
    }
    return result;
  }, [receivePart, queryClient, id]);

  // Transfer modal submit handler
  const handleTransferSubmit = React.useCallback(async (quantity: number, toLocation: string, notes?: string) => {
    const fromLocation = data?.location || 'default';
    const result = await transferPart(quantity, fromLocation, toLocation, notes);
    if (result.success) {
      queryClient.invalidateQueries({ queryKey: ['part', id] });
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
    }
    return result;
  }, [transferPart, queryClient, id, data?.location]);

  // Adjust stock modal submit handler
  const handleAdjustStockSubmit = React.useCallback(async (newQuantity: number, reason: string) => {
    const result = await adjustStock(newQuantity, reason);
    if (result.success) {
      queryClient.invalidateQueries({ queryKey: ['part', id] });
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
    }
    return result;
  }, [adjustStock, queryClient, id]);

  const handleWriteOff = React.useCallback(async () => {
    const result = await writeOff(1, 'Write off');
    if (result.success) {
      queryClient.invalidateQueries({ queryKey: ['part', id] });
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
    }
  }, [writeOff, queryClient, id]);

  const handleAddToShoppingList = React.useCallback(async () => {
    const result = await addToShoppingList(1);
    if (result.success) {
      queryClient.invalidateQueries({ queryKey: ['shopping-list'] });
    }
  }, [addToShoppingList, queryClient]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-red-400">Failed to load part</p>
      </div>
    );
  }

  const isLowStock = data.minimum_quantity && data.quantity_on_hand <= data.minimum_quantity;

  return (
    <div className="p-6 space-y-4">
      <div>
        <p className="text-xs text-white/40 font-mono">{data.part_number}</p>
        <h2 className="text-xl font-semibold text-white">{data.name}</h2>
      </div>
      <div className="flex gap-2">
        <span className={`px-2 py-1 text-xs rounded ${isLowStock ? 'bg-orange-500/20 text-orange-300' : 'bg-green-500/20 text-green-300'}`}>
          {isLowStock ? 'Low Stock' : 'In Stock'}
        </span>
        <span className="px-2 py-1 text-xs rounded bg-white/10 text-white/80">
          Qty: {data.quantity_on_hand}{data.unit_of_measure ? ` ${data.unit_of_measure}` : ''}
        </span>
      </div>
      {data.description && (
        <p className="text-sm text-white/60">{data.description}</p>
      )}
      {data.category && (
        <div className="text-sm">
          <span className="text-white/40">Category: </span>
          <span className="text-white/80">{data.category}</span>
        </div>
      )}
      {data.location && (
        <div className="text-sm">
          <span className="text-white/40">Location: </span>
          <span className="text-white/80">{data.location}</span>
        </div>
      )}
      {data.manufacturer && (
        <div className="text-sm">
          <span className="text-white/40">Manufacturer: </span>
          <span className="text-white/80">{data.manufacturer}</span>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-2 pt-4 border-t border-white/10">
        {permissions.canConsume && data.quantity_on_hand > 0 && (
          <button
            onClick={() => setShowConsumeModal(true)}
            disabled={isActionLoading}
            className="px-3 py-1.5 text-xs rounded bg-white/10 text-white/80 hover:bg-white/20 transition-colors disabled:opacity-50"
            data-testid="use-part-button"
          >
            Use Part
          </button>
        )}
        {permissions.canReceive && (
          <button
            onClick={() => setShowReceiveModal(true)}
            disabled={isActionLoading}
            className="px-3 py-1.5 text-xs rounded bg-white/10 text-white/80 hover:bg-white/20 transition-colors disabled:opacity-50"
            data-testid="receive-stock-button"
          >
            Receive Stock
          </button>
        )}
        {permissions.canTransfer && data.quantity_on_hand > 0 && (
          <button
            onClick={() => setShowTransferModal(true)}
            disabled={isActionLoading}
            className="px-3 py-1.5 text-xs rounded bg-white/10 text-white/80 hover:bg-white/20 transition-colors disabled:opacity-50"
            data-testid="transfer-button"
          >
            Transfer
          </button>
        )}
        {permissions.canAdjustStock && (
          <button
            onClick={() => setShowAdjustStockModal(true)}
            disabled={isActionLoading}
            className="px-3 py-1.5 text-xs rounded bg-white/10 text-white/80 hover:bg-white/20 transition-colors disabled:opacity-50"
            data-testid="adjust-stock-button"
          >
            Adjust
          </button>
        )}
        {permissions.canWriteOff && (
          <button
            onClick={handleWriteOff}
            disabled={isActionLoading}
            className="px-3 py-1.5 text-xs rounded bg-white/10 text-white/80 hover:bg-white/20 transition-colors disabled:opacity-50"
          >
            Write Off
          </button>
        )}
        {permissions.canAddToShoppingList && (
          <button
            onClick={handleAddToShoppingList}
            disabled={isActionLoading}
            className="px-3 py-1.5 text-xs rounded bg-white/10 text-white/80 hover:bg-white/20 transition-colors disabled:opacity-50"
          >
            Add to Shopping List
          </button>
        )}
      </div>

      {/* Consume Part Modal */}
      <ConsumePartModal
        open={showConsumeModal}
        onClose={() => setShowConsumeModal(false)}
        onSubmit={handleConsumeSubmit}
        isLoading={isActionLoading}
        partName={data.name}
        currentQuantity={data.quantity_on_hand}
        unitOfMeasure={data.unit_of_measure}
      />

      {/* Receive Part Modal */}
      <ReceivePartModal
        open={showReceiveModal}
        onClose={() => setShowReceiveModal(false)}
        onSubmit={handleReceiveSubmit}
        isLoading={isActionLoading}
        partName={data.name}
        currentQuantity={data.quantity_on_hand}
        unitOfMeasure={data.unit_of_measure}
      />

      {/* Transfer Part Modal */}
      <TransferPartModal
        open={showTransferModal}
        onClose={() => setShowTransferModal(false)}
        onSubmit={handleTransferSubmit}
        isLoading={isActionLoading}
        partName={data.name}
        currentQuantity={data.quantity_on_hand}
        currentLocation={data.location}
        unitOfMeasure={data.unit_of_measure}
      />

      {/* Adjust Stock Modal */}
      <AdjustStockModal
        open={showAdjustStockModal}
        onClose={() => setShowAdjustStockModal(false)}
        onSubmit={handleAdjustStockSubmit}
        isLoading={isActionLoading}
        partName={data.name}
        currentQuantity={data.quantity_on_hand}
        unitOfMeasure={data.unit_of_measure}
      />
    </div>
  );
}

function InventoryPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedId = searchParams.get('id');
  const activeFilter = searchParams.get('filter');

  const handleSelect = React.useCallback(
    (id: string) => {
      const params = new URLSearchParams();
      params.set('id', id);
      if (activeFilter) params.set('filter', activeFilter);
      router.push(`/inventory?${params.toString()}`, { scroll: false });
    },
    [router, activeFilter]
  );

  const handleCloseDetail = React.useCallback(() => {
    const params = activeFilter ? `?filter=${activeFilter}` : '';
    router.push(`/inventory${params}`, { scroll: false });
  }, [router, activeFilter]);

  const handleClearFilter = React.useCallback(() => {
    router.push('/inventory', { scroll: false });
  }, [router]);

  return (
    <div className="h-screen bg-surface-base">
      <EntityList<Part>
        queryKey={['inventory']}
        fetchFn={fetchParts}
        adapter={partToListResult}
        selectedId={selectedId}
        onSelect={handleSelect}
        emptyMessage="No parts found"
        filter={activeFilter}
        filterDomain="inventory"
        onClearFilter={handleClearFilter}
      />

      <EntityDetailOverlay isOpen={!!selectedId} onClose={handleCloseDetail}>
        {selectedId && <PartDetail id={selectedId} />}
      </EntityDetailOverlay>
    </div>
  );
}

export default function InventoryPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense
        fallback={
          <div className="h-screen flex items-center justify-center bg-surface-base">
            <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
          </div>
        }
      >
        <InventoryPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
