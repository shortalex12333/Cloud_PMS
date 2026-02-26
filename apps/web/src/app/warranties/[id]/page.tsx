'use client';

/**
 * Warranty Detail Page - /warranties/[id]
 *
 * Tier 1 fragmented route for viewing a single warranty.
 * Provides a full-page detail view with deep linking support.
 *
 * @see REQUIREMENTS_TABLE.md - T1-WAR-02
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
      router.replace(`/app?entity=warranty&id=${id}`);
    }
  }, [router, params]);

  if (!isFragmentedRoutesEnabled()) {
    return (
      <div className="h-screen flex items-center justify-center bg-surface-base">
        <p className="text-txt-primary/60">Redirecting...</p>
      </div>
    );
  }

  return <>{children}</>;
}

// Fetch warranty detail
async function fetchWarrantyDetail(id: string, token: string): Promise<Record<string, unknown>> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/entity/warranty/${id}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch warranty: ${response.status}`);
  }

  return response.json();
}

// Status color mapping
function getStatusColor(status: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'expired':
      return 'critical';
    case 'expiring_soon':
      return 'warning';
    case 'active':
      return 'success';
    default:
      return 'neutral';
  }
}

// Format date for display
function formatDate(dateString: string): string {
  if (!dateString) return '';
  return new Date(dateString).toLocaleDateString();
}

// Loading state
function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-border-subtle border-t-txt-primary rounded-full animate-spin" />
        <p className="text-sm text-txt-secondary">Loading warranty...</p>
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
      <h3 className="text-lg font-medium text-txt-primary mb-2">Warranty Not Found</h3>
      <p className="text-sm text-txt-secondary max-w-sm mb-4">
        This warranty may have been deleted or you may not have access.
      </p>
      <button
        onClick={() => router.push('/warranties')}
        className="px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors"
      >
        Back to Warranties
      </button>
    </div>
  );
}

// Warranty detail content
function WarrantyContent({
  data,
  onBack,
  onNavigate,
}: {
  data: Record<string, unknown>;
  onBack: () => void;
  onNavigate: (entityType: string, entityId: string) => void;
}) {
  const itemName = (data?.item_name || 'Warranty') as string;
  const manufacturer = (data?.manufacturer || '') as string;
  const warrantyProvider = (data?.warranty_provider || '') as string;
  const status = (data?.status || '') as string;
  const coverageDetails = data?.coverage_details as string;
  const purchaseDate = data?.purchase_date as string;
  const expiryDate = data?.expiry_date as string;
  const linkedEquipmentId = data?.linked_equipment_id as string;

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <p className="text-xs text-txt-muted uppercase tracking-wider">{manufacturer}</p>
        <h1 className="text-2xl font-semibold text-txt-primary">{itemName}</h1>
        <div className="flex gap-2">
          <StatusPill status={getStatusColor(status)} label={status.replace(/_/g, ' ')} />
        </div>
      </div>

      {/* Provider */}
      {warrantyProvider && (
        <div className="space-y-2">
          <h2 className="text-sm font-medium text-txt-muted uppercase tracking-wider">Warranty Provider</h2>
          <p className="text-txt-secondary">{warrantyProvider}</p>
        </div>
      )}

      {/* Dates */}
      <div className="grid grid-cols-2 gap-4">
        {purchaseDate && (
          <div className="space-y-1">
            <p className="text-xs text-txt-muted">Purchase Date</p>
            <p className="text-sm text-txt-secondary">{formatDate(purchaseDate)}</p>
          </div>
        )}
        {expiryDate && (
          <div className="space-y-1">
            <p className="text-xs text-txt-muted">Expiry Date</p>
            <p className="text-sm text-txt-secondary">{formatDate(expiryDate)}</p>
          </div>
        )}
      </div>

      {/* Coverage Details */}
      {coverageDetails && (
        <div className="space-y-2">
          <h2 className="text-sm font-medium text-txt-muted uppercase tracking-wider">Coverage Details</h2>
          <p className="text-txt-secondary">{coverageDetails}</p>
        </div>
      )}

      {/* Linked Equipment */}
      {linkedEquipmentId && (
        <div className="space-y-2">
          <h2 className="text-sm font-medium text-txt-muted uppercase tracking-wider">Linked Equipment</h2>
          <button
            onClick={() => onNavigate('equipment', linkedEquipmentId)}
            className="text-sm text-accent-primary hover:text-accent-primary-hover transition-colors"
            data-testid="equipment-link"
            data-navigate="equipment"
          >
            View Equipment
          </button>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 pt-4 border-t border-border-subtle">
        <button className="px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors">
          Edit Warranty
        </button>
        <button className="px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors">
          Upload Document
        </button>
      </div>
    </div>
  );
}

// Main page content
function WarrantyDetailPageContent() {
  const router = useRouter();
  const params = useParams();
  const { session } = useAuth();
  const token = session?.access_token;

  const warrantyId = params.id as string;

  // Fetch warranty
  const {
    data: warranty,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['warranty', warrantyId],
    queryFn: () => fetchWarrantyDetail(warrantyId, token || ''),
    enabled: !!warrantyId && !!token,
    staleTime: 30000,
    retry: 1,
  });

  // Handle back navigation
  const handleBack = React.useCallback(() => {
    router.back();
  }, [router]);

  // Handle close (go to list)
  const handleClose = React.useCallback(() => {
    router.push('/warranties');
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
          case 'equipment':
            router.push(`/equipment/${entityId}`);
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
  const payload = warranty?.payload as Record<string, unknown> | undefined;
  const itemName = (warranty?.item_name || payload?.item_name || 'Warranty') as string;
  const manufacturer = (warranty?.manufacturer || payload?.manufacturer) as string | undefined;

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
  } else if (!warranty) {
    content = <NotFoundState />;
  } else {
    content = (
      <WarrantyContent
        data={warranty}
        onBack={handleBack}
        onNavigate={handleNavigate}
      />
    );
  }

  return (
    <RouteLayout
      pageTitle={manufacturer ? `${manufacturer} - ${itemName}` : itemName}
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
            <p className="text-xs text-txt-muted uppercase tracking-wider">Warranty</p>
            <h1 className="text-lg font-semibold text-txt-primary truncate max-w-md">
              {manufacturer ? `${manufacturer} - ${itemName}` : itemName}
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
export default function WarrantyDetailPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense fallback={<LoadingState />}>
        <WarrantyDetailPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
