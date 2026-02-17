'use client';

/**
 * DocumentLens - Full-screen lens for viewing documents.
 *
 * Per UI_SPEC.md and CLAUDE.md:
 * - Fixed LensHeader (56px): back button, entity type overline, close button
 * - Title block: 28px display title (filename, NOT UUID)
 * - VitalSignsRow: 5 indicators (file type, size, uploaded, linked to, classification)
 * - NO UUID visible anywhere in the header
 * - All semantic tokens, zero raw hex values
 * - Glass transition animation via LensContainer (300ms ease-out)
 * - Body scroll locked when open
 *
 * Content Display:
 * - PDFs: iframe viewer with blob URL
 * - Images: inline display with zoom
 * - Other files: download card with file info
 *
 * Sections:
 * - LinkedEntitiesSection: what entities this doc is linked to
 * - CommentsSection: doc_metadata_comments display
 */

import * as React from 'react';
import { useEffect, useState, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { LensHeader, LensTitleBlock } from './LensHeader';
import { LensContainer } from './LensContainer';
import { VitalSignsRow, type VitalSign } from '@/components/ui/VitalSignsRow';
import { SectionContainer } from '@/components/ui/SectionContainer';
import { GhostButton } from '@/components/ui/GhostButton';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { formatRelativeTime } from '@/lib/utils';
import { formatFileSize, getDocumentIcon, getFileCategoryFromExtension } from '@/components/media/fileUtils';
import { loadDocumentWithBackend, type DocumentLoadResult } from '@/lib/documentLoader';
import { classifyDocument, getClassificationLabel, type DocumentClassification } from '@/lib/documentTypes';
import { useAuth } from '@/hooks/useAuth';

// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

export interface LinkedEntity {
  id: string;
  type: 'equipment' | 'work_order' | 'fault' | 'certificate' | 'part' | 'other';
  name: string;
  /** Optional URL to navigate to the entity lens */
  href?: string;
}

export interface DocumentComment {
  id: string;
  author: string;
  author_id?: string;
  content: string;
  created_at: string;
}

export interface DocumentLensData {
  id: string;
  /** Filename for display - NEVER show raw id UUID */
  filename: string;
  /** Optional display title override */
  title?: string;
  /** MIME type for file category detection */
  mime_type: string;
  /** File size in bytes */
  size_bytes: number;
  /** Storage path for loading via documentLoader */
  storage_path?: string;
  /** Pre-signed URL if already available */
  url?: string;
  /** Upload timestamp */
  uploaded_at: string;
  /** Uploader name */
  uploaded_by?: string;
  /** Document classification (operational vs compliance) */
  classification?: DocumentClassification;
  /** Source metadata for classification */
  source?: string;
  category?: string;
  /** Linked entities */
  linked_entities?: LinkedEntity[];
  /** Comments on the document */
  comments?: DocumentComment[];
}

export interface DocumentLensProps {
  /** The document data to render */
  document: DocumentLensData;
  /** Handler for back navigation */
  onBack?: () => void;
  /** Handler for close */
  onClose?: () => void;
  /** Additional CSS classes for the lens container */
  className?: string;
  /** Callback to refresh data after an action succeeds */
  onRefresh?: () => void;
  /** Callback when "Link to Entity" is clicked (for HOD+) */
  onLinkToEntity?: () => void;
}

// ---------------------------------------------------------------------------
// Permission helpers
// ---------------------------------------------------------------------------

/** All roles with HOD-level or above access */
const HOD_ROLES = ['chief_engineer', 'eto', 'chief_officer', 'captain', 'manager'];

export interface DocumentPermissions {
  /** Can link document to entities (HOD+) */
  canLinkToEntity: boolean;
  /** Can add comments (HOD+) */
  canAddComment: boolean;
}

/**
 * useDocumentPermissions
 *
 * Derives a set of boolean capability flags from the current user's role.
 * These are used to conditionally show (not disable) action buttons.
 */
export function useDocumentPermissions(): DocumentPermissions {
  const { user } = useAuth();
  const role = user?.role ?? '';

  return {
    canLinkToEntity: HOD_ROLES.includes(role),
    canAddComment: HOD_ROLES.includes(role),
  };
}

// ---------------------------------------------------------------------------
// File type helpers
// ---------------------------------------------------------------------------

/**
 * Get human-readable file type label from MIME type or filename.
 */
function getFileTypeLabel(mimeType: string, filename: string): string {
  const ext = filename.split('.').pop()?.toUpperCase() || '';

  // Map common MIME types to friendly names
  if (mimeType === 'application/pdf' || ext === 'PDF') return 'PDF';
  if (mimeType.startsWith('image/')) {
    if (ext === 'PNG') return 'PNG Image';
    if (ext === 'JPG' || ext === 'JPEG') return 'JPEG Image';
    if (ext === 'GIF') return 'GIF Image';
    if (ext === 'WEBP') return 'WebP Image';
    if (ext === 'HEIC') return 'HEIC Image';
    return 'Image';
  }
  if (mimeType.startsWith('video/')) return `${ext} Video`;
  if (ext === 'DOCX' || ext === 'DOC') return 'Word Document';
  if (ext === 'XLSX' || ext === 'XLS') return 'Excel Spreadsheet';
  if (ext === 'PPTX' || ext === 'PPT') return 'PowerPoint';
  if (ext === 'TXT') return 'Text File';
  if (ext === 'CSV') return 'CSV File';

  return ext || 'Document';
}

/**
 * Get display label for linked entity type.
 */
function getEntityTypeLabel(type: LinkedEntity['type']): string {
  const labels: Record<LinkedEntity['type'], string> = {
    equipment: 'Equipment',
    work_order: 'Work Order',
    fault: 'Fault',
    certificate: 'Certificate',
    part: 'Part',
    other: 'Other',
  };
  return labels[type] || 'Entity';
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** Download icon */
const DownloadIcon = () => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 16 16"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <path
      d="M8 11L8 2M8 11L5 8M8 11L11 8M2 14H14"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

/** External link icon */
const ExternalLinkIcon = () => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 16 16"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <path
      d="M6 3H3V13H13V10M9 3H13V7M13 3L7 9"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

/** Link icon */
const LinkIcon = () => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 16 16"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <path
      d="M6.5 9.5L9.5 6.5M7 11L5.5 12.5C4.4 13.6 2.6 13.6 1.5 12.5C0.4 11.4 0.4 9.6 1.5 8.5L3 7M9 5L10.5 3.5C11.6 2.4 13.4 2.4 14.5 3.5C15.6 4.6 15.6 6.4 14.5 7.5L13 9"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

/** Zoom in icon */
const ZoomInIcon = () => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 16 16"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.5" />
    <path d="M11 11L14 14M7 5V9M5 7H9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
  </svg>
);

/** Zoom out icon */
const ZoomOutIcon = () => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 16 16"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.5" />
    <path d="M11 11L14 14M5 7H9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
  </svg>
);

/**
 * PDF Viewer - iframe-based viewer for PDF files.
 */
interface PDFViewerProps {
  url: string;
  filename: string;
}

function PDFViewer({ url, filename }: PDFViewerProps) {
  return (
    <div className="w-full bg-surface-primary rounded-md overflow-hidden">
      <iframe
        src={`${url}#toolbar=1&navpanes=0&scrollbar=1`}
        title={`PDF viewer: ${filename}`}
        className="w-full h-[70vh] min-h-[500px] border-0"
        sandbox="allow-same-origin allow-scripts allow-popups"
      />
    </div>
  );
}

/**
 * Image Viewer - inline display with zoom controls.
 */
interface ImageViewerProps {
  url: string;
  filename: string;
}

function ImageViewer({ url, filename }: ImageViewerProps) {
  const [zoom, setZoom] = useState(1);
  const minZoom = 0.5;
  const maxZoom = 3;
  const zoomStep = 0.25;

  const handleZoomIn = () => {
    setZoom((prev) => Math.min(prev + zoomStep, maxZoom));
  };

  const handleZoomOut = () => {
    setZoom((prev) => Math.max(prev - zoomStep, minZoom));
  };

  const handleResetZoom = () => {
    setZoom(1);
  };

  return (
    <div className="w-full bg-surface-primary rounded-md overflow-hidden">
      {/* Zoom controls */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-surface-border">
        <div className="flex items-center gap-2">
          <button
            onClick={handleZoomOut}
            disabled={zoom <= minZoom}
            className={cn(
              'p-2 rounded-sm text-txt-secondary',
              'hover:bg-surface-hover hover:text-txt-primary',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'transition-colors duration-150'
            )}
            aria-label="Zoom out"
          >
            <ZoomOutIcon />
          </button>
          <span className="text-[13px] text-txt-secondary min-w-[48px] text-center">
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={handleZoomIn}
            disabled={zoom >= maxZoom}
            className={cn(
              'p-2 rounded-sm text-txt-secondary',
              'hover:bg-surface-hover hover:text-txt-primary',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'transition-colors duration-150'
            )}
            aria-label="Zoom in"
          >
            <ZoomInIcon />
          </button>
        </div>
        <button
          onClick={handleResetZoom}
          className={cn(
            'text-[13px] font-medium text-brand-interactive',
            'hover:text-brand-hover transition-colors'
          )}
        >
          Reset
        </button>
      </div>

      {/* Image container with scroll */}
      <div className="overflow-auto max-h-[70vh] min-h-[300px] p-4 flex items-center justify-center">
        <img
          src={url}
          alt={filename}
          style={{ transform: `scale(${zoom})`, transformOrigin: 'center center' }}
          className="max-w-full transition-transform duration-150"
        />
      </div>
    </div>
  );
}

/**
 * Download Card - for non-viewable file types.
 */
interface DownloadCardProps {
  filename: string;
  mimeType: string;
  sizeBytes: number;
  onDownload: () => void;
}

function DownloadCard({ filename, mimeType, sizeBytes, onDownload }: DownloadCardProps) {
  const icon = getDocumentIcon(filename);
  const fileType = getFileTypeLabel(mimeType, filename);
  const sizeLabel = formatFileSize(sizeBytes);

  return (
    <div
      className={cn(
        'w-full bg-surface-primary rounded-md p-6',
        'flex flex-col items-center justify-center gap-4',
        'min-h-[200px]'
      )}
    >
      {/* Large file icon */}
      <span className="text-[48px]" aria-hidden="true">
        {icon}
      </span>

      {/* File info */}
      <div className="text-center">
        <p className="text-[16px] font-medium text-txt-primary mb-1">
          {filename}
        </p>
        <p className="text-[14px] text-txt-secondary">
          {fileType} - {sizeLabel}
        </p>
      </div>

      {/* Download button */}
      <PrimaryButton onClick={onDownload}>
        <DownloadIcon />
        Download File
      </PrimaryButton>
    </div>
  );
}

/**
 * Loading state for document content.
 */
function DocumentLoadingState() {
  return (
    <div
      className={cn(
        'w-full bg-surface-primary rounded-md p-6',
        'flex flex-col items-center justify-center gap-4',
        'min-h-[200px]'
      )}
    >
      <div className="w-8 h-8 border-2 border-brand-interactive border-t-transparent rounded-full animate-spin" />
      <p className="text-[14px] text-txt-secondary">Loading document...</p>
    </div>
  );
}

/**
 * Error state for document loading.
 */
interface DocumentErrorStateProps {
  error: string;
  onRetry: () => void;
}

function DocumentErrorState({ error, onRetry }: DocumentErrorStateProps) {
  return (
    <div
      className={cn(
        'w-full bg-surface-primary rounded-md p-6',
        'flex flex-col items-center justify-center gap-4',
        'min-h-[200px]'
      )}
    >
      <span className="text-[32px]" aria-hidden="true">
        ⚠️
      </span>
      <div className="text-center">
        <p className="text-[16px] font-medium text-txt-primary mb-1">
          Failed to load document
        </p>
        <p className="text-[14px] text-txt-secondary">{error}</p>
      </div>
      <GhostButton onClick={onRetry}>Try Again</GhostButton>
    </div>
  );
}

/**
 * LinkedEntitiesSection - displays what entities this document is linked to.
 */
interface LinkedEntitiesSectionProps {
  entities: LinkedEntity[];
  stickyTop?: number;
}

function LinkedEntitiesSection({ entities, stickyTop }: LinkedEntitiesSectionProps) {
  return (
    <SectionContainer
      title="Linked Entities"
      count={entities.length}
      stickyTop={stickyTop}
    >
      {entities.length === 0 ? (
        <div className="py-8 text-center">
          <p className="text-[14px] text-txt-secondary leading-[1.6]">
            This document is not linked to any entities.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {entities.map((entity) => (
            <a
              key={entity.id}
              href={entity.href || '#'}
              className={cn(
                'flex items-center justify-between',
                'px-3 py-2 rounded-sm',
                'hover:bg-surface-hover transition-colors duration-150',
                'group'
              )}
            >
              <div className="flex items-center gap-2">
                <span className="text-[12px] text-txt-tertiary uppercase tracking-wider">
                  {getEntityTypeLabel(entity.type)}
                </span>
                <span className="text-[14px] font-medium text-txt-primary">
                  {entity.name}
                </span>
              </div>
              <svg
                className="w-4 h-4 text-txt-tertiary group-hover:text-txt-secondary"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
                aria-hidden="true"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
            </a>
          ))}
        </div>
      )}
    </SectionContainer>
  );
}

/**
 * CommentsSection - displays comments on the document.
 */
interface CommentsSectionProps {
  comments: DocumentComment[];
  canAddComment: boolean;
  onAddComment?: () => void;
  stickyTop?: number;
}

function CommentsSection({
  comments,
  canAddComment,
  onAddComment,
  stickyTop,
}: CommentsSectionProps) {
  return (
    <SectionContainer
      title="Comments"
      count={comments.length}
      action={
        canAddComment && onAddComment
          ? { label: '+ Add Comment', onClick: onAddComment }
          : undefined
      }
      stickyTop={stickyTop}
    >
      {comments.length === 0 ? (
        <div className="py-8 text-center">
          <p className="text-[14px] text-txt-secondary leading-[1.6]">
            No comments yet.
          </p>
          {canAddComment && onAddComment && (
            <GhostButton onClick={onAddComment} className="mt-3">
              + Add Comment
            </GhostButton>
          )}
        </div>
      ) : (
        <div className="-mx-4">
          {comments.map((comment) => (
            <CommentRow key={comment.id} comment={comment} />
          ))}
        </div>
      )}
    </SectionContainer>
  );
}

/**
 * Comment row component.
 */
interface CommentRowProps {
  comment: DocumentComment;
}

function CommentRow({ comment }: CommentRowProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const needsTruncation = comment.content.length > 200 || comment.content.split('\n').length > 3;

  /**
   * Format timestamp per UI_SPEC.md:
   * - Today: "Today at 14:32"
   * - Within 7 days: "3 hours ago", "Yesterday", "2 days ago"
   * - Older: "Jan 23, 2026"
   */
  const formatTimestamp = (isoString: string): string => {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      const hh = date.getHours().toString().padStart(2, '0');
      const mm = date.getMinutes().toString().padStart(2, '0');
      return `Today at ${hh}:${mm}`;
    }

    if (diffDays < 7) {
      if (diffDays === 1) return 'Yesterday';
      return `${diffDays} days ago`;
    }

    return date.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  };

  return (
    <div
      className={cn(
        'px-5 py-3 min-h-[44px]',
        'border-b border-surface-border-subtle last:border-b-0'
      )}
    >
      {/* Author + timestamp */}
      <div className="flex items-center gap-2 mb-1">
        <span className="text-[13px] font-medium text-txt-primary leading-[1.4]">
          {comment.author}
        </span>
        <span
          className="text-[12px] text-txt-tertiary leading-[1.4]"
          title={new Date(comment.created_at).toLocaleString()}
        >
          {formatTimestamp(comment.created_at)}
        </span>
      </div>

      {/* Comment content */}
      <div>
        <p
          className={cn(
            'text-[14px] font-normal text-txt-primary leading-[1.6]',
            !isExpanded && needsTruncation && 'line-clamp-3'
          )}
        >
          {comment.content}
        </p>

        {needsTruncation && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className={cn(
              'mt-1 text-[13px] font-medium text-brand-interactive',
              'hover:text-brand-hover transition-colors duration-150',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-interactive rounded-sm'
            )}
          >
            {isExpanded ? 'Show less' : 'Show more'}
          </button>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// DocumentLens component
// ---------------------------------------------------------------------------

/**
 * DocumentLens - Full-screen entity lens for documents.
 *
 * Usage:
 * ```tsx
 * <DocumentLens
 *   document={data}
 *   onBack={() => router.back()}
 *   onClose={() => router.push('/app')}
 * />
 * ```
 */
export const DocumentLens = React.forwardRef<HTMLDivElement, DocumentLensProps>(
  ({ document, onBack, onClose, className, onRefresh, onLinkToEntity }, ref) => {
    // Glass transition: lens mounts as closed then opens on first render
    const [isOpen, setIsOpen] = useState(false);

    // Document loading state
    const [loadResult, setLoadResult] = useState<DocumentLoadResult | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [loadError, setLoadError] = useState<string | null>(null);

    // Permissions
    const perms = useDocumentPermissions();

    useEffect(() => {
      // Trigger glass enter animation on mount
      setIsOpen(true);
    }, []);

    // Load document on mount
    const loadDocument = useCallback(async () => {
      setIsLoading(true);
      setLoadError(null);

      try {
        // If URL is already provided, use it directly
        if (document.url) {
          setLoadResult({
            success: true,
            url: document.url,
            metadata: {
              name: document.filename,
              size: document.size_bytes,
              mime_type: document.mime_type,
              last_modified: document.uploaded_at,
            },
          });
          setIsLoading(false);
          return;
        }

        // Load via backend
        const result = await loadDocumentWithBackend(document.id);

        if (result.success) {
          setLoadResult(result);
        } else {
          setLoadError(result.error || 'Failed to load document');
        }
      } catch (err) {
        setLoadError(err instanceof Error ? err.message : 'Unknown error loading document');
      } finally {
        setIsLoading(false);
      }
    }, [document.id, document.url, document.filename, document.size_bytes, document.mime_type, document.uploaded_at]);

    useEffect(() => {
      loadDocument();
    }, [loadDocument]);

    // Cleanup blob URL on unmount
    useEffect(() => {
      return () => {
        if (loadResult?.url && loadResult.url.startsWith('blob:')) {
          URL.revokeObjectURL(loadResult.url);
        }
      };
    }, [loadResult?.url]);

    // Derived display values
    const displayTitle = document.title || document.filename;
    const fileType = getFileTypeLabel(document.mime_type, document.filename);
    const fileCategory = getFileCategoryFromExtension(document.filename);
    const classification =
      document.classification ||
      classifyDocument(document.filename, { source: document.source, category: document.category });

    // Build the 5 vital signs
    const vitalSigns: VitalSign[] = [
      {
        label: 'Type',
        value: fileType,
      },
      {
        label: 'Size',
        value: formatFileSize(document.size_bytes),
      },
      {
        label: 'Uploaded',
        value: formatRelativeTime(document.uploaded_at),
      },
      {
        label: 'Linked to',
        value:
          document.linked_entities && document.linked_entities.length > 0
            ? document.linked_entities.length === 1
              ? getEntityTypeLabel(document.linked_entities[0].type)
              : `${document.linked_entities.length} entities`
            : 'None',
      },
      {
        label: 'Classification',
        value: getClassificationLabel(classification),
        color: classification === 'compliance' ? 'neutral' : undefined,
      },
    ];

    // Section data (safe fallbacks)
    const linkedEntities = document.linked_entities ?? [];
    const comments = document.comments ?? [];

    // Handle download
    const handleDownload = useCallback(() => {
      if (!loadResult?.url) return;

      const link = window.document.createElement('a');
      link.href = loadResult.url;
      link.download = document.filename;
      window.document.body.appendChild(link);
      link.click();
      window.document.body.removeChild(link);
    }, [loadResult?.url, document.filename]);

    // Handle view in new tab
    const handleViewInNewTab = useCallback(() => {
      if (!loadResult?.url) return;
      window.open(loadResult.url, '_blank');
    }, [loadResult?.url]);

    // Handle close with exit animation
    const handleClose = useCallback(() => {
      setIsOpen(false);
      if (onClose) {
        setTimeout(onClose, 210);
      }
    }, [onClose]);

    const handleBack = useCallback(() => {
      if (onBack) {
        onBack();
      } else {
        handleClose();
      }
    }, [onBack, handleClose]);

    // Render document content based on file type
    const renderDocumentContent = () => {
      if (isLoading) {
        return <DocumentLoadingState />;
      }

      if (loadError || !loadResult?.url) {
        return <DocumentErrorState error={loadError || 'Document URL not available'} onRetry={loadDocument} />;
      }

      // PDF viewer
      if (document.mime_type === 'application/pdf' || document.filename.toLowerCase().endsWith('.pdf')) {
        return <PDFViewer url={loadResult.url} filename={document.filename} />;
      }

      // Image viewer
      if (fileCategory === 'image') {
        return <ImageViewer url={loadResult.url} filename={document.filename} />;
      }

      // Download card for other files
      return (
        <DownloadCard
          filename={document.filename}
          mimeType={document.mime_type}
          sizeBytes={document.size_bytes}
          onDownload={handleDownload}
        />
      );
    };

    return (
      <LensContainer
        ref={ref}
        isOpen={isOpen}
        onClose={handleClose}
        className={className}
      >
        {/* Fixed navigation header - 56px, at z-header */}
        <LensHeader
          entityType="Document"
          title={displayTitle}
          onBack={handleBack}
          onClose={handleClose}
        />

        {/* Main content - padded top to clear fixed header (56px = h-14) */}
        <main
          className={cn(
            'pt-14',
            'px-10 md:px-6 sm:px-4',
            'max-w-[800px] mx-auto',
            'pb-12'
          )}
        >
          {/* Title block */}
          <div className="mt-6">
            <LensTitleBlock
              title={displayTitle}
              subtitle={document.uploaded_by ? `Uploaded by ${document.uploaded_by}` : undefined}
            />
          </div>

          {/* Vital Signs Row */}
          <div className="mt-3">
            <VitalSignsRow signs={vitalSigns} />
          </div>

          {/* Action buttons */}
          <div className="mt-4 flex items-center gap-2 flex-wrap">
            <PrimaryButton
              onClick={handleDownload}
              disabled={isLoading || !!loadError}
              className="text-[13px] min-h-[36px] px-4 py-2"
            >
              <DownloadIcon />
              Download
            </PrimaryButton>

            <GhostButton
              onClick={handleViewInNewTab}
              disabled={isLoading || !!loadError}
              className="text-[13px] min-h-[36px] px-4 py-2"
            >
              <ExternalLinkIcon />
              View in New Tab
            </GhostButton>

            {perms.canLinkToEntity && onLinkToEntity && (
              <GhostButton
                onClick={onLinkToEntity}
                className="text-[13px] min-h-[36px] px-4 py-2"
              >
                <LinkIcon />
                Link to Entity
              </GhostButton>
            )}
          </div>

          {/* Section divider */}
          <div
            className="mt-6 border-t border-surface-border"
            aria-hidden="true"
          />

          {/* Document content */}
          <div className="mt-6">{renderDocumentContent()}</div>

          {/* Linked Entities Section */}
          <div className="mt-6">
            <LinkedEntitiesSection entities={linkedEntities} stickyTop={56} />
          </div>

          {/* Comments Section */}
          <div className="mt-6">
            <CommentsSection
              comments={comments}
              canAddComment={perms.canAddComment}
              onAddComment={() => {
                // TODO: Implement add comment modal
                console.log('Add comment clicked');
              }}
              stickyTop={56}
            />
          </div>
        </main>
      </LensContainer>
    );
  }
);

DocumentLens.displayName = 'DocumentLens';

export default DocumentLens;
