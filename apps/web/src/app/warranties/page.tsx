'use client';

/**
 * Warranties List Page - /warranties
 *
 * Tier 1 fragmented route for warranties.
 * Displays a list of warranties with the ability to select and view details.
 *
 * @see REQUIREMENTS_TABLE.md - T1-WAR-01
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
        <p className="text-txt-primary/60">Redirecting...</p>
      </div>
    );
  }

  return <>{children}</>;
}

// Warranty list item type
interface WarrantyListItem {
  id: string;
  item_name: string;
  manufacturer: string;
  warranty_provider: string;
  purchase_date: string;
  expiry_date: string;
  coverage_details: string;
  status: 'active' | 'expiring_soon' | 'expired';
  linked_equipment_id?: string;
}

// Fetch warranties from API
async function fetchWarranties(yachtId: string, token: string): Promise<WarrantyListItem[]> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/warranties?yacht_id=${yachtId}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch warranties: ${response.status}`);
  }

  const data = await response.json();
  return data.warranties || data.items || data || [];
}

// Fetch single warranty detail
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

// Warranty List Item Component
function WarrantyRow({
  item,
  isSelected,
  onClick,
}: {
  item: WarrantyListItem;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full text-left px-6 py-4 border-b border-border-subtle',
        'hover:bg-surface-elevated transition-colors',
        'focus:outline-none focus:bg-surface-elevated',
        isSelected && 'bg-surface-selected'
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <StatusPill status={getStatusColor(item.status)} label={item.status.replace(/_/g, ' ')} />
          </div>
          <h3 className="text-sm font-medium text-txt-primary truncate">{item.item_name}</h3>
          <p className="text-xs text-txt-secondary mt-1 truncate">
            {item.manufacturer} {item.warranty_provider && `| ${item.warranty_provider}`}
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-txt-muted">Expires</p>
          <p className="text-xs text-txt-secondary whitespace-nowrap">
            {formatDate(item.expiry_date)}
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
          <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-txt-primary mb-2">No Warranties</h3>
      <p className="text-sm text-txt-secondary max-w-sm">
        Track warranty information for equipment and parts to stay informed about coverage.
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
        <p className="text-sm text-txt-secondary">Loading warranties...</p>
      </div>
    </div>
  );
}

// Warranty detail content
function WarrantyDetailContent({
  data,
  onBack,
  onClose,
}: {
  data: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
}) {
  const itemName = (data?.item_name || 'Warranty') as string;
  const manufacturer = data?.manufacturer as string;
  const warrantyProvider = data?.warranty_provider as string;
  const status = data?.status as string;
  const coverageDetails = data?.coverage_details as string;
  const purchaseDate = data?.purchase_date as string;
  const expiryDate = data?.expiry_date as string;

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
          <p className="text-xs text-txt-muted">{manufacturer}</p>
          <h2 className="text-lg font-semibold text-txt-primary">{itemName}</h2>
        </div>
      </div>
      <div className="flex gap-2">
        <StatusPill status={getStatusColor(status || '')} label={(status || '').replace(/_/g, ' ')} />
      </div>
      {warrantyProvider && (
        <div className="space-y-1">
          <p className="text-xs text-txt-muted">Provider</p>
          <p className="text-sm text-txt-secondary">{warrantyProvider}</p>
        </div>
      )}
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
      {coverageDetails && (
        <div className="space-y-1">
          <p className="text-xs text-txt-muted">Coverage Details</p>
          <p className="text-sm text-txt-secondary">{coverageDetails}</p>
        </div>
      )}
    </div>
  );
}

// Main page component
function WarrantiesPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, session } = useAuth();
  const token = session?.access_token;

  // Get selected ID from URL params
  const selectedId = searchParams.get('id');

  // Fetch warranties list
  const {
    data: warranties,
    isLoading: isLoadingList,
    error: listError,
    refetch: refetchList,
  } = useQuery({
    queryKey: ['warranties', user?.yachtId],
    queryFn: () => fetchWarranties(user?.yachtId || '', token || ''),
    enabled: !!user?.yachtId && !!token,
    staleTime: 30000,
  });

  // Fetch selected warranty detail
  const {
    data: selectedWarranty,
    isLoading: isLoadingDetail,
    refetch: refetchDetail,
  } = useQuery({
    queryKey: ['warranty', selectedId],
    queryFn: () => fetchWarrantyDetail(selectedId!, token || ''),
    enabled: !!selectedId && !!token,
    staleTime: 30000,
  });

  // Handle warranty selection
  const handleSelect = React.useCallback(
    (id: string) => {
      router.push(`/warranties?id=${id}`, { scroll: false });
    },
    [router]
  );

  // Handle close detail panel
  const handleCloseDetail = React.useCallback(() => {
    router.push('/warranties', { scroll: false });
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
          <p className="text-status-critical">Failed to load warranties</p>
        </div>
      );
    }

    if (!warranties || warranties.length === 0) {
      return <EmptyState />;
    }

    return (
      <div className="divide-y divide-border-subtle">
        {warranties.map((warranty) => (
          <WarrantyRow
            key={warranty.id}
            item={warranty}
            isSelected={warranty.id === selectedId}
            onClick={() => handleSelect(warranty.id)}
          />
        ))}
      </div>
    );
  }, [warranties, isLoadingList, listError, selectedId, handleSelect]);

  return (
    <RouteLayout
      pageTitle="Warranties"
      showTopNav={true}
      topNavContent={
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-semibold text-txt-primary">Warranties</h1>
        </div>
      }
      primaryPanel={
        selectedId
          ? {
              visible: true,
              title: selectedWarranty?.item_name as string || 'Warranty',
              subtitle: selectedWarranty?.manufacturer as string,
              children: isLoadingDetail ? (
                <LoadingState />
              ) : selectedWarranty ? (
                <WarrantyDetailContent
                  data={selectedWarranty}
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
export default function WarrantiesPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense fallback={<LoadingState />}>
        <WarrantiesPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
