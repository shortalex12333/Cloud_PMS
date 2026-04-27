'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/hooks/useAuth';
import { useActiveVessel } from '@/contexts/VesselContext';
import { FilteredEntityList } from '@/features/entity-list/components/FilteredEntityList';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { fetchPart } from '@/features/inventory/api';
import { partToListResult } from '@/features/inventory/adapter';
import { INVENTORY_FILTERS } from '@/features/entity-list/types/filter-config';
import { AddToListModal } from './AddToListModal';
import type { Part } from '@/features/inventory/types';

// ── Part detail overlay ───────────────────────────────────────────────────────

function PartDetail({
  id,
  onAddToList,
}: {
  id: string;
  onAddToList: (part: Part) => void;
}) {
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
        <p style={{ color: 'var(--red)', fontSize: 13, fontFamily: 'var(--font-sans)' }}>Failed to load part</p>
      </div>
    );
  }

  const isLowStock = data.minimum_quantity != null && data.quantity_on_hand <= data.minimum_quantity;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', fontFamily: 'var(--font-sans)' }}>

      {/* Identity */}
      <div style={{ padding: '20px 20px 16px', borderBottom: '1px solid var(--border-sub)' }}>
        <p style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--txt3)', margin: '0 0 4px', letterSpacing: '0.05em' }}>
          {data.part_number || '—'}
        </p>
        <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--txt1)', margin: 0, lineHeight: 1.3 }}>
          {data.name}
        </h2>
        <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
          <span style={{
            padding: '3px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600,
            color: isLowStock ? 'var(--amber)' : 'var(--green)',
            background: isLowStock ? 'var(--amber-bg, #2a2000)' : 'var(--green-bg, #001a0d)',
            border: `1px solid ${isLowStock ? 'var(--amber-border, #6b4e00)' : 'var(--green-border, #004d1a)'}`,
          }}>
            {isLowStock ? 'Low Stock' : 'In Stock'}
          </span>
          <span style={{
            padding: '3px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600,
            color: 'var(--txt2)', background: 'var(--surface-hover)',
            border: '1px solid var(--border-sub)', fontFamily: 'var(--font-mono)',
          }}>
            Qty: {data.quantity_on_hand}{data.unit_of_measure ? ` ${data.unit_of_measure}` : ''}
          </span>
        </div>
      </div>

      {/* Details */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px' }}>
        {data.description && (
          <p style={{ fontSize: 13, color: 'var(--txt3)', margin: '0 0 16px', lineHeight: 1.5 }}>{data.description}</p>
        )}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {data.category && (
            <div style={{ display: 'flex', gap: 8, fontSize: 13 }}>
              <span style={{ color: 'var(--txt3)', minWidth: 90 }}>Category</span>
              <span style={{ color: 'var(--txt2)' }}>{data.category}</span>
            </div>
          )}
          {data.location && (
            <div style={{ display: 'flex', gap: 8, fontSize: 13 }}>
              <span style={{ color: 'var(--txt3)', minWidth: 90 }}>Location</span>
              <span style={{ color: 'var(--txt2)' }}>{data.location}</span>
            </div>
          )}
          {data.manufacturer && (
            <div style={{ display: 'flex', gap: 8, fontSize: 13 }}>
              <span style={{ color: 'var(--txt3)', minWidth: 90 }}>Manufacturer</span>
              <span style={{ color: 'var(--txt2)' }}>{data.manufacturer}</span>
            </div>
          )}
          {data.minimum_quantity != null && (
            <div style={{ display: 'flex', gap: 8, fontSize: 13 }}>
              <span style={{ color: 'var(--txt3)', minWidth: 90 }}>Min. Stock</span>
              <span style={{ color: 'var(--txt2)', fontFamily: 'var(--font-mono)' }}>{data.minimum_quantity}</span>
            </div>
          )}
        </div>
      </div>

      {/* Action footer */}
      <div style={{
        padding: '12px 20px',
        borderTop: '1px solid var(--border-sub)',
        flexShrink: 0,
      }}>
        <button
          onClick={() => onAddToList(data)}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7,
            padding: '9px 0',
            background: 'var(--mark)', color: '#fff',
            border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 600,
            fontFamily: 'var(--font-sans)', cursor: 'pointer',
          }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M2 2h1.5l1.8 6.5h5.4l1.3-4.5H5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
            <circle cx="6.5" cy="11.5" r="0.8" fill="currentColor"/>
            <circle cx="10" cy="11.5" r="0.8" fill="currentColor"/>
          </svg>
          Add to Shopping List
        </button>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

function InventoryPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { vesselId } = useActiveVessel();
  const { user } = useAuth();
  const yachtId = vesselId || user?.yachtId || '';

  const selectedId = searchParams.get('id');
  const [addToListPart, setAddToListPart] = React.useState<Part | null>(null);
  const [successToast, setSuccessToast] = React.useState<string | null>(null);

  const handleSelect = React.useCallback(
    (id: string, yId?: string) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set('id', id);
      if (yId) params.set('yacht_id', yId);
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

  const handleAddSuccess = React.useCallback(() => {
    setAddToListPart(null);
    setSuccessToast('Part added to shopping list');
    setTimeout(() => setSuccessToast(null), 3500);
  }, []);

  return (
    <div className="h-full bg-surface-base">
      <FilteredEntityList<Part>
        domain="inventory"
        queryKey={['inventory']}
        table="v_parts_enriched"
        columns="id, name, part_number, description, category, manufacturer, quantity_on_hand, minimum_quantity, unit, location, is_critical, unit_cost, created_at, updated_at"
        adapter={partToListResult}
        filterConfig={INVENTORY_FILTERS}
        selectedId={selectedId}
        onSelect={handleSelect}
        emptyMessage="No parts found"
        sortBy="name"
      />

      <EntityDetailOverlay isOpen={!!selectedId} onClose={handleCloseDetail}>
        {selectedId && (
          <PartDetail
            id={selectedId}
            onAddToList={part => setAddToListPart(part)}
          />
        )}
      </EntityDetailOverlay>

      {addToListPart && (
        <AddToListModal
          partId={addToListPart.id}
          partName={addToListPart.name}
          partNumber={addToListPart.part_number}
          yachtId={yachtId}
          onClose={() => setAddToListPart(null)}
          onSuccess={handleAddSuccess}
        />
      )}

      {successToast && (
        <div style={{
          position: 'fixed', bottom: 24, left: '50%', transform: 'translateX(-50%)',
          background: 'var(--green)', color: '#fff',
          padding: '10px 20px', borderRadius: 8, fontSize: 13, fontWeight: 600,
          fontFamily: 'var(--font-sans)', zIndex: 2000,
          boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
        }}>
          {successToast}
        </div>
      )}
    </div>
  );
}

export default function InventoryPage() {
  return (
    <React.Suspense
      fallback={
        <div className="h-full flex items-center justify-center bg-surface-base">
          <div style={{ width: '32px', height: '32px', border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%' }} className="animate-spin" />
        </div>
      }
    >
      <InventoryPageContent />
    </React.Suspense>
  );
}
