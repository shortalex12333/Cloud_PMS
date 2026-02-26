'use client';

/**
 * Shopping List Page - /shopping-list
 *
 * Tier 1 fragmented route for shopping lists.
 * Displays a list of shopping lists with the ability to select and view details.
 *
 * @see REQUIREMENTS_TABLE.md - T1-SL-01
 */

import * as React from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { RouteLayout } from '@/components/layout';
import { isFragmentedRoutesEnabled } from '@/lib/featureFlags';
import { useAuth } from '@/hooks/useAuth';
import { StatusPill } from '@/components/ui/StatusPill';
import { cn } from '@/lib/utils';

// Feature flag guard - redirect if disabled
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
        <p className="text-txt-secondary">Redirecting...</p>
      </div>
    );
  }

  return <>{children}</>;
}

// Shopping list item type
interface ShoppingListItem {
  id: string;
  title: string;
  status: 'pending' | 'approved' | 'rejected' | 'ordered';
  requester_name?: string;
  approver_name?: string;
  created_at: string;
  items?: Array<{
    part_name: string;
    quantity_requested: number;
    urgency: string;
  }>;
}

// Fetch shopping lists from API
async function fetchShoppingLists(yachtId: string, token: string): Promise<ShoppingListItem[]> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/shopping-lists?yacht_id=${yachtId}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch shopping lists: ${response.status}`);
  }

  const data = await response.json();
  return data.shopping_lists || data.items || data || [];
}

// Fetch single shopping list detail
async function fetchShoppingListDetail(id: string, token: string): Promise<Record<string, unknown>> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/entity/shopping_list/${id}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch shopping list: ${response.status}`);
  }

  return response.json();
}

// Status color mapping
function getStatusColor(status: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'rejected':
      return 'critical';
    case 'pending':
      return 'warning';
    case 'approved':
    case 'ordered':
      return 'success';
    default:
      return 'neutral';
  }
}

// Urgency color mapping
function getUrgencyColor(urgency: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (urgency) {
    case 'critical':
    case 'emergency':
      return 'critical';
    case 'high':
    case 'urgent':
      return 'warning';
    default:
      return 'neutral';
  }
}

// Shopping List Row Component
function ShoppingListRow({
  item,
  isSelected,
  onClick,
}: {
  item: ShoppingListItem;
  isSelected: boolean;
  onClick: () => void;
}) {
  const itemCount = item.items?.length || 0;

  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full text-left px-6 py-4 border-b border-border-subtle',
        'hover:bg-surface-elevated transition-colors',
        'focus:outline-none focus:bg-surface-elevated',
        isSelected && 'bg-surface-active'
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <StatusPill status={getStatusColor(item.status)} label={item.status.replace(/_/g, ' ')} />
            {itemCount > 0 && (
              <span className="text-xs text-txt-tertiary">{itemCount} item{itemCount !== 1 ? 's' : ''}</span>
            )}
          </div>
          <h3 className="text-sm font-medium text-txt-primary truncate">{item.title}</h3>
          {item.requester_name && (
            <p className="text-xs text-txt-secondary mt-1 truncate">Requested by {item.requester_name}</p>
          )}
        </div>
        <div className="text-xs text-txt-tertiary whitespace-nowrap">
          {new Date(item.created_at).toLocaleDateString()}
        </div>
      </div>
    </button>
  );
}

// Empty state component
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="w-16 h-16 rounded-full bg-surface-elevated flex items-center justify-center mb-4">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-txt-tertiary">
          <path d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-txt-primary mb-2">No Shopping Lists</h3>
      <p className="text-sm text-txt-secondary max-w-sm">
        Create a shopping list to track parts and supplies that need to be ordered.
      </p>
    </div>
  );
}

// Loading state component
function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-border-subtle border-t-border-focus rounded-full animate-spin" />
        <p className="text-sm text-txt-secondary">Loading shopping lists...</p>
      </div>
    </div>
  );
}

// Shopping list detail content
function ShoppingListDetailContent({
  data,
  onBack,
  onClose,
}: {
  data: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
}) {
  const title = (data?.title || 'Shopping List') as string;
  const status = data?.status as string;
  const requesterName = data?.requester_name as string;
  const approverName = data?.approver_name as string;
  const items = (data?.items || []) as Array<{ part_name: string; quantity_requested: number; urgency: string }>;

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-4">
        <button
          onClick={onBack}
          className="p-2 hover:bg-surface-elevated rounded-lg transition-colors"
          aria-label="Back"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-txt-secondary">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
        <div>
          <h2 className="text-lg font-semibold text-txt-primary">{title}</h2>
        </div>
      </div>
      <div className="flex gap-2">
        <StatusPill status={getStatusColor(status || '')} label={(status || '').replace(/_/g, ' ')} />
      </div>
      {requesterName && (
        <p className="text-sm text-txt-secondary">Requested by: {requesterName}</p>
      )}
      {approverName && (
        <p className="text-sm text-txt-secondary">Approved by: {approverName}</p>
      )}
      {items.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-txt-secondary uppercase tracking-wider">Items</h3>
          <div className="space-y-2">
            {items.map((item, index) => (
              <div key={index} className="p-3 bg-surface-elevated rounded-lg">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-txt-primary">{item.part_name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-txt-tertiary">Qty: {item.quantity_requested}</span>
                    <StatusPill status={getUrgencyColor(item.urgency)} label={item.urgency} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Main page component
function ShoppingListPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, session } = useAuth();
  const token = session?.access_token;

  // Get selected ID from URL params
  const selectedId = searchParams.get('id');

  // Fetch shopping lists list
  const {
    data: shoppingLists,
    isLoading: isLoadingList,
    error: listError,
    refetch: refetchList,
  } = useQuery({
    queryKey: ['shopping-lists', user?.yachtId],
    queryFn: () => fetchShoppingLists(user?.yachtId || '', token || ''),
    enabled: !!user?.yachtId && !!token,
    staleTime: 30000,
  });

  // Fetch selected shopping list detail
  const {
    data: selectedShoppingList,
    isLoading: isLoadingDetail,
    refetch: refetchDetail,
  } = useQuery({
    queryKey: ['shopping-list', selectedId],
    queryFn: () => fetchShoppingListDetail(selectedId!, token || ''),
    enabled: !!selectedId && !!token,
    staleTime: 30000,
  });

  // Handle shopping list selection
  const handleSelect = React.useCallback(
    (id: string) => {
      router.push(`/shopping-list?id=${id}`, { scroll: false });
    },
    [router]
  );

  // Handle close detail panel
  const handleCloseDetail = React.useCallback(() => {
    router.push('/shopping-list', { scroll: false });
  }, [router]);

  // Handle back navigation
  const handleBack = React.useCallback(() => {
    router.back();
  }, [router]);

  // Handle refresh
  const handleRefresh = React.useCallback(() => {
    refetchList();
    refetchDetail();
  }, [refetchList, refetchDetail]);

  // Render list content
  const listContent = React.useMemo(() => {
    if (isLoadingList) {
      return <LoadingState />;
    }

    if (listError) {
      return (
        <div className="flex items-center justify-center h-full">
          <p className="text-status-critical">Failed to load shopping lists</p>
        </div>
      );
    }

    if (!shoppingLists || shoppingLists.length === 0) {
      return <EmptyState />;
    }

    return (
      <div className="divide-y divide-border-subtle">
        {shoppingLists.map((sl) => (
          <ShoppingListRow
            key={sl.id}
            item={sl}
            isSelected={sl.id === selectedId}
            onClick={() => handleSelect(sl.id)}
          />
        ))}
      </div>
    );
  }, [shoppingLists, isLoadingList, listError, selectedId, handleSelect]);

  return (
    <RouteLayout
      pageTitle="Shopping Lists"
      showTopNav={true}
      topNavContent={
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-semibold text-txt-primary">Shopping Lists</h1>
        </div>
      }
      primaryPanel={
        selectedId
          ? {
              visible: true,
              title: selectedShoppingList?.title as string || 'Shopping List',
              subtitle: undefined,
              children: isLoadingDetail ? (
                <LoadingState />
              ) : selectedShoppingList ? (
                <ShoppingListDetailContent
                  data={selectedShoppingList}
                  onBack={handleBack}
                  onClose={handleCloseDetail}
                />
              ) : null,
            }
          : undefined
      }
      onClosePrimaryPanel={handleCloseDetail}
    >
      {listContent}
    </RouteLayout>
  );
}

// Export with feature flag guard
export default function ShoppingListPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense fallback={<LoadingState />}>
        <ShoppingListPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
