'use client';

/**
 * Certificate Detail Page - /certificates/[id]
 *
 * Tier 1 fragmented route for viewing a single certificate.
 * Provides a full-page detail view with deep linking support.
 *
 * @see REQUIREMENTS_TABLE.md - T1-CERT-02
 */

import * as React from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { RouteLayout } from '@/components/layout';
import { isFragmentedRoutesEnabled } from '@/lib/featureFlags';
import { useAuth } from '@/hooks/useAuth';
import { StatusPill } from '@/components/ui/StatusPill';
import { executeAction } from '@/lib/actionClient';

// Feature flag guard
function FeatureFlagGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const params = useParams();

  React.useEffect(() => {
    if (!isFragmentedRoutesEnabled()) {
      // Redirect to legacy route with entity params
      const id = params.id as string;
      router.replace(`/app?entity=certificate&id=${id}`);
    }
  }, [router, params]);

  if (!isFragmentedRoutesEnabled()) {
    return (
      <div className="h-screen flex items-center justify-center bg-surface-base">
        <p className="text-txt-tertiary">Redirecting...</p>
      </div>
    );
  }

  return <>{children}</>;
}

// Fetch certificate detail
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

// Loading state
function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-surface-border border-t-txt-primary rounded-full animate-spin" />
        <p className="text-sm text-txt-secondary">Loading certificate...</p>
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
      <h3 className="text-lg font-medium text-txt-primary mb-2">Certificate Not Found</h3>
      <p className="text-sm text-txt-secondary max-w-sm mb-4">
        This certificate may have been deleted or you may not have access.
      </p>
      <button
        onClick={() => router.push('/certificates')}
        className="px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors"
      >
        Back to Certificates
      </button>
    </div>
  );
}

// Certificate detail content
function CertificateContent({
  data,
  onBack,
  onNavigate,
  onRefresh,
}: {
  data: Record<string, unknown>;
  onBack: () => void;
  onNavigate: (entityType: string, entityId: string) => void;
  onRefresh: () => void;
}) {
  const { user } = useAuth();
  const [isActionPending, setIsActionPending] = React.useState(false);

  const certificateId = data?.id as string;
  const name = (data?.name || 'Certificate') as string;
  const certificateType = data?.certificate_type as string;
  const status = (data?.status || '') as string;
  const issuingAuthority = data?.issuing_authority as string;
  const issueDate = data?.issue_date as string;
  const expiryDate = data?.expiry_date as string;
  const linkedEquipmentId = data?.linked_equipment_id as string;
  const linkedEquipmentName = data?.linked_equipment_name as string;

  // Action: Upload document for certificate
  const handleUploadDocument = React.useCallback(async () => {
    if (!certificateId || !user?.yachtId) return;

    // Placeholder for document upload - would need file picker integration
    console.log('[CertificateContent] Upload document - action_id: certificate.upload_document');
    // TODO: Integrate with file upload modal and executeAction
    // await executeAction('certificate.upload_document', { yacht_id: user.yachtId, certificate_id: certificateId }, { file: ... });
  }, [certificateId, user?.yachtId]);

  // Action: Set reminder for certificate expiry
  const handleSetReminder = React.useCallback(async () => {
    if (!certificateId || !user?.yachtId || !expiryDate) return;

    setIsActionPending(true);
    try {
      await executeAction(
        'certificate.set_reminder',
        { yacht_id: user.yachtId, certificate_id: certificateId },
        { expiry_date: expiryDate, reminder_days_before: 30 }
      );
      onRefresh();
    } catch (error) {
      console.error('[CertificateContent] Set reminder failed:', error);
    } finally {
      setIsActionPending(false);
    }
  }, [certificateId, user?.yachtId, expiryDate, onRefresh]);

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <p className="text-xs text-txt-tertiary font-mono uppercase">{certificateType}</p>
        <h1 className="text-2xl font-semibold text-txt-primary">{name}</h1>
        <div className="flex gap-2">
          <StatusPill status={getStatusColor(status)} label={formatStatusLabel(status)} />
        </div>
      </div>

      {/* Issuing Authority */}
      {issuingAuthority && (
        <div className="space-y-2">
          <h2 className="text-sm font-medium text-txt-tertiary uppercase tracking-wider">Issuing Authority</h2>
          <p className="text-txt-primary">{issuingAuthority}</p>
        </div>
      )}

      {/* Metadata */}
      <div className="grid grid-cols-2 gap-4">
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
        {linkedEquipmentId && (
          <div className="space-y-1">
            <p className="text-xs text-txt-tertiary">Linked Equipment</p>
            <button
              onClick={() => onNavigate('equipment', linkedEquipmentId)}
              className="text-sm text-accent-primary hover:text-accent-primary-hover transition-colors"
              data-testid="equipment-link"
              data-navigate="equipment"
            >
              {linkedEquipmentName || linkedEquipmentId}
            </button>
          </div>
        )}
      </div>

      {/* Expiry Information */}
      {status === 'expiring_soon' && (
        <div className="p-4 bg-status-warning/10 border border-status-warning/20 rounded-lg">
          <div className="flex items-start gap-3">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-status-warning flex-shrink-0 mt-0.5">
              <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div>
              <p className="text-sm font-medium text-status-warning">Certificate Expiring Soon</p>
              <p className="text-xs text-txt-secondary mt-1">
                This certificate will expire on {new Date(expiryDate).toLocaleDateString()}. Please arrange for renewal.
              </p>
            </div>
          </div>
        </div>
      )}

      {status === 'expired' && (
        <div className="p-4 bg-status-critical/10 border border-status-critical/20 rounded-lg">
          <div className="flex items-start gap-3">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-status-critical flex-shrink-0 mt-0.5">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 8v4M12 16h.01" />
            </svg>
            <div>
              <p className="text-sm font-medium text-status-critical">Certificate Expired</p>
              <p className="text-xs text-txt-secondary mt-1">
                This certificate expired on {new Date(expiryDate).toLocaleDateString()}. Immediate action is required.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 pt-4 border-t border-surface-border">
        <button
          onClick={handleUploadDocument}
          disabled={isActionPending}
          className="px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors disabled:opacity-50"
          data-action-id="certificate.upload_document"
        >
          Upload Document
        </button>
        <button
          onClick={handleSetReminder}
          disabled={isActionPending || !expiryDate}
          className="px-4 py-2 bg-surface-elevated hover:bg-surface-hover rounded-lg text-sm text-txt-primary transition-colors disabled:opacity-50"
          data-action-id="certificate.set_reminder"
        >
          {isActionPending ? 'Setting...' : 'Set Reminder'}
        </button>
      </div>
    </div>
  );
}

// Main page content
function CertificateDetailPageContent() {
  const router = useRouter();
  const params = useParams();
  const { session } = useAuth();
  const token = session?.access_token;

  const certificateId = params.id as string;

  // Fetch certificate
  const {
    data: certificate,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['certificate', certificateId],
    queryFn: () => fetchCertificateDetail(certificateId, token || ''),
    enabled: !!certificateId && !!token,
    staleTime: 30000,
    retry: 1,
  });

  // Handle back navigation
  const handleBack = React.useCallback(() => {
    router.back();
  }, [router]);

  // Handle close (go to list)
  const handleClose = React.useCallback(() => {
    router.push('/certificates');
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
  const payload = certificate?.payload as Record<string, unknown> | undefined;
  const name = (certificate?.name || payload?.name || 'Certificate') as string;
  const certificateType = (certificate?.certificate_type || payload?.certificate_type) as string | undefined;

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
  } else if (!certificate) {
    content = <NotFoundState />;
  } else {
    content = (
      <CertificateContent
        data={certificate}
        onBack={handleBack}
        onNavigate={handleNavigate}
      />
    );
  }

  return (
    <RouteLayout
      pageTitle={certificateType ? `${certificateType} - ${name}` : name}
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
            <p className="text-xs text-txt-tertiary uppercase tracking-wider">Certificate</p>
            <h1 className="text-lg font-semibold text-txt-primary truncate max-w-md">
              {certificateType ? `${certificateType} - ${name}` : name}
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
export default function CertificateDetailPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense fallback={<LoadingState />}>
        <CertificateDetailPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
