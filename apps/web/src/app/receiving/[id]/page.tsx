'use client';

/**
 * Receiving Detail Page - /receiving/[id]
 *
 * Tier 1 fragmented route for viewing a single receiving record.
 * Provides a full-page detail view with deep linking support.
 *
 * @see REQUIREMENTS_TABLE.md - T1-RCV-02
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
      router.replace(`/app?entity=receiving&id=${id}`);
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

// Receiving item type
interface ReceivingItem {
  description: string;
  quantity_received: number;
  unit_price: number;
}

// Fetch receiving detail
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

// Loading state
function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-border-subtle border-t-txt-primary rounded-full animate-spin" />
        <p className="text-sm text-txt-secondary">Loading receiving...</p>
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
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-txt-tertiary">
          <path d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-txt-primary mb-2">Receiving Not Found</h3>
      <p className="text-sm text-txt-secondary max-w-sm mb-4">
        This receiving record may have been deleted or you may not have access.
      </p>
      <button
        onClick={() => router.push('/receiving')}
        className="px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors"
      >
        Back to Receiving
      </button>
    </div>
  );
}

// Receiving detail content
function ReceivingContent({
  data,
  onBack,
  onNavigate,
}: {
  data: Record<string, unknown>;
  onBack: () => void;
  onNavigate: (entityType: string, entityId: string) => void;
}) {
  const vendorName = (data?.vendor_name || 'Receiving') as string;
  const poNumber = data?.po_number as string;
  const status = (data?.status || '') as string;
  const total = (data?.total || 0) as number;
  const currency = (data?.currency || 'USD') as string;
  const receivedBy = data?.received_by as string;
  const receivedDate = data?.received_date as string;
  const items = (data?.items || []) as ReceivingItem[];

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <p className="text-xs text-txt-tertiary font-mono">{poNumber}</p>
        <h1 className="text-2xl font-semibold text-txt-primary">{vendorName}</h1>
        <div className="flex gap-2">
          <StatusPill status={getStatusColor(status)} label={status.replace(/_/g, ' ')} />
        </div>
      </div>

      {/* Summary */}
      <div className="p-4 bg-surface-elevated rounded-lg">
        <div className="flex justify-between items-center">
          <span className="text-sm text-txt-secondary">Total Amount</span>
          <span className="text-xl font-semibold text-txt-primary">{formatCurrency(total, currency)}</span>
        </div>
      </div>

      {/* Metadata */}
      <div className="grid grid-cols-2 gap-4">
        {receivedBy && (
          <div className="space-y-1">
            <p className="text-xs text-txt-tertiary">Received By</p>
            <p className="text-sm text-txt-primary">{receivedBy}</p>
          </div>
        )}
        {receivedDate && (
          <div className="space-y-1">
            <p className="text-xs text-txt-tertiary">Received Date</p>
            <p className="text-sm text-txt-primary">{new Date(receivedDate).toLocaleDateString()}</p>
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
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-txt-primary">{item.description}</p>
                    <p className="text-xs text-txt-tertiary mt-1">Quantity: {item.quantity_received}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-txt-primary">{formatCurrency(item.unit_price, currency)}</p>
                    <p className="text-xs text-txt-tertiary">per unit</p>
                  </div>
                </div>
                <div className="mt-2 pt-2 border-t border-border-subtle flex justify-between">
                  <span className="text-xs text-txt-tertiary">Line Total</span>
                  <span className="text-sm text-txt-primary">{formatCurrency(item.quantity_received * item.unit_price, currency)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 pt-4 border-t border-border-subtle">
        <button className="px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors">
          Edit
        </button>
        {status === 'draft' && (
          <button className="px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors">
            Submit for Review
          </button>
        )}
        {status === 'in_review' && (
          <>
            <button className="px-4 py-2 bg-status-success/20 hover:bg-status-success/30 rounded-lg text-sm text-status-success transition-colors">
              Accept
            </button>
            <button className="px-4 py-2 bg-status-critical/20 hover:bg-status-critical/30 rounded-lg text-sm text-status-critical transition-colors">
              Reject
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// Main page content
function ReceivingDetailPageContent() {
  const router = useRouter();
  const params = useParams();
  const { session } = useAuth();
  const token = session?.access_token;

  const receivingId = params.id as string;

  // Fetch receiving
  const {
    data: receiving,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['receiving', receivingId],
    queryFn: () => fetchReceivingDetail(receivingId, token || ''),
    enabled: !!receivingId && !!token,
    staleTime: 30000,
    retry: 1,
  });

  // Handle back navigation
  const handleBack = React.useCallback(() => {
    router.back();
  }, [router]);

  // Handle close (go to list)
  const handleClose = React.useCallback(() => {
    router.push('/receiving');
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
            router.push(`/inventory/${entityId}`);
            break;
          case 'purchase_order':
            router.push(`/purchase-orders/${entityId}`);
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
  const payload = receiving?.payload as Record<string, unknown> | undefined;
  const vendorName = (receiving?.vendor_name || payload?.vendor_name || 'Receiving') as string;
  const poNumber = (receiving?.po_number || payload?.po_number) as string | undefined;

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
  } else if (!receiving) {
    content = <NotFoundState />;
  } else {
    content = (
      <ReceivingContent
        data={receiving}
        onBack={handleBack}
        onNavigate={handleNavigate}
      />
    );
  }

  return (
    <RouteLayout
      pageTitle={poNumber ? `${poNumber} — ${vendorName}` : vendorName}
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
            <p className="text-xs text-txt-tertiary uppercase tracking-wider">Receiving</p>
            <h1 className="text-lg font-semibold text-txt-primary truncate max-w-md">
              {poNumber ? `${poNumber} — ${vendorName}` : vendorName}
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
export default function ReceivingDetailPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense fallback={<LoadingState />}>
        <ReceivingDetailPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
