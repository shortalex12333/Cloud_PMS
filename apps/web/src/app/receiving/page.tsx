'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { isFragmentedRoutesEnabled } from '@/lib/featureFlags';
import { useAuth } from '@/hooks/useAuth';
import { useActionHandler } from '@/hooks/useActionHandler';
import { EntityList } from '@/features/entity-list/components/EntityList';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { fetchReceivingItems, fetchReceivingItem } from '@/features/receiving/api';
import { receivingToListResult } from '@/features/receiving/adapter';
import { ReceivingPhotos } from '@/features/receiving/components/ReceivingPhotos';
import type { ReceivingItem } from '@/features/receiving/types';
import type { MicroAction } from '@/types/actions';

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

function ReceivingDetail({ id }: { id: string }) {
  const { session, user } = useAuth();
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
    async (action: MicroAction) => {
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

  // Check if user is HOD (Head of Department) for verify action
  const isHOD = user?.role && ['chief_engineer', 'chief_officer', 'chief_steward', 'purser', 'captain', 'manager'].includes(user.role);

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
        <p className="text-red-400">Failed to load receiving item</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      <div>
        {data.receiving_number && (
          <p className="text-xs text-white/40 font-mono">{data.receiving_number}</p>
        )}
        <h2 className="text-xl font-semibold text-white">
          {data.supplier_name || `Receiving ${data.receiving_number || data.id.slice(0, 8)}`}
        </h2>
      </div>
      <div className="flex gap-2">
        <span className="px-2 py-1 text-xs rounded bg-white/10 text-white/80">
          {data.status?.replace(/_/g, ' ') || 'Pending'}
        </span>
        {data.items_count && (
          <span className="px-2 py-1 text-xs rounded bg-white/10 text-white/80">
            {data.items_count} items
          </span>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-2 pt-2 border-t border-white/10">
        <button
          onClick={() => handleAction('create_receiving')}
          disabled={isActionLoading}
          className="px-3 py-1.5 text-xs rounded bg-white/10 text-white/80 hover:bg-white/20 transition-colors disabled:opacity-50"
        >
          Start Receiving Event
        </button>
        <button
          onClick={() => handleAction('add_receiving_item')}
          disabled={isActionLoading}
          className="px-3 py-1.5 text-xs rounded bg-white/10 text-white/80 hover:bg-white/20 transition-colors disabled:opacity-50"
        >
          Add Line Item
        </button>
        <button
          onClick={() => handleAction('accept_receiving')}
          disabled={isActionLoading}
          className="px-3 py-1.5 text-xs rounded bg-white/10 text-white/80 hover:bg-white/20 transition-colors disabled:opacity-50"
        >
          Complete Receiving
        </button>
        <button
          onClick={() => handleAction('reject_receiving')}
          disabled={isActionLoading}
          className="px-3 py-1.5 text-xs rounded bg-white/10 text-white/80 hover:bg-white/20 transition-colors disabled:opacity-50"
        >
          Report Discrepancy
        </button>
        {isHOD && (
          <button
            onClick={() => handleAction('adjust_receiving_item')}
            disabled={isActionLoading}
            className="px-3 py-1.5 text-xs rounded bg-white/10 text-white/80 hover:bg-white/20 transition-colors disabled:opacity-50"
          >
            Verify Line Item
          </button>
        )}
      </div>

      {data.description && (
        <p className="text-sm text-white/60">{data.description}</p>
      )}
      {data.received_date && (
        <div className="text-sm">
          <span className="text-white/40">Received: </span>
          <span className="text-white/80">{new Date(data.received_date).toLocaleDateString()}</span>
        </div>
      )}
      {data.expected_date && !data.received_date && (
        <div className="text-sm">
          <span className="text-white/40">Expected: </span>
          <span className="text-white/80">{new Date(data.expected_date).toLocaleDateString()}</span>
        </div>
      )}
      {data.notes && (
        <div className="text-sm">
          <span className="text-white/40">Notes: </span>
          <span className="text-white/80">{data.notes}</span>
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
      router.push(`/receiving?id=${id}`, { scroll: false });
    },
    [router]
  );

  const handleCloseDetail = React.useCallback(() => {
    router.push('/receiving', { scroll: false });
  }, [router]);

  return (
    <div className="h-screen bg-surface-base">
      <EntityList<ReceivingItem>
        queryKey={['receiving']}
        fetchFn={fetchReceivingItems}
        adapter={receivingToListResult}
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
    <FeatureFlagGuard>
      <React.Suspense
        fallback={
          <div className="h-screen flex items-center justify-center bg-surface-base">
            <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
          </div>
        }
      >
        <ReceivingPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
