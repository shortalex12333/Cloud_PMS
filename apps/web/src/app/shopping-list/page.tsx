'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { isFragmentedRoutesEnabled } from '@/lib/featureFlags';
import { useAuth } from '@/hooks/useAuth';
import { EntityList } from '@/features/entity-list/components/EntityList';
import { EntityDetailOverlay } from '@/features/entity-list/components/EntityDetailOverlay';
import { fetchShoppingList, fetchShoppingListItem } from '@/features/shopping-list/api';
import { shoppingListToListResult } from '@/features/shopping-list/adapter';
import { executeAction } from '@/lib/actionClient';
import type { ShoppingListItem } from '@/features/shopping-list/types';

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

function ShoppingListDetail({ id, onRefresh }: { id: string; onRefresh: () => void }) {
  const { session, user } = useAuth();
  const token = session?.access_token;
  const [isActionLoading, setIsActionLoading] = React.useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ['shopping-list-item', id],
    queryFn: () => fetchShoppingListItem(id, token || ''),
    enabled: !!token,
    staleTime: 30000,
  });

  // Action: Approve Item (HOD)
  const handleApprove = React.useCallback(async () => {
    if (!user?.yachtId || !id) return;

    setIsActionLoading(true);
    try {
      await executeAction(
        'approve_shopping_list_item',
        { yacht_id: user.yachtId, shopping_list_item_id: id },
        {}
      );
      onRefresh();
    } catch (error) {
      console.error('[ShoppingListDetail] Approve item failed:', error);
    } finally {
      setIsActionLoading(false);
    }
  }, [id, user?.yachtId, onRefresh]);

  // Action: Reject Item (HOD)
  const handleReject = React.useCallback(async () => {
    if (!user?.yachtId || !id) return;

    setIsActionLoading(true);
    try {
      await executeAction(
        'reject_shopping_list_item',
        { yacht_id: user.yachtId, shopping_list_item_id: id },
        {}
      );
      onRefresh();
    } catch (error) {
      console.error('[ShoppingListDetail] Reject item failed:', error);
    } finally {
      setIsActionLoading(false);
    }
  }, [id, user?.yachtId, onRefresh]);

  // Action: Promote to Part (engineers)
  const handlePromoteToPart = React.useCallback(async () => {
    if (!user?.yachtId || !id) return;

    setIsActionLoading(true);
    try {
      await executeAction(
        'promote_candidate_to_part',
        { yacht_id: user.yachtId, shopping_list_item_id: id },
        {}
      );
      onRefresh();
    } catch (error) {
      console.error('[ShoppingListDetail] Promote to part failed:', error);
    } finally {
      setIsActionLoading(false);
    }
  }, [id, user?.yachtId, onRefresh]);

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
        <p className="text-red-400">Failed to load shopping list item</p>
      </div>
    );
  }

  // Determine if actions should be shown based on status
  const canApproveReject = data.status === 'pending' || data.status === 'requested';
  const canPromoteToPart = !data.part_id && (data.status === 'approved' || data.status === 'pending');

  return (
    <div className="p-6 space-y-4">
      <div>
        {data.part_number && (
          <p className="text-xs text-white/40 font-mono">{data.part_number}</p>
        )}
        <h2 className="text-xl font-semibold text-white">
          {data.part_name || `Item ${data.part_number || data.id.slice(0, 8)}`}
        </h2>
      </div>
      <div className="flex gap-2">
        <span className="px-2 py-1 text-xs rounded bg-white/10 text-white/80">
          {data.status?.replace(/_/g, ' ') || 'Pending'}
        </span>
        {data.priority && (
          <span className="px-2 py-1 text-xs rounded bg-white/10 text-white/80">
            {data.priority}
          </span>
        )}
        <span className="px-2 py-1 text-xs rounded bg-white/10 text-white/80">
          Qty: {data.quantity_requested}{data.unit_of_measure ? ` ${data.unit_of_measure}` : ''}
        </span>
      </div>
      {data.description && (
        <p className="text-sm text-white/60">{data.description}</p>
      )}
      {data.requested_by_name && (
        <div className="text-sm">
          <span className="text-white/40">Requested by: </span>
          <span className="text-white/80">{data.requested_by_name}</span>
        </div>
      )}
      {data.approved_by_name && (
        <div className="text-sm">
          <span className="text-white/40">Approved by: </span>
          <span className="text-white/80">{data.approved_by_name}</span>
        </div>
      )}
      {data.notes && (
        <div className="text-sm">
          <span className="text-white/40">Notes: </span>
          <span className="text-white/80">{data.notes}</span>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-2 pt-4 border-t border-white/10">
        {canApproveReject && (
          <>
            <button
              onClick={handleApprove}
              disabled={isActionLoading}
              className="px-3 py-1.5 text-xs rounded bg-white/10 text-white/80 hover:bg-white/20 transition-colors disabled:opacity-50"
              data-action-id="approve_shopping_list_item"
            >
              {isActionLoading ? 'Processing...' : 'Approve Item'}
            </button>
            <button
              onClick={handleReject}
              disabled={isActionLoading}
              className="px-3 py-1.5 text-xs rounded bg-white/10 text-white/80 hover:bg-white/20 transition-colors disabled:opacity-50"
              data-action-id="reject_shopping_list_item"
            >
              {isActionLoading ? 'Processing...' : 'Reject Item'}
            </button>
          </>
        )}
        {canPromoteToPart && (
          <button
            onClick={handlePromoteToPart}
            disabled={isActionLoading}
            className="px-3 py-1.5 text-xs rounded bg-white/10 text-white/80 hover:bg-white/20 transition-colors disabled:opacity-50"
            data-action-id="promote_candidate_to_part"
          >
            {isActionLoading ? 'Processing...' : 'Promote to Part'}
          </button>
        )}
      </div>
    </div>
  );
}

function ShoppingListPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const selectedId = searchParams.get('id');

  const handleSelect = React.useCallback(
    (id: string) => {
      router.push(`/shopping-list?id=${id}`, { scroll: false });
    },
    [router]
  );

  const handleCloseDetail = React.useCallback(() => {
    router.push('/shopping-list', { scroll: false });
  }, [router]);

  // Refresh handler for after actions complete
  const handleRefresh = React.useCallback(() => {
    // Invalidate both the list and the specific item queries
    queryClient.invalidateQueries({ queryKey: ['shopping-list'] });
    if (selectedId) {
      queryClient.invalidateQueries({ queryKey: ['shopping-list-item', selectedId] });
    }
  }, [queryClient, selectedId]);

  return (
    <div className="h-screen bg-surface-base">
      <EntityList<ShoppingListItem>
        queryKey={['shopping-list']}
        fetchFn={fetchShoppingList}
        adapter={shoppingListToListResult}
        selectedId={selectedId}
        onSelect={handleSelect}
        emptyMessage="No shopping list items found"
      />

      <EntityDetailOverlay isOpen={!!selectedId} onClose={handleCloseDetail}>
        {selectedId && <ShoppingListDetail id={selectedId} onRefresh={handleRefresh} />}
      </EntityDetailOverlay>
    </div>
  );
}

export default function ShoppingListPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense
        fallback={
          <div className="h-screen flex items-center justify-center bg-surface-base">
            <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin" />
          </div>
        }
      >
        <ShoppingListPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
