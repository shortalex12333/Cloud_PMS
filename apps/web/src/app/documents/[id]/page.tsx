'use client';

/**
 * Document Detail Page - /documents/[id]
 *
 * Tier 1 fragmented route for viewing a single document.
 * Provides a full-page detail view with deep linking support.
 *
 * @see REQUIREMENTS_TABLE.md - T1-DOC-02
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
      router.replace(`/app?entity=document&id=${id}`);
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

// Fetch document detail
async function fetchDocumentDetail(id: string, token: string): Promise<Record<string, unknown>> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/entity/document/${id}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch document: ${response.status}`);
  }

  return response.json();
}

// Status color mapping
function getStatusColor(status: string): 'critical' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'expired':
      return 'critical';
    case 'archived':
      return 'neutral';
    case 'active':
      return 'success';
    default:
      return 'neutral';
  }
}

// Document type display mapping
function formatDocumentType(type: string): string {
  return type
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

// Loading state
function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-txt-tertiary border-t-txt-primary rounded-full animate-spin" />
        <p className="text-sm text-txt-secondary">Loading document...</p>
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
        className="px-4 py-2 bg-surface-hover hover:bg-surface-active rounded-lg text-sm text-txt-primary transition-colors"
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
      <div className="w-16 h-16 rounded-full bg-surface-hover flex items-center justify-center mb-4">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-txt-tertiary">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="9" y1="15" x2="15" y2="15" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-txt-primary mb-2">Document Not Found</h3>
      <p className="text-sm text-txt-secondary max-w-sm mb-4">
        This document may have been deleted or you may not have access.
      </p>
      <button
        onClick={() => router.push('/documents')}
        className="px-4 py-2 bg-surface-hover hover:bg-surface-active rounded-lg text-sm text-txt-primary transition-colors"
      >
        Back to Documents
      </button>
    </div>
  );
}

// Document detail content
function DocumentContent({
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

  const documentId = data?.id as string;
  const title = (data?.title || 'Document') as string;
  const documentType = (data?.document_type || '') as string;
  const status = (data?.status || '') as string;
  const fileUrl = data?.file_url as string;
  const uploadedAt = data?.uploaded_at as string;
  const expiryDate = data?.expiry_date as string;
  const description = data?.description as string;
  const equipmentId = data?.equipment_id as string;
  const equipmentName = data?.equipment_name as string;

  // Action: Archive document
  const handleArchive = React.useCallback(async () => {
    if (!documentId || !user?.yachtId) return;

    setIsActionPending(true);
    try {
      await executeAction(
        'document.archive',
        { yacht_id: user.yachtId, document_id: documentId },
        {}
      );
      onRefresh();
    } catch (error) {
      console.error('[DocumentContent] Archive failed:', error);
    } finally {
      setIsActionPending(false);
    }
  }, [documentId, user?.yachtId, onRefresh]);

  // Action: Replace document (opens file picker, then uploads)
  const handleReplace = React.useCallback(async () => {
    if (!documentId || !user?.yachtId) return;

    // For now, this is a placeholder - actual file upload would need a file input
    console.log('[DocumentContent] Replace document - action_id: document.replace');
    // TODO: Integrate with file upload modal and executeAction
    // await executeAction('document.replace', { yacht_id: user.yachtId, document_id: documentId }, { file: ... });
  }, [documentId, user?.yachtId]);

  // Calculate days until expiry
  const daysUntilExpiry = React.useMemo(() => {
    if (!expiryDate) return null;
    const expiry = new Date(expiryDate);
    const today = new Date();
    return Math.ceil((expiry.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  }, [expiryDate]);

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <p className="text-xs text-txt-tertiary font-mono uppercase tracking-wider">
          {formatDocumentType(documentType)}
        </p>
        <h1 className="text-2xl font-semibold text-txt-primary">{title}</h1>
        <div className="flex gap-2 flex-wrap">
          <StatusPill status={getStatusColor(status)} label={status} />
          {daysUntilExpiry !== null && daysUntilExpiry > 0 && daysUntilExpiry <= 30 && (
            <StatusPill status="warning" label={`Expires in ${daysUntilExpiry} days`} />
          )}
          {daysUntilExpiry !== null && daysUntilExpiry <= 0 && (
            <StatusPill status="critical" label="Expired" />
          )}
        </div>
      </div>

      {/* Description */}
      {description && (
        <div className="space-y-2">
          <h2 className="text-sm font-medium text-txt-tertiary uppercase tracking-wider">Description</h2>
          <p className="text-txt-secondary">{description}</p>
        </div>
      )}

      {/* Metadata */}
      <div className="grid grid-cols-2 gap-4">
        {uploadedAt && (
          <div className="space-y-1">
            <p className="text-xs text-txt-tertiary">Uploaded</p>
            <p className="text-sm text-txt-secondary">{new Date(uploadedAt).toLocaleDateString()}</p>
          </div>
        )}
        {expiryDate && (
          <div className="space-y-1">
            <p className="text-xs text-txt-tertiary">Expiry Date</p>
            <p className="text-sm text-txt-secondary">{new Date(expiryDate).toLocaleDateString()}</p>
          </div>
        )}
        {equipmentId && (
          <div className="space-y-1">
            <p className="text-xs text-txt-tertiary">Related Equipment</p>
            <button
              onClick={() => onNavigate('equipment', equipmentId)}
              className="text-sm text-accent-primary hover:text-accent-primary-hover transition-colors"
              data-testid="equipment-link"
              data-navigate="equipment"
            >
              {equipmentName || equipmentId}
            </button>
          </div>
        )}
      </div>

      {/* Document Preview / Download */}
      {fileUrl && (
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-txt-tertiary uppercase tracking-wider">Document File</h2>
          <div className="flex gap-3">
            <a
              href={fileUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 bg-surface-hover hover:bg-surface-active rounded-lg text-sm text-txt-primary transition-colors"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" />
                <polyline points="15 3 21 3 21 9" />
                <line x1="10" y1="14" x2="21" y2="3" />
              </svg>
              Open in New Tab
            </a>
            <a
              href={fileUrl}
              download
              className="inline-flex items-center gap-2 px-4 py-2 bg-surface-hover hover:bg-surface-active rounded-lg text-sm text-txt-primary transition-colors"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              Download
            </a>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 pt-4 border-t border-surface-border">
        <button
          onClick={handleReplace}
          disabled={isActionPending}
          className="px-4 py-2 bg-surface-hover hover:bg-surface-active rounded-lg text-sm text-txt-primary transition-colors disabled:opacity-50"
          data-action-id="document.replace"
        >
          Replace Document
        </button>
        <button
          onClick={handleArchive}
          disabled={isActionPending || status === 'archived'}
          className="px-4 py-2 bg-surface-hover hover:bg-surface-active rounded-lg text-sm text-txt-primary transition-colors disabled:opacity-50"
          data-action-id="document.archive"
        >
          {isActionPending ? 'Archiving...' : 'Archive'}
        </button>
      </div>
    </div>
  );
}

// Main page content
function DocumentDetailPageContent() {
  const router = useRouter();
  const params = useParams();
  const { session } = useAuth();
  const token = session?.access_token;

  const documentId = params.id as string;

  // Fetch document
  const {
    data: document,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['document', documentId],
    queryFn: () => fetchDocumentDetail(documentId, token || ''),
    enabled: !!documentId && !!token,
    staleTime: 30000,
    retry: 1,
  });

  // Handle back navigation
  const handleBack = React.useCallback(() => {
    router.back();
  }, [router]);

  // Handle close (go to list)
  const handleClose = React.useCallback(() => {
    router.push('/documents');
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
  const payload = document?.payload as Record<string, unknown> | undefined;
  const title = (document?.title || payload?.title || 'Document') as string;
  const documentType = (document?.document_type || payload?.document_type) as string | undefined;

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
  } else if (!document) {
    content = <NotFoundState />;
  } else {
    content = (
      <DocumentContent
        data={document}
        onBack={handleBack}
        onNavigate={handleNavigate}
        onRefresh={handleRefresh}
      />
    );
  }

  return (
    <RouteLayout
      pageTitle={documentType ? `${formatDocumentType(documentType)} - ${title}` : title}
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
            <p className="text-xs text-txt-tertiary uppercase tracking-wider">Document</p>
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
export default function DocumentDetailPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense fallback={<LoadingState />}>
        <DocumentDetailPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
