'use client';

/**
 * Shopping List Detail Page - /shopping-list/[id]
 *
 * Tier 1 fragmented route for viewing a single shopping list.
 * Provides a full-page detail view with deep linking support.
 *
 * @see REQUIREMENTS_TABLE.md - T1-SL-02
 */

import * as React from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { RouteLayout } from '@/components/layout';
import { isFragmentedRoutesEnabled } from '@/lib/featureFlags';
import { useAuth } from '@/hooks/useAuth';
import { StatusPill } from '@/components/ui/StatusPill';

// Feature flag guard
function FeatureFlagGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const params = useParams();

  React.useEffect(() => {
    if (!isFragmentedRoutesEnabled()) {
      // Redirect to legacy route with entity params
      const id = params.id as string;
      router.replace(`/app?entity=shopping_list&id=${id}`);
    }
  }, [router, params]);

  if (!isFragmentedRoutesEnabled()) {
    return (
      <div className="h-screen flex items-center justify-center bg-surface-base">
        <p className="text-txt-secondary">Redirecting...</p>
      </div>
    );
  }

  return <>{children}</>;
}

// Fetch shopping list detail
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

// Loading state
function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-border-subtle border-t-border-focus rounded-full animate-spin" />
        <p className="text-sm text-txt-secondary">Loading shopping list...</p>
      </div>
    </div>
  );
}

// Error state
function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="w-16 h-16 rounded-full bg-status-critical/10 flex items-center justify-center mb-4">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-status-critical">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 8v4M12 16h.01" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-txt-primary mb-2">Failed to Load</h3>
      <p className="text-sm text-txt-secondary max-w-sm mb-4">{message}</p>
      <button
        onClick={onRetry}
        className="px-4 py-2 bg-surface-elevated hover:bg-surface-active rounded-lg text-sm text-txt-primary transition-colors"
      >
        Try Again
      </button>
    </div>
  );
}

// Not found state
function NotFoundState() {
  const router = useRouter();

  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="w-16 h-16 rounded-full bg-surface-elevated flex items-center justify-center mb-4">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-txt-tertiary">
          <path d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-txt-primary mb-2">Shopping List Not Found</h3>
      <p className="text-sm text-txt-secondary max-w-sm mb-4">
        This shopping list may have been deleted or you may not have access.
      </p>
      <button
        onClick={() => router.push('/shopping-list')}
        className="px-4 py-2 bg-surface-elevated hover:bg-surface-active rounded-lg text-sm text-txt-primary transition-colors"
      >
        Back to Shopping Lists
      </button>
    </div>
  );
}

// Shopping list detail content
function ShoppingListContent({
  data,
  onBack,
  onNavigate,
}: {
  data: Record<string, unknown>;
  onBack: () => void;
  onNavigate: (entityType: string, entityId: string) => void;
}) {
  const title = (data?.title || 'Shopping List') as string;
  const status = (data?.status || '') as string;
  const requesterName = data?.requester_name as string;
  const approverName = data?.approver_name as string;
  const createdAt = data?.created_at as string;
  const items = (data?.items || []) as Array<{ part_name: string; quantity_requested: number; urgency: string; part_id?: string }>;

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold text-txt-primary">{title}</h1>
        <div className="flex gap-2">
          <StatusPill status={getStatusColor(status)} label={status.replace(/_/g, ' ')} />
        </div>
      </div>

      {/* Metadata */}
      <div className="grid grid-cols-2 gap-4">
        {requesterName && (
          <div className="space-y-1">
            <p className="text-xs text-txt-tertiary">Requested By</p>
            <p className="text-sm text-txt-secondary">{requesterName}</p>
          </div>
        )}
        {approverName && (
          <div className="space-y-1">
            <p className="text-xs text-txt-tertiary">Approved By</p>
            <p className="text-sm text-txt-secondary">{approverName}</p>
          </div>
        )}
        {createdAt && (
          <div className="space-y-1">
            <p className="text-xs text-txt-tertiary">Created</p>
            <p className="text-sm text-txt-secondary">{new Date(createdAt).toLocaleDateString()}</p>
          </div>
        )}
      </div>

      {/* Items */}
      {items.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-txt-secondary uppercase tracking-wider">Items ({items.length})</h2>
          <div className="space-y-2">
            {items.map((item, index) => (
              <div key={index} className="p-4 bg-surface-elevated rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    {item.part_id ? (
                      <button
                        onClick={() => onNavigate('part', item.part_id!)}
                        className="text-sm text-action-primary hover:text-action-primary-hover transition-colors"
                        data-testid="part-link"
                        data-navigate="part"
                      >
                        {item.part_name}
                      </button>
                    ) : (
                      <span className="text-sm text-txt-primary">{item.part_name}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-txt-secondary">Qty: {item.quantity_requested}</span>
                    <StatusPill status={getUrgencyColor(item.urgency)} label={item.urgency} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty items state */}
      {items.length === 0 && (
        <div className="p-6 bg-surface-elevated rounded-lg text-center">
          <p className="text-sm text-txt-secondary">No items in this shopping list.</p>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 pt-4 border-t border-border-subtle">
        {status === 'pending' && (
          <>
            <button className="px-4 py-2 bg-status-success/20 hover:bg-status-success/30 rounded-lg text-sm text-status-success transition-colors">
              Approve
            </button>
            <button className="px-4 py-2 bg-status-critical/20 hover:bg-status-critical/30 rounded-lg text-sm text-status-critical transition-colors">
              Reject
            </button>
          </>
        )}
        {status === 'approved' && (
          <button className="px-4 py-2 bg-surface-elevated hover:bg-surface-active rounded-lg text-sm text-txt-primary transition-colors">
            Mark as Ordered
          </button>
        )}
        <button className="px-4 py-2 bg-surface-elevated hover:bg-surface-active rounded-lg text-sm text-txt-primary transition-colors">
          Add Item
        </button>
      </div>
    </div>
  );
}

// Main page content
function ShoppingListDetailPageContent() {
  const router = useRouter();
  const params = useParams();
  const { session } = useAuth();
  const token = session?.access_token;

  const shoppingListId = params.id as string;

  // Fetch shopping list
  const {
    data: shoppingList,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['shopping-list', shoppingListId],
    queryFn: () => fetchShoppingListDetail(shoppingListId, token || ''),
    enabled: !!shoppingListId && !!token,
    staleTime: 30000,
    retry: 1,
  });

  // Handle back navigation
  const handleBack = React.useCallback(() => {
    router.back();
  }, [router]);

  // Handle close (go to list)
  const handleClose = React.useCallback(() => {
    router.push('/shopping-list');
  }, [router]);

  // Handle refresh
  const handleRefresh = React.useCallback(() => {
    refetch();
  }, [refetch]);

  // Handle cross-entity navigation
  const handleNavigate = React.useCallback(
    (entityType: string, entityId: string) => {
      if (isFragmentedRoutesEnabled()) {
        switch (entityType) {
          case 'part':
            router.push(`/inventory/${entityId}`);
            break;
          case 'work_order':
            router.push(`/work-orders/${entityId}`);
            break;
          default:
            router.push(`/app?entity=${entityType}&id=${entityId}`);
        }
      } else {
        router.push(`/app?entity=${entityType}&id=${entityId}`);
      }
    },
    [router]
  );

  // Derive display values
  const payload = shoppingList?.payload as Record<string, unknown> | undefined;
  const title = (shoppingList?.title || payload?.title || 'Shopping List') as string;

  // Render content based on state
  let content: React.ReactNode;

  if (isLoading) {
    content = <LoadingState />;
  } else if (error) {
    const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';
    if (errorMessage.includes('404')) {
      content = <NotFoundState />;
    } else {
      content = <ErrorState message={errorMessage} onRetry={handleRefresh} />;
    }
  } else if (!shoppingList) {
    content = <NotFoundState />;
  } else {
    content = (
      <ShoppingListContent
        data={shoppingList}
        onBack={handleBack}
        onNavigate={handleNavigate}
      />
    );
  }

  return (
    <RouteLayout
      pageTitle={title}
      showTopNav={true}
      topNavContent={
        <div className="flex items-center gap-4">
          <button
            onClick={handleBack}
            className="p-2 hover:bg-surface-elevated rounded-lg transition-colors"
            aria-label="Back"
            data-testid="back-button"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-txt-secondary">
              <path d="M15 18l-6-6 6-6" />
            </svg>
          </button>
          <div>
            <p className="text-xs text-txt-tertiary uppercase tracking-wider">Shopping List</p>
            <h1 className="text-lg font-semibold text-txt-primary truncate max-w-md">
              {title}
            </h1>
          </div>
        </div>
      }
    >
      {content}
    </RouteLayout>
  );
}

// Export with feature flag guard
export default function ShoppingListDetailPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense fallback={<LoadingState />}>
        <ShoppingListDetailPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
