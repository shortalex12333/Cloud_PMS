'use client';

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { isFragmentedRoutesEnabled } from '@/lib/featureFlags';
import { useAuth } from '@/hooks/useAuth';
import { isHOD, isEngineer } from '@/contexts/AuthContext';
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
  const [showRejectDialog, setShowRejectDialog] = React.useState(false);
  const [rejectionReason, setRejectionReason] = React.useState('');
  const [showLinkWorkOrderDialog, setShowLinkWorkOrderDialog] = React.useState(false);
  const [workOrderSearchQuery, setWorkOrderSearchQuery] = React.useState('');
  const [workOrderSearchResults, setWorkOrderSearchResults] = React.useState<Array<{ id: string; title: string; work_order_number?: string; status?: string }>>([]);
  const [selectedWorkOrder, setSelectedWorkOrder] = React.useState<{ id: string; title: string } | null>(null);
  const [isSearchingWorkOrders, setIsSearchingWorkOrders] = React.useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ['shopping-list-item', id],
    queryFn: () => fetchShoppingListItem(id, token || ''),
    enabled: !!token,
    staleTime: 30000,
  });

  // Role-based permissions
  const userIsHOD = isHOD(user);
  const userIsEngineer = isEngineer(user);

  // Action: Approve Item (HOD)
  const handleApprove = React.useCallback(async (notes?: string) => {
    if (!user?.yachtId || !id) return;

    setIsActionLoading(true);
    try {
      await executeAction(
        'approve_shopping_list_item',
        { yacht_id: user.yachtId, shopping_list_item_id: id },
        notes ? { notes } : {}
      );
      onRefresh();
    } catch (error) {
      console.error('[ShoppingListDetail] Approve item failed:', error);
    } finally {
      setIsActionLoading(false);
    }
  }, [id, user?.yachtId, onRefresh]);

  // Action: Reject Item (HOD) - requires rejection_reason
  const handleReject = React.useCallback(async (reason: string) => {
    if (!user?.yachtId || !id || !reason.trim()) return;

    setIsActionLoading(true);
    try {
      await executeAction(
        'reject_shopping_list_item',
        { yacht_id: user.yachtId, shopping_list_item_id: id },
        { rejection_reason: reason.trim() }
      );
      setShowRejectDialog(false);
      setRejectionReason('');
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

  // Search work orders for linking
  const searchWorkOrders = React.useCallback(async (query: string) => {
    if (!token || !user?.yachtId || query.length < 2) {
      setWorkOrderSearchResults([]);
      return;
    }

    setIsSearchingWorkOrders(true);
    try {
      const response = await fetch('/api/search/fallback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          query,
          yacht_id: user.yachtId,
          limit: 10,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        // Filter to only work orders
        const workOrders = (data.results || [])
          .filter((r: { type: string }) => r.type === 'work_order')
          .map((r: { id: string; title: string; metadata?: { work_order_number?: string; status?: string } }) => ({
            id: r.id,
            title: r.title,
            work_order_number: r.metadata?.work_order_number,
            status: r.metadata?.status,
          }));
        setWorkOrderSearchResults(workOrders);
      }
    } catch (error) {
      console.error('[ShoppingListDetail] Work order search failed:', error);
    } finally {
      setIsSearchingWorkOrders(false);
    }
  }, [token, user?.yachtId]);

  // Debounced search
  React.useEffect(() => {
    const timer = setTimeout(() => {
      if (workOrderSearchQuery.length >= 2) {
        searchWorkOrders(workOrderSearchQuery);
      } else {
        setWorkOrderSearchResults([]);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [workOrderSearchQuery, searchWorkOrders]);

  // Action: Link to Work Order (all crew)
  const handleLinkToWorkOrder = React.useCallback(async () => {
    if (!user?.yachtId || !id || !selectedWorkOrder) return;

    setIsActionLoading(true);
    try {
      await executeAction(
        'link_to_work_order',
        { yacht_id: user.yachtId, shopping_list_item_id: id },
        { work_order_id: selectedWorkOrder.id }
      );
      setShowLinkWorkOrderDialog(false);
      setSelectedWorkOrder(null);
      setWorkOrderSearchQuery('');
      setWorkOrderSearchResults([]);
      onRefresh();
    } catch (error) {
      console.error('[ShoppingListDetail] Link to work order failed:', error);
    } finally {
      setIsActionLoading(false);
    }
  }, [id, user?.yachtId, selectedWorkOrder, onRefresh]);

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

  // Determine if actions should be shown based on status AND role
  // Valid DB statuses: candidate, under_review, approved, ordered, partially_fulfilled, installed
  const statusAllowsApproveReject = data.status === 'candidate' || data.status === 'under_review';
  const canApproveReject = statusAllowsApproveReject && userIsHOD;
  const canPromoteToPart = userIsEngineer && !data.part_id && (data.status === 'approved' || data.status === 'candidate');

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
      {data.source_work_order_id && (
        <div className="text-sm" data-testid="linked-work-order">
          <span className="text-white/40">Source: </span>
          <a
            href={`/work-orders?id=${data.source_work_order_id}`}
            className="text-blue-400 hover:text-blue-300 hover:underline"
            data-testid="linked-work-order-link"
          >
            Work Order
          </a>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-2 pt-4 border-t border-white/10">
        {canApproveReject && (
          <>
            <button
              onClick={() => handleApprove()}
              disabled={isActionLoading}
              className="px-3 py-1.5 text-xs rounded bg-green-600/80 text-white hover:bg-green-600 transition-colors disabled:opacity-50"
              data-action-id="approve_shopping_list_item"
              data-testid="approve-button"
            >
              {isActionLoading ? 'Processing...' : 'Approve'}
            </button>
            <button
              onClick={() => setShowRejectDialog(true)}
              disabled={isActionLoading}
              className="px-3 py-1.5 text-xs rounded bg-red-600/80 text-white hover:bg-red-600 transition-colors disabled:opacity-50"
              data-action-id="reject_shopping_list_item"
              data-testid="reject-button"
            >
              {isActionLoading ? 'Processing...' : 'Reject'}
            </button>
          </>
        )}
        {canPromoteToPart && (
          <button
            onClick={handlePromoteToPart}
            disabled={isActionLoading}
            className="px-3 py-1.5 text-xs rounded bg-white/10 text-white/80 hover:bg-white/20 transition-colors disabled:opacity-50"
            data-action-id="promote_candidate_to_part"
            data-testid="promote-to-part-button"
          >
            {isActionLoading ? 'Processing...' : 'Promote to Part'}
          </button>
        )}
        {/* Link to Work Order - available if no work order linked yet */}
        {!data.source_work_order_id && (
          <button
            onClick={() => setShowLinkWorkOrderDialog(true)}
            disabled={isActionLoading}
            className="px-3 py-1.5 text-xs rounded bg-blue-600/80 text-white hover:bg-blue-600 transition-colors disabled:opacity-50"
            data-action-id="link_to_work_order"
            data-testid="link-to-work-order-button"
          >
            {isActionLoading ? 'Processing...' : 'Link to Work Order'}
          </button>
        )}
      </div>

      {/* Reject Dialog */}
      {showRejectDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" data-testid="reject-dialog">
          <div className="bg-surface-raised p-6 rounded-lg shadow-xl max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-white mb-4">Reject Item</h3>
            <label className="block text-sm text-white/60 mb-2">
              Rejection Reason <span className="text-red-400">*</span>
            </label>
            <textarea
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              placeholder="Enter reason for rejection..."
              className="w-full h-24 bg-white/5 border border-white/10 rounded px-3 py-2 text-white text-sm resize-none focus:outline-none focus:border-white/30"
              data-testid="rejection-reason-input"
              autoFocus
            />
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => {
                  setShowRejectDialog(false);
                  setRejectionReason('');
                }}
                className="px-4 py-2 text-sm rounded bg-white/10 text-white/80 hover:bg-white/20 transition-colors"
                data-testid="reject-cancel-button"
              >
                Cancel
              </button>
              <button
                onClick={() => handleReject(rejectionReason)}
                disabled={isActionLoading || !rejectionReason.trim()}
                className="px-4 py-2 text-sm rounded bg-red-600 text-white hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                data-testid="reject-confirm-button"
              >
                {isActionLoading ? 'Rejecting...' : 'Confirm Reject'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Link to Work Order Dialog */}
      {showLinkWorkOrderDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" data-testid="link-work-order-dialog">
          <div className="bg-surface-raised p-6 rounded-lg shadow-xl max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-white mb-4">Link to Work Order</h3>
            <label className="block text-sm text-white/60 mb-2">
              Search Work Orders
            </label>
            <input
              type="text"
              value={workOrderSearchQuery}
              onChange={(e) => setWorkOrderSearchQuery(e.target.value)}
              placeholder="Search by title or WO number..."
              className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-white/30"
              data-testid="work-order-search-input"
              autoFocus
            />

            {/* Search Results */}
            <div className="mt-3 max-h-48 overflow-y-auto border border-white/10 rounded">
              {isSearchingWorkOrders ? (
                <div className="p-4 text-center">
                  <div className="w-5 h-5 border-2 border-white/20 border-t-white/80 rounded-full animate-spin mx-auto" />
                </div>
              ) : workOrderSearchQuery.length < 2 ? (
                <div className="p-4 text-center text-white/40 text-sm">
                  Type at least 2 characters to search
                </div>
              ) : workOrderSearchResults.length === 0 ? (
                <div className="p-4 text-center text-white/40 text-sm">
                  No work orders found
                </div>
              ) : (
                workOrderSearchResults.map((wo) => (
                  <button
                    key={wo.id}
                    onClick={() => setSelectedWorkOrder(wo)}
                    className={`w-full text-left p-3 border-b border-white/5 last:border-b-0 transition-colors ${
                      selectedWorkOrder?.id === wo.id
                        ? 'bg-blue-600/30 text-white'
                        : 'hover:bg-white/5 text-white/80'
                    }`}
                    data-testid={`work-order-option-${wo.id}`}
                    data-work-order-id={wo.id}
                  >
                    <div className="text-sm font-medium">{wo.title}</div>
                    <div className="text-xs text-white/40">
                      {wo.work_order_number && `#${wo.work_order_number} | `}
                      {wo.status || 'Unknown status'}
                    </div>
                  </button>
                ))
              )}
            </div>

            {/* Selected Work Order Display */}
            {selectedWorkOrder && (
              <div className="mt-3 p-2 bg-blue-600/20 rounded border border-blue-600/30 text-sm text-white">
                Selected: {selectedWorkOrder.title}
              </div>
            )}

            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => {
                  setShowLinkWorkOrderDialog(false);
                  setSelectedWorkOrder(null);
                  setWorkOrderSearchQuery('');
                  setWorkOrderSearchResults([]);
                }}
                className="px-4 py-2 text-sm rounded bg-white/10 text-white/80 hover:bg-white/20 transition-colors"
                data-testid="link-work-order-cancel"
              >
                Cancel
              </button>
              <button
                onClick={handleLinkToWorkOrder}
                disabled={isActionLoading || !selectedWorkOrder}
                className="px-4 py-2 text-sm rounded bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                data-testid="link-work-order-submit"
              >
                {isActionLoading ? 'Linking...' : 'Link'}
              </button>
            </div>
          </div>
        </div>
      )}
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
