'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/hooks/useAuth';
import { FilteredEntityList } from '@/features/entity-list/components/FilteredEntityList';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { fetchPart } from '@/features/inventory/api';
import { partToListResult } from '@/features/inventory/adapter';
import { INVENTORY_FILTERS } from '@/features/entity-list/types/filter-config';
import type { Part } from '@/features/inventory/types';

function PartDetail({ id }: { id: string }) {
  const { session } = useAuth();
  const token = session?.access_token;

  const { data, isLoading, error } = useQuery({
    queryKey: ['part', id],
    queryFn: () => fetchPart(id, token || ''),
    enabled: !!token,
    staleTime: 30000,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div style={{ width: '32px', height: '32px', border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%' }} className="animate-spin" />
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
        <p className="text-xs text-txt-tertiary font-mono">{data.part_number}</p>
        <h2 className="text-xl font-semibold text-txt-primary">{data.name}</h2>
      </div>
      <div className="flex gap-2">
        <span className={`px-2 py-1 text-xs rounded ${isLowStock ? 'bg-orange-500/20 text-orange-300' : 'bg-green-500/20 text-green-300'}`}>
          {isLowStock ? 'Low Stock' : 'In Stock'}
        </span>
        <span className="px-2 py-1 text-xs rounded bg-surface-hover text-txt-secondary">
          Qty: {data.quantity_on_hand}{data.unit_of_measure ? ` ${data.unit_of_measure}` : ''}
        </span>
      </div>
      {data.description && (
        <p className="text-sm text-txt-tertiary">{data.description}</p>
      )}
      {data.category && (
        <div className="text-sm">
          <span className="text-txt-tertiary">Category: </span>
          <span className="text-txt-secondary">{data.category}</span>
        </div>
      )}
      {data.location && (
        <div className="text-sm">
          <span className="text-txt-tertiary">Location: </span>
          <span className="text-txt-secondary">{data.location}</span>
        </div>
      )}
      {data.manufacturer && (
        <div className="text-sm">
          <span className="text-txt-tertiary">Manufacturer: </span>
          <span className="text-txt-secondary">{data.manufacturer}</span>
        </div>
      )}
    </div>
  );
}

function InventoryPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedId = searchParams.get('id');

  const handleSelect = React.useCallback(
    (id: string) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set('id', id);
      router.push(`/inventory?${params.toString()}`, { scroll: false });
    },
    [router, searchParams]
  );

  const handleCloseDetail = React.useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete('id');
    const qs = params.toString();
    router.push(`/inventory${qs ? `?${qs}` : ''}`, { scroll: false });
  }, [router, searchParams]);

  return (
    <div className="h-screen bg-surface-base">
      <FilteredEntityList<Part>
        domain="inventory"
        queryKey={['inventory']}
        table="pms_parts"
        columns="id, name, part_number, description, category, manufacturer, quantity_on_hand, minimum_quantity, unit, location, is_critical, unit_cost, created_at, updated_at"
        adapter={partToListResult}
        filterConfig={INVENTORY_FILTERS}
        selectedId={selectedId}
        onSelect={handleSelect}
        emptyMessage="No parts found"
        sortBy="name"
      />

      <EntityDetailOverlay isOpen={!!selectedId} onClose={handleCloseDetail}>
        {selectedId && <PartDetail id={selectedId} />}
      </EntityDetailOverlay>
    </div>
  );
}

export default function InventoryPage() {
  return (
    <React.Suspense
      fallback={
        <div className="h-screen flex items-center justify-center bg-surface-base">
          <div style={{ width: '32px', height: '32px', border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%' }} className="animate-spin" />
        </div>
      }
    >
      <InventoryPageContent />
    </React.Suspense>
  );
}
