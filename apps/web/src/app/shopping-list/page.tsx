'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/hooks/useAuth';
import { useActiveVessel } from '@/contexts/VesselContext';
import { FilteredEntityList } from '@/features/entity-list/components/FilteredEntityList';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { EntityLensPage } from '@/components/lens-v2/EntityLensPage';
import { ShoppingListContent } from '@/components/lens-v2/entity/ShoppingListContent';
import { ActionPopup } from '@/components/lens-v2/ActionPopup';
import lensStyles from '@/components/lens-v2/lens.module.css';
import { shoppingListToListResult } from '@/features/shopping-list/adapter';
import { SHOPPING_LIST_FILTERS } from '@/features/entity-list/types/filter-config';
import { API_BASE } from '@/lib/apiBase';
import { supabase } from '@/lib/supabaseClient';
import type { ShoppingListItem } from '@/features/shopping-list/types';

function LensContent() {
  return <div className={lensStyles.root}><ShoppingListContent /></div>;
}

function CreateItemModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const { session } = useAuth();
  const { vesselId: activeVesselId } = useActiveVessel();
  const { user } = useAuth();
  const yachtId = activeVesselId || user?.yachtId || '';
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const handleSubmit = React.useCallback(async (values: Record<string, unknown>) => {
    if (!yachtId) { setError('No vessel selected'); return; }
    setIsSubmitting(true);
    setError(null);
    try {
      const { data: sessionData } = await supabase.auth.getSession();
      const token = sessionData.session?.access_token;
      if (!token) { setError('Not authenticated'); return; }

      const res = await fetch('/api/v1/actions/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          action: 'create_shopping_list_item',
          context: { yacht_id: yachtId },
          payload: {
            part_name: values.part_name,
            quantity_requested: Number(values.quantity_requested) || 1,
            source_type: 'manual_add',
            urgency: values.urgency || 'normal',
            source_notes: values.source_notes || undefined,
            estimated_unit_price: values.estimated_unit_price ? Number(values.estimated_unit_price) : undefined,
            required_by_date: values.required_by_date || undefined,
            source_work_order_id: values.source_work_order_id || undefined,
          },
        }),
      });

      const result = await res.json();
      if (!res.ok || result.status === 'error') {
        setError(result.message || 'Failed to create item');
        return;
      }
      onSuccess();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Network error');
    } finally {
      setIsSubmitting(false);
    }
  }, [yachtId, onClose, onSuccess]);

  return (
    <ActionPopup
      mode="mutate"
      title="Add to Shopping List"
      subtitle="All crew can add items. HoD approves before ordering."
      fields={[
        { name: 'part_name', label: 'Item / Part Name', type: 'kv-edit', placeholder: 'e.g. Fuel filter, Safety harness', required: true },
        { name: 'quantity_requested', label: 'Quantity', type: 'kv-edit', placeholder: '1', required: true },
        { name: 'urgency', label: 'Urgency', type: 'select', options: [
          { value: 'low', label: 'Low' },
          { value: 'normal', label: 'Normal' },
          { value: 'high', label: 'High' },
          { value: 'critical', label: 'Critical' },
        ]},
        { name: 'estimated_unit_price', label: 'Estimated Price (per unit)', type: 'kv-edit', placeholder: '0.00' },
        { name: 'source_notes', label: 'Reason / Notes', type: 'text-area', placeholder: 'Why is this item needed?' },
        { name: 'required_by_date', label: 'Required By', type: 'date-pick' },
        { name: 'source_work_order_id', label: 'Link to Work Order (optional)', type: 'entity-search', search_domain: 'work_orders', placeholder: 'Search work orders...' },
      ]}
      signatureLevel={1}
      submitLabel={isSubmitting ? 'Adding...' : 'Add Item'}
      submitDisabled={isSubmitting}
      previewRows={error ? [{ key: 'Error', value: error }] : undefined}
      onSubmit={handleSubmit}
      onClose={onClose}
    />
  );
}

function ShoppingListPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const selectedId = searchParams.get('id');
  const [showCreate, setShowCreate] = React.useState(false);

  const handleSelect = React.useCallback(
    (id: string, yachtId?: string) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set('id', id);
      if (yachtId) params.set('yacht_id', yachtId);
      router.push(`/shopping-list?${params.toString()}`, { scroll: false });
    },
    [router, searchParams]
  );

  const handleCloseDetail = React.useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete('id');
    const qs = params.toString();
    router.push(`/shopping-list${qs ? `?${qs}` : ''}`, { scroll: false });
  }, [router, searchParams]);

  const handleCreated = React.useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['shopping-list'] });
  }, [queryClient]);

  return (
    <div className="h-full bg-surface-base" style={{ position: 'relative' }}>
      <FilteredEntityList<ShoppingListItem>
        domain="shopping-list"
        queryKey={['shopping-list']}
        table="pms_shopping_list_items"
        columns="id, part_name, part_number, manufacturer, quantity_requested, unit, status, urgency, requested_by, required_by_date, created_at, updated_at"
        adapter={shoppingListToListResult}
        filterConfig={SHOPPING_LIST_FILTERS}
        selectedId={selectedId}
        onSelect={handleSelect}
        emptyMessage="No shopping list items found"
      />

      {/* Add Item button — fixed bottom-right */}
      <button
        onClick={() => setShowCreate(true)}
        aria-label="Add item to shopping list"
        style={{
          position: 'fixed',
          bottom: 32,
          right: 32,
          zIndex: 50,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '10px 18px',
          background: 'var(--mark)',
          color: 'var(--surface-base)',
          border: 'none',
          borderRadius: 8,
          fontSize: 13,
          fontWeight: 600,
          fontFamily: 'var(--font-sans)',
          cursor: 'pointer',
          boxShadow: '0 4px 16px rgba(0,0,0,0.3)',
        }}
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M7 1v12M1 7h12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
        Add Item
      </button>

      <EntityDetailOverlay isOpen={!!selectedId} onClose={handleCloseDetail}>
        {selectedId && (
          <EntityLensPage
            entityType="shopping_list"
            entityId={selectedId}
            content={LensContent}
          />
        )}
      </EntityDetailOverlay>

      {showCreate && (
        <CreateItemModal
          onClose={() => setShowCreate(false)}
          onSuccess={handleCreated}
        />
      )}
    </div>
  );
}

export default function ShoppingListPage() {
  return (
    <React.Suspense
      fallback={
        <div className="h-full flex items-center justify-center bg-surface-base">
          <div style={{ width: '32px', height: '32px', border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%' }} className="animate-spin" />
        </div>
      }
    >
      <ShoppingListPageContent />
    </React.Suspense>
  );
}
