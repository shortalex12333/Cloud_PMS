'use client';

/**
 * Purchase Orders List Page - /purchasing
 *
 * Tier 1 fragmented route for purchase orders.
 * Displays a list of purchase orders with the ability to select and view details.
 *
 * @see REQUIREMENTS_TABLE.md - T1-PO-01
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

// Purchase order item type
interface PurchaseOrderItem {
  id: string;
  name: string;
  description?: string;
  quantity: number;
  unit_price: number;
  currency: string;
}

// Purchase order list item type
interface PurchaseOrderListItem {
  id: string;
  po_number: string;
  supplier_name: string;
  order_date: string;
  expected_delivery: string;
  total_amount: number;
  currency: string;
  status: 'draft' | 'submitted' | 'approved' | 'ordered' | 'received' | 'cancelled';
  items?: PurchaseOrderItem[];
}

// Fetch purchase orders from API
async function fetchPurchaseOrders(yachtId: string, token: string): Promise<PurchaseOrderListItem[]> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/purchase-orders?yacht_id=${yachtId}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch purchase orders: ${response.status}`);
  }

  const data = await response.json();
  return data.purchase_orders || data.items || data || [];
}

// Fetch single purchase order detail
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

// Purchase Order List Item Component
function PurchaseOrderRow({
  item,
  isSelected,
  onClick,
}: {
  item: PurchaseOrderListItem;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full text-left px-6 py-4 border-b border-border-subtle',
        'hover:bg-surface-hover transition-colors',
        'focus:outline-none focus:bg-surface-hover',
        isSelected && 'bg-surface-active'
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-txt-muted font-mono">{item.po_number}</span>
            <StatusPill status={getStatusColor(item.status)} label={item.status.replace(/_/g, ' ')} />
          </div>
          <h3 className="text-sm font-medium text-txt-primary truncate">{item.supplier_name}</h3>
          <p className="text-xs text-txt-secondary mt-1">
            Expected: {new Date(item.expected_delivery).toLocaleDateString()}
          </p>
        </div>
        <div className="text-right">
          <p className="text-sm font-medium text-txt-primary">
            {formatCurrency(item.total_amount, item.currency)}
          </p>
          <p className="text-xs text-txt-muted">
            {new Date(item.order_date).toLocaleDateString()}
          </p>
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
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-txt-muted">
          <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          <path d="M12 11v6M9 14h6" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-txt-primary mb-2">No Purchase Orders</h3>
      <p className="text-sm text-txt-secondary max-w-sm">
        Create a purchase order to track procurement of parts, supplies, and equipment.
      </p>
    </div>
  );
}

// Loading state component
function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-border-subtle border-t-txt-primary rounded-full animate-spin" />
        <p className="text-sm text-txt-secondary">Loading purchase orders...</p>
      </div>
    </div>
  );
}

// Purchase order detail content (simplified)
function PurchaseOrderDetailContent({
  data,
  onBack,
  onClose,
}: {
  data: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
}) {
  const supplierName = (data?.supplier_name || 'Purchase Order') as string;
  const poNumber = data?.po_number as string;
  const status = data?.status as string;
  const totalAmount = data?.total_amount as number;
  const currency = (data?.currency || 'USD') as string;
  const expectedDelivery = data?.expected_delivery as string;
  const items = (data?.items || []) as PurchaseOrderItem[];

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-4">
        <button
          onClick={onBack}
          className="p-2 hover:bg-surface-hover rounded-lg transition-colors"
          aria-label="Back"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-txt-secondary">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
        <div>
          <p className="text-xs text-txt-muted">{poNumber}</p>
          <h2 className="text-lg font-semibold text-txt-primary">{supplierName}</h2>
        </div>
      </div>
      <div className="flex gap-2">
        <StatusPill status={getStatusColor(status || '')} label={(status || '').replace(/_/g, ' ')} />
      </div>
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <p className="text-txt-muted">Total Amount</p>
          <p className="text-txt-primary font-medium">{formatCurrency(totalAmount || 0, currency)}</p>
        </div>
        {expectedDelivery && (
          <div>
            <p className="text-txt-muted">Expected Delivery</p>
            <p className="text-txt-primary">{new Date(expectedDelivery).toLocaleDateString()}</p>
          </div>
        )}
      </div>
      {items.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-txt-secondary uppercase tracking-wider">Items</h3>
          <div className="space-y-2">
            {items.map((item) => (
              <div key={item.id} className="p-3 bg-surface-elevated rounded-lg flex justify-between">
                <div>
                  <p className="text-sm text-txt-primary">{item.name}</p>
                  <p className="text-xs text-txt-muted">Qty: {item.quantity}</p>
                </div>
                <p className="text-sm text-txt-primary">{formatCurrency(item.unit_price * item.quantity, item.currency)}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Main page component
function PurchasingPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, session } = useAuth();
  const token = session?.access_token;

  // Get selected ID from URL params
  const selectedId = searchParams.get('id');

  // Fetch purchase orders list
  const {
    data: purchaseOrders,
    isLoading: isLoadingList,
    error: listError,
    refetch: refetchList,
  } = useQuery({
    queryKey: ['purchase-orders', user?.yachtId],
    queryFn: () => fetchPurchaseOrders(user?.yachtId || '', token || ''),
    enabled: !!user?.yachtId && !!token,
    staleTime: 30000,
  });

  // Fetch selected purchase order detail
  const {
    data: selectedPurchaseOrder,
    isLoading: isLoadingDetail,
    refetch: refetchDetail,
  } = useQuery({
    queryKey: ['purchase-order', selectedId],
    queryFn: () => fetchPurchaseOrderDetail(selectedId!, token || ''),
    enabled: !!selectedId && !!token,
    staleTime: 30000,
  });

  // Handle purchase order selection
  const handleSelect = React.useCallback(
    (id: string) => {
      router.push(`/purchasing?id=${id}`, { scroll: false });
    },
    [router]
  );

  // Handle close detail panel
  const handleCloseDetail = React.useCallback(() => {
    router.push('/purchasing', { scroll: false });
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
          <p className="text-status-critical">Failed to load purchase orders</p>
        </div>
      );
    }

    if (!purchaseOrders || purchaseOrders.length === 0) {
      return <EmptyState />;
    }

    return (
      <div className="divide-y divide-border-subtle">
        {purchaseOrders.map((po) => (
          <PurchaseOrderRow
            key={po.id}
            item={po}
            isSelected={po.id === selectedId}
            onClick={() => handleSelect(po.id)}
          />
        ))}
      </div>
    );
  }, [purchaseOrders, isLoadingList, listError, selectedId, handleSelect]);

  return (
    <RouteLayout
      pageTitle="Purchasing"
      showTopNav={true}
      topNavContent={
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-semibold text-txt-primary">Purchasing</h1>
        </div>
      }
      primaryPanel={
        selectedId
          ? {
              visible: true,
              title: selectedPurchaseOrder?.supplier_name as string || 'Purchase Order',
              subtitle: selectedPurchaseOrder?.po_number as string,
              children: isLoadingDetail ? (
                <LoadingState />
              ) : selectedPurchaseOrder ? (
                <PurchaseOrderDetailContent
                  data={selectedPurchaseOrder}
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
export default function PurchasingPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense fallback={<LoadingState />}>
        <PurchasingPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
