'use client';

/**
 * Documents List Page - /documents
 *
 * Tier 1 fragmented route for documents.
 * Displays a list of documents with the ability to select and view details.
 *
 * @see REQUIREMENTS_TABLE.md - T1-DOC-01
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

// Document list item type
interface DocumentListItem {
  id: string;
  title: string;
  document_type: string;
  file_url: string;
  uploaded_at: string;
  expiry_date?: string;
  status: 'active' | 'expired' | 'archived';
}

// Fetch documents from API
async function fetchDocuments(yachtId: string, token: string): Promise<DocumentListItem[]> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai';
  const response = await fetch(`${baseUrl}/v1/documents?yacht_id=${yachtId}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch documents: ${response.status}`);
  }

  const data = await response.json();
  return data.documents || data.items || data || [];
}

// Fetch single document detail
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

// Document List Item Component
function DocumentRow({
  item,
  isSelected,
  onClick,
}: {
  item: DocumentListItem;
  isSelected: boolean;
  onClick: () => void;
}) {
  const isExpiringSoon = React.useMemo(() => {
    if (!item.expiry_date) return false;
    const expiryDate = new Date(item.expiry_date);
    const today = new Date();
    const daysUntilExpiry = Math.ceil((expiryDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
    return daysUntilExpiry > 0 && daysUntilExpiry <= 30;
  }, [item.expiry_date]);

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
            <span className="text-xs text-txt-tertiary font-mono">
              {formatDocumentType(item.document_type)}
            </span>
            <StatusPill status={getStatusColor(item.status)} label={item.status} />
            {isExpiringSoon && (
              <StatusPill status="warning" label="Expiring Soon" />
            )}
          </div>
          <h3 className="text-sm font-medium text-txt-primary truncate">{item.title}</h3>
          {item.expiry_date && (
            <p className="text-xs text-txt-tertiary mt-1">
              Expires: {new Date(item.expiry_date).toLocaleDateString()}
            </p>
          )}
        </div>
        <div className="text-xs text-txt-tertiary whitespace-nowrap">
          {new Date(item.uploaded_at).toLocaleDateString()}
        </div>
      </div>
    </button>
  );
}

// Empty state component
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="w-16 h-16 rounded-full bg-surface-hover flex items-center justify-center mb-4">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-txt-tertiary">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
          <polyline points="10 9 9 9 8 9" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-txt-primary mb-2">No Documents</h3>
      <p className="text-sm text-txt-secondary max-w-sm">
        Upload documents to track certificates, permits, and other important files.
      </p>
    </div>
  );
}

// Loading state component
function LoadingState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-txt-tertiary border-t-txt-primary rounded-full animate-spin" />
        <p className="text-sm text-txt-secondary">Loading documents...</p>
      </div>
    </div>
  );
}

// Document detail content
function DocumentDetailContent({
  data,
  onBack,
  onClose,
}: {
  data: Record<string, unknown>;
  onBack: () => void;
  onClose: () => void;
}) {
  const title = (data?.title || 'Document') as string;
  const documentType = data?.document_type as string;
  const status = data?.status as string;
  const fileUrl = data?.file_url as string;
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
          <p className="text-xs text-txt-tertiary">{formatDocumentType(documentType || '')}</p>
          <h2 className="text-lg font-semibold text-txt-primary">{title}</h2>
        </div>
      </div>
      <div className="flex gap-2">
        <StatusPill status={getStatusColor(status || '')} label={status || ''} />
      </div>
      {expiryDate && (
        <p className="text-sm text-txt-secondary">
          Expires: {new Date(expiryDate).toLocaleDateString()}
        </p>
      )}
      {fileUrl && (
        <a
          href={fileUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 px-4 py-2 bg-surface-hover hover:bg-surface-active rounded-lg text-sm text-txt-primary transition-colors"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          Download Document
        </a>
      )}
    </div>
  );
}

// Main page component
function DocumentsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, session } = useAuth();
  const token = session?.access_token;

  // Get selected ID from URL params
  const selectedId = searchParams.get('id');

  // Fetch documents list
  const {
    data: documents,
    isLoading: isLoadingList,
    error: listError,
    refetch: refetchList,
  } = useQuery({
    queryKey: ['documents', user?.yachtId],
    queryFn: () => fetchDocuments(user?.yachtId || '', token || ''),
    enabled: !!user?.yachtId && !!token,
    staleTime: 30000,
  });

  // Fetch selected document detail
  const {
    data: selectedDocument,
    isLoading: isLoadingDetail,
    refetch: refetchDetail,
  } = useQuery({
    queryKey: ['document', selectedId],
    queryFn: () => fetchDocumentDetail(selectedId!, token || ''),
    enabled: !!selectedId && !!token,
    staleTime: 30000,
  });

  // Handle document selection
  const handleSelect = React.useCallback(
    (id: string) => {
      router.push(`/documents?id=${id}`, { scroll: false });
    },
    [router]
  );

  // Handle close detail panel
  const handleCloseDetail = React.useCallback(() => {
    router.push('/documents', { scroll: false });
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
          <p className="text-status-critical">Failed to load documents</p>
        </div>
      );
    }

    if (!documents || documents.length === 0) {
      return <EmptyState />;
    }

    return (
      <div className="divide-y divide-surface-border">
        {documents.map((doc) => (
          <DocumentRow
            key={doc.id}
            item={doc}
            isSelected={doc.id === selectedId}
            onClick={() => handleSelect(doc.id)}
          />
        ))}
      </div>
    );
  }, [documents, isLoadingList, listError, selectedId, handleSelect]);

  return (
    <RouteLayout
      pageTitle="Documents"
      showTopNav={true}
      topNavContent={
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-semibold text-txt-primary">Documents</h1>
        </div>
      }
      primaryPanel={
        selectedId
          ? {
              visible: true,
              title: selectedDocument?.title as string || 'Document',
              subtitle: selectedDocument?.document_type
                ? formatDocumentType(selectedDocument.document_type as string)
                : undefined,
              children: isLoadingDetail ? (
                <LoadingState />
              ) : selectedDocument ? (
                <DocumentDetailContent
                  data={selectedDocument}
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
export default function DocumentsPage() {
  return (
    <FeatureFlagGuard>
      <React.Suspense fallback={<LoadingState />}>
        <DocumentsPageContent />
      </React.Suspense>
    </FeatureFlagGuard>
  );
}
