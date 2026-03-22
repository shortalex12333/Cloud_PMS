'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/hooks/useAuth';
import { useActionHandler } from '@/hooks/useActionHandler';
import { FilteredEntityList } from '@/features/entity-list/components/FilteredEntityList';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { fetchReceivingItem } from '@/features/receiving/api';
import { receivingToListResult } from '@/features/receiving/adapter';
import { ReceivingPhotos } from '@/features/receiving/components/ReceivingPhotos';
import { RECEIVING_FILTERS } from '@/features/entity-list/types/filter-config';
import type { ReceivingItem } from '@/features/receiving/types';
function ReceivingDetail({ id }: { id: string }) {
  const { session } = useAuth();
  const token = session?.access_token;
  const queryClient = useQueryClient();
  const { executeAction, isLoading: isActionLoading } = useActionHandler();

  const { data, isLoading, error } = useQuery({
    queryKey: ['receiving', id],
    queryFn: () => fetchReceivingItem(id, token || ''),
    enabled: !!token,
    staleTime: 30000,
  });

  const handleRefresh = React.useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['receiving', id] });
    queryClient.invalidateQueries({ queryKey: ['receiving'] });
  }, [queryClient, id]);

  const handleAction = React.useCallback(
    async (action: string) => {
      const result = await executeAction(
        action,
        { receiving_id: id },
        {
          skipConfirmation: true,
          refreshData: true,
          onSuccess: handleRefresh,
        }
      );
      return result;
    },
    [executeAction, id, handleRefresh]
  );

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
        <p className="text-red-400">Failed to load receiving item</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      <div>
        {data.receiving_number && (
          <p className="text-xs text-txt-tertiary font-mono">{data.receiving_number}</p>
        )}
        <h2 className="text-xl font-semibold text-txt-primary">
          {data.supplier_name || `Receiving ${data.receiving_number || data.id.slice(0, 8)}`}
        </h2>
      </div>
      <div className="flex gap-2">
        <span className="px-2 py-1 text-xs rounded bg-surface-hover text-txt-secondary">
          {data.status?.replace(/_/g, ' ') || 'Pending'}
        </span>
        {data.items_count && (
          <span className="px-2 py-1 text-xs rounded bg-surface-hover text-txt-secondary">
            {data.items_count} items
          </span>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-2 pt-2 border-t border-surface-border">
        <button
          onClick={() => handleAction('create_receiving')}
          disabled={isActionLoading}
          className="px-3 py-1.5 text-xs rounded bg-surface-hover text-txt-secondary hover:bg-surface-hover transition-colors disabled:opacity-50"
        >
          Start Receiving Event
        </button>
        <button
          onClick={() => handleAction('add_receiving_item')}
          disabled={isActionLoading}
          className="px-3 py-1.5 text-xs rounded bg-surface-hover text-txt-secondary hover:bg-surface-hover transition-colors disabled:opacity-50"
        >
          Add Line Item
        </button>
        <button
          onClick={() => handleAction('accept_receiving')}
          disabled={isActionLoading}
          className="px-3 py-1.5 text-xs rounded bg-surface-hover text-txt-secondary hover:bg-surface-hover transition-colors disabled:opacity-50"
        >
          Complete Receiving
        </button>
        <button
          onClick={() => handleAction('reject_receiving')}
          disabled={isActionLoading}
          className="px-3 py-1.5 text-xs rounded bg-surface-hover text-txt-secondary hover:bg-surface-hover transition-colors disabled:opacity-50"
        >
          Report Discrepancy
        </button>
        <button
          onClick={() => handleAction('adjust_receiving_item')}
          disabled={isActionLoading}
          className="px-3 py-1.5 text-xs rounded bg-surface-hover text-txt-secondary hover:bg-surface-hover transition-colors disabled:opacity-50"
        >
          Verify Line Item
        </button>
      </div>

      {data.description && (
        <p className="text-sm text-txt-tertiary">{data.description}</p>
      )}
      {data.received_date && (
        <div className="text-sm">
          <span className="text-txt-tertiary">Received: </span>
          <span className="text-txt-secondary">{new Date(data.received_date).toLocaleDateString()}</span>
        </div>
      )}
      {data.expected_date && !data.received_date && (
        <div className="text-sm">
          <span className="text-txt-tertiary">Expected: </span>
          <span className="text-txt-secondary">{new Date(data.expected_date).toLocaleDateString()}</span>
        </div>
      )}
      {data.notes && (
        <div className="text-sm">
          <span className="text-txt-tertiary">Notes: </span>
          <span className="text-txt-secondary">{data.notes}</span>
        </div>
      )}

      {/* Photos & Documents Section - Action 6: view_receiving_photos */}
      {/* Read-only escape hatch - all crew can view attached photos/documents */}
      {token && (
        <ReceivingPhotos
          receivingId={id}
          token={token}
          onDocumentClick={(documentId) => {
            // Optional: Open document lens or viewer
            console.log('Document clicked:', documentId);
          }}
        />
      )}
    </div>
  );
}

function ReceivingPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedId = searchParams.get('id');

  const handleSelect = React.useCallback(
    (id: string) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set('id', id);
      router.push(`/receiving?${params.toString()}`, { scroll: false });
    },
    [router, searchParams]
  );

  const handleCloseDetail = React.useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete('id');
    const qs = params.toString();
    router.push(`/receiving${qs ? `?${qs}` : ''}`, { scroll: false });
  }, [router, searchParams]);

  return (
    <div className="h-screen bg-surface-base">
      <FilteredEntityList<ReceivingItem>
        domain="receiving"
        queryKey={['receiving']}
        table="pms_receiving"
        columns="id, vendor_name, vendor_reference, status, received_date, expected_date, notes, items_count, created_at, updated_at"
        adapter={receivingToListResult}
        filterConfig={RECEIVING_FILTERS}
        selectedId={selectedId}
        onSelect={handleSelect}
        emptyMessage="No receiving items found"
      />

      <EntityDetailOverlay isOpen={!!selectedId} onClose={handleCloseDetail}>
        {selectedId && <ReceivingDetail id={selectedId} />}
      </EntityDetailOverlay>
    </div>
  );
}

export default function ReceivingPage() {
  return (
    <React.Suspense
      fallback={
        <div className="h-screen flex items-center justify-center bg-surface-base">
          <div style={{ width: '32px', height: '32px', border: '2px solid var(--border-sub)', borderTopColor: 'var(--mark)', borderRadius: '50%' }} className="animate-spin" />
        </div>
      }
    >
      <ReceivingPageContent />
    </React.Suspense>
  );
}
