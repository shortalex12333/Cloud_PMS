'use client';

/**
 * Purchase Order Detail Page - /purchasing/[id]
 *
 * Tier 1 fragmented route for viewing a single purchase order.
 * Provides a full-page detail view with deep linking support.
 *
 * @see REQUIREMENTS_TABLE.md - T1-PO-02
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
      router.replace(`/app?entity=purchase_order&id=${id}`);
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

// Purchase order item type
interface PurchaseOrderItem {
  id: string;
  name: string;
  description?: string;
  quantity: number;
  unit_price: number;
  currency: string;
}

// Fetch purchase order detail
async function fetchPurchaseOrderDetail(id: string, token: string): Promise<Record<string, unknown>> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/entity/purchase_order/${id}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch purchase order: ${response.status}`);
  }

  return response.json();
}

// Status color mapping
function getStatusColor(status: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'cancelled':
      return 'critical';
    case 'draft':
    case 'submitted':
      return 'warning';
    case 'received':
      return 'success';
    case 'approved':
    case 'ordered':
      return 'neutral';
    default:
      return 'neutral';
  }
}

// Format currency amount
function formatCurrency(amount: number, currency: string): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency || 'USD',
  }).format(amount);
}

// Loading state
function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-border-subtle border-t-txt-primary rounded-full animate-spin" />
        <p className="text-sm text-txt-secondary">Loading purchase order...</p>
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
        className="px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors"
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
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-txt-muted">
          <path d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-txt-primary mb-2">Purchase Order Not Found</h3>
      <p className="text-sm text-txt-secondary max-w-sm mb-4">
        This purchase order may have been deleted or you may not have access.
      </p>
      <button
        onClick={() => router.push('/purchasing')}
        className="px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors"
      >
        Back to Purchasing
      </button>
    </div>
  );
}

// Purchase order detail content
function PurchaseOrderContent({
  data,
  onBack,
  onNavigate,
}: {
  data: Record<string, unknown>;
  onBack: () => void;
  onNavigate: (entityType: string, entityId: string) => void;
}) {
  const supplierName = (data?.supplier_name || 'Purchase Order') as string;
  const poNumber = data?.po_number as string;
  const status = (data?.status || '') as string;
  const orderDate = data?.order_date as string;
  const expectedDelivery = data?.expected_delivery as string;
  const totalAmount = (data?.total_amount || 0) as number;
  const currency = (data?.currency || 'USD') as string;
  const items = (data?.items || []) as PurchaseOrderItem[];
  const notes = data?.notes as string;

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <p className="text-xs text-txt-muted font-mono">{poNumber}</p>
        <h1 className="text-2xl font-semibold text-txt-primary">{supplierName}</h1>
        <div className="flex gap-2">
          <StatusPill status={getStatusColor(status)} label={status.replace(/_/g, ' ')} />
        </div>
      </div>

      {/* Order Details */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="space-y-1">
          <p className="text-xs text-txt-muted">Order Date</p>
          <p className="text-sm text-txt-primary">
            {orderDate ? new Date(orderDate).toLocaleDateString() : '-'}
          </p>
        </div>
        <div className="space-y-1">
          <p className="text-xs text-txt-muted">Expected Delivery</p>
          <p className="text-sm text-txt-primary">
            {expectedDelivery ? new Date(expectedDelivery).toLocaleDateString() : '-'}
          </p>
        </div>
        <div className="space-y-1">
          <p className="text-xs text-txt-muted">Total Amount</p>
          <p className="text-sm text-txt-primary font-medium">{formatCurrency(totalAmount, currency)}</p>
        </div>
        <div className="space-y-1">
          <p className="text-xs text-txt-muted">Currency</p>
          <p className="text-sm text-txt-primary">{currency}</p>
        </div>
      </div>

      {/* Line Items */}
      {items.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-txt-secondary uppercase tracking-wider">Line Items</h2>
          <div className="border border-border-subtle rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-surface-elevated">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-txt-muted uppercase tracking-wider">Item</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-txt-muted uppercase tracking-wider">Qty</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-txt-muted uppercase tracking-wider">Unit Price</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-txt-muted uppercase tracking-wider">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {items.map((item) => (
                  <tr key={item.id} className="hover:bg-surface-hover transition-colors">
                    <td className="px-4 py-3">
                      <p className="text-sm text-txt-primary">{item.name}</p>
                      {item.description && (
                        <p className="text-xs text-txt-muted mt-0.5">{item.description}</p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-txt-primary">{item.quantity}</td>
                    <td className="px-4 py-3 text-right text-sm text-txt-primary">
                      {formatCurrency(item.unit_price, item.currency || currency)}
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-txt-primary font-medium">
                      {formatCurrency(item.unit_price * item.quantity, item.currency || currency)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-surface-elevated">
                <tr>
                  <td colSpan={3} className="px-4 py-3 text-right text-sm font-medium text-txt-primary">Total</td>
                  <td className="px-4 py-3 text-right text-sm font-semibold text-txt-primary">
                    {formatCurrency(totalAmount, currency)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}

      {/* Notes */}
      {notes && (
        <div className="space-y-2">
          <h2 className="text-sm font-medium text-txt-secondary uppercase tracking-wider">Notes</h2>
          <p className="text-txt-primary">{notes}</p>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 pt-4 border-t border-border-subtle">
        {status === 'draft' && (
          <button className="px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors">
            Submit Order
          </button>
        )}
        {status === 'submitted' && (
          <button className="px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors">
            Approve
          </button>
        )}
        {status === 'ordered' && (
          <button className="px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors">
            Mark Received
          </button>
        )}
        {status !== 'cancelled' && status !== 'received' && (
          <button className="px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-status-critical transition-colors">
            Cancel Order
          </button>
        )}
      </div>
    </div>
  );
}

// Main page content
function PurchaseOrderDetailPageContent() {
  const router = useRouter();
  const params = useParams();
  const { session } = useAuth();
  const token = session?.access_token;

  const purchaseOrderId = params.id as string;

  // Fetch purchase order
  const {
    data: purchaseOrder,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['purchase-order', purchaseOrderId],
    queryFn: () => fetchPurchaseOrderDetail(purchaseOrderId, token || ''),
    enabled: !!purchaseOrderId && !!token,
    staleTime: 30000,
    retry: 1,
  });

  // Handle back navigation
  const handleBack = React.useCallback(() => {
    router.back();
  }, [router]);

  // Handle close (go to list)
  const handleClose = React.useCallback(() => {
    router.push('/purchasing');
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
          case 'inventory':
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
  const payload = purchaseOrder?.payload as Record<string, unknown> | undefined;
  const supplierName = (purchaseOrder?.supplier_name || payload?.supplier_name || 'Purchase Order') as string;
  const poNumber = (purchaseOrder?.po_number || payload?.po_number) as string | undefined;

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
  } else if (!purchaseOrder) {
    content = <NotFoundState />;
  } else {
    content = (
      <PurchaseOrderContent
        data={purchaseOrder}
        onBack={handleBack}
        onNavigate={handleNavigate}
      />
    );
  }

  return (
    <RouteLayout
      pageTitle={poNumber ? `${poNumber} — ${supplierName}` : supplierName}
      showTopNav={true}
      topNavContent={
        <div className="flex items-center gap-4">
          <button
            onClick={handleBack}
            className="p-2 hover:bg-surface-hover rounded-lg transition-colors"
            aria-label="Back"
            data-testid="back-button"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-txt-secondary">
              <path d="M15 18l-6-6 6-6" />
            </svg>
          </button>
          <div>
            <p className="text-xs text-txt-muted uppercase tracking-wider">Purchase Order</p>
            <h1 className="text-lg font-semibold text-txt-primary truncate max-w-md">
              {poNumber ? `${poNumber} — ${supplierName}` : supplierName}
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
export default function PurchaseOrderDetailPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense fallback={<LoadingState />}>
        <PurchaseOrderDetailPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
