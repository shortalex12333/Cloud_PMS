'use client';

/**
 * Certificates List Page - /certificates
 *
 * Tier 1 fragmented route for certificates.
 * Displays a list of certificates with the ability to select and view details.
 *
 * @see REQUIREMENTS_TABLE.md - T1-CERT-01
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
        <p className="text-txt-tertiary">Redirecting...</p>
      </div>
    );
  }

  return <>{children}</>;
}

// Certificate list item type
interface CertificateListItem {
  id: string;
  name: string;
  certificate_type: string;
  issuing_authority: string;
  issue_date: string;
  expiry_date: string;
  status: 'valid' | 'expiring_soon' | 'expired';
  linked_equipment_id?: string;
}

// Fetch certificates from API
async function fetchCertificates(yachtId: string, token: string): Promise<CertificateListItem[]> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/certificates?yacht_id=${yachtId}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch certificates: ${response.status}`);
  }

  const data = await response.json();
  return data.certificates || data.items || data || [];
}

// Fetch single certificate detail
async function fetchCertificateDetail(id: string, token: string): Promise<Record<string, unknown>> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/entity/certificate/${id}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch certificate: ${response.status}`);
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
    case 'valid':
      return 'success';
    default:
      return 'neutral';
  }
}

// Format status label
function formatStatusLabel(status: string): string {
  return status.replace(/_/g, ' ');
}

// Certificate List Item Component
function CertificateRow({
  item,
  isSelected,
  onClick,
}: {
  item: CertificateListItem;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full text-left px-6 py-4 border-b border-surface-border',
        'hover:bg-surface-hover transition-colors',
        'focus:outline-none focus:bg-surface-hover',
        isSelected && 'bg-surface-active'
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-txt-tertiary font-mono">{item.certificate_type}</span>
            <StatusPill status={getStatusColor(item.status)} label={formatStatusLabel(item.status)} />
          </div>
          <h3 className="text-sm font-medium text-txt-primary truncate">{item.name}</h3>
          {item.issuing_authority && (
            <p className="text-xs text-txt-secondary mt-1 truncate">{item.issuing_authority}</p>
          )}
        </div>
        <div className="text-right">
          <p className="text-xs text-txt-tertiary">Expires</p>
          <p className="text-xs text-txt-secondary">
            {new Date(item.expiry_date).toLocaleDateString()}
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
          <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-txt-primary mb-2">No Certificates</h3>
      <p className="text-sm text-txt-secondary max-w-sm">
        Add certificates to track compliance, inspections, and regulatory requirements.
      </p>
    </div>
  );
}

// Loading state component
function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-surface-border border-t-txt-primary rounded-full animate-spin" />
        <p className="text-sm text-txt-secondary">Loading certificates...</p>
      </div>
    </div>
  );
}

// Certificate detail content
function CertificateDetailContent({
  data,
  onBack,
  onClose,
}: {
  data: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
}) {
  const name = (data?.name || 'Certificate') as string;
  const certificateType = data?.certificate_type as string;
  const status = data?.status as string;
  const issuingAuthority = data?.issuing_authority as string;
  const issueDate = data?.issue_date as string;
  const expiryDate = data?.expiry_date as string;

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
          <p className="text-xs text-txt-tertiary">{certificateType}</p>
          <h2 className="text-lg font-semibold text-txt-primary">{name}</h2>
        </div>
      </div>
      <div className="flex gap-2">
        <StatusPill status={getStatusColor(status || '')} label={formatStatusLabel(status || '')} />
      </div>
      <div className="grid grid-cols-2 gap-4 pt-2">
        {issuingAuthority && (
          <div className="space-y-1">
            <p className="text-xs text-txt-tertiary">Issuing Authority</p>
            <p className="text-sm text-txt-primary">{issuingAuthority}</p>
          </div>
        )}
        {issueDate && (
          <div className="space-y-1">
            <p className="text-xs text-txt-tertiary">Issue Date</p>
            <p className="text-sm text-txt-primary">{new Date(issueDate).toLocaleDateString()}</p>
          </div>
        )}
        {expiryDate && (
          <div className="space-y-1">
            <p className="text-xs text-txt-tertiary">Expiry Date</p>
            <p className="text-sm text-txt-primary">{new Date(expiryDate).toLocaleDateString()}</p>
          </div>
        )}
      </div>
    </div>
  );
}

// Main page component
function CertificatesPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, session } = useAuth();
  const token = session?.access_token;

  // Get selected ID from URL params
  const selectedId = searchParams.get('id');

  // Fetch certificates list
  const {
    data: certificates,
    isLoading: isLoadingList,
    error: listError,
    refetch: refetchList,
  } = useQuery({
    queryKey: ['certificates', user?.yachtId],
    queryFn: () => fetchCertificates(user?.yachtId || '', token || ''),
    enabled: !!user?.yachtId && !!token,
    staleTime: 30000,
  });

  // Fetch selected certificate detail
  const {
    data: selectedCertificate,
    isLoading: isLoadingDetail,
    refetch: refetchDetail,
  } = useQuery({
    queryKey: ['certificate', selectedId],
    queryFn: () => fetchCertificateDetail(selectedId!, token || ''),
    enabled: !!selectedId && !!token,
    staleTime: 30000,
  });

  // Handle certificate selection
  const handleSelect = React.useCallback(
    (id: string) => {
      router.push(`/certificates?id=${id}`, { scroll: false });
    },
    [router]
  );

  // Handle close detail panel
  const handleCloseDetail = React.useCallback(() => {
    router.push('/certificates', { scroll: false });
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
          <p className="text-status-critical">Failed to load certificates</p>
        </div>
      );
    }

    if (!certificates || certificates.length === 0) {
      return <EmptyState />;
    }

    return (
      <div className="divide-y divide-surface-border">
        {certificates.map((cert) => (
          <CertificateRow
            key={cert.id}
            item={cert}
            isSelected={cert.id === selectedId}
            onClick={() => handleSelect(cert.id)}
          />
        ))}
      </div>
    );
  }, [certificates, isLoadingList, listError, selectedId, handleSelect]);

  return (
    <RouteLayout
      pageTitle="Certificates"
      showTopNav={true}
      topNavContent={
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-semibold text-txt-primary">Certificates</h1>
        </div>
      }
      primaryPanel={
        selectedId
          ? {
              visible: true,
              title: selectedCertificate?.name as string || 'Certificate',
              subtitle: selectedCertificate?.certificate_type as string,
              children: isLoadingDetail ? (
                <LoadingState />
              ) : selectedCertificate ? (
                <CertificateDetailContent
                  data={selectedCertificate}
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
export default function CertificatesPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense fallback={<LoadingState />}>
        <CertificatesPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
