'use client';

/**
 * Receiving List Page - /receiving
 *
 * Tier 1 fragmented route for receivings.
 * Displays a list of receiving records with the ability to select and view details.
 *
 * @see REQUIREMENTS_TABLE.md - T1-RCV-01
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

// Receiving item type for items array
interface ReceivingItem {
  description: string;
  quantity_received: number;
  unit_price: number;
}

// Receiving list item type
interface ReceivingListItem {
  id: string;
  vendor_name: string;
  po_number: string;
  status: 'draft' | 'in_review' | 'accepted' | 'rejected';
  received_date: string;
  total: number;
  currency: string;
  received_by: string;
  items?: ReceivingItem[];
}

// Fetch receivings from API
async function fetchReceivings(yachtId: string, token: string): Promise<ReceivingListItem[]> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/receivings?yacht_id=${yachtId}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch receivings: ${response.status}`);
  }

  const data = await response.json();
  return data.receivings || data.items || data || [];
}

// Fetch single receiving detail
async function fetchReceivingDetail(id: string, token: string): Promise<Record<string, unknown>> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/entity/receiving/${id}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch receiving: ${response.status}`);
  }

  return response.json();
}

// Status color mapping
function getStatusColor(status: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'rejected':
      return 'critical';
    case 'in_review':
    case 'draft':
      return 'warning';
    case 'accepted':
      return 'success';
    default:
      return 'neutral';
  }
}

// Format currency
function formatCurrency(amount: number, currency: string): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency || 'USD',
  }).format(amount);
}

// Receiving List Item Component
function ReceivingRow({
  item,
  isSelected,
  onClick,
}: {
  item: ReceivingListItem;
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
            <span className="text-xs text-txt-tertiary font-mono">{item.po_number}</span>
            <StatusPill status={getStatusColor(item.status)} label={item.status.replace(/_/g, ' ')} />
          </div>
          <h3 className="text-sm font-medium text-txt-primary truncate">{item.vendor_name}</h3>
          <p className="text-xs text-txt-secondary mt-1">
            Received by {item.received_by}
          </p>
        </div>
        <div className="text-right">
          <p className="text-sm font-medium text-txt-primary">
            {formatCurrency(item.total, item.currency)}
          </p>
          <p className="text-xs text-txt-tertiary whitespace-nowrap">
            {new Date(item.received_date).toLocaleDateString()}
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
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-txt-tertiary">
          <path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-txt-primary mb-2">No Receiving Records</h3>
      <p className="text-sm text-txt-secondary max-w-sm">
        Create a receiving record to track deliveries and incoming shipments from vendors.
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
        <p className="text-sm text-txt-secondary">Loading receivings...</p>
      </div>
    </div>
  );
}

// Receiving detail content (simplified - will use full lens when available)
function ReceivingDetailContent({
  data,
  onBack,
  onClose,
}: {
  data: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
}) {
  const vendorName = (data?.vendor_name || 'Receiving') as string;
  const poNumber = data?.po_number as string;
  const status = data?.status as string;
  const total = data?.total as number;
  const currency = (data?.currency || 'USD') as string;
  const receivedBy = data?.received_by as string;
  const receivedDate = data?.received_date as string;
  const items = (data?.items || []) as ReceivingItem[];

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
          <p className="text-xs text-txt-tertiary">{poNumber}</p>
          <h2 className="text-lg font-semibold text-txt-primary">{vendorName}</h2>
        </div>
      </div>
      <div className="flex gap-2">
        <StatusPill status={getStatusColor(status || '')} label={(status || '').replace(/_/g, ' ')} />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-xs text-txt-tertiary">Total</p>
          <p className="text-sm text-txt-primary">{formatCurrency(total || 0, currency)}</p>
        </div>
        <div>
          <p className="text-xs text-txt-tertiary">Received By</p>
          <p className="text-sm text-txt-primary">{receivedBy}</p>
        </div>
        {receivedDate && (
          <div>
            <p className="text-xs text-txt-tertiary">Received Date</p>
            <p className="text-sm text-txt-primary">{new Date(receivedDate).toLocaleDateString()}</p>
          </div>
        )}
      </div>
      {items.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-txt-secondary uppercase tracking-wider">Items</h3>
          <div className="space-y-2">
            {items.map((item, index) => (
              <div key={index} className="p-3 bg-surface-elevated rounded-lg">
                <p className="text-sm text-txt-primary">{item.description}</p>
                <div className="flex justify-between mt-1">
                  <span className="text-xs text-txt-tertiary">Qty: {item.quantity_received}</span>
                  <span className="text-xs text-txt-primary">{formatCurrency(item.unit_price, currency)}</span>
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
function ReceivingPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, session } = useAuth();
  const token = session?.access_token;

  // Get selected ID from URL params
  const selectedId = searchParams.get('id');

  // Fetch receivings list
  const {
    data: receivings,
    isLoading: isLoadingList,
    error: listError,
    refetch: refetchList,
  } = useQuery({
    queryKey: ['receivings', user?.yachtId],
    queryFn: () => fetchReceivings(user?.yachtId || '', token || ''),
    enabled: !!user?.yachtId && !!token,
    staleTime: 30000,
  });

  // Fetch selected receiving detail
  const {
    data: selectedReceiving,
    isLoading: isLoadingDetail,
    refetch: refetchDetail,
  } = useQuery({
    queryKey: ['receiving', selectedId],
    queryFn: () => fetchReceivingDetail(selectedId!, token || ''),
    enabled: !!selectedId && !!token,
    staleTime: 30000,
  });

  // Handle receiving selection
  const handleSelect = React.useCallback(
    (id: string) => {
      router.push(`/receiving?id=${id}`, { scroll: false });
    },
    [router]
  );

  // Handle close detail panel
  const handleCloseDetail = React.useCallback(() => {
    router.push('/receiving', { scroll: false });
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
          <p className="text-status-critical">Failed to load receivings</p>
        </div>
      );
    }

    if (!receivings || receivings.length === 0) {
      return <EmptyState />;
    }

    return (
      <div className="divide-y divide-border-subtle">
        {receivings.map((rcv) => (
          <ReceivingRow
            key={rcv.id}
            item={rcv}
            isSelected={rcv.id === selectedId}
            onClick={() => handleSelect(rcv.id)}
          />
        ))}
      </div>
    );
  }, [receivings, isLoadingList, listError, selectedId, handleSelect]);

  return (
    <RouteLayout
      pageTitle="Receiving"
      showTopNav={true}
      topNavContent={
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-semibold text-txt-primary">Receiving</h1>
        </div>
      }
      primaryPanel={
        selectedId
          ? {
              visible: true,
              title: selectedReceiving?.vendor_name as string || 'Receiving',
              subtitle: selectedReceiving?.po_number as string,
              children: isLoadingDetail ? (
                <LoadingState />
              ) : selectedReceiving ? (
                <ReceivingDetailContent
                  data={selectedReceiving}
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
export default function ReceivingPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense fallback={<LoadingState />}>
        <ReceivingPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
